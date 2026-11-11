# Antibiogram data — sources, checks and exclusions

All values are **% susceptible** (susceptible ÷ tested), stored with their raw counts.

## 1. ICMR AMRSN Annual Report 2022 (national, used by AMRShield)

Indian Council of Medical Research, *Antimicrobial Resistance Research and Surveillance
Network — Annual Report, January–December 2022*. Multi-centre national surveillance.

| File | Tables | Content |
|---|---|---|
| `amrsn_2022_by_specimen.csv` | 2.7–2.11, 2.13–2.15, 2.18–2.22 | 456 cells: E. coli, K. pneumoniae, S. aureus, P. aeruginosa, A. baumannii × blood / urine / pus × OPD / Ward / ICU |
| `amrsn_yearly_trend.csv` | 3.6, 3.7, 6.4 | 54 cells: India yearly trend 2017–2022 (E. coli, K. pneumoniae, S. aureus) |

**Extraction:** `scripts/extract_amrsn_2022.py`. Each cell is printed as "S / N (%)"; the
script recomputes every percentage from its counts and stops on any disagreement, any row
with the wrong number of cells, or any skipped row. Result: **0 disagreements**.
Spot-checked against rendered pages (PDF pages 62, 82, 151).

Notes:
- Where the report prints "(-)" (percentage suppressed, small sample), counts are kept and
  the percentage is computed from them.
- Table 2.11, S. aureus oxacillin, ICU: printed 45%, counts 84/183 = 45.9%. The table
  prints whole numbers; the computed value is used.
- Specimens are not syndromes: urine ≈ UTI, blood ≈ bloodstream infection, pus ≈ skin and
  soft-tissue infection. Respiratory specimens are not tabulated in Chapter 2.
- `pct_non_susceptible` = 100 − % susceptible (includes intermediate). It is **not** the same
  measure as ECDC's "% resistant".

## 2. Single-hospital studies (regional reference only — not used for recommendations)

`hospital_antibiograms_india.csv`, both CC BY 4.0 (via Zenodo):

- **Kumari N et al.**, *Int J Pharm Clin Res* 2023;15(11):239–244 — NMCH Patna, Bihar;
  E. coli from urine, n = 226. Every row checked: S + I + R = 226.
  **Excluded:** levofloxacin (table gives S = 18, R = 182, but the paper's text names
  levofloxacin among the most effective drugs — the row contradicts the text).
- **Yadav et al.**, *Int J Pharm Clin Res* 2024;16(12):1448–1453 — Rajpura, Punjab;
  IPD, mixed specimens; E. coli n = 273, S. aureus n = 133. Each printed % checked against
  its count. **Excluded:** E. coli ciprofloxacin (printed 31.7% vs 92/273 = 33.7%);
  E. coli cefotaxime (53.1%) and ceftriaxone (29.7%) — two near-identical third-generation
  cephalosporins cannot plausibly differ this much, and the source does not show which is
  wrong; "Klebsiella species" (not identified to K. pneumoniae).

## 3. Reviewed and not used

- **Hiren et al.**, *Int J Pharm Clin Res* 2024;16(7):758–764 (Morbi, Gujarat): 12–18
  isolates per organism, and many rows where resistant + susceptible ≠ number tested
  (e.g. S. aureus vancomycin: 12 tested, 0 R, 1 S). Too small and internally inconsistent.
