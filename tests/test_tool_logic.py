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


def test_uncovered_antibiotic_is_not_screened_not_safe():
    # temocillin is in neither source; must never report "no interactions".
    r = check_drug_interactions("temocillin", ["warfarin"])
    assert r["screening_status"] == "NOT_SCREENED"
    assert r["requires_review"] is True
    assert "No significant interactions" not in r["summary"]


def test_covered_antibiotic_without_hits_is_screened():
    r = check_drug_interactions("ciprofloxacin", ["paracetamol"])
    assert r["screening_status"] == "SCREENED"
    assert r["interaction_count"] == 0


# ── AWaRe lookup guard ───────────────────────────────────────────────

def test_empty_antibiotic_is_not_classified():
    assert lookup_aware_tier("")["aware_tier"] == "Not classified"


def test_known_antibiotic_still_resolves():
    assert lookup_aware_tier("meropenem")["aware_tier"] == "Watch"


# ── Antibiogram site honesty ─────────────────────────────────────────

def test_missing_site_is_warned_not_silently_swapped():
    r = query_local_antibiogram("E. coli", "pneumonia")  # E. coli has no pneumonia entry
    assert "site_warning" in r


# ── DDInter subset ───────────────────────────────────────────────────

def test_ddinter_catches_clarithromycin_warfarin():
    # Previously NOT_SCREENED; DDInter grades this pair Major.
    r = check_drug_interactions("clarithromycin", ["Warfarin 5 mg"])
    assert r["screening_status"] == "SCREENED"
    assert r["interactions_found"][0]["severity"] == "HIGH"
    assert r["interactions_found"][0]["source"] == "DDInter"
    assert r["requires_review"] is True


def test_combination_antibiotic_uses_components():
    r = check_drug_interactions("co-trimoxazole", ["warfarin"])
    assert r["screening_status"] == "SCREENED"
    assert r["interaction_count"] == 1


def test_curated_text_kept_when_both_sources_match():
    r = check_drug_interactions("ciprofloxacin", ["warfarin"])
    hit = r["interactions_found"][0]
    assert "INR" in hit["clinical_effect"]
    assert hit["severity"] == "HIGH"


def test_no_hit_summary_states_partial_coverage():
    r = check_drug_interactions("azithromycin", ["paracetamol"])
    assert r["interaction_count"] == 0
    assert "cardiovascular" in r["coverage_note"]


# ── Antibiogram: ICMR AMRSN 2022 (real data) ─────────────────────────

def test_antibiogram_pools_amrsn_counts():
    # Table 2.13, E. coli urine nitrofurantoin: (5259+3625+398)/(5762+4056+469) = 90.2%
    r = query_local_antibiogram("E. coli", "UTI")
    assert r["specimen"] == "urine"
    assert r["susceptibility_data"]["nitrofurantoin"] == 90.2
    assert "AMRSN" in r["data_source"]


def test_antibiogram_icu_setting_uses_icu_counts_only():
    # Table 2.13, E. coli urine nitrofurantoin ICU: 398/469 = 84.9%
    r = query_local_antibiogram("E. coli", "UTI", "ICU")
    assert r["susceptibility_data"]["nitrofurantoin"] == 84.9


def test_reserve_agents_never_preferred():
    r = query_local_antibiogram("E. coli", "UTI")
    assert "colistin" not in r["preferred_agents"]
    assert "colistin" in r["reserve_agents"]


def test_small_samples_are_not_reported():
    # Table 2.18, E. coli pus nitrofurantoin: 22/28 isolates pooled -> below 30, suppressed
    r = query_local_antibiogram("E. coli", "skin")
    assert "nitrofurantoin" not in r["susceptibility_data"]
    assert r["isolates_tested"]["nitrofurantoin"] < 30


def test_mrsa_request_carries_mixed_population_warning():
    r = query_local_antibiogram("MRSA", "skin")
    assert "MRSA and MSSA" in r["note"]
    assert "cefoxitin" not in r["preferred_agents"]
