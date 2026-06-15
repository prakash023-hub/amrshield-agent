"""
AMRShield - Self-Audit Agent
Runs Phoenix MCP safety tools, then Gemini 2.5 Flash synthesis on Vertex AI.
"""

import os
import json
import re
import time
from datetime import datetime

from google import genai
from google.genai import types

from mcp_tools.phoenix_integration import (
    ensure_phoenix_tracing,
    get_current_trace_id,
    merge_mcp_into_audit,
    record_audit_to_store,
    run_phoenix_mcp_audit_pipeline,
    get_audit_traces,
)
from mcp_tools.audit_store import audit_stats
from mcp_tools.pharmaguard_trust import run_pharmaguard_pipeline, verify_chain_integrity

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "project-d52ffa3b-95bb-4dfb-af0")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
AUDIT_MODEL = "publishers/google/models/gemini-2.5-flash"

AUDIT_PROMPT = """You are a clinical pharmacist safety auditor for an AI antibiotic stewardship system.

Phoenix MCP tools already ran these checks:
MCP HALLUCINATION: {hallucination}
MCP ACCURACY: {accuracy}

Review this antibiotic recommendation and return ONLY a JSON object (no markdown, no extra text):

RECOMMENDATION: {recommendation}
PATIENT: {patient}

Check these 4 things:
1. HALLUCINATION — any absolutist language like "always", "never", "100% effective", "guaranteed"?
2. ALLERGY CONFLICT — does the antibiotic conflict with patient allergies?
3. RENAL DOSING — if CrCl < 30, are renally-cleared drugs avoided/adjusted?
4. GUIDELINE ADHERENCE — is WHO AWaRe tier appropriate for this indication?

Return ONLY this JSON:
{{
  "overall_result": "PASS",
  "issues_found": [],
  "severity_level": "LOW",
  "recommendation_safe_to_proceed": true,
  "physician_review_required": false,
  "audit_reasoning": "Brief explanation in one sentence"
}}

Use "FLAG" if medium issues, "HOLD" if critical issues (allergy conflict, dangerous dosing).
"""


def run_audit_agent(recommendation: dict, patient_profile: dict) -> dict:
    """Run Self-Audit Agent — Phoenix MCP tools first, then Gemini review."""
    started = time.perf_counter()
    ensure_phoenix_tracing()

    trace_id = recommendation.get("trace_id") or get_current_trace_id()
    mcp_pipeline = run_phoenix_mcp_audit_pipeline(recommendation, patient_profile, trace_id)

    try:
        prompt = AUDIT_PROMPT.format(
            hallucination=json.dumps(mcp_pipeline["hallucination_check"]),
            accuracy=json.dumps(mcp_pipeline["accuracy_check"]),
            recommendation=json.dumps({
                "antibiotic": recommendation.get("antibiotic", ""),
                "dose": recommendation.get("dose", ""),
                "aware_tier": recommendation.get("aware_tier", ""),
                "drug_class": recommendation.get("drug_class", ""),
                "confidence_score": recommendation.get("confidence_score", 0),
                "rationale": str(recommendation.get("rationale", ""))[:300],
            }),
            patient=json.dumps({
                "age": patient_profile.get("age", ""),
                "sex": patient_profile.get("sex", ""),
                "crcl": patient_profile.get("serum_creatinine", ""),
                "allergies": patient_profile.get("allergies", []),
                "medications": patient_profile.get("current_medications", []),
                "diagnosis": patient_profile.get("diagnosis", ""),
            }),
        )

        response = client.models.generate_content(
            model=AUDIT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=500,
            ),
        )

        text = response.text.strip()
        text = re.sub(r"```json|```", "", text).strip()
        gemini_audit = json.loads(text)
        audit_result = merge_mcp_into_audit(gemini_audit, mcp_pipeline)

    except json.JSONDecodeError:
        audit_result = _rule_based_audit(recommendation, patient_profile, mcp_pipeline)
        audit_result["audit_reasoning"] += " (JSON parse fallback)"
    except Exception:
        audit_result = _rule_based_audit(recommendation, patient_profile, mcp_pipeline)

    latency_ms = int((time.perf_counter() - started) * 1000)
    audit_result["audit_id"] = f"AUDIT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    audit_result["latency_ms"] = latency_ms
    record_audit_to_store(recommendation, patient_profile, audit_result, latency_ms)

    try:
        pg = run_pharmaguard_pipeline(
            patient_profile,
            event_type="AUDIT_COMPLETE",
            recommendation=recommendation,
            audit_result=audit_result,
        )
        audit_result["pharmaguard"] = {
            "wallet_id": pg.get("wallet", {}).get("wallet_id"),
            "chain_valid": pg.get("chain_valid"),
            "tools": pg.get("pharmaguard_tools", []),
            "audit_block_id": pg.get("audit_block", {}).get("block_id"),
        }
    except Exception:
        pass

    return audit_result


def _rule_based_audit(recommendation: dict, patient_profile: dict, mcp_pipeline: dict | None = None) -> dict:
    """Rule-based safety checks as fallback — still merges MCP results when available."""
    issues = []
    score = 1.0

    allergies = [a.lower() for a in patient_profile.get("allergies", [])]
    drug_class = recommendation.get("drug_class", "").lower()
    antibiotic = recommendation.get("antibiotic", "").lower()

    if "penicillin" in allergies and ("penicillin" in drug_class or "amoxicillin" in antibiotic or "ampicillin" in antibiotic):
        issues.append({"type": "ALLERGY_CONFLICT", "severity": "CRITICAL", "message": "Penicillin allergy conflict"})
        score = 0.0

    if "cephalosporins" in allergies and "cephalosporin" in drug_class:
        issues.append({"type": "ALLERGY_CONFLICT", "severity": "CRITICAL", "message": "Cephalosporin allergy conflict"})
        score = 0.0

    serum_cr = patient_profile.get("serum_creatinine", 1.0)
    age = patient_profile.get("age", 50)
    weight = patient_profile.get("weight", 70)
    sex = patient_profile.get("sex", "male")
    sex_factor = 1.0 if sex == "male" else 0.85
    crcl = ((140 - age) * weight * sex_factor) / (72 * serum_cr) if serum_cr > 0 else 90

    renally_cleared = ["nitrofurantoin", "vancomycin", "ciprofloxacin", "gentamicin", "meropenem"]
    if crcl < 30 and any(d in antibiotic for d in renally_cleared):
        issues.append({"type": "RENAL_DOSE_ADJUSTMENT", "severity": "HIGH", "message": f"CrCl {crcl:.0f} mL/min — dose adjustment required"})
        score -= 0.3

    meds = [m.lower() for m in patient_profile.get("current_medications", [])]
    if "warfarin" in meds and "ciprofloxacin" in antibiotic:
        issues.append({"type": "DRUG_INTERACTION", "severity": "HIGH", "message": "Ciprofloxacin + warfarin — INR monitoring required"})
        score -= 0.2

    if "warfarin" in meds and "metronidazole" in antibiotic:
        issues.append({"type": "DRUG_INTERACTION", "severity": "HIGH", "message": "Metronidazole + warfarin — potentiates anticoagulation"})
        score -= 0.2

    score = max(0.0, score)
    result = "HOLD" if score == 0.0 else ("FLAG" if issues else "PASS")
    severity = "CRITICAL" if score == 0.0 else ("HIGH" if any(i["severity"] == "HIGH" for i in issues) else ("MEDIUM" if issues else "LOW"))

    base = {
        "overall_result": result,
        "issues_found": issues,
        "severity_level": severity,
        "recommendation_safe_to_proceed": score > 0.5,
        "physician_review_required": score < 0.8,
        "audit_reasoning": f"Rule-based audit: {len(issues)} issue(s) found. CrCl≈{crcl:.0f} mL/min." if issues else f"Rule-based audit passed. CrCl≈{crcl:.0f} mL/min. No conflicts detected.",
    }

    if mcp_pipeline:
        return merge_mcp_into_audit(base, mcp_pipeline)
    return base


def run_batch_audit(n_recent_traces: int = 20) -> dict:
    """Fetch recent audit decisions for Audit Console / API."""
    rows = get_audit_traces(limit=n_recent_traces)
    stats = audit_stats()
    return {
        "batch_audit_timestamp": datetime.utcnow().isoformat(),
        "traces_audited": len(rows),
        "traces": rows,
        "stats": stats,
        "source": "phoenix_mcp_and_audit_store" if rows else "empty",
    }
