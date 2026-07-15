"""
Clinical safety enrichment — comorbidities, dialysis, IBW, pediatrics, TDM,
de-escalation, antibiotic time-out, and confidence gating for audit.
"""

from datetime import datetime, timedelta
from typing import Optional

from agents.clinical_agent.tools import calculate_crcl, check_allergy_conflict, suggest_renal_dose

CONFIDENCE_PASS_THRESHOLD = 0.75


def ideal_body_weight(height_cm: float, sex: str) -> float:
    """Devine formula — kg."""
    if sex == "male":
        return 50 + 2.3 * max(0, (height_cm - 152.4) / 2.54)
    return 45.5 + 2.3 * max(0, (height_cm - 152.4) / 2.54)


def adjusted_body_weight(actual_kg: float, ibw: float) -> float:
    if actual_kg <= ibw:
        return actual_kg
    return ibw + 0.4 * (actual_kg - ibw)


def enrich_clinical_profile(patient: dict) -> dict:
    """Compute derived clinical fields from expanded intake."""
    age = patient.get("age", 50)
    weight = patient.get("weight", 70)
    height = patient.get("height_cm", 170)
    sex = patient.get("sex", "male")
    cr = patient.get("serum_creatinine", 1.0)
    bmi = weight / ((height / 100) ** 2) if height else None

    ibw = ideal_body_weight(height, sex)
    abw = adjusted_body_weight(weight, ibw)
    use_weight = abw if bmi and bmi >= 30 else weight

    crcl_cg = calculate_crcl(age, use_weight, cr, sex)
    crcl_val = crcl_cg.get("crcl_ml_min", 90)

    egfr_note = "Use CKD-EPI in production EMR; Cockcroft-Gault shown for renal dosing"
    if patient.get("on_dialysis"):
        crcl_val = 0
        crcl_cg = {**crcl_cg, "crcl_ml_min": 0, "renal_category": "DIALYSIS", "note": "CrCl not used — dialysis dosing rules apply"}

    warnings = []
    comorbidities = patient.get("comorbidities", [])
    if "CKD" in comorbidities or "diabetes" in comorbidities:
        warnings.append("Metabolic comorbidity — verify renal dosing and glycemic agents")
    if patient.get("immunocompromised"):
        warnings.append("Immunocompromised — consider broader empiric coverage; ID consult if severe")
    if patient.get("prior_antibiotics_90d"):
        warnings.append(f"Prior antibiotics ({', '.join(patient['prior_antibiotics_90d'])}) — avoid duplicative class; resistance risk")
    if patient.get("acquisition") in ("Hospital-acquired", "Healthcare-associated"):
        warnings.append("HCAI/HAP — anti-pseudomonal and MRSA risk factors per IDSA")
    if patient.get("pregnancy") and patient.get("pregnancy_trimester") == "3rd trimester":
        warnings.append("3rd trimester — avoid nitrofurantoin near term; obstetric review")
    if age < 18:
        warnings.append("Pediatric patient — weight-based mg/kg dosing required; adult rules insufficient")
    if patient.get("child_pugh") in ("B", "C"):
        warnings.append(f"Child-Pugh {patient['child_pugh']} — adjust hepatically cleared agents")

    return {
        **patient,
        "bmi": round(bmi, 1) if bmi else None,
        "ibw_kg": round(ibw, 1),
        "dosing_weight_kg": round(use_weight, 1),
        "renal_function": crcl_cg,
        "egfr_note": egfr_note,
        "clinical_warnings": warnings,
    }


def build_tdm_plan(antibiotic: str) -> list:
    ab = antibiotic.lower()
    plan = []
    if "vancomycin" in ab:
        plan.extend([
            "Vancomycin TDM: trough 15–20 mg/L (serious infection) or AUC/MIC 400–600",
            "Repeat trough before 4th dose; adjust interval for renal function",
        ])
    if "gentamicin" in ab or "amikacin" in ab:
        plan.extend(["Aminoglycoside TDM: peak/trough per extended-interval protocol", "Daily renal function while on therapy"])
    if "meropenem" in ab and "dialysis" in ab:
        plan.append("Meropenem post-HD supplemental dose if on intermittent dialysis")
    return plan


def build_de_escalation_plan(patient: dict, recommendation: dict) -> dict:
    """Culture-directed de-escalation when susceptibilities available."""
    culture = patient.get("culture_results") or {}
    org = culture.get("organism", "")
    sens = culture.get("susceptible", [])
    current = recommendation.get("antibiotic", "")

    if not org or not sens:
        return {
            "status": "PENDING_CULTURE",
            "trigger": "48–72h antibiotic time-out OR culture & susceptibility available",
            "actions": [
                "Reassess clinical response at 48–72h",
                "Review cultures — narrow to targeted agent",
                "IV-to-PO switch when clinically stable",
                "Set hard stop date on order (duration field)",
            ],
            "timeout_due": (datetime.utcnow() + timedelta(hours=72)).strftime("%Y-%m-%d %H:%M UTC"),
        }

    targeted = [s for s in sens if s.lower() in current.lower() or current.lower() in s.lower()]
    narrow_options = [s for s in sens if s.lower() != current.lower()]

    return {
        "status": "CULTURE_AVAILABLE",
        "organism": org,
        "current_empiric": current,
        "culture_confirms_current": bool(targeted),
        "narrow_to": narrow_options[:3] if narrow_options else sens,
        "recommended_action": (
            f"De-escalate to {narrow_options[0]} PO if susceptible and clinically stable"
            if narrow_options else f"Continue {current} — culture supports current agent"
        ),
        "timeout_due": (datetime.utcnow() + timedelta(hours=48)).strftime("%Y-%m-%d %H:%M UTC"),
        "stop_date": (datetime.utcnow() + timedelta(days=recommendation.get("duration_days", 7))).strftime("%Y-%m-%d"),
    }


def apply_confidence_gate(recommendation: dict, audit_result: dict) -> dict:
    """Force FLAG/HOLD if AI confidence below clinical release threshold."""
    conf = float(recommendation.get("confidence_score", 0.75))
    if conf < CONFIDENCE_PASS_THRESHOLD:
        audit_result["overall_result"] = "FLAG" if conf >= 0.60 else "HOLD"
        audit_result["physician_review_required"] = True
        audit_result["recommendation_safe_to_proceed"] = False
        audit_result.setdefault("issues_found", []).append({
            "type": "LOW_CONFIDENCE",
            "severity": "HIGH",
            "message": f"AI confidence {conf:.0%} below release threshold {CONFIDENCE_PASS_THRESHOLD:.0%} — mandatory physician review",
        })
        audit_result["audit_reasoning"] = (
            audit_result.get("audit_reasoning", "") + f" Confidence gate: {conf:.2f} < {CONFIDENCE_PASS_THRESHOLD}."
        ).strip()
    return audit_result


def detect_hallucination_details(recommendation: dict, patient: dict) -> dict:
    """Specific hallucination / unsupported claim detection for audit UI."""
    findings = []
    rationale = (recommendation.get("rationale") or "").lower()
    ab = (recommendation.get("antibiotic") or "").lower()
    dose = (recommendation.get("dose") or "").lower()

    absolutist = ["always use", "never use", "100% effective", "guaranteed", "cure", "completely safe"]
    for p in absolutist:
        if p in rationale:
            findings.append({"category": "ABSOLUTIST_LANGUAGE", "detail": f'Unsupported phrase in rationale: "{p}"'})

    diag = patient.get("diagnosis", "").lower()
    path = patient.get("suspected_pathogen", "").lower()
    is_uti = "uti" in diag or "urinary" in diag
    is_ssti = "skin" in diag or "soft tissue" in diag

    if "vancomycin" in ab and is_ssti and "mrsa" not in path:
        findings.append({"category": "INDICATION_MISMATCH", "detail": "Vancomycin for SSTI without MRSA risk or culture — verify indication"})

    if "meropenem" in ab and is_uti and "esbl" not in path and "cre" not in path:
        findings.append({"category": "OVERUSE", "detail": "Carbapenem for UTI without ESBL/CRE risk — stewardship concern"})

    if not dose or dose in ("—", "unknown", "n/a"):
        findings.append({"category": "DOSE_MISSING", "detail": "No verifiable dose in recommendation — cannot release without dose validation"})

    if recommendation.get("aware_tier") == "Reserve" and not patient.get("id_consult"):
        findings.append({"category": "RESERVE_WITHOUT_ID", "detail": "Reserve-tier agent without documented ID consult"})

    return {
        "hallucination_detected": len(findings) > 0,
        "finding_count": len(findings),
        "findings": findings,
        "summary": "; ".join(f["detail"] for f in findings) if findings else "No specific unsupported claims detected",
    }
