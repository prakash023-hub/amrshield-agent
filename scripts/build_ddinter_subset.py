"""
Build AMRShield's antibiotic drug-drug interaction subset from DDInter exports.

Source: DDInter (https://ddinter.scbdd.com), Xiong G. et al., Nucleic Acids Res.
        2022;50(D1):D1200-D1207. Licensed CC BY-NC-SA 4.0 — NON-COMMERCIAL use
        only, with attribution, and derived data shared under the same licence.

Usage:
    python scripts/build_ddinter_subset.py ddinter_downloads_code_*.csv \
        --out data/interactions/ddinter_antibiotic_pairs.csv

Keeps only pairs where one drug is an antibiotic AMRShield can recommend and
records which ATC files were used, because any pair whose two drugs both fall
in a class that was not downloaded is missing from the subset.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

# AMRShield antibiotic name -> DDInter drug name(s) (combinations split into parts)
ANTIBIOTIC_COMPONENTS = {
    "amoxicillin": ["Amoxicillin"],
    "amoxicillin-clavulanate": ["Amoxicillin", "Clavulanic acid"],
    "ampicillin": ["Ampicillin"],
    "benzylpenicillin": ["Benzylpenicillin"],
    "cefalexin": ["Cephalexin"],
    "cefazolin": ["Cefazolin"],
    "chloramphenicol": ["Chloramphenicol"],
    "clindamycin": ["Clindamycin"],
    "co-trimoxazole": ["Sulfamethoxazole", "Trimethoprim"],
    "doxycycline": ["Doxycycline"],
    "gentamicin": ["Gentamicin"],
    "metronidazole": ["Metronidazole"],
    "nitrofurantoin": ["Nitrofurantoin"],
    "phenoxymethylpenicillin": ["Phenoxymethylpenicillin"],
    "trimethoprim": ["Trimethoprim"],
    "azithromycin": ["Azithromycin"],
    "cefixime": ["Cefixime"],
    "cefotaxime": ["Cefotaxime"],
    "ceftriaxone": ["Ceftriaxone"],
    "cefuroxime": ["Cefuroxime"],
    "ciprofloxacin": ["Ciprofloxacin"],
    "clarithromycin": ["Clarithromycin"],
    "levofloxacin": ["Levofloxacin"],
    "meropenem": ["Meropenem"],
    "imipenem-cilastatin": ["Imipenem"],
    "piperacillin-tazobactam": ["Piperacillin"],
    "vancomycin": ["Vancomycin"],
    "cefepime": ["Cefepime"],
    "ceftazidime": ["Ceftazidime"],
    "ceftazidime-avibactam": ["Ceftazidime"],
    "colistin": ["Colistimethate"],
    "daptomycin": ["Daptomycin"],
    "fosfomycin": ["Fosfomycin"],
    "fosfomycin iv": ["Fosfomycin"],
    "linezolid": ["Linezolid"],
    "meropenem-vaborbactam": ["Meropenem"],
    "polymyxin b": ["Polymyxin B"],
    "tedizolid": ["Tedizolid"],
    "tigecycline": ["Tigecycline"],
    "rifampicin": ["Rifampicin"],
}


def build(paths: list[str]) -> tuple[pd.DataFrame, list[str]]:
    d = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
    atc_codes = sorted({m.group(1) for p in paths if (m := re.search(r"code_([A-Z])", Path(p).name))})

    component_to_ab: dict[str, set[str]] = {}
    for ab, comps in ANTIBIOTIC_COMPONENTS.items():
        for c in comps:
            component_to_ab.setdefault(c.lower(), set()).add(ab)

    rows = []
    for a, b, level in d[["Drug_A", "Drug_B", "Level"]].itertuples(index=False):
        for drug, other in ((a, b), (b, a)):
            for ab in component_to_ab.get(str(drug).lower(), ()):
                rows.append((ab, drug, other, level))

    out = pd.DataFrame(rows, columns=["antibiotic", "antibiotic_component", "other_drug", "level"])
    # One row per antibiotic/other-drug: keep the most severe level reported
    rank = {"Major": 3, "Moderate": 2, "Minor": 1, "Unknown": 0}
    out["_r"] = out["level"].map(rank).fillna(0)
    out = (out.sort_values("_r", ascending=False)
              .drop_duplicates(["antibiotic", "other_drug"])
              .drop(columns="_r")
              .sort_values(["antibiotic", "other_drug"])
              .reset_index(drop=True))
    out = out[out["antibiotic_component"].str.lower() != out["other_drug"].str.lower()]
    return out, atc_codes


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("inputs", nargs="+", help="DDInter ddinter_downloads_code_*.csv files")
    ap.add_argument("--out", default="data/interactions/ddinter_antibiotic_pairs.csv")
    args = ap.parse_args(argv)

    df, atc = build(args.inputs)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    (out.parent / "ddinter_metadata.json").write_text(json.dumps({
        "source": "DDInter, https://ddinter.scbdd.com",
        "citation": "Xiong G. et al. DDInter: an online drug-drug interaction database. Nucleic Acids Res. 2022;50(D1):D1200-D1207",
        "licence": "CC BY-NC-SA 4.0 (non-commercial)",
        "atc_files_included": atc,
        "rows": len(df),
    }, indent=2) + "\n")
    print(f"Wrote {len(df)} rows to {out}; ATC files: {', '.join(atc)}")
    print(df["level"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
