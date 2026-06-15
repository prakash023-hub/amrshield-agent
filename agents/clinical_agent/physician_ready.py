"""
Physician-ready enrichment — structured order sets, contraindications,
renal adjustments, guideline citations, and attestation workflow.
"""

from datetime import datetime
from typing import Optional

from agents.clinical_agent.tools import (
    calculate_crcl,
    check_drug_interactions,
    lookup_aware_tier,
    query_local_antibiogram,
    check_allergy_conflict,
    suggest_renal_dose,
    get_indication_guideline,
)

PHYSICIAN_DISCLAIMER = (
    "DECISION SUPPORT ONLY — Licensed physician must verify diagnosis, dose, "
    "duration, and local formulary before prescribing. Not medical advice."
)


def enrich_for_physician(recommendation: dict, patient_profile: dict) -> dict:
    """Build physician-ready order set from agent recommendation + deterministic checks."""
    age = patient_profile.get("age", 50)
    weight = patient_profile.get("weight", 70)
    sex = patient_profile.get("sex", "male")
    cr = patient_profile.get("serum_creatinine", 1.0)
    allergies = patient_profile.get("allergies", [])
    meds = patient_profile.get("current_medications", [])
    diagnosis = patient_profile.get("diagnosis", "")
    pathogen = patient_profile.get("suspected_pathogen", "Unknown")
    site = patient_profile.get("infection_site", diagnosis)

    crcl_data = calculate_crcl(age, weight, cr, sex)
    crcl = crcl_data.get("crcl_ml_min", 90)
    antibiotic = recommendation.get("antibiotic", "")

    allergy_check = check_allergy_conflict(antibiotic, recommendation.get("drug_class", ""), allergies)
    interaction_check = check_drug_interactions(antibiotic, meds) if antibiotic else {"interactions_found": []}
    renal_dose = suggest_renal_dose(antibiotic, crcl) if antibiotic else {}
    antibiogram = query_local_antibiogram(pathogen, site)
    guideline = get_indication_guideline(diagnosis, pathogen)
    aware = lookup_aware_tier(antibiotic) if antibiotic else {}

    contraindications = []
    if allergy_check.get("conflict"):
        contraindications.append({
            "type": "ALLERGY",
            "severity": "ABSOLUTE",
            "detail": allergy_check.get("message"),
        })
    for issue in interaction_check.get("interactions_found", []):
        if issue.get("severity") == "HIGH":
            contraindications.append({
                "type": "DRUG_INTERACTION",
                "severity": "HIGH",
                "detail": f"{issue.get('interacting_drug')}: {issue.get('clinical_effect')}",
            })
    if renal_dose.get("adjustment_required"):
        contraindications.append({
            "type": "RENAL",
            "severity": renal_dose.get("severity", "HIGH"),
            "detail": renal_dose.get("message"),
        })

    order_id = f"ORD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    physician_order = {
        "order_id": order_id,
        "status": "PENDING_PHYSICIAN_ATTESTATION",
        "medication": antibiotic.title() if antibiotic else "—",
        "dose": recommendation.get("dose", "—"),
        "route": recommendation.get("route", "PO"),
        "frequency": recommendation.get("frequency", "—"),
        "duration": f"{recommendation.get('duration_days', '—')} days",
        "indication": diagnosis,
        "pathogen": pathogen,
        "aware_tier": recommendation.get("aware_tier", aware.get("aware_tier", "—")),
        "dispense_as_written": False,
        "substitutions_allowed": recommendation.get("aware_tier") != "Reserve",
    }

    monitoring_labs = _build_monitoring_plan(antibiotic, crcl, contraindications)
    stewardship_actions = _stewardship_checklist(recommendation, aware, guideline)

    safe_to_sign = (
        not allergy_check.get("conflict")
        and not any(c["severity"] == "ABSOLUTE" for c in contraindications)
        and (
            recommendation.get("aware_tier") != "Reserve"
            or patient_profile.get("id_consult", False)
        )
    )

    return {
        **recommendation,
        "physician_ready": True,
        "physician_disclaimer": PHYSICIAN_DISCLAIMER,
        "order_id": order_id,
        "physician_order": physician_order,
        "renal_function": crcl_data,
        "renal_dose_adjustment": renal_dose,
        "allergy_screen": allergy_check,
        "interaction_screen": interaction_check,
        "antibiogram_summary": {
            "preferred": antibiogram.get("preferred_agents", {}),
            "alternatives": antibiogram.get("alternative_agents", {}),
            "source": antibiogram.get("data_source"),
        },
        "guideline": guideline,
        "contraindications": contraindications,
        "monitoring_labs": monitoring_labs,
        "stewardship_actions": stewardship_actions,
        "iv_to_po_criteria": _iv_to_po_criteria(antibiotic, diagnosis),
        "de_escalation_plan": _de_escalation_plan(pathogen, antibiotic),
        "safe_to_sign": safe_to_sign,
        "physician_attestation_required": True,
        "attestation_text": (
            "I have reviewed the AI recommendation, patient allergies, renal function, "
            "drug interactions, and local antibiogram. I accept clinical responsibility for this order."
        ),
    }


def _build_monitoring_plan(antibiotic: str, crcl: float, contraindications: list) -> list:
    ab = antibiotic.lower()
    labs = ["Clinical response at 48–72h", "Review culture & susceptibility when available"]
    if crcl < 60 or any(c["type"] == "RENAL" for c in contraindications):
        labs.append("Serum creatinine at 48h and 7 days")
    if "vancomycin" in ab:
        labs.extend(["Vancomycin trough (target 15–20 mg/L)", "Weekly CBC"])
    if "gentamicin" in ab or "amikacin" in ab:
        labs.extend(["Peak/trough aminoglycoside levels", "Daily renal function"])
    if "warfarin" in str(contraindications).lower() or "ciprofloxacin" in ab:
        labs.append("INR if on anticoagulation")
    if "meropenem" in ab or "piperacillin" in ab:
        labs.append("Consider LFTs at day 5 if prolonged course")
    return labs


def _stewardship_checklist(recommendation: dict, aware: dict, guideline: dict) -> list:
    items = []
    tier = recommendation.get("aware_tier", "")
    if tier == "Access":
        items.append("✅ WHO AWaRe Access tier — first-line stewardship goal met")
    elif tier == "Watch":
        items.append("⚠️ Watch tier — document indication if Access-tier alternative exists")
    elif tier == "Reserve":
        items.append("🛑 Reserve tier — ID specialist consultation required")
    items.append(f"Guideline: {guideline.get('source', 'IDSA/WHO')} — {guideline.get('first_line', 'See local policy')}")
    if recommendation.get("duration_days", 7) > 7:
        items.append("Review duration — reassess at 72h for de-escalation or IV-to-PO switch")
    return items


def _iv_to_po_criteria(antibiotic: str, diagnosis: str) -> list:
    return [
        "Hemodynamically stable ≥24h",
        "Tolerating oral intake",
        "No unresolved source control issues",
        "Oral agent with adequate bioavailability for infection site",
        f"Consider PO switch for {antibiotic} when clinical criteria met (typically day 3–5)",
    ]


def _de_escalation_plan(pathogen: str, antibiotic: str) -> dict:
    return {
        "trigger": "Culture & susceptibility results available OR clinical improvement at 72h",
        "actions": [
            "Narrow spectrum to targeted agent based on culture",
            "Step down IV → PO when clinically appropriate",
            "Shorten duration if uncomplicated infection resolving",
        ],
        "pathogen": pathogen,
        "current_empiric": antibiotic,
    }


def record_physician_attestation(order_id: str, physician_id: str, action: str = "APPROVED") -> dict:
    """Record physician sign-off (stored locally for demo)."""
    import json
    import os
    path = os.path.join(os.path.dirname(__file__), "../../data/attestations.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    records = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            records = json.load(f)
    record = {
        "order_id": order_id,
        "physician_id": physician_id,
        "action": action,
        "timestamp": datetime.utcnow().isoformat(),
    }
    records.append(record)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    return record
