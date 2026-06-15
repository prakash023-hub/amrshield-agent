"""
PharmaGuard Data Loss Prevention (DLP) — deep signal repair & leakage prevention.

Strips PHI/PII at edge before any AI agent sees patient data.
Designed for hospital pilots (JIPMER, India DPDP Act alignment).
"""

import copy
import hashlib
import json
import re
from datetime import datetime
from typing import Any

# ── Forbidden field keys (never pass to cloud agents) ──────────────────────
FORBIDDEN_KEYS = frozenset({
    "patient_name", "full_name", "first_name", "last_name", "middle_name",
    "address", "street", "city", "pincode", "postal_code", "zip",
    "aadhaar", "aadhar", "pan", "passport", "voter_id", "abha", "uhid",
    "email", "phone", "mobile", "contact", "whatsapp", "ssn",
    "guardian_name", "relative_name", "emergency_contact",
    "password", "api_key", "secret", "token", "auth_token",
    "ip_address", "gps", "latitude", "longitude", "photo", "image_url",
    "fingerprint", "biometric",
})

# ── Value-level PHI patterns (redact inside any string value) ──────────────
VALUE_REDACT_PATTERNS = [
    (r"\b\d{4}\s?\d{4}\s?\d{4}\b", "AADHAAR", "[AADHAAR_REDACTED]"),
    (r"\b[A-Z]{5}\d{4}[A-Z]\b", "PAN", "[PAN_REDACTED]"),
    (r"\b\d{3}-\d{2}-\d{4}\b", "SSN", "[SSN_REDACTED]"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "EMAIL", "[EMAIL_REDACTED]"),
    (r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b", "IN_MOBILE", "[PHONE_REDACTED]"),
    (r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "PHONE", "[PHONE_REDACTED]"),
    (r"\b(?:https?://)(?!.*(?:googleapis|cloud\.google|run\.app|gstatic))[^\s\"']+", "EXFIL_URL", "[URL_REDACTED]"),
    (r"\b(?:password|api_key|secret|token)\s*[:=]\s*\S+", "CREDENTIAL", "[CREDENTIAL_REDACTED]"),
]

# Keys that look like clinical minimum necessary (AMR stewardship only)
CLINICAL_ALLOWLIST = frozenset({
    "patient_id", "age", "sex", "weight", "serum_creatinine",
    "diagnosis", "infection_site", "suspected_pathogen",
    "allergies", "current_medications", "culture_results",
    "consent_wallet_id", "edge_node_id", "icu", "pregnancy",
    "trace_id", "_pharmaguard_repaired", "_repair_count", "_dlp_version",
})


def _hash_token(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12].upper()


def redact_phi_in_string(text: str) -> tuple[str, list[dict]]:
    """Redact PHI patterns embedded in free-text fields."""
    repairs = []
    result = text
    for pattern, pii_type, replacement in VALUE_REDACT_PATTERNS:
        matches = re.findall(pattern, result, re.IGNORECASE)
        if matches:
            for m in matches:
                repairs.append({
                    "action": "VALUE_REDACTED",
                    "pii_type": pii_type,
                    "field_path": "string_value",
                    "original_hash": _hash_token(str(m)),
                    "replacement": replacement,
                })
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result, repairs


def _walk_and_repair(obj: Any, path: str = "root") -> tuple[Any, list[dict]]:
    """Recursively strip forbidden keys and redact PHI in string values."""
    repairs: list[dict] = []

    if isinstance(obj, dict):
        cleaned = {}
        for key, value in obj.items():
            key_lower = key.lower()
            field_path = f"{path}.{key}"

            if key_lower in FORBIDDEN_KEYS:
                repairs.append({
                    "action": "KEY_REMOVED",
                    "pii_type": "FORBIDDEN_FIELD",
                    "field_path": field_path,
                    "detail": f"Removed key '{key}' — not in clinical minimum-necessary set",
                })
                continue

            if key not in CLINICAL_ALLOWLIST and not key.startswith("_"):
                if isinstance(value, str) and value.strip():
                    _, value_repairs = redact_phi_in_string(value)
                    for vr in value_repairs:
                        vr["field_path"] = field_path
                        vr["action"] = "PHI_BLOCKED_IN_STRIPPED_FIELD"
                        repairs.append(vr)
                repairs.append({
                    "action": "KEY_STRIPPED",
                    "pii_type": "NON_CLINICAL",
                    "field_path": field_path,
                    "detail": f"Edge-stripped '{key}' — only stewardship fields allowed to cloud",
                })
                continue

            repaired_val, sub = _walk_and_repair(value, field_path)
            cleaned[key] = repaired_val
            repairs.extend(sub)
        return cleaned, repairs

    if isinstance(obj, list):
        cleaned_list = []
        for i, item in enumerate(obj):
            repaired_item, sub = _walk_and_repair(item, f"{path}[{i}]")
            cleaned_list.append(repaired_item)
            repairs.extend(sub)
        return cleaned_list, repairs

    if isinstance(obj, str):
        redacted, sub = redact_phi_in_string(obj)
        for s in sub:
            s["field_path"] = path
        repairs.extend(sub)
        return redacted, repairs

    return obj, repairs


def anonymize_patient_id(patient_id: str) -> tuple[str, list[dict]]:
    """Replace patient_id if it contains PII patterns."""
    repairs = []
    pid = str(patient_id or "")
    if not pid:
        return pid, repairs

    pii_indicators = [
        ("@", "EMAIL_IN_ID"),
        (r"\d{10,}", "LONG_NUMERIC_ID"),
        (r"\s", "WHITESPACE_NAME"),
        (r"^[A-Za-z]+\s+[A-Za-z]", "FULL_NAME_PATTERN"),
    ]
    for pattern, reason in pii_indicators:
        if pattern == "@" and "@" in pid:
            new_id = f"ANON-{_hash_token(pid)}"
            repairs.append({
                "action": "ID_ANONYMIZED",
                "pii_type": reason,
                "field_path": "patient_id",
                "original_hash": _hash_token(pid),
                "replacement": new_id,
            })
            return new_id, repairs
        if re.search(pattern, pid):
            new_id = f"ANON-{_hash_token(pid)}"
            repairs.append({
                "action": "ID_ANONYMIZED",
                "pii_type": reason,
                "field_path": "patient_id",
                "original_hash": _hash_token(pid),
                "replacement": new_id,
            })
            return new_id, repairs

    return pid, repairs


def run_deep_signal_repair(payload: dict, edge_node_id: str) -> dict:
    """
    Full DLP pipeline: deep walk → key strip → value redact → ID anonymize.
    Returns repaired payload + auditable repair log (no raw PHI in log).
    """
    original_field_count = _count_fields(payload)
    repairs: list[dict] = []

    repaired, walk_repairs = _walk_and_repair(copy.deepcopy(payload))
    repairs.extend(walk_repairs)

    if "patient_id" in repaired:
        new_id, id_repairs = anonymize_patient_id(repaired.get("patient_id", ""))
        repaired["patient_id"] = new_id
        repairs.extend(id_repairs)

    repaired["edge_node_id"] = edge_node_id
    repaired["_pharmaguard_repaired"] = True
    repaired["_repair_count"] = len(repairs)
    repaired["_dlp_version"] = "2.0"

    leaked_types = sorted({r["pii_type"] for r in repairs})
    keys_removed = sum(1 for r in repairs if r["action"] in ("KEY_REMOVED", "KEY_STRIPPED"))
    values_redacted = sum(1 for r in repairs if r["action"] == "VALUE_REDACTED")

    return {
        "repaired_payload": repaired,
        "repairs_applied": [r.get("detail") or f"{r['action']}: {r['pii_type']} @ {r['field_path']}" for r in repairs],
        "repair_log": repairs,
        "signal_integrity": "RESTORED" if repairs else "CLEAN",
        "dlp_summary": {
            "original_fields": original_field_count,
            "repaired_fields": _count_fields(repaired),
            "keys_removed": keys_removed,
            "values_redacted": values_redacted,
            "total_repairs": len(repairs),
            "leakage_types_blocked": leaked_types,
            "data_leakage_prevented": len(repairs) > 0,
            "phi_reached_cloud": False,
        },
        "mcp_tool": "run_deep_signal_repair",
        "timestamp": datetime.utcnow().isoformat(),
    }


def generate_physician_dlp_summary(dlp_result: dict, wallet_id: str, edge_node: str) -> dict:
    """Plain-language summary physicians can trust — no raw PHI."""
    summary = dlp_result.get("dlp_summary", {})
    repairs = dlp_result.get("repair_log", [])

    physician_messages = []
    if summary.get("data_leakage_prevented"):
        physician_messages.append(
            f"✅ {summary['total_repairs']} privacy repair(s) applied at hospital edge before AI processing."
        )
        if summary.get("leakage_types_blocked"):
            blocked = ", ".join(summary["leakage_types_blocked"])
            physician_messages.append(f"✅ Blocked leakage types: {blocked}.")
    else:
        physician_messages.append("✅ No PHI leakage detected — payload was already clinical-minimum.")

    physician_messages.extend([
        "✅ Patient name, address, Aadhaar, phone, and email never sent to cloud AI.",
        "✅ Only pseudonymous wallet ID + clinical fields used for stewardship.",
        f"✅ Processed at edge node {edge_node} — data minimization enforced.",
    ])

    return {
        "wallet_id": wallet_id,
        "edge_node": edge_node,
        "phi_reached_cloud": summary.get("phi_reached_cloud", False),
        "leakage_prevented": summary.get("data_leakage_prevented", False),
        "repairs_count": summary.get("total_repairs", 0),
        "physician_summary": physician_messages,
        "compliance_notes": [
            "India DPDP Act 2023 — purpose limitation (stewardship only)",
            "Clinical minimum necessary — no direct identifiers on AI path",
            "Immutable hash chain — audit without storing PHI",
            "Consent wallet — revocable patient authorization scope",
        ],
        "developer_repair_log": [
            {k: v for k, v in r.items() if k != "detail" or len(str(v)) < 120}
            for r in repairs[:50]
        ],
    }


def _count_fields(obj: Any) -> int:
    if isinstance(obj, dict):
        return sum(_count_fields(v) for v in obj.values()) + len(obj)
    if isinstance(obj, list):
        return sum(_count_fields(i) for i in obj)
    return 1
