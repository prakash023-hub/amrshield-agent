"""
Unit tests for AMRShield's deterministic components.
These do not call Gemini, Vertex AI or Phoenix — they run offline.

    pytest -q
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.clinical_agent.tools import calculate_crcl, lookup_aware_tier, suggest_renal_dose  # noqa: E402
from agents.prediction_agent.agent import run_prediction_agent  # noqa: E402
from mcp_tools.phoenix_integration import detect_hallucination  # noqa: E402

CASES = os.path.join(os.path.dirname(__file__), "..", "evaluations", "synthetic_patient_cases.json")


def _uti_case():
    with open(CASES, encoding="utf-8") as f:
        return next(c for c in json.load(f) if c["case_id"] == "EVAL-UTI-001")


# ── Clinical tools ───────────────────────────────────────────

def test_crcl_matches_uti_eval_case():
    case = _uti_case()
    p = case["patient_profile"]
    crcl = calculate_crcl(p["age"], p["weight"], p["serum_creatinine"], p["sex"])["crcl_ml_min"]
    assert crcl == case["expected_outcome"]["expected_crcl_ml_min"]  # 22.8 mL/min


def test_uti_case_expects_fosfomycin_not_nitrofurantoin():
    case = _uti_case()
    assert case["expected_outcome"]["antibiotic"] == "fosfomycin"
    assert suggest_renal_dose("nitrofurantoin", 22.8)["adjustment_required"] is True


def test_aware_tiers():
    assert lookup_aware_tier("nitrofurantoin")["aware_tier"] == "Access"
    assert lookup_aware_tier("fosfomycin")["aware_tier"] == "Watch"      # oral
    assert lookup_aware_tier("fosfomycin iv")["aware_tier"] == "Reserve"


# ── Prediction agent ─────────────────────────────────────────

def test_forecast_is_deterministic():
    a = run_prediction_agent("India", "E. coli", 6)
    b = run_prediction_agent("India", "E. coli", 6)
    assert a["forecast"] == b["forecast"]
    assert len(a["forecast"]) == 6
    assert a["validated"] is False


def test_forecast_interval_contains_point():
    for row in run_prediction_agent("USA", "MRSA", 6)["forecast"]:
        assert row["lower_80"] <= row["resistance_pct"] <= row["upper_80"]


# ── Grounding / hallucination check ─────────────────────────

PATIENT = {"age": 72, "sex": "female", "weight": 54, "serum_creatinine": 1.9,
           "allergies": [], "current_medications": ["amlodipine"]}


def _check(rec, text):
    return detect_hallucination("T-1", text, {"recommendation": rec, "patient_profile": PATIENT})


def test_grounded_output_passes():
    rec = {"antibiotic": "fosfomycin", "aware_tier": "Watch"}
    r = _check(rec, "Fosfomycin single dose; CrCl 23 mL/min so nitrofurantoin avoided.")
    assert r["hallucination_detected"] is False
    assert r["faithfulness_score"] == 1.0


def test_wrong_tier_is_flagged():
    rec = {"antibiotic": "meropenem", "aware_tier": "Access"}
    r = _check(rec, "Meropenem is an Access antibiotic.")
    assert r["hallucination_detected"] is True


def test_wrong_crcl_is_flagged():
    rec = {"antibiotic": "nitrofurantoin", "aware_tier": "Access"}
    r = _check(rec, "CrCl 45 mL/min, nitrofurantoin is appropriate.")
    assert r["hallucination_detected"] is True


def test_unknown_drug_is_flagged():
    r = _check({"antibiotic": "zentramycin", "aware_tier": "Access"}, "Use zentramycin.")
    assert r["hallucination_detected"] is True
