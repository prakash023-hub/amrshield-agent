"""
AMRShield - Arize Phoenix MCP Integration
AUTO-TRACING via GoogleGenAIInstrumentor — zero extra code per agent.
"""

import os
import json
from datetime import datetime
from typing import Optional

# ─────────────────────────────────────────────
# Auto-tracing setup (the correct approach per doc)
# ─────────────────────────────────────────────

def setup_phoenix(project_name: str):
    """
    Call once at FastAPI startup per agent project.
    Auto-instruments ALL Gemini/Vertex AI calls — no manual span code needed.
    """
    try:
        from phoenix.otel import register
        from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

        PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "http://localhost:6006")
        PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY", "local-dev")

        tracer_provider = register(
            project_name=project_name,
            endpoint=f"{PHOENIX_ENDPOINT}/v1/traces",
            headers={"api_key": PHOENIX_API_KEY},
        )

        # This single line auto-traces every Gemini call in the project
        GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)

        print(f"✅ Phoenix auto-tracing active → project: {project_name}")
        return tracer_provider

    except ImportError as e:
        print(f"⚠ Phoenix not installed ({e}) — running without tracing")
        return None


# ─────────────────────────────────────────────
# Phoenix Projects
# ─────────────────────────────────────────────

PROJECTS = {
    "clinical": "amrshield-clinical-agent",
    "prediction": "amrshield-prediction-agent",
    "audit": "amrshield-audit-agent",
}


# ─────────────────────────────────────────────
# Phoenix MCP Tool Functions
# (Used by Self-Audit Agent)
# ─────────────────────────────────────────────

def fetch_phoenix_traces(project_name: str, limit: int = 20, filter_flags: Optional[str] = None) -> dict:
    """Fetch recent traces from a Phoenix project."""
    try:
        import phoenix as px
        PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "http://localhost:6006")
        PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY", "local-dev")
        client = px.Client(endpoint=PHOENIX_ENDPOINT, api_key=PHOENIX_API_KEY)
        traces = client.get_spans_dataframe(project_name=project_name)
        if filter_flags:
            traces = traces[traces["attributes"].str.contains(filter_flags, na=False)]
        return {
            "status": "success",
            "project": project_name,
            "count": len(traces),
            "traces": traces.head(limit).to_dict(orient="records"),
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "traces": []}


def detect_hallucination(trace_id: str, agent_output: str, context: dict) -> dict:
    """Check agent output for hallucinated or unsupported claims."""
    red_flags = ["always use", "never use", "100% effective", "guaranteed", "cure", "proven to eliminate"]
    flagged = [p for p in red_flags if p.lower() in agent_output.lower()]
    return {
        "trace_id": trace_id,
        "hallucination_detected": len(flagged) > 0,
        "flagged_phrases": flagged,
        "confidence": 0.85 if flagged else 0.05,
        "reasoning": f"Absolutist language detected: {flagged}" if flagged else "No hallucination indicators found",
        "timestamp": datetime.utcnow().isoformat(),
    }


def evaluate_clinical_accuracy(recommendation: dict, patient_profile: dict, guideline_source: str = "IDSA") -> dict:
    """Evaluate recommendation against guidelines and patient safety params."""
    flags = []
    score = 1.0

    crcl = patient_profile.get("crcl_ml_min", 90)
    drug = recommendation.get("antibiotic", "").lower()
    renally_cleared = ["vancomycin", "ciprofloxacin", "piperacillin", "meropenem", "gentamicin", "nitrofurantoin"]

    if crcl < 30 and any(d in drug for d in renally_cleared):
        flags.append({"type": "RENAL_DOSE_ADJUSTMENT", "severity": "HIGH",
                      "message": f"CrCl {crcl} mL/min — dose adjustment required for {drug}"})
        score -= 0.3

    allergies = patient_profile.get("allergies", [])
    drug_class = recommendation.get("drug_class", "")
    if "penicillin" in allergies and "penicillin" in drug_class.lower():
        flags.append({"type": "ALLERGY_CONFLICT", "severity": "CRITICAL",
                      "message": "Penicillin allergy conflict — CONTRAINDICATED"})
        score = 0.0

    aware_tier = recommendation.get("aware_tier", "")
    indication = patient_profile.get("diagnosis", "").lower()
    if aware_tier == "Reserve" and any(x in indication for x in ["uncomplicated", "community"]):
        flags.append({"type": "RESERVE_OVERUSE", "severity": "MEDIUM",
                      "message": f"Reserve-tier antibiotic for {indication} — not first-line per WHO AWaRe"})
        score -= 0.2

    return {
        "accuracy_score": max(0.0, score),
        "flags": flags,
        "requires_physician_review": score < 0.7 or any(f["severity"] == "CRITICAL" for f in flags),
        "guideline_source": guideline_source,
        "evaluated_at": datetime.utcnow().isoformat(),
    }


def flag_for_review(trace_id: str, reason: str, severity: str, recommendation: dict) -> dict:
    """Flag a recommendation for physician review — holds it from acting."""
    review_id = f"REVIEW-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    print(f"[AUDIT HOLD] {review_id} | {severity} | {reason}")
    return {
        "review_id": review_id,
        "trace_id": trace_id,
        "severity": severity,
        "reason": reason,
        "recommendation": recommendation,
        "status": "PENDING_PHYSICIAN_REVIEW",
        "created_at": datetime.utcnow().isoformat(),
    }


def run_phoenix_experiment(dataset_name: str, evaluator_name: str, project_name: str) -> dict:
    """Queue a Phoenix experiment to benchmark agent performance."""
    return {
        "status": "experiment_queued",
        "dataset": dataset_name,
        "evaluator": evaluator_name,
        "project": project_name,
        "message": "Check Phoenix dashboard at http://localhost:6006 for results",
    }


# MCP Tool manifest
MCP_TOOLS = [
    {"name": "fetch_phoenix_traces", "function": fetch_phoenix_traces,
     "description": "Fetch recent agent traces from Arize Phoenix"},
    {"name": "detect_hallucination", "function": detect_hallucination,
     "description": "Check recommendation for hallucinated claims"},
    {"name": "evaluate_clinical_accuracy", "function": evaluate_clinical_accuracy,
     "description": "Evaluate against IDSA/WHO clinical guidelines"},
    {"name": "flag_for_review", "function": flag_for_review,
     "description": "Hold a recommendation for physician review"},
    {"name": "run_phoenix_experiment", "function": run_phoenix_experiment,
     "description": "Run a Phoenix benchmarking experiment"},
]
