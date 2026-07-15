"""Stewardship alerts, overrides, and antibiotic time-out tracking."""

import json
import os
from datetime import datetime
from typing import Optional

_STORE_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_OVERRIDES_PATH = os.path.join(_STORE_DIR, "audit_overrides.json")
_TIMEOUTS_PATH = os.path.join(_STORE_DIR, "antibiotic_timeouts.json")
_ALERTS_PATH = os.path.join(_STORE_DIR, "stewardship_alerts.json")


def _load(path: str, default):
    os.makedirs(_STORE_DIR, exist_ok=True)
    if not os.path.exists(path):
        return default if not isinstance(default, list) else list(default)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save(path: str, data):
    os.makedirs(_STORE_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


DEFAULT_ALERTS = [
    {
        "alert_id": "ALT-MRSA-ICU",
        "level": "HIGH",
        "dept": "ICU",
        "msg": "MRSA cluster — 3 cases in 7 days",
        "escalate_to": "ID on-call + Infection Control",
        "status": "OPEN",
        "created_at": datetime.utcnow().isoformat(),
    },
    {
        "alert_id": "ALT-ESBL-SURG",
        "level": "HIGH",
        "dept": "Surgery",
        "msg": "ESBL E. coli UTI isolates — 34% non-susceptibility this month (ICMR reference)",
        "escalate_to": "Surgery AMS lead + Microbiology",
        "status": "OPEN",
        "created_at": datetime.utcnow().isoformat(),
    },
]


def get_active_alerts() -> list:
    alerts = _load(_ALERTS_PATH, DEFAULT_ALERTS)
    return [a for a in alerts if a.get("status") == "OPEN"]


def escalate_alert(alert_id: str, assignee: str, note: str) -> dict:
    alerts = _load(_ALERTS_PATH, DEFAULT_ALERTS)
    for a in alerts:
        if a.get("alert_id") == alert_id:
            a["status"] = "ESCALATED"
            a["assigned_to"] = assignee
            a["escalation_note"] = note
            a["escalated_at"] = datetime.utcnow().isoformat()
            _save(_ALERTS_PATH, alerts)
            return a
    return {"error": "alert not found"}


def record_override(trace_id: str, physician_id: str, justification: str, action: str = "OVERRIDE") -> dict:
    if len(justification.strip()) < 20:
        return {"error": "Override requires ≥20 characters of clinical justification (medico-legal)"}
    rows = _load(_OVERRIDES_PATH, [])
    row = {
        "trace_id": trace_id,
        "physician_id": physician_id,
        "justification": justification.strip(),
        "action": action,
        "timestamp": datetime.utcnow().isoformat(),
    }
    rows.insert(0, row)
    _save(_OVERRIDES_PATH, rows[:200])
    return row


def schedule_antibiotic_timeout(order_id: str, patient_id: str, antibiotic: str, due_hours: int = 72) -> dict:
    from datetime import timedelta
    rows = _load(_TIMEOUTS_PATH, [])
    due = datetime.utcnow() + timedelta(hours=due_hours)
    row = {
        "order_id": order_id,
        "patient_id": patient_id,
        "antibiotic": antibiotic,
        "timeout_type": "48-72h stewardship review",
        "due_at": due.isoformat(),
        "status": "PENDING",
        "actions": ["Review culture", "De-escalate if able", "IV-to-PO", "Set stop date"],
    }
    rows.insert(0, row)
    _save(_TIMEOUTS_PATH, rows[:300])
    return row


def get_pending_timeouts() -> list:
    rows = _load(_TIMEOUTS_PATH, [])
    return [r for r in rows if r.get("status") == "PENDING"]


def list_overrides(limit: int = 20) -> list:
    return _load(_OVERRIDES_PATH, [])[:limit]
