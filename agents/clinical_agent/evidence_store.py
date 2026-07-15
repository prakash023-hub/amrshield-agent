"""Real-world evidence store — antibiogram, metrics, case studies."""

import json
import os
from datetime import datetime
from typing import Optional

from mcp_tools.audit_store import audit_stats, list_audit_events

_DATA_DIR = os.path.join(os.path.dirname(__file__), "../../data")
_ANTIBIOGRAM_PATH = os.path.join(_DATA_DIR, "india_reference_antibiogram.json")
_CASE_STUDIES_PATH = os.path.join(_DATA_DIR, "published_case_studies.json")
_HOSPITAL_UPLOAD_PATH = os.path.join(_DATA_DIR, "hospital_antibiogram_upload.json")


def load_reference_antibiogram() -> dict:
    with open(_ANTIBIOGRAM_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_hospital_antibiogram() -> Optional[dict]:
    if os.path.exists(_HOSPITAL_UPLOAD_PATH):
        with open(_HOSPITAL_UPLOAD_PATH, encoding="utf-8") as f:
            return json.load(f)
    return None


def get_active_antibiogram() -> dict:
    """Hospital upload overrides India reference data."""
    hospital = load_hospital_antibiogram()
    if hospital:
        return hospital
    return load_reference_antibiogram()


def load_case_studies() -> list:
    with open(_CASE_STUDIES_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_live_dashboard_metrics() -> dict:
    """Real metrics from audit log — no fake numbers."""
    stats = audit_stats()
    rows = list_audit_events(limit=500)
    access = sum(1 for r in rows if r.get("aware") == "Access")
    watch = sum(1 for r in rows if r.get("aware") == "Watch")
    reserve = sum(1 for r in rows if r.get("aware") == "Reserve")
    tier_total = access + watch + reserve
    today = datetime.utcnow().date().isoformat()
    today_count = sum(1 for r in rows if r.get("timestamp", "").startswith(today))
    flagged = sum(1 for r in rows if r.get("result") in ("FLAG", "HOLD"))

    ab = get_active_antibiogram()
    return {
        "total_recommendations": stats["total"],
        "today_recommendations": today_count,
        "audit_pass_rate_pct": round(stats["pass_rate"] * 100, 1) if stats["total"] else None,
        "access_tier_pct": round(access / tier_total * 100, 1) if tier_total else None,
        "flagged_for_review": flagged,
        "physician_reviews_pending": stats["physician_reviews_pending"],
        "antibiogram_source": ab.get("meta", {}).get("title", "Reference antibiogram"),
        "antibiogram_dataset_id": ab.get("meta", {}).get("dataset_id", "—"),
        "is_live_data": stats["total"] > 0,
        "metrics_label": "Live from audit log" if stats["total"] > 0 else "No cases yet — run Clinician Console",
    }


def get_resistance_chart_for_case(pathogen: str, infection_site: str) -> dict:
    """Pull real resistance % from active antibiogram for sidebar chart."""
    ab = get_active_antibiogram()
    orgs = ab.get("organisms", ab)  # support legacy flat dict
    if "organisms" in ab:
        orgs = ab["organisms"]

    key = pathogen.lower().strip()
    matched = None
    for ok in orgs:
        if ok in key or key in ok:
            matched = ok
            break
    if not matched:
        return {"drugs": [], "resistance_pct": [], "source": ab.get("meta", {}).get("title", "Reference")}

    sites = orgs[matched]
    site_key = infection_site.lower()
    site_data = next(
        (v for k, v in sites.items() if k in site_key or site_key in k),
        list(sites.values())[0],
    )

    drugs, resist = [], []
    for drug, val in site_data.items():
        if isinstance(val, dict):
            drugs.append(drug.title())
            resist.append(val.get("resistance_pct", 100 - val.get("susceptibility_pct", 50)))
        elif isinstance(val, (int, float)):
            drugs.append(drug.title())
            resist.append(100 - val)

    return {
        "drugs": drugs[:6],
        "resistance_pct": resist[:6],
        "pathogen": matched,
        "source": ab.get("meta", {}).get("title", "India reference antibiogram"),
        "citation": ab.get("meta", {}).get("citation", ""),
    }


def save_hospital_antibiogram(payload: dict) -> dict:
    """Save JIPMER/hospital WHONET-style upload."""
    os.makedirs(_DATA_DIR, exist_ok=True)
    payload.setdefault("meta", {})
    payload["meta"]["uploaded_at"] = datetime.utcnow().isoformat()
    payload["meta"]["dataset_id"] = payload["meta"].get("dataset_id", "HOSPITAL-UPLOAD")
    with open(_HOSPITAL_UPLOAD_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return payload
