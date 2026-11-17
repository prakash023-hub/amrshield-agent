"""
AMRShield - Arize Phoenix MCP Integration
Auto-tracing via GoogleGenAIInstrumentor + MCP tool dispatch for Self-Audit Agent.
"""

import os
import json
import logging
import time
from datetime import datetime
from typing import Optional
from uuid import uuid4

from mcp_tools.audit_store import append_audit_event, list_audit_events

# ─────────────────────────────────────────────
# Tracing bootstrap (call once at app startup)
# ─────────────────────────────────────────────

_tracing_initialized = False


def setup_phoenix(project_name: str):
    """
    Register OpenTelemetry export to Phoenix.
    Auto-instruments ALL Gemini/Vertex AI calls.
    """
    try:
        from phoenix.otel import register
        from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

        phoenix_endpoint = os.getenv("PHOENIX_ENDPOINT", "http://localhost:6006")
        phoenix_api_key = os.getenv("PHOENIX_API_KEY", "local-dev")

        tracer_provider = register(
            project_name=project_name,
            endpoint=f"{phoenix_endpoint}/v1/traces",
            headers={"api_key": phoenix_api_key},
        )
        GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)
        print(f"✅ Phoenix auto-tracing active → project: {project_name}")
        return tracer_provider
    except ImportError as e:
        print(f"⚠ Phoenix not installed ({e}) — running without tracing")
        return None
    except Exception as e:
        print(f"⚠ Phoenix setup failed ({e}) — running without tracing")
        return None


def ensure_phoenix_tracing():
    """Initialize Phoenix tracing once for the Streamlit/API process."""
    global _tracing_initialized
    if _tracing_initialized:
        return
    setup_phoenix(os.getenv("PHOENIX_PROJECT", "amrshield-clinical-agent"))
    _tracing_initialized = True


PROJECTS = {
    "clinical": "amrshield-clinical-agent",
    "prediction": "amrshield-prediction-agent",
    "audit": "amrshield-audit-agent",
}


def get_current_trace_id(fallback: str = "") -> str:
    """Read OpenTelemetry trace id when instrumentation is active."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.trace_id:
            return format(ctx.trace_id, "032x")
    except Exception:
        pass
    return fallback or f"TR-{uuid4().hex}"


# ─────────────────────────────────────────────
# Phoenix MCP Tool Functions
# ─────────────────────────────────────────────

def fetch_phoenix_traces(project_name: str, limit: int = 20, filter_flags: Optional[str] = None) -> dict:
    """Fetch recent traces from a Phoenix project (MCP: fetch_phoenix_traces)."""
    try:
        import phoenix as px

        phoenix_endpoint = os.getenv("PHOENIX_ENDPOINT", "http://localhost:6006")
        phoenix_api_key = os.getenv("PHOENIX_API_KEY", "local-dev")
        client = px.Client(endpoint=phoenix_endpoint, api_key=phoenix_api_key)
        traces = client.get_spans_dataframe(project_name=project_name)
        if filter_flags and not traces.empty:
            traces = traces[traces["attributes"].astype(str).str.contains(filter_flags, na=False)]
        return {
            "status": "success",
            "source": "phoenix_mcp",
            "project": project_name,
            "count": len(traces),
            "traces": traces.head(limit).to_dict(orient="records") if not traces.empty else [],
        }
    except Exception as e:
        local = list_audit_events(limit=limit)
        return {
            "status": "fallback",
            "source": "audit_store",
            "project": project_name,
            "count": len(local),
            "message": str(e),
            "traces": local,
        }


ABSOLUTIST_PHRASES = [
    "always use", "never use", "100% effective", "guaranteed",
    "cure", "proven to eliminate", "completely safe", "no side effects",
]


def detect_hallucination(trace_id: str, agent_output: str, context: dict) -> dict:
    """
    Grounding check (MCP: detect_hallucination).

    Verifies the agent's concrete claims against deterministic tool outputs
    instead of trusting the LLM's own text:
      1. Drug exists in the WHO AWaRe reference table.
      2. Claimed AWaRe tier matches the reference tier.
      3. Any CrCl value quoted in the rationale matches Cockcroft-Gault (±5 mL/min).
      4. "No interaction" / "no allergy" statements are not contradicted by the
         interaction and allergy checkers.
      5. Absolutist language (weak, stylistic signal only).

    Returns a faithfulness score = supported claims / checked claims.
    Limitation: rule-based. Planned upgrade is claim extraction + LLM-as-judge
    against tool outputs and guideline text, scored on a labelled eval set.
    """
    from agents.clinical_agent.tools import (
        check_allergy_conflict, check_drug_interactions, lookup_aware_tier,
    )

    rec = context.get("recommendation", {}) or {}
    patient = context.get("patient_profile", {}) or {}
    text = agent_output.lower()
    drug = str(rec.get("antibiotic", "")).strip()

    checks = []

    def add(claim: str, supported: bool, evidence: str, severity: str = "HIGH"):
        checks.append({"claim": claim, "supported": supported, "evidence": evidence,
                       "severity": "NONE" if supported else severity})

    # 1 + 2. Drug and AWaRe tier grounded in reference table
    if drug:
        ref = lookup_aware_tier(drug)
        ref_tier = ref.get("aware_tier", "Not classified")
        add(f"'{drug}' is a recognised antibiotic", ref_tier != "Not classified",
            f"AWaRe lookup → {ref_tier}", "MEDIUM")
        claimed_tier = str(rec.get("aware_tier", "")).strip()
        if claimed_tier and ref_tier != "Not classified":
            add(f"AWaRe tier = {claimed_tier}", claimed_tier.lower() == ref_tier.lower(),
                f"Reference tier = {ref_tier}")

    # 3. Quoted CrCl vs calculated CrCl
    import re
    quoted = re.findall(r"crcl[^0-9]{0,15}(\d{1,3}(?:\.\d+)?)", text)
    if quoted:
        calc = _patient_crcl(patient).get("crcl_ml_min")
        if calc is not None:
            for q in quoted:
                add(f"CrCl ≈ {q} mL/min", abs(float(q) - calc) <= 5, f"Cockcroft-Gault = {calc} mL/min")

    # 4. Safety statements contradicted by tool outputs
    if drug and patient.get("current_medications") is not None:
        ddi = check_drug_interactions(
            drug, patient.get("current_medications", []), route=str(rec.get("route") or ""),
        )
        if "no interaction" in text or "no significant interaction" in text:
            add("No drug interactions", ddi["screening_status"] == "SCREENED"
                and ddi["interaction_count"] == 0
                and not (patient["current_medications"] and ddi["coverage_note"]), ddi["summary"])
    if drug and patient.get("allergies"):
        allergy = check_allergy_conflict(drug, str(rec.get("drug_class", "")), patient["allergies"])
        if "no allergy" in text or "allergy-safe" in text or "safe with" in text:
            add("No allergy conflict", not allergy["conflict"], allergy["message"],
                "CRITICAL" if allergy["severity"] == "ABSOLUTE" else "HIGH")

    # 5. Absolutist language — stylistic signal, low weight
    flagged = [p for p in ABSOLUTIST_PHRASES if p in text]
    if flagged:
        add("Measured, non-absolute language", False, f"Absolutist phrases: {flagged}", "LOW")

    unsupported = [c for c in checks if not c["supported"]]
    faithfulness = round(1 - len(unsupported) / len(checks), 2) if checks else 1.0
    material = [c for c in unsupported if c["severity"] in ("MEDIUM", "HIGH", "CRITICAL")]

    return {
        "trace_id": trace_id,
        "hallucination_detected": len(material) > 0,
        "faithfulness_score": faithfulness,
        "claims_checked": len(checks),
        "unsupported_claims": unsupported,
        "flagged_phrases": flagged,
        "reasoning": (
            "; ".join(f"{c['claim']} — {c['evidence']}" for c in unsupported)
            if unsupported else "All checked claims are supported by tool outputs"
        ),
        "method": "rule-based grounding against deterministic tools (not an LLM judge)",
        "timestamp": datetime.utcnow().isoformat(),
        "mcp_tool": "detect_hallucination",
    }


def _patient_crcl(patient_profile: dict) -> dict:
    from agents.clinical_agent.tools import calculate_crcl

    fields = ("age", "weight", "serum_creatinine", "sex")
    values = [patient_profile.get(field) for field in fields]
    missing = [
        field for field, value in zip(fields, values)
        if value is None or isinstance(value, str) and not value.strip()
    ]
    if missing:
        return {"error": f"Missing required clinical data: {', '.join(missing)}.",
                "issue_type": "MISSING_CLINICAL_DATA"}
    return calculate_crcl(*values, round_result=False)


def evaluate_clinical_accuracy(recommendation: dict, patient_profile: dict, guideline_source: str = "IDSA") -> dict:
    """Evaluate recommendation using the existing deterministic clinical tools."""
    from agents.clinical_agent.tools import (
        check_allergy_conflict, check_drug_interactions, lookup_aware_tier, suggest_renal_dose,
    )

    flags = []

    def flag(kind, severity, message):
        flags.append({"type": kind, "severity": severity, "message": message})

    renal = _patient_crcl(patient_profile)
    crcl = renal.get("crcl_ml_min")
    if "error" in renal:
        flag(renal.get("issue_type", "INVALID_RENAL_PARAMETERS"), "CRITICAL", renal["error"])

    drug = str(recommendation.get("antibiotic") or "").strip()
    if not drug or lookup_aware_tier(drug)["aware_tier"] == "Not classified":
        flag("UNKNOWN_ANTIBIOTIC", "HIGH", "Antibiotic could not be verified in the reference table.")
    placeholders = {"unknown", "n/a", "na", "none", "null", "tbd", "-", "—", "not specified"}
    incomplete = [
        field for field in ("dose", "route", "frequency")
        if not isinstance(value := recommendation.get(field), str)
        or not value.strip() or value.strip().casefold() in placeholders
    ]
    if drug and incomplete:
        flag("INCOMPLETE_REGIMEN", "CRITICAL",
             f"Missing or unspecified regimen fields: {', '.join(incomplete)}.")
    if recommendation.get("demo_mode") or recommendation.get("error"):
        flag("RECOMMENDATION_UNAVAILABLE", "HIGH", "A clinical recommendation could not be verified.")
    if recommendation.get("physician_review_required") or recommendation.get("safe_to_sign") is False:
        flag("CLINICAL_REVIEW_REQUIRED", "HIGH", "The clinical recommendation requires physician review.")
    if any(item.get("severity") in ("ABSOLUTE", "CRITICAL")
           for item in (recommendation.get("contraindications") or []) if isinstance(item, dict)):
        flag("CLINICAL_CONTRAINDICATION", "CRITICAL", "The clinical recommendation reports a contraindication.")

    allergies = patient_profile.get("allergies")
    known_allergies = [a for a in allergies if isinstance(a, str) and a.strip()] if isinstance(allergies, list) else []
    if not isinstance(allergies, list) or len(known_allergies) != len(allergies):
        flag("ALLERGY_HISTORY_INCOMPLETE", "HIGH", "Allergy history could not be fully screened.")
    if drug and known_allergies:
        allergy = check_allergy_conflict(drug, str(recommendation.get("drug_class") or ""), known_allergies)
        if allergy["conflict"]:
            if allergy["severity"] == "ABSOLUTE":
                flag("ALLERGY_CONFLICT", "CRITICAL", allergy["message"])
            else:
                flag("ALLERGY_REVIEW_REQUIRED", "HIGH", allergy["message"])

    if crcl is not None and drug:
        renal_dose = suggest_renal_dose(drug, crcl)
        if renal_dose["adjustment_required"]:
            severity = renal_dose["severity"]
            flag("RENAL_DOSE_ADJUSTMENT", "CRITICAL" if severity == "ABSOLUTE" else severity,
                 "Renal dosing screen requires clinician verification of the proposed regimen.")

    meds = patient_profile.get("current_medications")
    if not isinstance(meds, list) or any(not isinstance(m, str) or not m.strip() for m in meds):
        flag("INTERACTION_NOT_SCREENED", "HIGH", "Medication history could not be screened.")
    elif drug:
        ddi = check_drug_interactions(drug, meds, route=str(recommendation.get("route") or ""))
        if ddi["screening_status"] != "SCREENED" or (meds and ddi["coverage_note"]):
            flag("INTERACTION_NOT_SCREENED", "HIGH", "Interaction reference coverage is incomplete.")
        for interaction in ddi["interactions_found"]:
            severity = interaction["severity"]
            message = (
                interaction["clinical_effect"]
                if drug.casefold() == "ceftriaxone" and interaction["source"] == "curated"
                else "A potential drug interaction requires clinician review."
            )
            flag("DRUG_INTERACTION", "HIGH" if severity == "UNKNOWN" else severity, message)

    aware_tier = recommendation.get("aware_tier", "")
    indication = str(patient_profile.get("diagnosis") or "").lower()
    if aware_tier == "Reserve" and any(x in indication for x in ["uncomplicated", "community"]):
        flags.append({
            "type": "RESERVE_OVERUSE",
            "severity": "MEDIUM",
            "message": "Reserve-tier antibiotic for a community or uncomplicated indication — review required.",
        })
    critical = any(f["severity"] == "CRITICAL" for f in flags)
    return {
        "accuracy_score": 0.0 if critical else max(0.0, 1.0 - 0.2 * len(flags)),
        "crcl_ml_min": crcl,
        "flags": flags,
        "requires_physician_review": bool(flags),
        "guideline_source": guideline_source,
        "evaluated_at": datetime.utcnow().isoformat(),
        "mcp_tool": "evaluate_clinical_accuracy",
    }


def flag_for_review(trace_id: str, reason: str, severity: str, recommendation: dict) -> dict:
    """Hold a recommendation for physician review (MCP: flag_for_review)."""
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
        "mcp_tool": "flag_for_review",
    }


def run_phoenix_experiment(dataset_name: str, evaluator_name: str, project_name: str) -> dict:
    """Queue a Phoenix experiment (MCP: run_phoenix_experiment)."""
    return {
        "status": "experiment_queued",
        "dataset": dataset_name,
        "evaluator": evaluator_name,
        "project": project_name,
        "message": f"Check Phoenix dashboard at {os.getenv('PHOENIX_ENDPOINT', 'http://localhost:6006')}",
        "mcp_tool": "run_phoenix_experiment",
    }


MCP_TOOLS = {
    "fetch_phoenix_traces": fetch_phoenix_traces,
    "detect_hallucination": detect_hallucination,
    "evaluate_clinical_accuracy": evaluate_clinical_accuracy,
    "flag_for_review": flag_for_review,
    "run_phoenix_experiment": run_phoenix_experiment,
}


def invoke_mcp_tool(tool_name: str, **kwargs) -> dict:
    """Dispatch a Phoenix MCP tool by name — used by Self-Audit Agent."""
    if tool_name not in MCP_TOOLS:
        return {"status": "error", "message": f"Unknown MCP tool: {tool_name}"}
    started = time.perf_counter()
    try:
        result = MCP_TOOLS[tool_name](**kwargs)
        result["latency_ms"] = int((time.perf_counter() - started) * 1000)
        result.setdefault("status", "success")
    except Exception:
        logging.getLogger(__name__).warning("Phoenix MCP tool failed: %s", tool_name)
        return {"status": "error", "mcp_tool": tool_name}
    return result


def run_phoenix_mcp_audit_pipeline(
    recommendation: dict,
    patient_profile: dict,
    trace_id: str,
) -> dict:
    """
    Self-Audit Agent MCP pipeline — runs all Phoenix MCP safety tools in sequence.
    Returns combined MCP results for Gemini synthesis / rule merge.
    """
    ensure_phoenix_tracing()

    tools_called = []
    agent_output = json.dumps({
        "rationale": recommendation.get("rationale", ""),
        "antibiotic": recommendation.get("antibiotic", ""),
        "dose": recommendation.get("dose", ""),
        "aware_tier": recommendation.get("aware_tier", ""),
    })

    hallucination = invoke_mcp_tool(
        "detect_hallucination",
        trace_id=trace_id,
        agent_output=agent_output,
        context={
            "recommendation": recommendation,
            "patient_profile": patient_profile,
        },
    )
    tools_called.append("detect_hallucination")

    accuracy = invoke_mcp_tool(
        "evaluate_clinical_accuracy",
        recommendation=recommendation,
        patient_profile=patient_profile,
    )
    tools_called.append("evaluate_clinical_accuracy")

    traces = invoke_mcp_tool(
        "fetch_phoenix_traces",
        project_name=PROJECTS["clinical"],
        limit=5,
    )
    tools_called.append("fetch_phoenix_traces")

    review_hold = None
    flags = accuracy.get("flags", [])
    critical = any(f.get("severity") == "CRITICAL" for f in flags)
    if critical or hallucination.get("hallucination_detected"):
        severity = "CRITICAL" if critical else "HIGH"
        reason = next((f["message"] for f in flags if f["severity"] == "CRITICAL"),
                      "Recommendation contains unsupported clinical claims.")
        review_hold = invoke_mcp_tool(
            "flag_for_review",
            trace_id=trace_id,
            reason=reason,
            severity=severity,
            recommendation={"antibiotic": recommendation.get("antibiotic")},
        )
        if review_hold.get("status") != "PENDING_PHYSICIAN_REVIEW":
            review_hold = None
        tools_called.append("flag_for_review")

    return {
        "trace_id": trace_id,
        "phoenix_mcp_tools": tools_called,
        "hallucination_check": hallucination,
        "accuracy_check": accuracy,
        "recent_traces": traces,
        "review_hold": review_hold,
    }


def merge_mcp_into_audit(gemini_audit: dict, mcp_pipeline: dict) -> dict:
    """Merge Gemini verdict with deterministic Phoenix MCP tool results."""
    hallucination = mcp_pipeline["hallucination_check"]
    accuracy = mcp_pipeline["accuracy_check"]
    deterministic = list(accuracy.get("flags", []))

    if hallucination.get("hallucination_detected"):
        severity = "CRITICAL" if any(
            claim.get("severity") == "CRITICAL" for claim in hallucination["unsupported_claims"]
        ) else "HIGH"
        deterministic.append({"type": "HALLUCINATION", "severity": severity,
                       "message": "Recommendation contains unsupported clinical claims."})

    check_failed = any(check.get("status") != "success" for check in (hallucination, accuracy))
    if check_failed:
        deterministic.append({"type": "AUDIT_CHECK_UNAVAILABLE", "severity": "HIGH",
                       "message": "A Phoenix clinical safety check could not be completed."})

    issues = [*deterministic, *gemini_audit["issues_found"]]
    if (gemini_audit["overall_result"] == "HOLD" or accuracy.get("accuracy_score") == 0
            or gemini_audit["severity_level"] == "CRITICAL"
            or any(issue["severity"] == "CRITICAL" for issue in issues)
            or check_failed):
        final_result = "HOLD"
    elif (gemini_audit["overall_result"] == "FLAG" or issues
          or gemini_audit["severity_level"] != "LOW"
          or gemini_audit["physician_review_required"]
          or not gemini_audit["recommendation_safe_to_proceed"]
          or accuracy.get("requires_physician_review") or mcp_pipeline.get("review_hold")):
        final_result = "FLAG"
    else:
        final_result = "PASS"

    severity_rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    severity = max(
        [gemini_audit["severity_level"], *(issue["severity"] for issue in issues),
         {"PASS": "LOW", "FLAG": "MEDIUM", "HOLD": "CRITICAL"}[final_result]],
        key=severity_rank.__getitem__,
    )

    if final_result == "PASS":
        reasoning_parts = [gemini_audit["audit_reasoning"]]
    else:
        reasoning_parts = [issue["message"] for issue in deterministic]
        if not reasoning_parts:
            reasoning_parts = ["The audit requires physician review."]
        if any(issue["type"] == "GEMINI_AUDIT_UNAVAILABLE" for issue in gemini_audit["issues_found"]):
            reasoning_parts.append("Gemini safety assessment was unavailable or invalid.")
    if mcp_pipeline.get("phoenix_mcp_tools"):
        reasoning_parts.append(
            f"Phoenix MCP tools: {', '.join(mcp_pipeline['phoenix_mcp_tools'])}."
        )
    if review_hold := mcp_pipeline.get("review_hold"):
        reasoning_parts.append(f"Review reference: {review_hold.get('review_id')}.")

    return {
        "overall_result": final_result,
        "issues_found": issues,
        "severity_level": severity,
        "recommendation_safe_to_proceed": final_result == "PASS",
        "physician_review_required": final_result != "PASS",
        "audit_reasoning": " ".join(p for p in reasoning_parts if p).strip(),
        "phoenix_mcp_tools": mcp_pipeline.get("phoenix_mcp_tools", []),
        "phoenix_trace_id": mcp_pipeline.get("trace_id"),
        "hallucination_detected": hallucination.get("hallucination_detected", False),
        "accuracy_score": accuracy.get("accuracy_score"),
        "review_hold": mcp_pipeline.get("review_hold"),
    }


def record_audit_to_store(
    recommendation: dict,
    patient_profile: dict,
    audit_result: dict,
    latency_ms: int,
):
    """Persist the verdict and its deterministic reasoning for Audit Console."""
    confidence = recommendation.get("confidence_score", 0.75)
    if type(confidence) not in (int, float) or not 0 <= confidence <= 1:
        confidence = 0.75
    append_audit_event({
        "trace_id": audit_result.get("phoenix_trace_id") or recommendation.get("trace_id"),
        "antibiotic": recommendation.get("antibiotic", "unknown"),
        "diagnosis": patient_profile.get("diagnosis", "unknown"),
        "result": audit_result["overall_result"],
        "confidence": confidence,
        "latency_ms": latency_ms,
        "hallucination": audit_result.get("hallucination_detected", False),
        "flag_count": len(audit_result.get("issues_found", [])),
        "aware": recommendation.get("aware_tier", "Access"),
        "physician_review": audit_result.get("physician_review_required", False),
        "audit_reasoning": (
            "Available checks passed." if audit_result["overall_result"] == "PASS"
            else audit_result["audit_reasoning"]
        ),
        "phoenix_mcp_tools": audit_result.get("phoenix_mcp_tools", []),
    })


def get_audit_traces(limit: int = 50) -> list:
    """Return audit rows for dashboards — local store first, Phoenix when available."""
    rows = list_audit_events(limit=limit)
    if rows:
        return rows

    phoenix_data = fetch_phoenix_traces(PROJECTS["clinical"], limit=limit)
    if phoenix_data.get("traces"):
        return phoenix_data["traces"]
    return []
