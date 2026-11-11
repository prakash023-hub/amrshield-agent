"""
AMRShield - Clinical Agent Tools
Reusable from AMS-Gemma4 project — ported and expanded.
"""

import csv
import json
import re
from functools import lru_cache
from pathlib import Path
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
    "cefepime": {"tier": "Watch", "class": "4th gen cephalosporin", "route": "IV"},
    "ceftazidime": {"tier": "Watch", "class": "3rd gen cephalosporin", "route": "IV"},
    "ceftazidime-avibactam": {"tier": "Reserve", "class": "3rd gen cephalosporin+BLI", "route": "IV"},
    "colistin": {"tier": "Reserve", "class": "Polymyxin", "route": "IV/inhaled"},
    "daptomycin": {"tier": "Reserve", "class": "Lipopeptide", "route": "IV"},
    "fosfomycin": {"tier": "Watch", "class": "Phosphonic acid", "route": "PO"},  # oral = Watch (WHO AWaRe 2023)
    "fosfomycin iv": {"tier": "Reserve", "class": "Phosphonic acid", "route": "IV"},  # IV = Reserve
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

    if not key:
        return {
            "antibiotic": antibiotic_name,
            "aware_tier": "Not classified",
            "note": "No antibiotic name provided",
        }

    data = AWARE_DB.get(key)

    if not data and len(key) >= 4:
        # Fuzzy match attempt — only for substantial names, so an empty or
        # 1-2 char string can never substring-match every entry.
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
        return {"error": "Invalid serum creatinine value (must be > 0 mg/dL)"}
    if not isinstance(age, (int, float)) or not (0 < age <= 120):
        return {"error": f"Invalid age '{age}' (expected 0-120 years)"}
    if not isinstance(weight, (int, float)) or not (0 < weight <= 400):
        return {"error": f"Invalid weight '{weight}' (expected 0-400 kg)"}

    # Validate sex explicitly — do NOT silently treat an unrecognised value as
    # female, which would under-estimate CrCl by 15% and mis-dose the patient.
    sex_norm = str(sex).strip().lower()
    if sex_norm in ("male", "m", "man"):
        sex_factor = 1.0
    elif sex_norm in ("female", "f", "woman"):
        sex_factor = 0.85
    else:
        return {"error": f"Unrecognised sex '{sex}' (expected 'male' or 'female')"}

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


# Class/category keys in INTERACTION_DB expanded to the real drug names a
# prescriber actually enters. Without this, "linezolid" + "sertraline" (an SSRI,
# serotonin-syndrome risk) matched nothing, because the DB key is the class "ssri".
INTERACTION_SYNONYMS = {
    "ssri": [
        "sertraline", "fluoxetine", "paroxetine", "citalopram",
        "escitalopram", "fluvoxamine", "ssri",
    ],
    "antacids": ["antacid", "sucralfate", "aluminium hydroxide", "magnesium hydroxide", "calcium carbonate"],
    "calcium": ["calcium", "calcium gluconate", "calcium chloride"],
    "alcohol": ["alcohol", "ethanol"],
    "tyramine": ["tyramine"],
    "oral_contraceptives": ["oral contraceptive", "ethinylestradiol", "ethinyl estradiol", "levonorgestrel", "ocp"],
    "hiv_medications": ["dolutegravir", "efavirenz", "ritonavir", "tenofovir", "lamivudine", "antiretroviral"],
}


def _med_matches_interactor(med_lower: str, interacting_drug: str) -> bool:
    """True if a patient med matches an interaction key, by name or class synonym."""
    if interacting_drug in med_lower or med_lower in interacting_drug:
        return True
    for synonym in INTERACTION_SYNONYMS.get(interacting_drug, []):
        if synonym in med_lower:
            return True
    return False


# DDInter subset (CC BY-NC-SA 4.0, non-commercial) — optional data file.
# Built by scripts/build_ddinter_subset.py; if absent, only the curated table is used.
_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "interactions"
DDINTER_PATH = _DATA_DIR / "ddinter_antibiotic_pairs.csv"
DDINTER_META = _DATA_DIR / "ddinter_metadata.json"
DDINTER_SEVERITY = {"Major": "HIGH", "Moderate": "MEDIUM", "Minor": "LOW", "Unknown": "UNKNOWN"}
_SEVERITY_RANK = {"HIGH": 3, "UNKNOWN": 2, "MEDIUM": 2, "LOW": 1}
ATC_NAMES = {"A": "alimentary/metabolism", "B": "blood", "C": "cardiovascular", "D": "dermatological",
             "G": "genito-urinary/sex hormones", "H": "systemic hormonal", "J": "anti-infective",
             "L": "antineoplastic/immunomodulating", "M": "musculo-skeletal", "N": "nervous system",
             "P": "antiparasitic", "R": "respiratory", "S": "sensory organ", "V": "various"}


@lru_cache(maxsize=1)
def _ddinter_pairs() -> dict:
    """{antibiotic: {other_drug_lower: (other_drug, level)}} from the DDInter subset."""
    pairs: dict = {}
    if not DDINTER_PATH.exists():
        return pairs
    with open(DDINTER_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pairs.setdefault(row["antibiotic"], {})[row["other_drug"].lower()] = (row["other_drug"], row["level"])
    return pairs


@lru_cache(maxsize=1)
def _ddinter_missing_classes() -> list:
    """ATC groups whose DDInter file was not included (their pairs may be missing)."""
    if not DDINTER_META.exists():
        return []
    included = set(json.loads(DDINTER_META.read_text())["atc_files_included"])
    return [ATC_NAMES[c] for c in ATC_NAMES if c not in included]


def _ddinter_match(med_lower: str, table: dict):
    """Match a free-text medication ("Warfarin 5 mg") to a DDInter drug name."""
    if med_lower in table:
        return table[med_lower]
    for name, entry in table.items():
        if re.search(r"\b" + re.escape(name) + r"\b", med_lower):
            return entry
    return None


def check_drug_interactions(antibiotic: str, current_medications: list) -> dict:
    """
    Check for drug-drug interactions between proposed antibiotic and current meds.

    Two deterministic sources: a hand-curated table (with clinical-effect text)
    and the DDInter antibiotic subset (severity only). The more severe finding
    wins; curated text is kept when both match.

    Args:
        antibiotic: Proposed antibiotic (generic name)
        current_medications: List of current medications

    Returns:
        Dict with interaction list, severity summary and coverage note
    """
    antibiotic_key = antibiotic.lower().strip()
    curated = INTERACTION_DB.get(antibiotic_key)
    ddinter = _ddinter_pairs().get(antibiotic_key)

    # An antibiotic missing from both sources was NOT checked. Saying
    # "no interactions" here would be false reassurance, so report it as not screened.
    if curated is None and ddinter is None:
        return {
            "antibiotic_checked": antibiotic,
            "medications_screened": current_medications,
            "screening_status": "NOT_SCREENED",
            "interactions_found": [],
            "interaction_count": 0,
            "requires_review": bool(current_medications),
            "summary": (
                f"⚠️ {antibiotic or 'This antibiotic'} is not covered by the interaction "
                "database — interactions were NOT checked. Verify manually before prescribing."
            ),
        }

    interactions_found = []
    for med in current_medications:
        med_lower = str(med).lower().strip()
        hit = None
        for interacting_drug, details in (curated or {}).items():
            if _med_matches_interactor(med_lower, interacting_drug):
                hit = {"interacting_drug": med, "severity": details["severity"],
                       "clinical_effect": details["effect"], "source": "curated"}
                break
        dd = _ddinter_match(med_lower, ddinter) if ddinter else None
        if dd:
            dd_sev = DDINTER_SEVERITY.get(dd[1], "UNKNOWN")
            if hit is None:
                effect = (f"DDInter: {dd[1].lower()} interaction with {dd[0]} — check mechanism and management"
                          if dd[1] != "Unknown" else
                          f"DDInter: interaction with {dd[0]} reported, severity not graded — review")
                hit = {"interacting_drug": med, "severity": dd_sev, "clinical_effect": effect, "source": "DDInter"}
            elif _SEVERITY_RANK[dd_sev] > _SEVERITY_RANK.get(hit["severity"], 0):
                hit["severity"] = dd_sev
                hit["source"] = "curated + DDInter"
        if hit:
            interactions_found.append(hit)

    requires_review = any(i["severity"] in ("HIGH", "UNKNOWN") for i in interactions_found)
    missing = _ddinter_missing_classes() if ddinter else []
    coverage_note = (
        f"Co-medications in these drug classes are only partly covered: {', '.join(missing)}."
        if missing else ("Curated table only (DDInter data not installed)." if not ddinter else "")
    )

    return {
        "antibiotic_checked": antibiotic,
        "medications_screened": current_medications,
        "screening_status": "SCREENED",
        "sources": [x for x, used in (("curated", curated), ("DDInter", ddinter)) if used],
        "interactions_found": interactions_found,
        "interaction_count": len(interactions_found),
        "requires_review": requires_review,
        "coverage_note": coverage_note,
        "summary": (
            f"⚠️ {len(interactions_found)} interaction(s) found — review before prescribing"
            if interactions_found else
            "✅ No interactions found in the screened sources" + (f" — {coverage_note}" if coverage_note else "")
        ),
    }


# ─────────────────────────────────────────────
# Antibiogram — ICMR AMRSN Annual Report 2022 (national, real data)
# data/antibiogram/amrsn_2022_by_specimen.csv, built by
# scripts/extract_amrsn_2022.py; provenance in data/antibiogram/SOURCES.md
# ─────────────────────────────────────────────

ANTIBIOGRAM_PATH = Path(__file__).resolve().parents[2] / "data" / "antibiogram" / "amrsn_2022_by_specimen.csv"
ANTIBIOGRAM_SOURCE = "ICMR AMRSN Annual Report 2022 (national multi-centre surveillance, India)"
MIN_ISOLATES = 30          # CLSI M39: report % susceptible only with >= 30 isolates

ANTIBIOGRAM_PATHOGENS = {
    "e. coli": "E. coli", "escherichia coli": "E. coli", "ecoli": "E. coli",
    "k. pneumoniae": "K. pneumoniae", "klebsiella pneumoniae": "K. pneumoniae", "klebsiella": "K. pneumoniae",
    "s. aureus": "S. aureus", "staphylococcus aureus": "S. aureus", "mrsa": "S. aureus", "mssa": "S. aureus",
    "p. aeruginosa": "P. aeruginosa", "pseudomonas aeruginosa": "P. aeruginosa", "pseudomonas": "P. aeruginosa",
    "a. baumannii": "A. baumannii", "acinetobacter baumannii": "A. baumannii", "acinetobacter": "A. baumannii",
}
# Clinical infection site -> AMRSN specimen
SITE_TO_SPECIMEN = {
    "uti": "urine", "urine": "urine", "urinary": "urine", "cystitis": "urine", "pyelonephritis": "urine",
    "bloodstream": "blood", "blood": "blood", "bacteremia": "blood", "bacteraemia": "blood", "sepsis": "blood",
    "skin": "pus", "ssti": "pus", "soft tissue": "pus", "wound": "pus", "pus": "pus", "abscess": "pus",
    "cellulitis": "pus",
}
# Laboratory screening markers, not drugs to prescribe
SCREENING_MARKERS = {"cefoxitin", "oxacillin"}
CARE_SETTINGS = {"opd": "OPD", "outpatient": "OPD", "ward": "Ward", "inpatient": "Ward", "icu": "ICU"}


def _amr_name(antibiotic: str) -> str:
    """AMRSN antibiotic name -> AMRShield name."""
    a = antibiotic.lower()
    return {"trimethoprim-sulfamethoxazole": "co-trimoxazole"}.get(a, a)


@lru_cache(maxsize=1)
def _antibiogram_rows() -> list:
    if not ANTIBIOGRAM_PATH.exists():
        return []
    with open(ANTIBIOGRAM_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _susceptibility(pathogen: str, specimen: str, setting: Optional[str]) -> tuple[dict, dict, str]:
    """Pooled % susceptible (and isolate counts) for one pathogen/specimen."""
    totals: dict = {}
    tables = set()
    for r in _antibiogram_rows():
        if r["pathogen"] != pathogen or r["specimen"] != specimen:
            continue
        if setting and r["location"] != setting:
            continue
        s, n = totals.get(r["antibiotic"], (0, 0))
        totals[r["antibiotic"]] = (s + int(r["susceptible"]), n + int(r["tested"]))
        tables.add(r["source"].replace("AMRSN 2022 ", ""))
    pct = {_amr_name(a): round(100 * s / n, 1) for a, (s, n) in totals.items() if n >= MIN_ISOLATES}
    counts = {_amr_name(a): n for a, (s, n) in totals.items()}
    return pct, counts, ", ".join(sorted(tables))


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
    "vancomycin": {"threshold": 50, "action": "Dose by level/AUC monitoring; reduce dose and extend interval as CrCl falls", "severity": "HIGH"},
    "ciprofloxacin": {"threshold": 50, "action": "Reduce dose if CrCl <50; halve dose if CrCl <30", "severity": "HIGH"},
    "levofloxacin": {"threshold": 50, "action": "Reduce dose / extend interval if CrCl <50", "severity": "HIGH"},
    "meropenem": {"threshold": 50, "action": "Reduce dose and/or extend interval if CrCl <50", "severity": "HIGH"},
    "piperacillin-tazobactam": {"threshold": 40, "action": "Reduce dose if CrCl <40", "severity": "MEDIUM"},
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
    """
    Cross-check antibiotic against allergy list with class cross-reactivity.

    Matches allergy terms by substring against the whole free-text allergy list,
    so real-world entries like "Penicillin (anaphylaxis)", "penicillins" or
    "sulfa drugs" are caught — the previous exact list-membership test missed them.
    """
    ab = antibiotic.lower()
    dc = drug_class.lower()
    allergy_text = " ".join(str(a).lower() for a in allergies)

    def allergic_to(*terms: str) -> bool:
        return any(t in allergy_text for t in terms)

    if allergic_to("penicillin", "amoxicillin", "ampicillin", "augmentin", "beta-lactam", "betalactam") and (
        any(p in ab for p in PENICILLIN_CLASS) or "penicillin" in dc or "aminopenicillin" in dc
    ):
        return {"conflict": True, "severity": "ABSOLUTE", "message": "Penicillin allergy — avoid penicillin-class agents"}

    if allergic_to("cephalosporin", "cefalosporin") and (
        any(c in ab for c in CEPHALOSPORIN_CLASS) or "cephalosporin" in dc
    ):
        return {"conflict": True, "severity": "ABSOLUTE", "message": "Cephalosporin allergy — avoid cephalosporin-class agents"}

    if allergic_to("sulfa", "sulphonamide", "sulfonamide", "co-trimoxazole", "cotrimoxazole", "trimethoprim") and (
        any(s in ab for s in SULFA_CLASS) or "sulfonamide" in dc
    ):
        return {"conflict": True, "severity": "ABSOLUTE", "message": "Sulfa allergy — avoid sulfonamide agents"}

    if allergic_to("fluoroquinolone", "quinolone", "floxacin") and ("floxacin" in ab or "fluoroquinolone" in dc):
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
    infection_site: Optional[str] = None,
    care_setting: Optional[str] = None,
) -> dict:
    """
    Susceptibility data from the ICMR AMRSN 2022 national antibiogram.

    Args:
        pathogen: Pathogen name (e.g., "E. coli", "MRSA")
        infection_site: Clinical site (UTI, bloodstream, skin...) mapped to the
            AMRSN specimen (urine, blood, pus)
        care_setting: Optional "OPD", "Ward" or "ICU"; default pools all three

    Returns:
        Dict with % susceptible per antibiotic, preferred (>=80%) and alternative
        (60-79%) agents, isolate counts and the data source. This is national
        Indian data, not the patient's own hospital antibiogram.
    """
    key = pathogen.lower().strip()
    matched = next((v for k, v in ANTIBIOGRAM_PATHOGENS.items() if k == key or k in key), None)
    if not matched or not _antibiogram_rows():
        return {
            "pathogen": pathogen,
            "message": "Pathogen not in the antibiogram — use national guidelines or empirical therapy",
            "recommendation": "Consider infectious disease consultation for unusual pathogens",
            "data_source": ANTIBIOGRAM_SOURCE,
        }

    setting = CARE_SETTINGS.get(str(care_setting).lower().strip()) if care_setting else None
    site_note = None
    specimen = None
    if infection_site:
        site_key = infection_site.lower()
        specimen = next((v for k, v in SITE_TO_SPECIMEN.items() if k in site_key), None)
    available = sorted({r["specimen"] for r in _antibiogram_rows() if r["pathogen"] == matched})
    if specimen not in available:
        fallback = "blood" if "blood" in available else available[0]
        if infection_site:
            site_note = (f"No AMRSN specimen data for '{infection_site}' in {matched}; "
                         f"showing '{fallback}' isolates instead — interpret with caution")
        specimen = fallback

    susceptibility, isolates, tables = _susceptibility(matched, specimen, setting)
    usable = {k: v for k, v in susceptibility.items() if k not in SCREENING_MARKERS}
    # WHO AWaRe Reserve agents are last-resort: never offered as preferred empirical choices
    reserve_agents = {k: v for k, v in sorted(usable.items(), key=lambda x: -x[1])
                      if lookup_aware_tier(k).get("aware_tier") == "Reserve"}
    usable = {k: v for k, v in usable.items() if k not in reserve_agents}
    preferred_agents = {k: v for k, v in sorted(usable.items(), key=lambda x: -x[1]) if v >= 80}
    alternative_agents = {k: v for k, v in sorted(usable.items(), key=lambda x: -x[1]) if 60 <= v < 80}

    notes = ["National Indian surveillance data, not this hospital's antibiogram — "
             "use a local antibiogram when available."]
    if reserve_agents:
        notes.append("Reserve-tier agents are listed separately: use only for confirmed "
                     "multidrug-resistant infections, with stewardship approval.")
    if key in ("mrsa", "mssa"):
        notes.append("AMRSN S. aureus tables include both MRSA and MSSA; for MRSA, beta-lactam "
                     "susceptibility does not apply.")
    if "cefoxitin" in susceptibility:
        notes.append(f"Cefoxitin is the MRSA screen: {susceptibility['cefoxitin']}% susceptible "
                     f"means about {round(100 - susceptibility['cefoxitin'], 1)}% of isolates are MRSA.")

    result = {
        "pathogen": pathogen,
        "infection_site": infection_site or specimen,
        "specimen": specimen,
        "care_setting": setting or "OPD + Ward + ICU (pooled)",
        "susceptibility_data": susceptibility,
        "isolates_tested": isolates,
        "preferred_agents": preferred_agents,
        "alternative_agents": alternative_agents,
        "reserve_agents": reserve_agents,
        "data_source": f"{ANTIBIOGRAM_SOURCE}, {tables}",
        "note": " ".join(notes),
    }
    if site_note:
        result["site_warning"] = site_note
    return result
