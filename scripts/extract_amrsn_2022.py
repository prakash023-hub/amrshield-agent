"""
Extract antibiogram data from the ICMR AMRSN Annual Report 2022 (PDF).

Source: Indian Council of Medical Research, Antimicrobial Resistance Research
        and Surveillance Network (AMRSN), Annual Report, January–December 2022.

Usage (needs poppler's pdftotext):
    python scripts/extract_amrsn_2022.py AMRSN_Annual_Report_2022.pdf

Writes:
    data/antibiogram/amrsn_2022_by_specimen.csv   (Chapter 2 tables, OPD/Ward/ICU)
    data/antibiogram/amrsn_yearly_trend.csv       (Tables 3.6, 3.7, 6.4; 2017–2022)

Every cell is printed in the report as "susceptible / tested (percent)". The
script recomputes the percent from the counts and stops if any cell disagrees
with the printed value (whole-number cells: ±1; one-decimal cells: ±0.15), if a
row has the wrong number of cells, or if any table row is skipped.
"""

from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "antibiogram"

SPECIMEN_TABLES = {
    "2.7": ("E. coli", "blood"), "2.8": ("K. pneumoniae", "blood"),
    "2.9": ("A. baumannii", "blood"), "2.10": ("P. aeruginosa", "blood"),
    "2.11": ("S. aureus", "blood"),
    "2.13": ("E. coli", "urine"), "2.14": ("K. pneumoniae", "urine"),
    "2.15": ("P. aeruginosa", "urine"),
    "2.18": ("E. coli", "pus"), "2.19": ("S. aureus", "pus"),
    "2.20": ("K. pneumoniae", "pus"), "2.21": ("A. baumannii", "pus"),
    "2.22": ("P. aeruginosa", "pus"),
}
YEARLY = [  # (table, end marker, pathogen, antibiotics)
    ("Table 3.6:", "Figure 3.7", "E. coli", ["Ciprofloxacin", "Cefotaxime", "Meropenem", "Imipenem"]),
    ("Table 3.7:", "Figure 3.8", "K. pneumoniae", ["Meropenem", "Cefotaxime", "Imipenem", "Ciprofloxacin"]),
    ("Table 6.4:", "Figure 6.1", "S. aureus", ["Cefoxitin"]),
]
FRAC = re.compile(r"(\d+)\s*/\s*(\d+)")
PCT = re.compile(r"\(\s*([\d.]+|-)\s*%?\s*\)")


def pdf_text(pdf: str) -> tuple[list[str], list[int]]:
    txt = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, check=True).stdout
    lines, page_of = [], []
    for page_no, page in enumerate(txt.split("\f"), start=1):
        for line in page.split("\n"):
            lines.append(line)
            page_of.append(page_no)
    return lines, page_of


def check(s: int, n: int, printed: str | None) -> bool:
    if printed in (None, "-"):
        return True                                   # report hides % for small samples
    tol = 0.15 if "." in printed else 1.0
    return n > 0 and abs(100 * s / n - float(printed)) <= tol


def specimen_tables(lines, page_of) -> list[dict]:
    rows, errors = [], []
    starts = {}
    for i, line in enumerate(lines):
        m = re.match(r"\s*Table (2\.\d+)\b", line)
        if m and m.group(1) in SPECIMEN_TABLES and m.group(1) not in starts:
            starts[m.group(1)] = i
    missing = set(SPECIMEN_TABLES) - set(starts)
    if missing:
        sys.exit(f"Tables not found: {sorted(missing)}")

    for tid, start in starts.items():
        pathogen, specimen = SPECIMEN_TABLES[tid]
        end = next(i for i in range(start + 1, len(lines)) if re.search(r"Figure 2\.\d+", lines[i]))
        block = lines[start:end]
        expected = sum(1 for b in block if FRAC.search(b))
        names, pending, j = set(), "", 0
        while j < len(block):
            fr = FRAC.findall(block[j])
            if len(fr) == 3:
                name = re.sub(r"\s+", " ", (pending + " " + FRAC.sub("", block[j])).strip()).replace("- ", "-")
                pending = ""
                pct_line = block[j + 1] if j + 1 < len(block) else ""
                pcts = PCT.findall(pct_line)
                tail = PCT.sub("", pct_line).strip()
                if tail:
                    name = name + tail if name.endswith("-") else f"{name} {tail}"
                if len(pcts) != 3:
                    errors.append(f"{tid} {name}: {len(pcts)} percentages")
                    pcts = [None] * 3
                for loc, (s, n), p in zip(("OPD", "Ward", "ICU"), fr, pcts):
                    s, n = int(s), int(n)
                    if not check(s, n, p):
                        errors.append(f"{tid} {name} {loc}: {s}/{n} printed {p}")
                    rows.append({"pathogen": pathogen, "specimen": specimen, "antibiotic": name,
                                 "location": loc, "susceptible": s, "tested": n,
                                 "pct_susceptible": round(100 * s / n, 1) if n else "",
                                 "source": f"AMRSN 2022 Table {tid}", "pdf_page": page_of[start]})
                names.add(name)
                j += 2
                continue
            t = block[j].strip()
            keep = t and not re.search(r"Table|AMA|OPD|n=|Escherichia|Klebsiella|aureus|aeruginosa|baumannii|^\d", t)
            pending = f"{pending} {t}".strip() if keep else ""
            j += 1
        if len(names) != expected:
            errors.append(f"{tid}: {expected} rows in table, {len(names)} parsed")
    if errors:
        sys.exit("Extraction check failed:\n" + "\n".join(errors))
    return rows


def yearly_tables(lines, page_of) -> list[dict]:
    rows, errors = [], []
    for title, stop, pathogen, antibiotics in YEARLY:
        i = next(k for k, l in enumerate(lines) if title in l)
        j = next(k for k in range(i + 1, len(lines)) if stop in lines[k])
        for ab in antibiotics:
            k = next(k for k in range(i, j) if re.match(r"^\s*" + ab + r"\b", lines[k]))
            window = [k, k + 1] if FRAC.search(lines[k]) else [k - 1, k + 1]
            fr = [f for w in window for f in FRAC.findall(lines[w])]
            pc = [p for w in window for p in PCT.findall(lines[w])]
            if len(fr) != 6 or len(pc) != 6:
                errors.append(f"{title} {ab}: {len(fr)} counts, {len(pc)} percentages")
                continue
            for year, (s, n), p in zip(range(2017, 2023), fr, pc):
                s, n = int(s), int(n)
                if not check(s, n, p):
                    errors.append(f"{title} {ab} {year}: {s}/{n} printed {p}")
                rows.append({"pathogen": pathogen, "antibiotic": ab, "year": year, "susceptible": s,
                             "tested": n, "pct_susceptible": round(100 * s / n, 1),
                             "pct_non_susceptible": round(100 - 100 * s / n, 1),
                             "source": f"AMRSN 2022 {title.strip(':')}", "pdf_page": page_of[i]})
    if errors:
        sys.exit("Extraction check failed:\n" + "\n".join(errors))
    return rows


def write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {path}")


def main() -> int:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    lines, page_of = pdf_text(sys.argv[1])
    write(OUT / "amrsn_2022_by_specimen.csv", specimen_tables(lines, page_of))
    write(OUT / "amrsn_yearly_trend.csv", yearly_tables(lines, page_of))
    print("All cells match their printed percentages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
