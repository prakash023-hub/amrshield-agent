"""
AMRShield - Self-Audit Agent
Runs Phoenix MCP safety tools, then Gemini 2.5 Flash synthesis on Vertex AI.
"""

import os
import json
import time
from datetime import datetime

from google import genai
from google.genai import types

from mcp_tools.phoenix_integration import (
    get_current_trace_id,
    invoke_mcp_tool,
    merge_mcp_into_audit,
    record_audit_to_store,
    run_phoenix_mcp_audit_pipeline,
    get_audit_traces,
)
from mcp_tools.audit_store import audit_stats
from mcp_tools.pharmaguard_trust import run_pharmaguard_pipeline

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "project-d52ffa3b-95bb-4dfb-af0")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")

client = genai.Client(
    vertexai=True, project=PROJECT_ID, location=LOCATION,
    http_options=types.HttpOptions(timeout=15_000),
)
AUDIT_MODEL = "publishers/google/models/gemini-2.5-flash"

AUDIT_PROMPT = """You are a clinical pharmacist safety auditor for an AI antibiotic stewardship system.

Phoenix MCP tools already ran these checks:
MCP HALLUCINATION: {hallucination}
MCP ACCURACY: {accuracy}

Review this antibiotic recommendation and return ONLY a JSON object (no markdown, no extra text):

RECOMMENDATION: {recommendation}
PATIENT: {patient}

Check these 4 things:
1. HALLUCINATION — is every concrete claim (drug, AWaRe tier, CrCl, interaction/allergy statements) supported by the MCP grounding results above? Treat unsupported claims as issues; absolutist language ("always", "guaranteed") is a minor style issue only.
2. ALLERGY CONFLICT — does the antibiotic conflict with patient allergies?
3. RENAL DOSING — use the supplied Cockcroft-Gault estimate in mL/min. Review the proposed regimen against the deterministic renal findings.
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


def _parse_gemini_audit(text: str) -> dict:
    text = text.strip()
    if text.startswith(("```json\n", "```\n")) and text.endswith("```"):
        text = text.split("\n", 1)[1][:-3]

    def unique_fields(pairs):
        result = dict(pairs)
        if len(result) != len(pairs):
            raise ValueError("Duplicate fields in Gemini audit response.")
        return result

    audit = json.loads(text, object_pairs_hook=unique_fields)
    severities = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    if (
        not isinstance(audit, dict)
        or audit.get("overall_result") not in ("PASS", "FLAG", "HOLD")
        or audit.get("severity_level") not in severities
        or type(audit.get("recommendation_safe_to_proceed")) is not bool
        or type(audit.get("physician_review_required")) is not bool
        or not isinstance(audit.get("audit_reasoning"), str)
        or not audit["audit_reasoning"].strip()
        or not isinstance(audit.get("issues_found"), list)
        or any(
            not isinstance(issue, dict)
            or issue.get("severity") not in severities
            or any(not isinstance(issue.get(key), str) or not issue[key].strip()
                   for key in ("type", "message"))
            for issue in audit["issues_found"]
        )
    ):
        raise ValueError("Invalid Gemini audit response.")
    return audit


def run_audit_agent(recommendation: dict, patient_profile: dict) -> dict:
    """Run deterministic Phoenix safety checks before any Gemini assessment."""
    started = time.perf_counter()
    trace_id = recommendation.get("trace_id") or get_current_trace_id()
    try:
        mcp_pipeline = run_phoenix_mcp_audit_pipeline(recommendation, patient_profile, trace_id)
    except Exception:
        mcp_pipeline = {
            "trace_id": trace_id,
            "hallucination_check": {"status": "error"},
            "accuracy_check": {"status": "error"},
        }

    # A neutral verdict lets the deterministic findings set the minimum result.
    base = {
        "overall_result": "PASS",
        "issues_found": [],
        "severity_level": "LOW",
        "recommendation_safe_to_proceed": True,
        "physician_review_required": False,
        "audit_reasoning": "",
    }
    audit_result = merge_mcp_into_audit(base, mcp_pipeline)
    if audit_result["overall_result"] != "HOLD":
        try:
            prompt = AUDIT_PROMPT.format(
                hallucination=json.dumps(mcp_pipeline["hallucination_check"]),
                accuracy=json.dumps(mcp_pipeline["accuracy_check"]),
                recommendation=json.dumps({
                    key: recommendation.get(key)
                    for key in ("antibiotic", "dose", "route", "frequency", "duration_days",
                                "aware_tier", "drug_class", "confidence_score")
                }),
                patient=json.dumps({
                    "age": patient_profile["age"],
                    "sex": patient_profile["sex"],
                    "weight_kg": patient_profile["weight"],
                    "serum_creatinine_mg_dl": patient_profile["serum_creatinine"],
                    "estimated_crcl_ml_min": mcp_pipeline["accuracy_check"]["crcl_ml_min"],
                    "allergies": patient_profile.get("allergies"),
                    "medications": patient_profile.get("current_medications"),
                    "diagnosis": patient_profile.get("diagnosis"),
                }),
            )
            response = client.models.generate_content(
                model=AUDIT_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1, max_output_tokens=500, response_mime_type="application/json",
                ),
            )
            base = _parse_gemini_audit(response.text)
        except Exception:
            message = "Gemini safety assessment was unavailable or invalid. Physician review required."
            base.update(overall_result="HOLD", audit_reasoning=message, issues_found=[
                {"type": "GEMINI_AUDIT_UNAVAILABLE", "severity": "HIGH", "message": message}
            ])
        audit_result = merge_mcp_into_audit(base, mcp_pipeline)

    if (audit_result["physician_review_required"]
            and "flag_for_review" not in audit_result["phoenix_mcp_tools"]):
        review = invoke_mcp_tool(
            "flag_for_review", trace_id=trace_id,
            reason="Self-audit requires physician review.",
            severity=audit_result["severity_level"],
            recommendation={"antibiotic": recommendation.get("antibiotic")},
        )
        audit_result["phoenix_mcp_tools"].append("flag_for_review")
        if review.get("status") == "PENDING_PHYSICIAN_REVIEW":
            audit_result["review_hold"] = review
            audit_result["audit_reasoning"] += f" Review reference: {review['review_id']}."

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
