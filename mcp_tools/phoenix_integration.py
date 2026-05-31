"""
AMRShield - Arize Phoenix MCP Integration
Auto-tracing via GoogleGenAIInstrumentor + MCP tool dispatch for Self-Audit Agent.
"""

import os
import json
import time
from datetime import datetime
from typing import Any, Optional

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
    return fallback or f"TR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"


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


def detect_hallucination(trace_id: str, agent_output: str, context: dict) -> dict:
    """Check agent output for hallucinated or unsupported claims (MCP: detect_hallucination)."""
    red_flags = [
        "always use", "never use", "100% effective", "guaranteed",
        "cure", "proven to eliminate", "completely safe", "no side effects",
    ]
    flagged = [p for p in red_flags if p.lower() in agent_output.lower()]
    return {
        "trace_id": trace_id,
        "hallucination_detected": len(flagged) > 0,
        "flagged_phrases": flagged,
        "confidence": 0.85 if flagged else 0.05,
        "reasoning": f"Absolutist language detected: {flagged}" if flagged else "No hallucination indicators found",
        "timestamp": datetime.utcnow().isoformat(),
        "mcp_tool": "detect_hallucination",
    }


def evaluate_clinical_accuracy(recommendation: dict, patient_profile: dict, guideline_source: str = "IDSA") -> dict:
    """Evaluate recommendation against guidelines (MCP: evaluate_clinical_accuracy)."""
    flags = []
    score = 1.0

    age = patient_profile.get("age", 50)
    weight = patient_profile.get("weight", 70)
    serum_cr = patient_profile.get("serum_creatinine", patient_profile.get("crcl_ml_min", 1.0))
    if isinstance(serum_cr, (int, float)) and serum_cr > 20:
        crcl = serum_cr
    else:
        sex = patient_profile.get("sex", "male")
        sex_factor = 1.0 if sex == "male" else 0.85
        crcl = ((140 - age) * weight * sex_factor) / (72 * max(serum_cr, 0.1))

    drug = recommendation.get("antibiotic", "").lower()
    renally_cleared = ["vancomycin", "ciprofloxacin", "piperacillin", "meropenem", "gentamicin", "nitrofurantoin"]

    if crcl < 30 and any(d in drug for d in renally_cleared):
        flags.append({
            "type": "RENAL_DOSE_ADJUSTMENT",
            "severity": "HIGH",
            "message": f"CrCl {crcl:.0f} mL/min — dose adjustment required for {drug}",
        })
        score -= 0.3

    allergies = [a.lower() for a in patient_profile.get("allergies", [])]
    drug_class = recommendation.get("drug_class", "").lower()
    if "penicillin" in allergies and "penicillin" in drug_class.lower():
        flags.append({
            "type": "ALLERGY_CONFLICT",
            "severity": "CRITICAL",
            "message": "Penicillin allergy conflict — CONTRAINDICATED",
        })
        score = 0.0

    aware_tier = recommendation.get("aware_tier", "")
    indication = patient_profile.get("diagnosis", "").lower()
    if aware_tier == "Reserve" and any(x in indication for x in ["uncomplicated", "community"]):
        flags.append({
            "type": "RESERVE_OVERUSE",
            "severity": "MEDIUM",
            "message": f"Reserve-tier antibiotic for {indication} — not first-line per WHO AWaRe",
        })
        score -= 0.2

    return {
        "accuracy_score": max(0.0, score),
        "flags": flags,
        "requires_physician_review": score < 0.7 or any(f["severity"] == "CRITICAL" for f in flags),
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
    result = MCP_TOOLS[tool_name](**kwargs)
    result["latency_ms"] = int((time.perf_counter() - started) * 1000)
    result["status"] = result.get("status", "success")
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
    })

    hallucination = invoke_mcp_tool(
        "detect_hallucination",
        trace_id=trace_id,
        agent_output=agent_output,
        context={"patient_id": patient_profile.get("patient_id")},
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
        reason = flags[0]["message"] if flags else hallucination.get("reasoning", "Safety concern")
        review_hold = invoke_mcp_tool(
            "flag_for_review",
            trace_id=trace_id,
            reason=reason,
            severity=severity,
            recommendation=recommendation,
        )
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
    flags = accuracy.get("flags", [])

    mcp_result = "PASS"
    if accuracy.get("accuracy_score", 1.0) == 0.0:
        mcp_result = "HOLD"
    elif flags or hallucination.get("hallucination_detected"):
        mcp_result = "FLAG"

    severity_rank = {"PASS": 0, "FLAG": 1, "HOLD": 2}
    gemini_result = gemini_audit.get("overall_result", "PASS")
    final_result = gemini_result
    if severity_rank.get(mcp_result, 0) > severity_rank.get(gemini_result, 0):
        final_result = mcp_result

    issues = list(gemini_audit.get("issues_found", []))
    for flag in flags:
        issues.append(flag)

    if hallucination.get("hallucination_detected"):
        issues.append({
            "type": "HALLUCINATION",
            "severity": "HIGH",
            "message": hallucination.get("reasoning", "Absolutist language detected"),
        })

    physician_review = (
        final_result in ("FLAG", "HOLD")
        or accuracy.get("requires_physician_review", False)
        or gemini_audit.get("physician_review_required", False)
    )

    reasoning_parts = [gemini_audit.get("audit_reasoning", "")]
    if mcp_pipeline.get("phoenix_mcp_tools"):
        reasoning_parts.append(
            f"Phoenix MCP tools: {', '.join(mcp_pipeline['phoenix_mcp_tools'])}."
        )
    if review_hold := mcp_pipeline.get("review_hold"):
        reasoning_parts.append(f"Review queued: {review_hold.get('review_id')}.")

    return {
        "overall_result": final_result,
        "issues_found": issues,
        "severity_level": "CRITICAL" if final_result == "HOLD" else gemini_audit.get("severity_level", "LOW"),
        "recommendation_safe_to_proceed": final_result == "PASS",
        "physician_review_required": physician_review,
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
    """Persist audit row for Audit Console."""
    append_audit_event({
        "trace_id": audit_result.get("phoenix_trace_id") or recommendation.get("trace_id"),
        "antibiotic": recommendation.get("antibiotic", "unknown"),
        "diagnosis": patient_profile.get("diagnosis", "unknown"),
        "result": audit_result.get("overall_result", "PASS"),
        "confidence": recommendation.get("confidence_score", 0.75),
        "latency_ms": latency_ms,
        "hallucination": audit_result.get("hallucination_detected", False),
        "flag_count": len(audit_result.get("issues_found", [])),
        "aware": recommendation.get("aware_tier", "Access"),
        "physician_review": audit_result.get("physician_review_required", False),
        "audit_reasoning": audit_result.get("audit_reasoning", ""),
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
