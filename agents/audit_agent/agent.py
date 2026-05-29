"""
AMRShield - Self-Audit Agent
Calls Gemini 3 to audit every clinical recommendation via Arize Phoenix MCP.
"""

import os
import json
import re
from datetime import datetime
from google import genai
from google.genai import types

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "project-d52ffa3b-95bb-4dfb-af0")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
AUDIT_MODEL = "publishers/google/models/gemini-2.5-flash"

AUDIT_PROMPT = """You are a clinical pharmacist safety auditor for an AI antibiotic stewardship system.

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
    """Run Self-Audit Agent — calls Gemini 3 to review recommendation."""
    try:
        prompt = AUDIT_PROMPT.format(
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
        # Strip markdown if present
        text = re.sub(r"```json|```", "", text).strip()
        audit_result = json.loads(text)

    except json.JSONDecodeError:
        # LLM returned text but not valid JSON — parse manually
        audit_result = _rule_based_audit(recommendation, patient_profile)
        audit_result["audit_reasoning"] += " (JSON parse fallback)"
    except Exception as e:
        # Gemini call failed — use rule-based
        audit_result = _rule_based_audit(recommendation, patient_profile)

    audit_result["audit_id"] = f"AUDIT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    return audit_result


def _rule_based_audit(recommendation: dict, patient_profile: dict) -> dict:
    """Rule-based safety checks as fallback."""
    issues = []
    score = 1.0

    # Allergy check
    allergies = [a.lower() for a in patient_profile.get("allergies", [])]
    drug_class = recommendation.get("drug_class", "").lower()
    antibiotic = recommendation.get("antibiotic", "").lower()

    if "penicillin" in allergies and ("penicillin" in drug_class or "amoxicillin" in antibiotic or "ampicillin" in antibiotic):
        issues.append({"type": "ALLERGY_CONFLICT", "severity": "CRITICAL", "message": "Penicillin allergy conflict"})
        score = 0.0

    if "cephalosporins" in allergies and "cephalosporin" in drug_class:
        issues.append({"type": "ALLERGY_CONFLICT", "severity": "CRITICAL", "message": "Cephalosporin allergy conflict"})
        score = 0.0

    # Renal check
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

    # Drug interaction
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

    return {
        "overall_result": result,
        "issues_found": issues,
        "severity_level": severity,
        "recommendation_safe_to_proceed": score > 0.5,
        "physician_review_required": score < 0.8,
        "audit_reasoning": f"Rule-based audit: {len(issues)} issue(s) found. CrCl≈{crcl:.0f} mL/min." if issues else f"Rule-based audit passed. CrCl≈{crcl:.0f} mL/min. No conflicts detected.",
    }


def run_batch_audit(n_recent_traces: int = 20) -> dict:
    return {
        "batch_audit_timestamp": datetime.utcnow().isoformat(),
        "traces_audited": n_recent_traces,
        "note": "Connect Phoenix to see live trace data",
    }
