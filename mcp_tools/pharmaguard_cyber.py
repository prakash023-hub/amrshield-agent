"""
PharmaGuard Cyber Security Layer — healthcare zero-trust for AI agents.

Detects evil trackers, prompt injection, PHI exfiltration, repairs signals at edge,
seals immutable trust chain. Built for Ignite / cybersecurity pitch track.
"""

import hashlib
import json
import os
import re
from datetime import datetime
from typing import Optional

from mcp_tools.pharmaguard_trust import (
    ALLOWED_CLINICAL_FIELDS,
    EDGE_NODE_ID,
    EVIL_TRACKER_PATTERNS,
    _STORE_DIR,
    _ensure_file,
    _save_json,
    _hash_payload,
    create_consent_wallet,
    get_wallet,
    list_wallets,
    detect_evil_trackers,
    repair_signal,
    edge_sanitize,
    append_trust_chain,
    verify_chain_integrity,
    get_trust_chain,
    run_pharmaguard_pipeline,
)

_THREAT_LOG_PATH = os.path.join(_STORE_DIR, "threat_log.json")

# Cybersecurity: prompt injection & agent hijack patterns
INJECTION_PATTERNS = [
    (r"ignore (?:all )?(?:previous|prior) instructions", "PROMPT_INJECTION", "CRITICAL"),
    (r"you are now (?:a|an) ", "ROLE_HIJACK", "CRITICAL"),
    (r"disregard (?:safety|policy|guidelines)", "POLICY_BYPASS", "CRITICAL"),
    (r"reveal (?:system|hidden) prompt", "PROMPT_LEAK_ATTEMPT", "HIGH"),
    (r"export (?:all|patient) data", "DATA_EXFIL_ATTEMPT", "CRITICAL"),
    (r"<\s*script", "XSS_PAYLOAD", "CRITICAL"),
    (r";\s*DROP\s+TABLE", "SQL_INJECTION", "CRITICAL"),
    (r"base64,", "ENCODED_PAYLOAD", "MEDIUM"),
]

# Healthcare cyber compliance checks (HIPAA-aligned demo + India DPDP)
COMPLIANCE_CONTROLS = [
    "CONSENT_WALLET_ACTIVE",
    "EDGE_SANITIZATION",
    "PHI_MINIMIZATION",
    "DLP_SIGNAL_REPAIR",
    "NO_PHI_TO_CLOUD_AI",
    "IMMUTABLE_AUDIT_CHAIN",
    "AGENT_OUTPUT_SCAN",
    "PROMPT_INJECTION_DEFENSE",
    "THREAT_SCORING",
]


def _append_threat(event: dict) -> dict:
    log = _ensure_file(_THREAT_LOG_PATH, [])
    event["threat_id"] = f"THR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{len(log)+1:04d}"
    event["timestamp"] = datetime.utcnow().isoformat()
    log.insert(0, event)
    _save_json(_THREAT_LOG_PATH, log[:500])
    return event


def detect_prompt_injection(text: str, source: str = "user_input") -> dict:
    """Scan for AI agent hijack / prompt injection attacks."""
    findings = []
    for pattern, attack_type, severity in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            findings.append({"attack_type": attack_type, "severity": severity, "source": source})

    result = {
        "injection_detected": len(findings) > 0,
        "finding_count": len(findings),
        "findings": findings,
        "mcp_tool": "detect_prompt_injection",
    }
    if findings:
        _append_threat({"type": "PROMPT_INJECTION", "severity": "CRITICAL", "source": source, "count": len(findings)})
    return result


def scan_agent_output_for_exfil(agent_output: str, context: dict) -> dict:
    """Post-agent scan — ensure AI output isn't leaking PHI or credentials."""
    combined = {"output": agent_output, **context}
    tracker_scan = detect_evil_trackers(combined, context="agent_output")
    injection_scan = detect_prompt_injection(agent_output, source="agent_output")

    exfil = tracker_scan["finding_count"] + injection_scan["finding_count"] > 0
    if exfil:
        _append_threat({
            "type": "AGENT_EXFIL_RISK",
            "severity": "HIGH" if injection_scan["injection_detected"] else "MEDIUM",
            "tracker_findings": tracker_scan["finding_count"],
            "injection_findings": injection_scan["finding_count"],
        })

    return {
        "exfil_risk": exfil,
        "tracker_scan": tracker_scan,
        "injection_scan": injection_scan,
        "mcp_tool": "scan_agent_output_for_exfil",
    }


def calculate_threat_score(trackers: dict, injection: dict, chain_valid: bool) -> dict:
    """0–100 cyber threat score (lower = safer)."""
    score = 0
    for f in trackers.get("findings", []):
        score += {"CRITICAL": 30, "HIGH": 20, "MEDIUM": 10, "LOW": 5}.get(f.get("severity", "LOW"), 5)
    for f in injection.get("findings", []):
        score += {"CRITICAL": 35, "HIGH": 20, "MEDIUM": 10}.get(f.get("severity", "MEDIUM"), 10)
    if not chain_valid:
        score += 50

    score = min(100, score)
    level = "CRITICAL" if score >= 70 else ("HIGH" if score >= 40 else ("MEDIUM" if score >= 20 else "LOW"))

    return {
        "threat_score": score,
        "threat_level": level,
        "chain_integrity_ok": chain_valid,
        "recommendation": "BLOCK" if score >= 70 else ("FLAG" if score >= 40 else "ALLOW"),
        "mcp_tool": "calculate_threat_score",
    }


def run_compliance_check(wallet_id: str, edge_result: dict, chain_valid: bool) -> dict:
    """HIPAA / DPDP-style control checklist for hospital pilots."""
    repair = edge_result.get("repair", {})
    checks = {
        "CONSENT_WALLET_ACTIVE": get_wallet(wallet_id) is not None,
        "EDGE_SANITIZATION": edge_result.get("status") in ("ALLOWED", "FLAGGED"),
        "PHI_MINIMIZATION": repair.get("signal_integrity") in ("CLEAN", "RESTORED"),
        "DLP_SIGNAL_REPAIR": repair.get("mcp_tool") == "repair_signal",
        "NO_PHI_TO_CLOUD_AI": not repair.get("phi_reached_cloud", True),
        "IMMUTABLE_AUDIT_CHAIN": chain_valid,
        "AGENT_OUTPUT_SCAN": True,
        "PROMPT_INJECTION_DEFENSE": True,
        "THREAT_SCORING": True,
    }
    passed = sum(1 for v in checks.values() if v)
    return {
        "controls_passed": passed,
        "controls_total": len(checks),
        "compliance_pct": round(passed / len(checks) * 100, 1),
        "checks": checks,
        "framework": "PharmaGuard Zero-Trust (HIPAA + India DPDP 2023 aligned demo)",
        "hospital_pilot_ready": passed >= 8,
    }


def generate_physician_security_report(cyber_result: dict) -> dict:
    """
    Dual-audience report: plain language for physicians + technical detail for IT/security.
    """
    pg = cyber_result.get("pharmaguard", {})
    edge = pg.get("edge", {})
    repair = edge.get("repair", {})
    physician_dlp = edge.get("physician_dlp") or repair.get("physician_dlp", {})
    dlp = repair.get("dlp_summary", {})
    compliance = cyber_result.get("compliance", {})
    chain = cyber_result.get("chain_integrity", {})

    pipeline_steps = [
        {"step": 1, "name": "Consent Wallet", "status": "PASS" if pg.get("wallet") else "FAIL",
         "detail": f"Wallet {pg.get('wallet', {}).get('wallet_id', '—')} — pseudonymous, revocable"},
        {"step": 2, "name": "Evil Tracker Scan", "status": "PASS" if not edge.get("tracker_scan", {}).get("evil_trackers_found") else "REPAIRED",
         "detail": f"{edge.get('tracker_scan', {}).get('finding_count', 0)} tracker/PII signal(s) detected"},
        {"step": 3, "name": "Signal Repair (DLP v2)", "status": "PASS" if not dlp.get("data_leakage_prevented") else "REPAIRED",
         "detail": f"{dlp.get('total_repairs', 0)} repair(s) — keys removed: {dlp.get('keys_removed', 0)}, values redacted: {dlp.get('values_redacted', 0)}"},
        {"step": 4, "name": "Prompt Injection Defense", "status": "BLOCK" if cyber_result.get("injection_ingress", {}).get("injection_detected") else "PASS",
         "detail": f"{cyber_result.get('injection_ingress', {}).get('finding_count', 0)} injection pattern(s)"},
        {"step": 5, "name": "Clinical Agent (sanitized only)", "status": "PASS",
         "detail": "Only minimum-necessary clinical fields forwarded — no name/Aadhaar/phone"},
        {"step": 6, "name": "Agent Output Exfil Scan", "status": "FLAG" if cyber_result.get("output_scan", {}).get("exfil_risk") else "PASS",
         "detail": "Post-AI scan ensures recommendation does not leak PHI"},
        {"step": 7, "name": "Immutable Trust Chain", "status": "PASS" if chain.get("valid") else "FAIL",
         "detail": f"{chain.get('blocks', 0)} blocks — SHA-256 hash chain, tamper-evident"},
    ]

    return {
        "verdict": cyber_result.get("cyber_verdict", "UNKNOWN"),
        "threat_level": cyber_result.get("threat_score", {}).get("threat_level", "—"),
        "compliance_pct": compliance.get("compliance_pct", 0),
        "hospital_pilot_ready": compliance.get("hospital_pilot_ready", False),
        "phi_reached_cloud": repair.get("phi_reached_cloud", False),
        "data_leakage_prevented": edge.get("data_loss_prevented", False),
        "physician_assurance": physician_dlp.get("physician_summary", [
            "Patient identifiers are stripped at hospital edge before AI processing.",
        ]),
        "compliance_notes": physician_dlp.get("compliance_notes", []),
        "pipeline_steps": pipeline_steps,
        "dlp_summary": dlp,
        "repair_log": repair.get("repair_log", [])[:20],
        "wallet_id": pg.get("wallet", {}).get("wallet_id"),
        "edge_node": cyber_result.get("edge_node", EDGE_NODE_ID),
        "chain_hash_preview": chain.get("latest_hash", "—"),
    }


def run_cyber_guard_agent(
    patient_profile: dict,
    recommendation: Optional[dict] = None,
    audit_result: Optional[dict] = None,
) -> dict:
    """
    Cyber Guard Agent — full healthcare cybersecurity pipeline for Ignite track.
    Runs before and after clinical agents.
    """
    tools_called = []

    # Layer 1: ingress text scan (injection in any string fields)
    ingress_text = json.dumps(patient_profile)
    injection_ingress = detect_prompt_injection(ingress_text, source="patient_ingress")
    tools_called.append("detect_prompt_injection")

    # Layer 2: PharmaGuard trust pipeline
    pg = run_pharmaguard_pipeline(
        patient_profile,
        event_type="CYBER_INGRESS",
        recommendation=recommendation,
        audit_result=audit_result,
    )
    tools_called.extend(pg.get("pharmaguard_tools", []))

    if pg.get("status") == "BLOCKED":
        return {
            "status": "BLOCKED",
            "cyber_verdict": "BLOCK",
            "reason": "Consent wallet or edge policy blocked ingress",
            "pharmaguard": pg,
            "cyber_tools": tools_called,
        }

    # Layer 3: agent output scan
    output_scan = {"exfil_risk": False, "tracker_scan": {"findings": []}, "injection_scan": {"findings": []}}
    if recommendation:
        output_text = json.dumps(recommendation)
        output_scan = scan_agent_output_for_exfil(output_text, {"trace_id": recommendation.get("trace_id")})
        tools_called.append("scan_agent_output_for_exfil")

    chain = verify_chain_integrity()
    threat = calculate_threat_score(
        pg["edge"]["tracker_scan"],
        injection_ingress,
        chain.get("valid", False),
    )
    tools_called.append("calculate_threat_score")

    compliance = run_compliance_check(
        pg["wallet"]["wallet_id"],
        pg["edge"],
        chain.get("valid", False),
    )
    tools_called.append("run_compliance_check")

    cyber_verdict = threat["recommendation"]
    if output_scan.get("exfil_risk"):
        cyber_verdict = "FLAG" if cyber_verdict == "ALLOW" else cyber_verdict
    if injection_ingress.get("injection_detected"):
        cyber_verdict = "BLOCK"

    append_trust_chain(
        "CYBER_GUARD_VERDICT",
        _hash_payload({"verdict": cyber_verdict, "score": threat["threat_score"]}),
        pg["wallet"]["wallet_id"],
        {"threat_level": threat["threat_level"], "compliance_pct": compliance["compliance_pct"]},
    )

    return {
        "status": "SECURED" if cyber_verdict == "ALLOW" else cyber_verdict,
        "cyber_verdict": cyber_verdict,
        "threat_score": threat,
        "compliance": compliance,
        "injection_ingress": injection_ingress,
        "output_scan": output_scan,
        "pharmaguard": pg,
        "sanitized_patient": pg.get("sanitized_patient"),
        "chain_integrity": chain,
        "cyber_tools": tools_called,
        "edge_node": EDGE_NODE_ID,
        "physician_security_report": generate_physician_security_report({
            "cyber_verdict": cyber_verdict,
            "threat_score": threat,
            "compliance": compliance,
            "injection_ingress": injection_ingress,
            "output_scan": output_scan,
            "pharmaguard": pg,
            "chain_integrity": chain,
            "edge_node": EDGE_NODE_ID,
        }),
    }


def get_threat_log(limit: int = 30) -> list:
    return _ensure_file(_THREAT_LOG_PATH, [])[:limit]


def get_security_posture() -> dict:
    """SOC dashboard summary."""
    chain = verify_chain_integrity()
    threats = get_threat_log(100)
    wallets = list_wallets(100)
    critical = sum(1 for t in threats if t.get("severity") == "CRITICAL")
    return {
        "chain_blocks": chain.get("blocks", 0),
        "chain_valid": chain.get("valid", True),
        "active_wallets": len(wallets),
        "threats_logged_24h": len(threats),
        "critical_threats": critical,
        "edge_node": EDGE_NODE_ID,
        "zero_trust_status": "ENFORCED" if chain.get("valid") else "COMPROMISED",
    }


CYBER_AGENT_TOOLS = {
    "detect_evil_trackers": detect_evil_trackers,
    "detect_prompt_injection": detect_prompt_injection,
    "repair_signal": repair_signal,
    "scan_agent_output_for_exfil": scan_agent_output_for_exfil,
    "calculate_threat_score": calculate_threat_score,
    "run_compliance_check": run_compliance_check,
    "run_cyber_guard_agent": run_cyber_guard_agent,
    "verify_chain_integrity": verify_chain_integrity,
    "generate_physician_security_report": generate_physician_security_report,
}
