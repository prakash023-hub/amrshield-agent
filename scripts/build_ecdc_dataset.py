"""
Build AMRShield's tidy surveillance dataset from ECDC Surveillance Atlas exports.

Source: ECDC Surveillance Atlas of Infectious Diseases (EARS-Net),
        https://atlas.ecdc.europa.eu — indicator "R - resistant isolates, percentage".
        Reuse is permitted with acknowledgement of the source (ECDC copyright policy).

Usage:
    python scripts/build_ecdc_dataset.py raw1.csv raw2.csv ... \
        --out data/surveillance/ecdc_ears_net_resistance.csv

Only single antibiotic-group indicators are kept; "Combined resistance" rows
(resistant to several classes at once) are dropped because AMRShield asks
"will THIS antibiotic group work?".
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

INDICATOR = "R - resistant isolates, percentage"

# ECDC organism name -> short name used across AMRShield
PATHOGEN_SHORT = {
    "Escherichia coli": "E. coli",
    "Klebsiella pneumoniae": "K. pneumoniae",
    "Staphylococcus aureus": "S. aureus",
}


def tidy(paths: list[str]) -> pd.DataFrame:
    frames = []
    for p in paths:
        d = pd.read_csv(p, encoding="utf-8-sig")
        d = d[d["Indicator"].str.strip() == INDICATOR]
        org_ab = d["Population"].str.split("|", n=1, expand=True)
        d = d.assign(organism=org_ab[0].str.strip(), antibiotic_group=org_ab[1].str.strip())
        d = d[~d["antibiotic_group"].str.startswith("Combined resistance")]
        frames.append(d)

    d = pd.concat(frames, ignore_index=True)
    d["resistance_pct"] = pd.to_numeric(d["NumValue"], errors="coerce")   # "-" = not reported
    d = d.dropna(subset=["resistance_pct"])
    d["pathogen"] = d["organism"].map(PATHOGEN_SHORT).fillna(d["organism"])
    # MRSA is the name clinicians and the rest of AMRShield use for S. aureus + meticillin
    d.loc[d["antibiotic_group"].str.startswith("Meticillin"), "pathogen"] = "MRSA"

    out = d.rename(columns={"RegionCode": "country_code", "RegionName": "country", "Time": "year"})[
        ["country_code", "country", "pathogen", "antibiotic_group", "year", "resistance_pct"]
    ]
    out["year"] = out["year"].astype(int)
    out["resistance_pct"] = out["resistance_pct"].round(2)
    out = out.drop_duplicates(["country_code", "pathogen", "antibiotic_group", "year"])
    return out.sort_values(["pathogen", "antibiotic_group", "country", "year"]).reset_index(drop=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("inputs", nargs="+", help="ECDC atlas CSV exports")
    ap.add_argument("--out", default="data/surveillance/ecdc_ears_net_resistance.csv")
    args = ap.parse_args(argv)

    df = tidy(args.inputs)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} rows to {args.out}")
    print(df.groupby(["pathogen", "antibiotic_group"]).agg(
        countries=("country", "nunique"), first=("year", "min"), last=("year", "max")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
