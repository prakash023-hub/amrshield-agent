# 🛡️ AMRShield — AI-Powered Antibiotic Stewardship with Self-Auditing Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Built with Gemini](https://img.shields.io/badge/Built%20with-Gemini%203-blue)](https://cloud.google.com/)
[![Powered by Arize Phoenix](https://img.shields.io/badge/Observability-Arize%20Phoenix-purple)](https://phoenix.arize.com/)
[![Google Cloud](https://img.shields.io/badge/Platform-Google%20Cloud-red)](https://cloud.google.com/)
[![Track: Arize](https://img.shields.io/badge/Hackathon%20Track-Arize-orange)](https://rapid-agent.devpost.com/)

> **Research prototype. Not for clinical use without licensed physician oversight.**

AMRShield is a multi-agent clinical decision support system for **Antimicrobial Stewardship (AMS)** — powered by **Gemini 3** on Google Cloud Agent Builder, instrumented with **Arize Phoenix MCP** for real-time agent observability and self-auditing.

Antimicrobial resistance (AMR) kills **1.27 million people per year** and costs the global economy over **$100 billion annually**. AI can help — but only if we can trust the AI. AMRShield solves both problems simultaneously.

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
│  └──────────────┘    │  [Gemini 3]  │    │     [Gemini 3]      │  │
│                      └──────┬───────┘    └──────────┬──────────┘  │
│  ┌──────────────┐           │                       │             │
│  │ Stewardship  │    ┌──────▼───────┐    ┌──────────▼──────────┐  │
│  │   Admin      │    │  PREDICTION  │    │   Arize Phoenix     │  │
│  │  Dashboard   │    │    AGENT     │    │   MCP Server        │  │
│  └──────────────┘    │  [Gemini 3]  │    │  Traces/Evals/      │  │
│                      └──────┬───────┘    │  Experiments/       │  │
│  ┌──────────────┐           │            │  Annotations        │  │
│  │ Surveillance │    ┌──────▼───────┐    └─────────────────────┘  │
│  │     Map      │    │  WHO GLASS   │                             │
│  │  Dashboard   │    │  FHIR / AMR  │    Google Cloud Agent      │
│  └──────────────┘    │  Databases   │    Builder + Cloud Run     │
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
| 🌍 **Surveillance Map** | Epidemiologists, public health | Geographic AMR spread + 6-month Gemini 3 forecast |
| 🔍 **Audit Console** | Quality officers, AI safety team | Live Phoenix traces, hallucination flags, drift detection |

---

## 🤖 Three Specialized Agents

### 1. Clinical Recommendation Agent
- Ingests patient profile (symptoms, culture results, CrCl, comorbidities, allergies)
- Applies WHO AWaRe classification logic
- Recommends antibiotic with dose + duration + monitoring plan
- Tools: `query_local_antibiogram`, `check_drug_interactions`, `calculate_crcl`, `get_aware_tier`

### 2. AMR Prediction Agent
- Queries WHO GLASS API for global resistance trends
- Forecasts local resistance emergence (6-month horizon)
- Tools: `fetch_who_glass_data`, `query_resistance_db`, `run_temporal_forecast`

### 3. Self-Audit Agent ⭐ *(The Novel Differentiator)*
- Monitors every Clinical Agent decision via Phoenix MCP
- Detects hallucinations, guideline deviations, confidence miscalibration
- Flags high-risk recommendations for human physician review
- Tools: `fetch_phoenix_traces`, `detect_hallucination`, `evaluate_clinical_accuracy`, `flag_for_review`, `run_phoenix_experiment`

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|-----------|
| **AI Models** | Gemini 3 (via Vertex AI) |
| **Orchestration** | Google Cloud Agent Builder |
| **Observability** | Arize Phoenix MCP Server |
| **Hosting** | Google Cloud Run |
| **Dashboards** | Streamlit (4 apps) |
| **Database** | Cloud Firestore (patient cases, audit logs) |
| **Data Sources** | WHO GLASS API, synthetic MIMIC-IV-style cases |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Google Cloud account with Vertex AI enabled
- Arize Phoenix account + API key
- `gcloud` CLI installed

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/amrshield-agent.git
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

### 5. Deploy to Cloud Run

```bash
bash infrastructure/deploy.sh
```

---

## 📁 Repository Structure

```
amrshield-agent/
├── LICENSE                          ← MIT License
├── README.md
├── requirements.txt
├── agents/
│   ├── clinical_agent/
│   │   ├── agent.py                 ← Core clinical recommendation logic
│   │   └── tools.py                 ← AWaRe, CrCl, drug interaction tools
│   ├── prediction_agent/
│   │   ├── agent.py                 ← AMR trend forecasting
│   │   └── tools.py                 ← WHO GLASS, resistance DB tools
│   └── audit_agent/
│       ├── agent.py                 ← Self-audit orchestrator
│       └── tools.py                 ← Phoenix MCP tool wrappers
├── mcp_tools/
│   ├── phoenix_integration.py       ← Phoenix MCP server setup
│   ├── aware_tool.py                ← WHO AWaRe classification
│   ├── crcl_tool.py                 ← Cockcroft-Gault CrCl calculator
│   ├── resistance_tool.py           ← Local resistance lookup
│   └── who_glass_tool.py            ← WHO GLASS API integration
├── dashboards/
│   ├── clinician_console/app.py     ← Dashboard 1: Point-of-care
│   ├── stewardship_admin/app.py     ← Dashboard 2: Hospital oversight
│   ├── surveillance_map/app.py      ← Dashboard 3: Geographic AMR
│   └── audit_console/app.py         ← Dashboard 4: Agent audit
├── evaluations/
│   ├── synthetic_patient_cases.json ← Test cases (no real PHI)
│   ├── phoenix_evaluators.py        ← Custom clinical evaluators
│   └── run_benchmarks.py            ← CI evaluation runner
├── infrastructure/
│   ├── secrets_template.env
│   ├── cloudrun_deploy.yaml
│   └── deploy.sh
└── docs/
    ├── setup_guide.md
    ├── architecture.md
    └── safety_disclaimers.md
```

---

## ⚠️ Safety & Ethics

- **Research prototype only** — not validated for clinical use
- All patient data used is **fully synthetic** (no real PHI, no HIPAA concerns)
- Every high-risk recommendation requires **physician approval** before acting
- All AI decisions are fully **explainable and traceable** via Phoenix
- Follows WHO AWaRe, IDSA, and CDC NHSN antibiotic stewardship guidelines

---

## 📊 Potential Impact

If deployed in a 500-bed tertiary hospital:
- ~**40% reduction** in inappropriate broad-spectrum antibiotic prescriptions
- ~**$200K/year** savings in antibiotic acquisition costs
- ~**15% reduction** in C. difficile infections from overuse
- Real-time AMR surveillance replacing manual quarterly audits

---

## 🔗 Links

- **Live Demo**: [Cloud Run URL — added after deployment]
- **Demo Video**: [YouTube link — added before submission]
- **Devpost Submission**: [Link — added on submission day]

---

## 👤 Author

**Prakash Raj K** — M.Pharm (Industrial Pharmacy)  
Associate Professor, Dept. of Pharmaceutics  
Sri Balaji Vidyapeeth (SBV), Puducherry  
Mahatma Gandhi Medical College & Research Institute

*Domain expertise: Pharmacometrics, Novel Drug Delivery, Antibiotic Stewardship, Computational Pharmacy*
