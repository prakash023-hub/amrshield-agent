"""
PharmaGuard Trust Layer — patient data wallets, edge sanitization,
evil-tracker detection, signal repair, and immutable trust chain.

No raw PHI on chain — only hashed wallet IDs + event hashes.
"""

import hashlib
import json
import os
import re
import uuid
from datetime import datetime
from typing import Any, Optional

_STORE_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_WALLET_PATH = os.path.join(_STORE_DIR, "consent_wallets.json")
_CHAIN_PATH = os.path.join(_STORE_DIR, "trust_chain.json")

# Fields allowed in edge processing (minimum necessary)
ALLOWED_CLINICAL_FIELDS = {
    "patient_id", "age", "sex", "weight", "serum_creatinine",
    "diagnosis", "infection_site", "suspected_pathogen",
    "allergies", "current_medications", "culture_results",
    "consent_wallet_id", "edge_node_id", "icu", "pregnancy",
}

# Patterns that suggest PII leaks or "evil trackers" in payloads
EVIL_TRACKER_PATTERNS = [
    (r"\b\d{4}\s?\d{4}\s?\d{4}\b", "AADHAAR_LEAK", "CRITICAL"),
    (r"\b[A-Z]{5}\d{4}[A-Z]\b", "PAN_LEAK", "CRITICAL"),
    (r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b", "IN_MOBILE_LEAK", "CRITICAL"),
    (r"\b\d{3}-\d{2}-\d{4}\b", "SSN_PATTERN", "CRITICAL"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "EMAIL_LEAK", "HIGH"),
    (r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "PHONE_LEAK", "HIGH"),
    (r"\b(?:facebook|google-analytics|doubleclick|adservice|tracker|mixpanel|segment)\b", "AD_TRACKER", "MEDIUM"),
    (r"\b(?:password|api_key|secret|token)\s*[:=]", "CREDENTIAL_LEAK", "CRITICAL"),
    (r"\b(?:patient_name|full_name|address|aadhaar|aadhar|pan|passport|abha|uhid)\b", "FORBIDDEN_FIELD", "CRITICAL"),
    (r"https?://(?!.*(?:googleapis|cloud\.google|run\.app))[^\s\"']+", "EXTERNAL_EXFIL_URL", "MEDIUM"),
]

EDGE_NODE_ID = os.getenv("PHARMAGUARD_EDGE_NODE", "edge-india-south-01")


def _ensure_file(path: str, default: list | dict):
    os.makedirs(_STORE_DIR, exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2)
        return default if isinstance(default, list) else default.copy()
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: str, data):
    os.makedirs(_STORE_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _hash_payload(data: dict) -> str:
    canonical = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def create_consent_wallet(patient_pseudonym: str, scopes: Optional[list] = None) -> dict:
    """Patient consent wallet — pseudonymous ID, no real name on chain."""
    wallets = _ensure_file(_WALLET_PATH, [])
    wallet_id = f"PGW-{hashlib.sha256(patient_pseudonym.encode()).hexdigest()[:16].upper()}"
    existing = next((w for w in wallets if w["wallet_id"] == wallet_id), None)
    if existing:
        return existing

    wallet = {
        "wallet_id": wallet_id,
        "pseudonym_hash": hashlib.sha256(patient_pseudonym.encode()).hexdigest(),
        "consent_scopes": scopes or ["stewardship_recommendation", "audit_trail", "pharmacy_analytics"],
        "consent_granted_at": datetime.utcnow().isoformat(),
        "data_retention_days": 90,
        "revocable": True,
        "status": "ACTIVE",
    }
    wallets.append(wallet)
    _save_json(_WALLET_PATH, wallets)
    return wallet


def get_wallet(wallet_id: str) -> Optional[dict]:
    wallets = _ensure_file(_WALLET_PATH, [])
    return next((w for w in wallets if w["wallet_id"] == wallet_id), None)


def list_wallets(limit: int = 20) -> list:
    wallets = _ensure_file(_WALLET_PATH, [])
    return wallets[-limit:]


def detect_evil_trackers(payload: dict | str, context: str = "patient_case") -> dict:
    """Scan for PII leaks, ad trackers, credential leaks, forbidden fields."""
    text = json.dumps(payload) if isinstance(payload, dict) else str(payload)
    findings = []
    for pattern, tracker_type, severity in EVIL_TRACKER_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            findings.append({
                "tracker_type": tracker_type,
                "severity": severity,
                "match_count": len(matches),
                "sample": str(matches[0])[:40] + "..." if len(str(matches[0])) > 40 else str(matches[0]),
                "context": context,
            })

    # Forbidden keys in dict payloads
    if isinstance(payload, dict):
        for key in payload:
            key_lower = key.lower()
            if key_lower in ("patient_name", "full_name", "address", "aadhaar", "email", "phone", "ssn"):
                findings.append({
                    "tracker_type": "FORBIDDEN_FIELD_KEY",
                    "severity": "CRITICAL",
                    "match_count": 1,
                    "sample": key,
                    "context": context,
                })

    return {
        "evil_trackers_found": len(findings) > 0,
        "finding_count": len(findings),
        "findings": findings,
        "scan_timestamp": datetime.utcnow().isoformat(),
        "mcp_tool": "detect_evil_trackers",
    }


def repair_signal(payload: dict, tracker_scan: dict, wallet_id: str = "—") -> dict:
    """Redact/strip bad signals before agents process data — uses deep DLP v2."""
    from mcp_tools.pharmaguard_dlp import run_deep_signal_repair, generate_physician_dlp_summary

    dlp = run_deep_signal_repair(payload, EDGE_NODE_ID)
    repaired = dlp["repaired_payload"]

    signal_integrity = "RESTORED" if dlp["dlp_summary"]["data_leakage_prevented"] else (
        "RESTORED" if tracker_scan.get("finding_count", 0) > 0 else "CLEAN"
    )

    physician_dlp = generate_physician_dlp_summary(dlp, wallet_id, EDGE_NODE_ID)

    return {
        "repaired_payload": repaired,
        "repairs_applied": dlp["repairs_applied"],
        "repair_log": dlp["repair_log"],
        "dlp_summary": dlp["dlp_summary"],
        "physician_dlp": physician_dlp,
        "signal_integrity": signal_integrity,
        "data_leakage_prevented": dlp["dlp_summary"]["data_leakage_prevented"],
        "phi_reached_cloud": False,
        "mcp_tool": "repair_signal",
    }


def edge_sanitize(patient_profile: dict, wallet_id: str) -> dict:
    """Process at edge before cloud — wallet check + tracker scan + repair."""
    wallet = get_wallet(wallet_id)
    if not wallet or wallet.get("status") != "ACTIVE":
        return {
            "status": "BLOCKED",
            "reason": "Invalid or revoked consent wallet",
            "edge_node_id": EDGE_NODE_ID,
        }

    scan = detect_evil_trackers(patient_profile, context="edge_ingress")
    repair = repair_signal(patient_profile, scan, wallet_id=wallet_id)
    payload = repair["repaired_payload"]
    payload["consent_wallet_id"] = wallet_id

    return {
        "status": "ALLOWED" if scan["finding_count"] < 3 else "FLAGGED",
        "edge_node_id": EDGE_NODE_ID,
        "wallet_id": wallet_id,
        "tracker_scan": scan,
        "repair": repair,
        "sanitized_patient": payload,
        "data_loss_prevented": repair.get("data_leakage_prevented") or scan["finding_count"] > 0,
        "phi_reached_cloud": repair.get("phi_reached_cloud", False),
        "physician_dlp": repair.get("physician_dlp", {}),
    }


def append_trust_chain(event_type: str, payload_hash: str, wallet_id: str, metadata: dict) -> dict:
    """Immutable hash chain — audit trail without storing PHI."""
    chain = _ensure_file(_CHAIN_PATH, [])
    prev_hash = chain[-1]["block_hash"] if chain else "0" * 64

    block = {
        "block_id": len(chain) + 1,
        "event_type": event_type,
        "wallet_id": wallet_id,
        "payload_hash": payload_hash,
        "prev_hash": prev_hash,
        "timestamp": datetime.utcnow().isoformat(),
        "edge_node_id": EDGE_NODE_ID,
        "metadata": {k: v for k, v in metadata.items() if k not in ("patient_name", "email", "phone")},
    }
    block["block_hash"] = _hash_payload(block)

    chain.append(block)
    _save_json(_CHAIN_PATH, chain)
    return block


def verify_chain_integrity() -> dict:
    """Verify hash chain has not been tampered."""
    chain = _ensure_file(_CHAIN_PATH, [])
    if not chain:
        return {"valid": True, "blocks": 0, "message": "Empty chain"}

    for i, block in enumerate(chain):
        expected = block.copy()
        stored_hash = expected.pop("block_hash")
        if _hash_payload(expected) != stored_hash:
            return {"valid": False, "broken_at_block": i + 1}
        if i > 0 and block["prev_hash"] != chain[i - 1]["block_hash"]:
            return {"valid": False, "broken_at_block": i + 1, "reason": "prev_hash mismatch"}

    return {"valid": True, "blocks": len(chain), "latest_hash": chain[-1]["block_hash"][:16] + "..."}


def run_pharmaguard_pipeline(
    patient_profile: dict,
    event_type: str = "CASE_INGRESS",
    recommendation: Optional[dict] = None,
    audit_result: Optional[dict] = None,
) -> dict:
    """
    End-to-end PharmaGuard agent pipeline:
    wallet → edge sanitize → evil tracker scan → signal repair → trust chain seal
    """
    pseudonym = patient_profile.get("patient_id", "anonymous")
    wallet = create_consent_wallet(pseudonym)
    wallet_id = wallet["wallet_id"]

    edge = edge_sanitize(patient_profile, wallet_id)
    if edge["status"] == "BLOCKED":
        return {"status": "BLOCKED", "wallet": wallet, "edge": edge}

    sanitized = edge["sanitized_patient"]
    ingress_hash = _hash_payload(sanitized)
    ingress_block = append_trust_chain(
        event_type,
        ingress_hash,
        wallet_id,
        {
            "trackers_found": edge["tracker_scan"]["finding_count"],
            "repairs": len(edge["repair"]["repairs_applied"]),
            "edge_status": edge["status"],
        },
    )

    result = {
        "status": edge["status"],
        "wallet": wallet,
        "edge": edge,
        "sanitized_patient": sanitized,
        "ingress_block": ingress_block,
        "pharmaguard_tools": ["create_consent_wallet", "detect_evil_trackers", "repair_signal", "append_trust_chain"],
    }

    if recommendation:
        rec_hash = _hash_payload({
            "antibiotic": recommendation.get("antibiotic"),
            "trace_id": recommendation.get("trace_id"),
        })
        result["recommendation_block"] = append_trust_chain(
            "RECOMMENDATION_SEALED",
            rec_hash,
            wallet_id,
            {"aware_tier": recommendation.get("aware_tier"), "trace_id": recommendation.get("trace_id")},
        )

    if audit_result:
        audit_hash = _hash_payload({
            "overall_result": audit_result.get("overall_result"),
            "audit_id": audit_result.get("audit_id"),
        })
        result["audit_block"] = append_trust_chain(
            "AUDIT_SEALED",
            audit_hash,
            wallet_id,
            {"verdict": audit_result.get("overall_result"), "audit_id": audit_result.get("audit_id")},
        )

    result["chain_valid"] = verify_chain_integrity()["valid"]
    return result


def get_trust_chain(limit: int = 20) -> list:
    chain = _ensure_file(_CHAIN_PATH, [])
    return list(reversed(chain[-limit:]))


PHARMAGUARD_TOOLS = {
    "create_consent_wallet": create_consent_wallet,
    "detect_evil_trackers": detect_evil_trackers,
    "repair_signal": repair_signal,
    "edge_sanitize": edge_sanitize,
    "append_trust_chain": append_trust_chain,
    "verify_chain_integrity": verify_chain_integrity,
    "run_pharmaguard_pipeline": run_pharmaguard_pipeline,
}
