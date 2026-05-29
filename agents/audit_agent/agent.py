"""
AMRShield - Self-Audit Agent
Uses google.genai SDK with Vertex AI ADC auth.
THE KEY DIFFERENTIATOR: An agent that audits other agents in real-time.
"""

import os
import json
from datetime import datetime
from google import genai
from google.genai import types
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from mcp_tools.phoenix_integration import (
    fetch_phoenix_traces,
    detect_hallucination,
    evaluate_clinical_accuracy,
    flag_for_review,
    run_phoenix_experiment,
    PROJECTS,
)

# ─────────────────────────────────────────────
# Client setup
# ─────────────────────────────────────────────

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "project-d52ffa3b-95bb-4dfb-af0")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

# Use gemini-3 for audit — needs stronger reasoning
AUDIT_MODEL = "publishers/google/models/gemini-3-flash-preview"

# ─────────────────────────────────────────────
# Audit System Prompt
# ─────────────────────────────────────────────

AUDIT_SYSTEM_PROMPT = """You are AMRShield's Self-Audit Agent — an AI safety monitor.

Your mission: Ensure every antibiotic recommendation is safe, accurate, and follows guidelines BEFORE it reaches a clinician.

Audit checklist:
1. Hallucination Detection — Any absolutist/unsupported claims?
2. Safety Checks — Allergy conflicts? Renal dosing? Drug interactions?
3. Guideline Adherence — Follows WHO AWaRe, IDSA, CDC NHSN?
4. Confidence Calibration — Is confidence score realistic?

Return ONLY this JSON:
{
  "audit_id": "<ID>",
  "overall_result": "PASS" or "FLAG" or "HOLD",
  "issues_found": [],
  "severity_level": "LOW or MEDIUM or HIGH or CRITICAL",
  "recommendation_safe_to_proceed": true or false,
  "physician_review_required": true or false,
  "audit_reasoning": "<explanation>"
}
"""

# ─────────────────────────────────────────────
# Tool dispatcher
# ─────────────────────────────────────────────

AUDIT_TOOL_MAP = {
    "fetch_phoenix_traces": fetch_phoenix_traces,
    "detect_hallucination": detect_hallucination,
    "evaluate_clinical_accuracy": evaluate_clinical_accuracy,
    "flag_for_review": flag_for_review,
    "run_phoenix_experiment": run_phoenix_experiment,
}

def dispatch_audit_tool(name: str, args: dict) -> str:
    if name not in AUDIT_TOOL_MAP:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        return json.dumps(AUDIT_TOOL_MAP[name](**args))
    except Exception as e:
        return json.dumps({"error": str(e)})


# ─────────────────────────────────────────────
# Main Audit Function
# ─────────────────────────────────────────────

def run_audit_agent(recommendation: dict, patient_profile: dict) -> dict:
    """
    Run the Self-Audit Agent against a clinical recommendation.
    Returns audit result with PASS/FLAG/HOLD decision.
    """

    audit_prompt = f"""
Audit this clinical recommendation from AMRShield Clinical Agent:

RECOMMENDATION:
{json.dumps(recommendation, indent=2)}

PATIENT:
{json.dumps(patient_profile, indent=2)}

Run your 4 audit checks and return your JSON verdict.
"""

    config = types.GenerateContentConfig(
        system_instruction=AUDIT_SYSTEM_PROMPT,
    )

    try:
        response = client.models.generate_content(
            model=AUDIT_MODEL,
            contents=audit_prompt,
            config=config,
        )

        final_text = response.text
        try:
            import re
            json_match = re.search(r"\{[\s\S]*\}", final_text)
            audit_result = json.loads(json_match.group()) if json_match else {"raw": final_text}
        except Exception:
            audit_result = {"raw": final_text}

    except Exception as e:
        # Fallback audit if model call fails
        audit_result = _fallback_audit(recommendation, patient_profile)

    audit_result["audit_id"] = f"AUDIT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    return audit_result


def _fallback_audit(recommendation: dict, patient_profile: dict) -> dict:
    """Rule-based fallback audit when LLM is unavailable."""
    issues = []
    score = 1.0

    # Allergy check
    allergies = patient_profile.get("allergies", [])
    drug_class = recommendation.get("drug_class", "")
    if "penicillin" in allergies and "penicillin" in drug_class.lower():
        issues.append({"type": "ALLERGY_CONFLICT", "severity": "CRITICAL"})
        score = 0.0

    # Confidence check
    if recommendation.get("confidence_score", 1.0) > 0.95:
        issues.append({"type": "OVERCONFIDENCE", "severity": "LOW"})
        score -= 0.1

    result = "HOLD" if score == 0.0 else ("FLAG" if issues else "PASS")

    return {
        "overall_result": result,
        "issues_found": issues,
        "severity_level": "CRITICAL" if score == 0.0 else ("MEDIUM" if issues else "LOW"),
        "recommendation_safe_to_proceed": score > 0.5,
        "physician_review_required": score < 0.8,
        "audit_reasoning": "Rule-based fallback audit (LLM unavailable)",
    }


def run_batch_audit(n_recent_traces: int = 20) -> dict:
    """Batch audit for Stewardship dashboard."""
    return {
        "batch_audit_timestamp": datetime.utcnow().isoformat(),
        "traces_audited": n_recent_traces,
        "note": "Connect Phoenix to see live trace data",
    }


if __name__ == "__main__":
    test_rec = {
        "antibiotic": "ciprofloxacin",
        "dose": "500mg",
        "route": "PO",
        "aware_tier": "Watch",
        "drug_class": "Fluoroquinolone",
        "confidence_score": 0.78,
        "trace_id": "TEST-001",
    }
    test_patient = {
        "patient_id": "TEST-001",
        "age": 68, "sex": "female",
        "allergies": [],
        "current_medications": ["warfarin"],
        "diagnosis": "UTI",
    }
    print("Running audit test...")
    result = run_audit_agent(test_rec, test_patient)
    print(json.dumps(result, indent=2))
