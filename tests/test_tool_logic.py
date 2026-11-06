"""
Regression tests for the clinical tool-logic fixes.

These lock in the bugs found in review: the CrCl sex-validation gap, renal-dose
coverage, brittle allergy matching, the serotonin-syndrome interaction miss, the
empty-string AWaRe lookup, and the antibiogram site mislabel. Run: pytest -q
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.clinical_agent.tools import (  # noqa: E402
    calculate_crcl,
    check_allergy_conflict,
    check_drug_interactions,
    lookup_aware_tier,
    query_local_antibiogram,
    suggest_renal_dose,
)


# ── CrCl sex validation ──────────────────────────────────────────────

def test_crcl_rejects_unrecognised_sex():
    assert "error" in calculate_crcl(60, 70, 1.0, "unknown")


def test_crcl_m_and_male_agree():
    # "M" must not be silently treated as female (0.85 factor).
    assert calculate_crcl(60, 70, 1.0, "M")["crcl_ml_min"] == calculate_crcl(60, 70, 1.0, "male")["crcl_ml_min"]


def test_crcl_rejects_impossible_age():
    assert "error" in calculate_crcl(150, 70, 1.0, "male")


# ── Renal dosing coverage ────────────────────────────────────────────

def test_levofloxacin_flagged_in_renal_impairment():
    # Previously absent from the table, so never flagged at any CrCl.
    assert suggest_renal_dose("levofloxacin", 35)["adjustment_required"] is True


def test_meropenem_flagged_at_crcl_40():
    assert suggest_renal_dose("meropenem", 40)["adjustment_required"] is True


# ── Allergy matching robustness ──────────────────────────────────────

def test_free_text_penicillin_allergy_is_caught():
    r = check_allergy_conflict("amoxicillin", "Aminopenicillin", ["Penicillin (anaphylaxis)"])
    assert r["conflict"] is True


def test_plural_sulfa_allergy_is_caught():
    r = check_allergy_conflict("co-trimoxazole", "Sulfonamide", ["sulfa drugs"])
    assert r["conflict"] is True


# ── Interaction matching (serotonin syndrome) ────────────────────────

def test_linezolid_plus_ssri_name_is_flagged():
    r = check_drug_interactions("linezolid", ["sertraline"])
    assert r["interaction_count"] >= 1
    assert any(i["severity"] == "HIGH" for i in r["interactions_found"])


# ── AWaRe lookup guard ───────────────────────────────────────────────

def test_empty_antibiotic_is_not_classified():
    assert lookup_aware_tier("")["aware_tier"] == "Not classified"


def test_known_antibiotic_still_resolves():
    assert lookup_aware_tier("meropenem")["aware_tier"] == "Watch"


# ── Antibiogram site honesty ─────────────────────────────────────────

def test_missing_site_is_warned_not_silently_swapped():
    r = query_local_antibiogram("E. coli", "pneumonia")  # E. coli has no pneumonia entry
    assert "site_warning" in r
