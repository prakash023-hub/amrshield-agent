# 🛡️ AMRShield — AI-Powered Antibiotic Stewardship with Self-Auditing Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Built with Gemini](https://img.shields.io/badge/Built%20with-Gemini%202.5%20Flash-blue)](https://cloud.google.com/vertex-ai)
[![Powered by Arize Phoenix](https://img.shields.io/badge/Observability-Arize%20Phoenix-purple)](https://phoenix.arize.com/)
[![Google Cloud](https://img.shields.io/badge/Platform-Google%20Cloud-red)](https://cloud.google.com/)
[![Track: Arize](https://img.shields.io/badge/Hackathon%20Track-Arize-orange)](https://rapid-agent.devpost.com/)

> **Research prototype. Not for clinical use without licensed physician oversight.**

AMRShield is a multi-agent clinical decision support system for **Antimicrobial Stewardship (AMS)** — powered by **Gemini 2.5 Flash** on Vertex AI (function calling), instrumented with **Arize Phoenix MCP** for real-time agent observability and self-auditing.

Bacterial antimicrobial resistance (AMR) was directly responsible for an estimated **1.27 million deaths in 2019** (GRAM study, *The Lancet*, 2022). AI can help — but only if clinicians can trust it. AMRShield pairs each recommendation with an automated audit of that recommendation.

---

## 🎯 What Makes This Different

Most AMS tools give you a recommendation. AMRShield gives you a recommendation **and audits itself** in real-time — flagging hallucinations, confidence miscalibrations, and guideline deviations before a clinician acts on them.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AMRShield Architecture                        │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   Clinician  │───▶│  CLINICAL    │───▶│   SELF-AUDIT AGENT  │  │
│  │   Dashboard  │    │    AGENT     │    │  (Phoenix MCP Core) │  │
│  └──────────────┘    │ [Gemini 2.5] │    │    [Gemini 2.5]     │  │
│                      └──────┬───────┘    └──────────┬──────────┘  │
│  ┌──────────────┐           │                       │             │
│  │ Stewardship  │    ┌──────▼───────┐    ┌──────────▼──────────┐  │
│  │   Admin      │    │  PREDICTION  │    │   Arize Phoenix     │  │
│  │  Dashboard   │    │    AGENT     │    │   MCP Server        │  │
│  └──────────────┘    │ [Holt base.] │    │  Traces/Evals/      │  │
│                      └──────┬───────┘    │  Experiments/       │  │
│  ┌──────────────┐           │            │  Annotations        │  │
│  │ Surveillance │    ┌──────▼───────┐    └─────────────────────┘  │
│  │     Map      │    │ ICMR AMRSN + │                             │
│  │  Dashboard   │    │ECDC + DDInter│    Vertex AI Gemini +      │
│  └──────────────┘    │    data      │    Cloud Run               │
│                      └──────────────┘                             │
│  ┌──────────────┐                                                  │
│  │ Audit Console│◀─── Real-time Phoenix traces streaming ─────────│
│  │  Dashboard   │                                                  │
│  └──────────────┘                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🖥️ Four Specialized Dashboards

| Dashboard | Users | Purpose |
|-----------|-------|---------|
| 🩺 **Clinician Console** | Bedside physicians | Real-time antibiotic recommendation + explainability |
| 🏥 **Stewardship Admin** | AMS pharmacists, hospital admin | Hospital-wide usage trends, compliance, cost savings |
| 🌍 **Surveillance Map** | Epidemiologists, public health | Geographic AMR view + 6-month baseline forecast (map still uses synthetic data; the prediction API uses real ECDC data) |
| 🔍 **Audit Console** | Quality officers, AI safety team | Live Phoenix traces, hallucination flags, drift detection |

---

## 🤖 Three Specialized Agents

### 1. Clinical Recommendation Agent
- Ingests patient profile (symptoms, culture results, CrCl, comorbidities, allergies)
- Applies WHO AWaRe classification logic
- Recommends antibiotic with dose + duration + monitoring plan
- Tools: `query_local_antibiogram`, `check_drug_interactions`, `calculate_crcl`, `lookup_aware_tier`
- **Antibiogram: real Indian data** — ICMR AMRSN 2022 national surveillance (456 verified values: E. coli, K. pneumoniae, S. aureus, P. aeruginosa, A. baumannii × blood / urine / pus × OPD / ward / ICU). Fewer than 30 isolates are not reported (CLSI M39), and WHO **Reserve** antibiotics are never offered as preferred agents

### 2. AMR Prediction Agent *(baseline — not a trained model)*
- **Real data:** annual EARS-Net resistance percentages for **30 EU/EEA countries, up to 2025** (ECDC Surveillance Atlas) — *E. coli* (fluoroquinolones, 3rd-gen cephalosporins), *K. pneumoniae* (carbapenems, 3rd-gen cephalosporins) and MRSA
- **Damped-trend Holt smoothing** with an approximate 80% interval; the damped trend stops long forecasts from running away (e.g. past 100%)
- **Backtested honestly** — rolling-origin, one-step-ahead, settings chosen on half the countries and tested on the other half:

  | Model | Mean absolute error (held-out countries) |
  |---|---|
  | Damped Holt (α 0.7, β 0.2, φ 0.5) | **2.06** percentage points |
  | Naive "same as last year" | 2.07 percentage points |
  | Original Holt (α 0.5, β 0.2) | ~2.8 percentage points |

  Damped Holt **matches but does not beat** the naive baseline on annual data, so any future model (ARIMA, Chronos) must beat both.
- **India:** real yearly data 2017–2022 from the ICMR AMRSN report (% non-susceptible for E. coli, K. pneumoniae and MRSA). Six years is a short series, so India forecasts are indicative only
- Countries in neither source still use a **clearly labelled synthetic** series

### 3. Self-Audit Agent ⭐ *(The Novel Differentiator)*
- Monitors every Clinical Agent decision via Phoenix MCP
- **Grounding check** (`detect_hallucination`): verifies the drug, its WHO AWaRe tier, any quoted CrCl value and any "no interaction / no allergy" statement against deterministic tool outputs, and returns a faithfulness score
- Rule-based guideline checks: renal dosing, allergy conflicts, Reserve-tier overuse
- Flags high-risk recommendations for human physician review (PASS / FLAG / HOLD)
- Tools: `detect_hallucination`, `evaluate_clinical_accuracy`, `fetch_phoenix_traces`, `flag_for_review`
- **Limitation:** the grounding check is rule-based. Planned upgrade: claim extraction + LLM-as-judge scoring against tool outputs and guideline text, measured on a labelled evaluation set

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|-----------|
| **AI Models** | Gemini 2.5 Flash (via Vertex AI) |
| **Orchestration** | Gemini function calling via the Google GenAI SDK (an ADK agent definition is in `agent_builder/`) |
| **Observability** | Arize Phoenix MCP Server |
| **Hosting** | Google Cloud Run |
| **Dashboards** | Streamlit (4 apps) |
| **Storage** | Local audit-event store (`mcp_tools/audit_store.py`); CSV data files in `data/` |
| **Data Sources** | ICMR AMRSN 2022 (Indian antibiogram + India trends); ECDC EARS-Net (Europe trends); DDInter (drug interactions); synthetic patient cases |
| **Forecasting** | Damped-trend Holt baseline (NumPy), backtested against a naive forecast |
| **Testing** | pytest (offline unit tests for deterministic components) |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Google Cloud account with Vertex AI enabled
- Arize Phoenix account + API key
- `gcloud` CLI installed

### 1. Clone & Install

```bash
git clone https://github.com/prakash023-hub/amrshield-agent.git
cd amrshield-agent
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp infrastructure/secrets_template.env .env
# Fill in your API keys in .env
```

### 3. Start Phoenix MCP Server

```bash
python mcp_tools/phoenix_integration.py
```

### 4. Run All Dashboards

```bash
# Terminal 1 - Clinician Console (port 8501)
streamlit run dashboards/clinician_console/app.py --server.port 8501

# Terminal 2 - Stewardship Admin (port 8502)
streamlit run dashboards/stewardship_admin/app.py --server.port 8502

# Terminal 3 - Surveillance Map (port 8503)
streamlit run dashboards/surveillance_map/app.py --server.port 8503

# Terminal 4 - Audit Console (port 8504)
streamlit run dashboards/audit_console/app.py --server.port 8504
```

### 5. Run Tests

```bash
pytest -q tests
```

38 offline tests cover the Cockcroft-Gault calculator, AWaRe lookups, renal dosing, allergy matching, drug-interaction screening (curated + DDInter, NOT_SCREENED handling), the AMRSN antibiogram (pooling, ICU filter, small-sample and Reserve-tier rules), real-data forecasting for Europe and India and backtesting, and the grounding check.

### 6. Deploy to Cloud Run

```bash
bash infrastructure/deploy.sh
```

---

## 📁 Repository Structure

```
amrshield-agent/
├── Home.py                          ← Streamlit multipage entry point
├── pages/                           ← Clinician, Audit, Stewardship, Surveillance, PharmaGuard pages
├── agents/
│   ├── clinical_agent/
│   │   ├── agent.py                 ← Gemini 2.5 Flash recommendation agent (function calling)
│   │   ├── tools.py                 ← AWaRe lookup, Cockcroft-Gault CrCl, interactions, allergy, renal dosing, antibiogram
│   │   └── physician_ready.py       ← Physician-ready order formatting
│   ├── prediction_agent/
│   │   └── agent.py                 ← Damped Holt forecast on real ECDC (Europe) and ICMR (India) data
│   └── audit_agent/
│       └── agent.py                 ← Self-Audit Agent (MCP checks + Gemini review)
├── mcp_tools/
│   ├── phoenix_integration.py       ← Phoenix tracing + MCP audit tools (grounding check, accuracy, review hold)
│   ├── audit_store.py               ← Local audit-event store (fallback when Phoenix is unavailable)
│   ├── pharmaguard_dlp.py           ← PHI redaction / DLP
│   ├── pharmaguard_cyber.py         ← Security checks
│   └── pharmaguard_trust.py         ← Trust & safety layer
├── api/
│   ├── main.py                      ← FastAPI endpoints
│   └── schemas.py
├── dashboards/                      ← Standalone Streamlit apps (one per dashboard)
├── agent_builder/amrshield_agent.py ← ADK agent definition (not used by the running app)
├── data/
│   ├── antibiogram/                 ← ICMR AMRSN 2022 antibiogram + India trends (real)
│   ├── surveillance/                ← ECDC EARS-Net resistance data (real)
│   └── interactions/                ← DDInter antibiotic pairs (CC BY-NC-SA 4.0)
├── scripts/                         ← Rebuild the data files from the raw downloads
├── evaluations/
│   └── synthetic_patient_cases.json ← 5 synthetic evaluation cases (no real PHI)
├── tests/
│   ├── test_core.py                 ← Forecasting, backtest, grounding tests
│   └── test_tool_logic.py           ← Clinical tool and interaction tests
├── infrastructure/                  ← Dockerfile, deploy.sh, secrets template
└── docs/                            ← Setup guide, safety disclaimers, demo and submission notes
```

---

## ⚠️ Safety & Ethics

- **Research prototype only** — not validated for clinical use
- All patient data used is **fully synthetic** (no real PHI, no HIPAA concerns)
- Every high-risk recommendation requires **physician approval** before acting
- Every agent step and tool call is **traceable** via Phoenix
- Rules are informed by WHO AWaRe and IDSA guidance; they have not been reviewed by a hospital stewardship committee

---

## 📊 Potential Impact *(projections, not measured results)*

AMRShield has **not** been evaluated on real patients or in a hospital, so no outcome has been measured. Published antimicrobial stewardship programme literature reports reductions in inappropriate broad-spectrum use, antibiotic costs and *C. difficile* infections; AMRShield is designed to support those same stewardship interventions. Any impact on a specific hospital would need to be measured in a supervised pilot against a pre-deployment baseline.

---

## 🚧 Known Limitations

- **National, not local, antibiogram** — the AMRSN data describes Indian surveillance centres, not the patient's own hospital. Hospitals should replace it with their own antibiogram.
- **Synthetic patient cases** — evaluation cases are synthetic, so there is **no clinical validation**.
- **Forecast is a baseline** — on real ECDC data it only ties the naive forecast. India has only six years of data (2017–2022), and AMRSN reports % non-susceptible while ECDC reports % resistant, so the two are not directly comparable.
- **Drug-interaction coverage is partial** — 7,558 antibiotic pairs from DDInter plus a curated table, but co-medications in some drug classes (cardiovascular, nervous system, anti-infective and a few others) are only partly covered, and this is stated in every result. Antibiotics in neither source are reported as **NOT_SCREENED**, never as safe.
- **DDInter data is non-commercial (CC BY-NC-SA 4.0)** — any commercial deployment must replace it with a commercially licensed interaction source.
- **Grounding check is rule-based** — it verifies specific claim types, not free-text reasoning.
- **Small evaluation set** — 5 synthetic cases; a larger, clinician-labelled set is needed before any accuracy figure can be reported.
- Dashboards display synthetic demo KPIs where no live data source exists.

---

## 📚 Data Sources & Attribution

- **ECDC Surveillance Atlas of Infectious Diseases** (EARS-Net), indicator *R - resistant isolates, percentage*, 2000–2025, accessed November 2026. Source: European Centre for Disease Prevention and Control, https://atlas.ecdc.europa.eu. Tidy file: `data/surveillance/ecdc_ears_net_resistance.csv`, rebuilt from the raw exports with `python scripts/build_ecdc_dataset.py <exports...>`.
- **DDInter** drug-drug interaction database — Xiong G. et al., *Nucleic Acids Res.* 2022;50(D1):D1200–D1207, https://ddinter.scbdd.com. Licensed **CC BY-NC-SA 4.0**: the derived file `data/interactions/ddinter_antibiotic_pairs.csv` (7,558 antibiotic pairs, built with `scripts/build_ddinter_subset.py`) is shared under the same non-commercial licence and is **not** covered by this repository's MIT licence.
- **ICMR AMRSN Annual Report 2022** — Indian Council of Medical Research, Antimicrobial Resistance Research and Surveillance Network, January–December 2022. Chapter 2 specimen tables and the yearly trend tables 3.6, 3.7 and 6.4 were extracted with `scripts/extract_amrsn_2022.py`, which recomputes every percentage from its printed counts (0 disagreements). Files and full provenance: `data/antibiogram/` (see `data/antibiogram/SOURCES.md`).
- **Single-hospital studies (regional reference only)** — Kumari N et al. 2023 (Patna, Bihar) and Yadav et al. 2024 (Rajpura, Punjab), *Int J Pharm Clin Res*, CC BY 4.0. Rows that failed consistency checks were excluded; the exclusions are listed in `SOURCES.md`.
- **WHO AWaRe classification** (antibiotic tiers).

---

## 🔗 Links

- **Demo Video**: https://youtu.be/H_-2WemM5Kw
- **Live Demo** (Cloud Run): https://amrshield-105254876763.us-central1.run.app

---

## 👤 Developer Profile
**Prakash Raj K**  
*Healthcare AI Engineer & Applied Data Scientist*  
**Domain Background:** M.Pharm (Industrial Pharmacy) | Ex-Associate Professor, Dept. of Pharmaceutics  
**Specializations:** Multi-Agent Systems, Reinforcement Learning, Clinical Data Architectures, Pharmacometrics.  
*   [LinkedIn Profile](https://www.linkedin.com/in/prakashraj-pharmaai/)
*   [GitHub Portfolio](https://github.com/prakash023-hub)  
