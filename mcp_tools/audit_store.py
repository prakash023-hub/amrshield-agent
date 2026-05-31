"""
Persistent audit event store — backs Audit Console when Phoenix is offline.
Every Self-Audit Agent run appends a row here.
"""

import json
import os
import threading
from datetime import datetime
from typing import Optional

_STORE_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_STORE_PATH = os.path.join(_STORE_DIR, "audit_log.json")
_LOCK = threading.Lock()
_MAX_ENTRIES = 500


def _ensure_store() -> list:
    os.makedirs(_STORE_DIR, exist_ok=True)
    if not os.path.exists(_STORE_PATH):
        with open(_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)
        return []
    with open(_STORE_PATH, encoding="utf-8") as f:
        return json.load(f)


def append_audit_event(event: dict) -> dict:
    """Append an audit record and return the stored row."""
    row = {
        "trace_id": event.get("trace_id", f"TR-{datetime.utcnow().strftime('%H%M%S')}"),
        "time": event.get("time") or datetime.utcnow().strftime("%H:%M:%S"),
        "timestamp": event.get("timestamp") or datetime.utcnow().isoformat(),
        "antibiotic": event.get("antibiotic", "unknown"),
        "diagnosis": event.get("diagnosis", "unknown"),
        "result": event.get("result", "PASS"),
        "confidence": float(event.get("confidence", 0.75)),
        "latency_ms": int(event.get("latency_ms", 0)),
        "hallucination": bool(event.get("hallucination", False)),
        "flag_count": int(event.get("flag_count", 0)),
        "aware": event.get("aware", "Access"),
        "physician_review": bool(event.get("physician_review", False)),
        "audit_reasoning": event.get("audit_reasoning", ""),
        "phoenix_mcp_tools": event.get("phoenix_mcp_tools", []),
        "source": event.get("source", "self-audit-agent"),
    }
    with _LOCK:
        rows = _ensure_store()
        rows.insert(0, row)
        rows = rows[:_MAX_ENTRIES]
        with open(_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)
    return row


def list_audit_events(limit: int = 50) -> list:
    with _LOCK:
        rows = _ensure_store()
    return rows[:limit]


def audit_stats() -> dict:
    rows = list_audit_events(limit=_MAX_ENTRIES)
    if not rows:
        return {
            "total": 0,
            "pass_rate": 0.0,
            "flag_rate": 0.0,
            "hold_rate": 0.0,
            "hallucinations_detected_today": 0,
            "physician_reviews_pending": 0,
        }
    total = len(rows)
    pass_c = sum(1 for r in rows if r.get("result") == "PASS")
    flag_c = sum(1 for r in rows if r.get("result") == "FLAG")
    hold_c = sum(1 for r in rows if r.get("result") == "HOLD")
    today = datetime.utcnow().date().isoformat()
    hallucinations_today = sum(
        1 for r in rows
        if r.get("hallucination") and r.get("timestamp", "").startswith(today)
    )
    pending = sum(1 for r in rows if r.get("physician_review"))
    return {
        "total": total,
        "pass_rate": round(pass_c / total, 3),
        "flag_rate": round(flag_c / total, 3),
        "hold_rate": round(hold_c / total, 3),
        "hallucinations_detected_today": hallucinations_today,
        "physician_reviews_pending": pending,
    }
