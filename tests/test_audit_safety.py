"""Self-audit regressions with synthetic profiles and offline services."""

import json
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from google.genai.errors import APIError

from agents.audit_agent import agent as audit_agent
from agents.clinical_agent import agent as clinical_agent
from agents.clinical_agent.physician_ready import enrich_for_physician
from api.main import app
from mcp_tools import audit_store, pharmaguard_trust, phoenix_integration as phoenix


PASS = {
    "overall_result": "PASS",
    "issues_found": [],
    "severity_level": "LOW",
    "recommendation_safe_to_proceed": True,
    "physician_review_required": False,
    "audit_reasoning": "No issues detected in the available checks.",
}


@pytest.fixture
def patient():
    return {
        "patient_id": "SYNTH-AUDIT",
        "age": 60,
        "weight": 72,
        "sex": "male",
        "serum_creatinine": 1.0,
        "allergies": [],
        "current_medications": [],
        "diagnosis": "Synthetic inpatient case",
        "infection_site": "Bloodstream",
    }


@pytest.fixture
def recommendation():
    return {
        "antibiotic": "meropenem",
        "drug_class": "Carbapenem",
        "aware_tier": "Watch",
        "dose": "1 g",
        "route": "IV",
        "frequency": "Every 8 hours",
        "trace_id": "TR-AUDIT-TEST",
    }


@pytest.fixture(autouse=True)
def offline_services(monkeypatch, tmp_path):
    monkeypatch.setattr(audit_store, "_STORE_PATH", str(tmp_path / "audit.json"))
    monkeypatch.setattr(pharmaguard_trust, "_WALLET_PATH", str(tmp_path / "wallets.json"))
    monkeypatch.setattr(pharmaguard_trust, "_CHAIN_PATH", str(tmp_path / "chain.json"))
    monkeypatch.setattr(phoenix, "ensure_phoenix_tracing", Mock())
    monkeypatch.setitem(phoenix.MCP_TOOLS, "fetch_phoenix_traces", Mock(return_value={"traces": []}))
    generate = Mock(return_value=SimpleNamespace(text=json.dumps(PASS)))
    monkeypatch.setattr(audit_agent, "client", SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    return generate


def assert_review(audit, verdict, issue=None):
    assert audit["overall_result"] == verdict
    assert audit["recommendation_safe_to_proceed"] is False
    assert audit["physician_review_required"] is True
    if issue:
        assert issue in {item["type"] for item in audit["issues_found"]}


@pytest.mark.parametrize("field", ["serum_creatinine", "age", "weight", "sex"])
def test_missing_renal_fields_hold(patient, recommendation, offline_services, field):
    del patient[field]
    audit = audit_agent.run_audit_agent(recommendation, patient)
    assert_review(audit, "HOLD", "MISSING_CLINICAL_DATA")
    assert field in audit["audit_reasoning"]
    offline_services.assert_not_called()


@pytest.mark.parametrize("field", ["serum_creatinine", "age", "weight", "sex"])
@pytest.mark.parametrize("value", ["", "  ", None])
def test_blank_and_null_values_hold(patient, recommendation, offline_services, field, value):
    patient[field] = value
    assert_review(audit_agent.run_audit_agent(recommendation, patient), "HOLD", "MISSING_CLINICAL_DATA")
    offline_services.assert_not_called()


@pytest.mark.parametrize("field,value", [
    ("serum_creatinine", 0), ("serum_creatinine", -1), ("serum_creatinine", float("nan")),
    ("serum_creatinine", float("inf")), ("serum_creatinine", float("-inf")),
    ("serum_creatinine", "unknown"), ("serum_creatinine", True),
    ("age", 0), ("age", 17), ("age", 121), ("age", "unknown"), ("age", float("inf")), ("age", True),
    ("weight", -1), ("weight", 0), ("weight", 401), ("weight", "unknown"),
    ("weight", float("nan")), ("weight", True),
    ("sex", "unknown"), ("sex", "other"), ("sex", 0),
])
def test_invalid_renal_fields_hold(patient, recommendation, offline_services, field, value):
    patient[field] = value
    assert_review(audit_agent.run_audit_agent(recommendation, patient), "HOLD", "INVALID_RENAL_PARAMETERS")
    offline_services.assert_not_called()


def test_allergy_conflict_blocks_even_if_model_would_pass(patient, offline_services):
    patient["allergies"] = ["Penicillin (anaphylaxis)"]
    recommendation = {"antibiotic": "amoxicillin-clavulanate", "aware_tier": "Access"}
    audit = audit_agent.run_audit_agent(recommendation, patient)
    assert_review(audit, "HOLD", "ALLERGY_CONFLICT")
    offline_services.assert_not_called()

    # Also exercise the verdict merge directly with an actual PASS payload.
    pipeline = phoenix.run_phoenix_mcp_audit_pipeline(recommendation, patient, "TR-ALLERGY")
    assert_review(phoenix.merge_mcp_into_audit(PASS, pipeline), "HOLD", "ALLERGY_CONFLICT")


def test_invalid_allergy_entry_cannot_hide_known_conflict(patient, offline_services):
    patient["allergies"] = [None, "Penicillin (anaphylaxis)"]
    audit = audit_agent.run_audit_agent({"antibiotic": "amoxicillin-clavulanate"}, patient)
    assert_review(audit, "HOLD", "ALLERGY_CONFLICT")
    offline_services.assert_not_called()


@pytest.mark.parametrize("antibiotic,scr,verdict", [
    ("meropenem", 2.0, "FLAG"),
    ("meropenem", 21.0, "FLAG"),
    ("nitrofurantoin", 3.0, "HOLD"),
])
def test_renal_dose_flags_override_pass(patient, recommendation, antibiotic, scr, verdict):
    patient["serum_creatinine"] = scr
    recommendation["antibiotic"] = antibiotic
    recommendation["aware_tier"] = "Access" if antibiotic == "nitrofurantoin" else "Watch"
    assert_review(audit_agent.run_audit_agent(recommendation, patient), verdict, "RENAL_DOSE_ADJUSTMENT")


def test_rounding_cannot_clear_a_renal_cutoff(patient):
    patient["serum_creatinine"] = 80 / 29.98
    recommendation = {"antibiotic": "nitrofurantoin", "aware_tier": "Access"}
    assert_review(audit_agent.run_audit_agent(recommendation, patient), "HOLD", "RENAL_DOSE_ADJUSTMENT")


def test_valid_inputs_pass_with_separately_labeled_units(patient, recommendation, offline_services):
    patient.update(sex=" F ", serum_creatinine=1.2)
    result = audit_agent.run_audit_agent(recommendation, patient)
    assert result["overall_result"] == "PASS", result
    assert result["recommendation_safe_to_proceed"] is True
    assert result["physician_review_required"] is False
    prompt = offline_services.call_args.kwargs["contents"]
    assert '"serum_creatinine_mg_dl": 1.2' in prompt
    prompt_patient = json.loads(prompt.split("PATIENT: ", 1)[1].split("\n", 1)[0])
    assert prompt_patient["estimated_crcl_ml_min"] == pytest.approx(56.6666667)
    assert patient["patient_id"] not in prompt


@pytest.mark.parametrize("failure", [TimeoutError(), APIError(503, {"error": {"message": "Unavailable"}})])
def test_gemini_service_failure_holds(patient, recommendation, offline_services, failure):
    offline_services.side_effect = failure
    assert_review(audit_agent.run_audit_agent(recommendation, patient), "HOLD", "GEMINI_AUDIT_UNAVAILABLE")


@pytest.mark.parametrize("text", [
    "{bad json", "[]", "{}", '{"overall_result":"PASS"}',
    json.dumps(PASS).replace('{"overall_result"', '{"overall_result":"HOLD","overall_result"'),
    json.dumps({**PASS, "issues_found": ["something"]}),
    json.dumps({**PASS, "recommendation_safe_to_proceed": "true"}),
])
def test_malformed_gemini_results_hold(patient, recommendation, offline_services, text):
    offline_services.return_value = SimpleNamespace(text=text)
    assert_review(audit_agent.run_audit_agent(recommendation, patient), "HOLD", "GEMINI_AUDIT_UNAVAILABLE")


@pytest.mark.parametrize("overrides", [
    {"physician_review_required": True},
    {"recommendation_safe_to_proceed": False},
])
def test_model_review_and_proceed_flags_are_preserved(patient, recommendation, offline_services, overrides):
    offline_services.return_value = SimpleNamespace(text=json.dumps({**PASS, **overrides}))
    audit = audit_agent.run_audit_agent(recommendation, patient)
    assert_review(audit, "FLAG")
    assert audit["review_hold"]["status"] == "PENDING_PHYSICIAN_REVIEW"


def test_upstream_review_flag_is_preserved(patient, recommendation):
    recommendation["safe_to_sign"] = False
    assert_review(audit_agent.run_audit_agent(recommendation, patient), "FLAG", "CLINICAL_REVIEW_REQUIRED")


@pytest.mark.parametrize("drug,meds,issue", [
    ("nonexistent-mycin", [], "UNKNOWN_ANTIBIOTIC"),
    ("meropenem", ["amlodipine"], "INTERACTION_NOT_SCREENED"),
    ("meropenem", None, "INTERACTION_NOT_SCREENED"),
    ("ciprofloxacin", ["warfarin"], "DRUG_INTERACTION"),
])
def test_interaction_uncertainty_and_known_conflicts_require_review(patient, recommendation, drug, meds, issue):
    patient["current_medications"] = meds
    assert_review(audit_agent.run_audit_agent({**recommendation, "antibiotic": drug, "aware_tier": ""}, patient), "FLAG", issue)


@pytest.mark.parametrize("tool", ["detect_hallucination", "evaluate_clinical_accuracy"])
def test_phoenix_safety_tool_error_holds(patient, recommendation, offline_services, monkeypatch, tool):
    monkeypatch.setitem(phoenix.MCP_TOOLS, tool, Mock(side_effect=RuntimeError("MCP unavailable")))
    assert_review(audit_agent.run_audit_agent(recommendation, patient), "HOLD", "AUDIT_CHECK_UNAVAILABLE")
    offline_services.assert_not_called()


def test_review_tool_failure_preserves_and_records_hold(patient, recommendation, monkeypatch):
    del patient["age"]
    review = Mock(side_effect=RuntimeError("Review tool unavailable"))
    monkeypatch.setitem(phoenix.MCP_TOOLS, "flag_for_review", review)
    audit = audit_agent.run_audit_agent(recommendation, patient)
    assert_review(audit, "HOLD", "MISSING_CLINICAL_DATA")
    assert audit["review_hold"] is None
    assert audit_store.list_audit_events()[0]["result"] == "HOLD"
    review.assert_called_once()


def test_phoenix_trace_fetch_uses_local_fallback(patient, recommendation, monkeypatch):
    unavailable = Mock(side_effect=ConnectionError("Phoenix unavailable"))
    monkeypatch.setitem(sys.modules, "phoenix", SimpleNamespace(Client=unavailable))
    monkeypatch.setitem(phoenix.MCP_TOOLS, "fetch_phoenix_traces", phoenix.fetch_phoenix_traces)
    audit_store.append_audit_event({"result": "HOLD"})
    pipeline = phoenix.run_phoenix_mcp_audit_pipeline(recommendation, patient, "TR-FALLBACK")
    assert pipeline["recent_traces"]["source"] == "audit_store"
    assert pipeline["recent_traces"]["traces"][0]["result"] == "HOLD"
    assert audit_agent.run_audit_agent(recommendation, patient)["overall_result"] == "PASS"


def test_hold_is_persisted_and_sealed(patient, recommendation):
    del patient["serum_creatinine"]
    audit = audit_agent.run_audit_agent(recommendation, patient)
    row, = audit_store.list_audit_events()
    assert row["result"] == "HOLD"
    assert row["physician_review"] is True
    assert row["trace_id"] == audit["phoenix_trace_id"] == recommendation["trace_id"]
    assert "serum_creatinine" in row["audit_reasoning"]
    assert patient["patient_id"] not in json.dumps(row)
    assert audit["pharmaguard"]["chain_valid"] is True
    assert audit["pharmaguard"]["audit_block_id"]


def test_invalid_profile_stops_recommendation_and_order_enrichment(patient, recommendation, monkeypatch):
    del patient["weight"]
    generate = Mock()
    monkeypatch.setattr(clinical_agent, "client", SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    generated = clinical_agent.run_clinical_agent(patient)
    assert generated["physician_review_required"] is True
    generate.assert_not_called()
    enriched = enrich_for_physician(recommendation, patient)
    assert enriched["safe_to_sign"] is False
    assert "physician_order" not in enriched


@pytest.mark.parametrize("change,expected", [("pediatric", "HOLD"), ("omitted_history", "FLAG"), ("valid", "PASS")])
def test_recommend_route_preserves_audit_decision(patient, recommendation, monkeypatch, change, expected):
    recommendation["safe_to_sign"] = True
    clinical = Mock(return_value=recommendation)
    if change == "pediatric":
        clinical = clinical_agent.run_clinical_agent
        patient["age"] = 17
    elif change == "omitted_history":
        del patient["current_medications"]
    monkeypatch.setattr(app.state, "run_clinical", clinical, raising=False)
    monkeypatch.setattr(app.state, "run_audit", audit_agent.run_audit_agent, raising=False)
    response = TestClient(app).post("/recommend", json=patient)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["audit"]["overall_result"] == expected
    assert body["safe_to_proceed"] is (expected == "PASS")
    assert body["physician_review_required"] is (expected != "PASS")
    if change == "omitted_history":
        assert body["recommendation"]["safe_to_sign"] is False


def test_api_preserves_validation_error_contract(patient, monkeypatch):
    clinical = Mock()
    monkeypatch.setattr(app.state, "run_clinical", clinical, raising=False)
    del patient["serum_creatinine"]
    api = TestClient(app)
    assert api.post("/recommend", json=patient).status_code == 422
    patient["serum_creatinine"] = True
    assert api.post("/recommend", json=patient).status_code == 422
    patient["serum_creatinine"] = "Infinity"
    assert api.post("/recommend", json=patient).status_code == 422
    clinical.assert_not_called()


@pytest.mark.parametrize("field,value", [("dose", None), ("route", " "), ("frequency", "TBD"), ("dose", 1)])
def test_incomplete_regimen_holds(patient, recommendation, offline_services, field, value):
    recommendation[field] = value
    audit = audit_agent.run_audit_agent(recommendation, patient)
    assert_review(audit, "HOLD", "INCOMPLETE_REGIMEN")
    offline_services.assert_not_called()


def test_drug_only_recommendation_holds(patient, offline_services):
    audit = audit_agent.run_audit_agent({"antibiotic": "meropenem"}, patient)
    assert_review(audit, "HOLD", "INCOMPLETE_REGIMEN")
    offline_services.assert_not_called()


@pytest.mark.parametrize("entry", ["Vancomycin (anaphylaxis)", "vancomycin: anaphylaxis", "VANCOMYCIN — anaphylaxis"])
def test_named_drug_allergy_with_reaction_holds(patient, recommendation, offline_services, entry):
    patient["allergies"] = [entry]
    recommendation["antibiotic"] = "vancomycin"
    audit = audit_agent.run_audit_agent(recommendation, patient)
    assert_review(audit, "HOLD", "ALLERGY_CONFLICT")
    offline_services.assert_not_called()


def test_named_drug_match_requires_full_name(patient, recommendation):
    patient["allergies"] = ["Vancomycin-like compound (anaphylaxis)"]
    recommendation["antibiotic"] = "vancomycin"
    audit = audit_agent.run_audit_agent(recommendation, patient)
    assert audit["overall_result"] == "PASS"


@pytest.mark.parametrize("drug", ["piperacillin-tazobactam", "ceftriaxone", "meropenem"])
def test_broad_beta_lactam_label_blocks_proceeding_without_absolute_contraindication(
    patient, recommendation, drug
):
    patient["allergies"] = ["Beta-lactam allergy"]
    recommendation.update(antibiotic=drug, drug_class="")
    audit = audit_agent.run_audit_agent(recommendation, patient)
    assert_review(audit, "FLAG", "ALLERGY_REVIEW_REQUIRED")
    assert not any(issue["type"] == "ALLERGY_CONFLICT" for issue in audit["issues_found"])
    order = enrich_for_physician(recommendation, patient)
    assert order["safe_to_sign"] is False
    assert order["allergy_screen"]["severity"] == "HIGH"


def test_specific_allergy_still_holds_with_broad_label(patient, recommendation, offline_services):
    patient["allergies"] = ["β-lactam allergy", "Ceftriaxone (anaphylaxis)"]
    recommendation["antibiotic"] = "ceftriaxone"
    audit = audit_agent.run_audit_agent(recommendation, patient)
    assert_review(audit, "HOLD", "ALLERGY_CONFLICT")
    offline_services.assert_not_called()


def test_broad_beta_lactam_label_does_not_flag_unrelated_drug(patient, recommendation):
    patient["allergies"] = ["Beta-lactam allergy"]
    recommendation.update(antibiotic="vancomycin", drug_class="Glycopeptide")
    assert audit_agent.run_audit_agent(recommendation, patient)["overall_result"] == "PASS"


@pytest.mark.parametrize("medication,route,expected", [
    ("calcium carbonate", "IV", None),
    ("oral calcium gluconate", "IV", None),
    ("calcium gluconate IV", "IV", "HIGH"),
    ("lactated Ringer's", "IV", "HIGH"),
    ("calcium gluconate", "IV", "UNKNOWN"),
    ("calcium gluconate IV", "IM", None),
    ("calcium chloride injection", "", "HIGH"),
])
def test_ceftriaxone_calcium_screen_respects_both_routes(medication, route, expected):
    from agents.clinical_agent.tools import check_drug_interactions

    result = check_drug_interactions("ceftriaxone", [medication], route=route)
    assert [item["severity"] for item in result["interactions_found"]] == (
        [expected] if expected else []
    )
    assert result["requires_review"] == bool(expected)


@pytest.mark.parametrize("medication,expected_interaction", [
    ("calcium carbonate 500 mg tablet", False), ("IV calcium chloride", True), ("calcium", True),
])
def test_ceftriaxone_calcium_audit_distinguishes_known_oral_and_uncertain_routes(
    patient, recommendation, medication, expected_interaction
):
    patient["current_medications"] = [medication]
    recommendation.update(antibiotic="ceftriaxone", drug_class="Cephalosporin")
    audit = audit_agent.run_audit_agent(recommendation, patient)
    # Other coverage limits are still reported for non-empty medication lists.
    assert ("DRUG_INTERACTION" in {issue["type"] for issue in audit["issues_found"]}) == expected_interaction
