"""
AMRShield - Clinical Agent Tools
Reusable from AMS-Gemma4 project — ported and expanded.
"""

from typing import Optional


# ─────────────────────────────────────────────
# WHO AWaRe Classification Database
# Source: WHO Model List of Essential Medicines (2023)
# ─────────────────────────────────────────────

AWARE_DB = {
    # ACCESS tier
    "amoxicillin": {"tier": "Access", "class": "Aminopenicillin", "route": "PO"},
    "amoxicillin-clavulanate": {"tier": "Access", "class": "Aminopenicillin+BLI", "route": "PO/IV"},
    "ampicillin": {"tier": "Access", "class": "Aminopenicillin", "route": "IV"},
    "benzylpenicillin": {"tier": "Access", "class": "Natural penicillin", "route": "IV"},
    "cefalexin": {"tier": "Access", "class": "1st gen cephalosporin", "route": "PO"},
    "cefazolin": {"tier": "Access", "class": "1st gen cephalosporin", "route": "IV"},
    "chloramphenicol": {"tier": "Access", "class": "Phenicol", "route": "PO/IV"},
    "clindamycin": {"tier": "Access", "class": "Lincosamide", "route": "PO/IV"},
    "co-trimoxazole": {"tier": "Access", "class": "Sulfonamide", "route": "PO"},
    "doxycycline": {"tier": "Access", "class": "Tetracycline", "route": "PO"},
    "gentamicin": {"tier": "Access", "class": "Aminoglycoside", "route": "IV/IM"},
    "metronidazole": {"tier": "Access", "class": "Nitroimidazole", "route": "PO/IV"},
    "nitrofurantoin": {"tier": "Access", "class": "Nitrofuran", "route": "PO"},
    "phenoxymethylpenicillin": {"tier": "Access", "class": "Natural penicillin", "route": "PO"},
    "trimethoprim": {"tier": "Access", "class": "Diaminopyrimidine", "route": "PO"},
    
    # WATCH tier
    "azithromycin": {"tier": "Watch", "class": "Macrolide", "route": "PO/IV"},
    "cefixime": {"tier": "Watch", "class": "3rd gen cephalosporin", "route": "PO"},
    "cefotaxime": {"tier": "Watch", "class": "3rd gen cephalosporin", "route": "IV"},
    "ceftriaxone": {"tier": "Watch", "class": "3rd gen cephalosporin", "route": "IV/IM"},
    "cefuroxime": {"tier": "Watch", "class": "2nd gen cephalosporin", "route": "PO/IV"},
    "ciprofloxacin": {"tier": "Watch", "class": "Fluoroquinolone", "route": "PO/IV"},
    "clarithromycin": {"tier": "Watch", "class": "Macrolide", "route": "PO"},
    "levofloxacin": {"tier": "Watch", "class": "Fluoroquinolone", "route": "PO/IV"},
    "meropenem": {"tier": "Watch", "class": "Carbapenem", "route": "IV"},
    "imipenem-cilastatin": {"tier": "Watch", "class": "Carbapenem", "route": "IV"},
    "piperacillin-tazobactam": {"tier": "Watch", "class": "Ureidopenicillin+BLI", "route": "IV"},
    "vancomycin": {"tier": "Watch", "class": "Glycopeptide", "route": "IV/PO"},
    
    # RESERVE tier
    "ceftazidime-avibactam": {"tier": "Reserve", "class": "3rd gen cephalosporin+BLI", "route": "IV"},
    "colistin": {"tier": "Reserve", "class": "Polymyxin", "route": "IV/inhaled"},
    "daptomycin": {"tier": "Reserve", "class": "Lipopeptide", "route": "IV"},
    "fosfomycin": {"tier": "Reserve", "class": "Phosphonic acid", "route": "IV/PO"},
    "linezolid": {"tier": "Reserve", "class": "Oxazolidinone", "route": "PO/IV"},
    "meropenem-vaborbactam": {"tier": "Reserve", "class": "Carbapenem+BLI", "route": "IV"},
    "polymyxin b": {"tier": "Reserve", "class": "Polymyxin", "route": "IV"},
    "tedizolid": {"tier": "Reserve", "class": "Oxazolidinone", "route": "PO/IV"},
    "temocillin": {"tier": "Reserve", "class": "Penicillin", "route": "IV"},
    "tigecycline": {"tier": "Reserve", "class": "Tetracycline", "route": "IV"},
}


def lookup_aware_tier(antibiotic_name: str) -> dict:
    """
    Return WHO AWaRe tier for an antibiotic.
    
    Args:
        antibiotic_name: Generic antibiotic name (case-insensitive)
    
    Returns:
        Dict with tier, class, route, guidance
    """
    key = antibiotic_name.lower().strip()
    data = AWARE_DB.get(key)
    
    if not data:
        # Fuzzy match attempt
        for db_key, db_val in AWARE_DB.items():
            if key in db_key or db_key in key:
                data = db_val
                break
    
    if data:
        guidance_map = {
            "Access": "First-line therapy — prefer when clinically appropriate",
            "Watch": "For specific indications where Access-tier agents are not suitable",
            "Reserve": "Last resort only — use requires infectious disease specialist consultation",
        }
        return {
            "antibiotic": antibiotic_name,
            "aware_tier": data["tier"],
            "drug_class": data["class"],
            "preferred_route": data["route"],
            "stewardship_guidance": guidance_map[data["tier"]],
        }
    else:
        return {
            "antibiotic": antibiotic_name,
            "aware_tier": "Not classified",
            "note": "Not found in WHO AWaRe 2023 list — check locally",
        }


# ─────────────────────────────────────────────
# CrCl Calculator (Cockcroft-Gault)
# ─────────────────────────────────────────────

def calculate_crcl(
    age: float,
    weight: float,
    serum_creatinine: float,
    sex: str,
    use_ibw: bool = False
) -> dict:
    """
    Calculate creatinine clearance using Cockcroft-Gault equation.
    
    Args:
        age: Age in years
        weight: Body weight in kg (actual or IBW)
        serum_creatinine: Serum creatinine in mg/dL
        sex: 'male' or 'female'
        use_ibw: Whether to use ideal body weight
    
    Returns:
        Dict with CrCl value and renal function category
    """
    if serum_creatinine <= 0:
        return {"error": "Invalid serum creatinine value"}
    
    sex_factor = 1.0 if sex.lower() == "male" else 0.85
    
    # Cockcroft-Gault
    crcl = ((140 - age) * weight * sex_factor) / (72 * serum_creatinine)
    crcl = round(crcl, 1)
    
    # Classify renal function
    if crcl >= 90:
        category = "Normal"
        dose_note = "Standard dosing"
    elif crcl >= 60:
        category = "Mild CKD (G2)"
        dose_note = "Standard dosing for most agents; monitor"
    elif crcl >= 30:
        category = "Moderate CKD (G3)"
        dose_note = "Dose adjustment required for renally-cleared antibiotics"
    elif crcl >= 15:
        category = "Severe CKD (G4)"
        dose_note = "Significant dose reductions required; consult nephrology"
    else:
        category = "Kidney Failure (G5)"
        dose_note = "Avoid renally-cleared nephrotoxins; renal replacement therapy considerations"
    
    return {
        "crcl_ml_min": crcl,
        "renal_category": category,
        "dose_note": dose_note,
        "equation": "Cockcroft-Gault",
        "caution": "Use actual body weight; adjust for obesity if BMI >30",
    }


# ─────────────────────────────────────────────
# Drug Interaction Checker
# ─────────────────────────────────────────────

# Clinically significant interactions (curated, not exhaustive)
INTERACTION_DB = {
    "ciprofloxacin": {
        "warfarin": {"severity": "HIGH", "effect": "Increases warfarin effect — INR monitoring required"},
        "theophylline": {"severity": "HIGH", "effect": "Increases theophylline levels — toxicity risk"},
        "antacids": {"severity": "MEDIUM", "effect": "Reduces ciprofloxacin absorption — separate by 2h"},
        "metformin": {"severity": "LOW", "effect": "Monitor blood glucose — may affect renal elimination"},
    },
    "levofloxacin": {
        "warfarin": {"severity": "HIGH", "effect": "Increases warfarin effect — INR monitoring required"},
        "amiodarone": {"severity": "HIGH", "effect": "QT prolongation risk — avoid combination"},
    },
    "vancomycin": {
        "gentamicin": {"severity": "HIGH", "effect": "Additive nephrotoxicity — monitor renal function and drug levels"},
        "furosemide": {"severity": "MEDIUM", "effect": "Additive nephrotoxicity and ototoxicity"},
        "piperacillin-tazobactam": {"severity": "MEDIUM", "effect": "May increase nephrotoxicity — monitor AKI"},
    },
    "metronidazole": {
        "warfarin": {"severity": "HIGH", "effect": "Potentiates anticoagulant effect — reduce warfarin, monitor INR"},
        "alcohol": {"severity": "HIGH", "effect": "Disulfiram-like reaction — counsel patient"},
        "lithium": {"severity": "MEDIUM", "effect": "Increases lithium levels — monitor toxicity"},
    },
    "linezolid": {
        "ssri": {"severity": "HIGH", "effect": "Serotonin syndrome risk — avoid combination"},
        "tramadol": {"severity": "HIGH", "effect": "Serotonin syndrome risk — avoid"},
        "tyramine": {"severity": "MEDIUM", "effect": "MAO inhibition — avoid tyramine-rich foods"},
    },
    "ceftriaxone": {
        "calcium": {"severity": "HIGH", "effect": "Ceftriaxone-calcium precipitate — do not co-administer IV in neonates"},
    },
    "rifampicin": {
        "warfarin": {"severity": "HIGH", "effect": "Strong CYP inducer — reduces warfarin effect significantly"},
        "hiv_medications": {"severity": "HIGH", "effect": "Multiple interactions — specialist consultation required"},
        "oral_contraceptives": {"severity": "HIGH", "effect": "Reduces contraceptive efficacy — alternative contraception needed"},
    },
}


def check_drug_interactions(antibiotic: str, current_medications: list) -> dict:
    """
    Check for drug-drug interactions between proposed antibiotic and current meds.
    
    Args:
        antibiotic: Proposed antibiotic (generic name)
        current_medications: List of current medications
    
    Returns:
        Dict with interaction list and severity summary
    """
    antibiotic_key = antibiotic.lower().strip()
    interactions_found = []
    
    drug_interactions = INTERACTION_DB.get(antibiotic_key, {})
    
    for med in current_medications:
        med_lower = med.lower().strip()
        for interacting_drug, details in drug_interactions.items():
            if interacting_drug in med_lower or med_lower in interacting_drug:
                interactions_found.append({
                    "interacting_drug": med,
                    "severity": details["severity"],
                    "clinical_effect": details["effect"],
                })
    
    has_critical = any(i["severity"] == "HIGH" for i in interactions_found)
    
    return {
        "antibiotic_checked": antibiotic,
        "medications_screened": current_medications,
        "interactions_found": interactions_found,
        "interaction_count": len(interactions_found),
        "requires_review": has_critical,
        "summary": (
            f"⚠️ {len(interactions_found)} interaction(s) found — review before prescribing"
            if interactions_found else "✅ No significant interactions detected"
        ),
    }


# ─────────────────────────────────────────────
# Local Antibiogram (Synthetic Hospital Data)
# Replace with real hospital antibiogram data
# ─────────────────────────────────────────────

SYNTHETIC_ANTIBIOGRAM = {
    "e. coli": {
        "UTI": {
            "nitrofurantoin": 88,
            "co-trimoxazole": 62,
            "ciprofloxacin": 71,
            "ceftriaxone": 79,
            "amoxicillin-clavulanate": 72,
        },
        "bloodstream": {
            "ceftriaxone": 81,
            "piperacillin-tazobactam": 88,
            "meropenem": 97,
            "ciprofloxacin": 70,
        },
    },
    "staphylococcus aureus": {
        "skin": {
            "cefalexin": 72,  # MSSA
            "clindamycin": 78,
            "co-trimoxazole": 91,
            "vancomycin": 100,  # All S. aureus susceptible
        },
    },
    "klebsiella pneumoniae": {
        "pneumonia": {
            "ceftriaxone": 75,
            "piperacillin-tazobactam": 78,
            "meropenem": 96,
            "ciprofloxacin": 73,
        },
        "UTI": {
            "nitrofurantoin": 40,
            "ciprofloxacin": 73,
            "ceftriaxone": 75,
            "meropenem": 96,
        },
    },
    "pseudomonas aeruginosa": {
        "pneumonia": {
            "piperacillin-tazobactam": 72,
            "ceftazidime": 76,
            "meropenem": 81,
            "ciprofloxacin": 68,
            "colistin": 95,
        },
    },
    "mrsa": {
        "bloodstream": {
            "vancomycin": 98,
            "linezolid": 96,
            "daptomycin": 97,
            "co-trimoxazole": 92,
        },
        "pneumonia": {
            "vancomycin": 98,
            "linezolid": 96,
            "clindamycin": 45,
        },
        "skin": {
            "co-trimoxazole": 92,
            "clindamycin": 78,
            "vancomycin": 98,
            "doxycycline": 88,
        },
    },
    "esbl": {
        "UTI": {
            "nitrofurantoin": 55,
            "fosfomycin": 82,
            "meropenem": 99,
            "piperacillin-tazobactam": 35,
        },
        "bloodstream": {
            "meropenem": 99,
            "cefepime": 40,
            "piperacillin-tazobactam": 30,
        },
    },
}


# ─────────────────────────────────────────────
# IDSA-style indication guidelines (curated)
# ─────────────────────────────────────────────

INDICATION_GUIDELINES = {
    "Urinary Tract Infection": {
        "source": "IDSA UTI Guidelines 2010 / EAU 2024",
        "first_line": "Nitrofurantoin, Fosfomycin, or TMP-SMX (if local susceptibility >80%)",
        "duration": "5–7 days uncomplicated; 7–14 days complicated",
        "avoid": "Fluoroquinolones as first-line unless no alternatives",
    },
    "Community-Acquired Pneumonia": {
        "source": "IDSA/ATS CAP Guidelines 2019",
        "first_line": "Amoxicillin, Doxycycline, or Macrolide (outpatient); Beta-lactam + macrolide (inpatient)",
        "duration": "5–7 days if clinically improving",
        "avoid": "Reserve broad-spectrum unless risk factors for resistant organisms",
    },
    "Hospital-Acquired Pneumonia": {
        "source": "IDSA/ATS HAP-VAP Guidelines 2016",
        "first_line": "Anti-pseudomonal beta-lactam ± vancomycin if MRSA risk",
        "duration": "7–8 days if good clinical response",
        "avoid": "Double anaerobic coverage unless aspiration suspected",
    },
    "Sepsis (unknown source)": {
        "source": "Surviving Sepsis Campaign 2021",
        "first_line": "Broad-spectrum within 1h — adjust to culture at 48–72h",
        "duration": "Shortest effective course after source control",
        "avoid": "Prolonged broad-spectrum without de-escalation",
    },
    "Skin & Soft Tissue Infection": {
        "source": "IDSA SSTI Guidelines 2014",
        "first_line": "Cephalexin, Clindamycin, or TMP-SMX for purulent; Beta-lactam for non-purulent",
        "duration": "5–10 days depending on severity",
        "avoid": "Vancomycin monotherapy for uncomplicated cellulitis without MRSA risk",
    },
    "Intra-Abdominal Infection": {
        "source": "IDSA/SIS IAI Guidelines 2010",
        "first_line": "Source control + ceftriaxone/metronidazole or piperacillin-tazobactam",
        "duration": "4–7 days if adequate source control",
        "avoid": "Prolonged therapy after source control without evidence of ongoing infection",
    },
}

PENICILLIN_CLASS = {"penicillin", "amoxicillin", "ampicillin", "amoxicillin-clavulanate", "piperacillin", "piperacillin-tazobactam", "benzylpenicillin"}
CEPHALOSPORIN_CLASS = {"cefalexin", "cefazolin", "ceftriaxone", "cefotaxime", "cefixime", "cefuroxime", "ceftazidime", "cefepime"}
SULFA_CLASS = {"co-trimoxazole", "trimethoprim", "sulfonamides"}

RENAL_DOSE_TABLE = {
    "nitrofurantoin": {"threshold": 30, "action": "AVOID if CrCl <30 mL/min — ineffective and toxicity risk", "severity": "ABSOLUTE"},
    "gentamicin": {"threshold": 60, "action": "Extend interval; monitor levels; reduce dose if CrCl <60", "severity": "HIGH"},
    "vancomycin": {"threshold": 30, "action": "Reduce dose and monitor trough; extend interval if CrCl <30", "severity": "HIGH"},
    "ciprofloxacin": {"threshold": 30, "action": "Reduce dose 50% if CrCl <30", "severity": "HIGH"},
    "meropenem": {"threshold": 20, "action": "Reduce dose if CrCl <20–40", "severity": "HIGH"},
    "amoxicillin-clavulanate": {"threshold": 30, "action": "Reduce frequency if CrCl <30", "severity": "MEDIUM"},
}


def get_indication_guideline(diagnosis: str, pathogen: str = "Unknown") -> dict:
    """Return stewardship guideline summary for indication."""
    for key, val in INDICATION_GUIDELINES.items():
        if key.lower() in diagnosis.lower() or diagnosis.lower() in key.lower():
            out = dict(val)
            out["diagnosis"] = diagnosis
            if "mrsa" in pathogen.lower():
                out["pathogen_note"] = "MRSA — consider vancomycin, linezolid, daptomycin, or TMP-SMX per site"
            elif "esbl" in pathogen.lower():
                out["pathogen_note"] = "ESBL — carbapenem preferred; avoid piperacillin-tazobactam unless susceptible"
            return out
    return {
        "source": "WHO AWaRe 2023 / Local AMS policy",
        "first_line": "Prefer Access-tier agent guided by local antibiogram",
        "duration": "Shortest effective course",
        "diagnosis": diagnosis,
    }


def check_allergy_conflict(antibiotic: str, drug_class: str, allergies: list) -> dict:
    """Cross-check antibiotic against allergy list with class cross-reactivity."""
    ab = antibiotic.lower()
    dc = drug_class.lower()
    allergy_lower = [a.lower() for a in allergies]

    if "penicillin" in allergy_lower and (
        any(p in ab for p in PENICILLIN_CLASS) or "penicillin" in dc or "aminopenicillin" in dc
    ):
        return {"conflict": True, "severity": "ABSOLUTE", "message": "Penicillin allergy — avoid penicillin-class agents"}

    if "cephalosporins" in allergy_lower and (
        any(c in ab for c in CEPHALOSPORIN_CLASS) or "cephalosporin" in dc
    ):
        return {"conflict": True, "severity": "ABSOLUTE", "message": "Cephalosporin allergy — avoid cephalosporin-class agents"}

    if "sulfonamides" in allergy_lower and (
        any(s in ab for s in SULFA_CLASS) or "sulfonamide" in dc
    ):
        return {"conflict": True, "severity": "ABSOLUTE", "message": "Sulfa allergy — avoid sulfonamide agents"}

    if "fluoroquinolones" in allergy_lower and ("floxacin" in ab or "fluoroquinolone" in dc):
        return {"conflict": True, "severity": "ABSOLUTE", "message": "Fluoroquinolone allergy — avoid quinolone class"}

    return {"conflict": False, "severity": "NONE", "message": "No allergy conflict detected"}


def suggest_renal_dose(antibiotic: str, crcl: float) -> dict:
    """Renal dose adjustment suggestion for common antibiotics."""
    ab = antibiotic.lower().strip()
    for drug_key, rule in RENAL_DOSE_TABLE.items():
        if drug_key in ab:
            if crcl < rule["threshold"]:
                return {
                    "adjustment_required": True,
                    "severity": rule["severity"],
                    "message": rule["action"],
                    "crcl": crcl,
                    "drug": antibiotic,
                }
    if crcl < 30:
        return {
            "adjustment_required": True,
            "severity": "MEDIUM",
            "message": f"CrCl {crcl:.0f} mL/min — verify renal dosing for {antibiotic}",
            "crcl": crcl,
            "drug": antibiotic,
        }
    return {"adjustment_required": False, "message": "Standard dosing likely appropriate", "crcl": crcl}


def query_local_antibiogram(
    pathogen: str,
    infection_site: Optional[str] = None
) -> dict:
    """
    Query synthetic local antibiogram for susceptibility data.
    
    Args:
        pathogen: Pathogen name (e.g., "E. coli", "MRSA")
        infection_site: Infection site for site-specific susceptibility
    
    Returns:
        Dict with susceptibility percentages and recommended agents
    """
    pathogen_key = pathogen.lower().strip()
    
    # Find matching pathogen
    matched_pathogen = None
    for db_key in SYNTHETIC_ANTIBIOGRAM:
        if db_key in pathogen_key or pathogen_key in db_key:
            matched_pathogen = db_key
            break
    
    if not matched_pathogen:
        return {
            "pathogen": pathogen,
            "message": "Pathogen not in local antibiogram — use national guidelines or empirical therapy",
            "recommendation": "Consider infectious disease consultation for unusual pathogens",
        }
    
    pathogen_data = SYNTHETIC_ANTIBIOGRAM[matched_pathogen]
    
    # Get site-specific or first available data
    if infection_site:
        site_key = infection_site.lower()
        susceptibility = next(
            (v for k, v in pathogen_data.items() if k in site_key or site_key in k),
            list(pathogen_data.values())[0]
        )
    else:
        susceptibility = list(pathogen_data.values())[0]
    
    # Identify best agents (>80% susceptibility)
    preferred_agents = {k: v for k, v in susceptibility.items() if v >= 80}
    alternative_agents = {k: v for k, v in susceptibility.items() if 60 <= v < 80}
    
    return {
        "pathogen": pathogen,
        "infection_site": infection_site or "general",
        "susceptibility_data": susceptibility,
        "preferred_agents": preferred_agents,
        "alternative_agents": alternative_agents,
        "data_source": "Synthetic Hospital Antibiogram 2025 (Demo Data)",
        "note": "Replace with your hospital's actual antibiogram data — WHONET format recommended",
    }
