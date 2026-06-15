# AMRShield — Devpost + YouTube Submission (Copy-Paste Ready)

Use this document when submitting to Devpost and uploading your demo video to YouTube.

---

## PART A: YouTube Upload

### Step-by-step

1. Record your demo (see `docs/DEMO_VIDEO_FULL_GUIDE.md`)
2. Edit to **under 3:00** → export as MP4
3. Go to **https://studio.youtube.com**
4. Click **Create** (top right) → **Upload videos**
5. Select your `AMRShield_Demo_Final.mp4`
6. Fill in the fields below (copy-paste)
7. Set visibility to **Unlisted**
8. Click **Publish**
9. Copy the video URL for Devpost

---

### YouTube — Title (pick one)

```
AMRShield — AI Antibiotic Stewardship with Self-Auditing Agent | Google Cloud Hackathon | Arize Track
```

Shorter alternative:

```
AMRShield — Self-Auditing AI for Antibiotic Stewardship | Arize Phoenix MCP
```

---

### YouTube — Description (copy all)

```
AMRShield is an AI-powered Antibiotic Stewardship system built for the Google Cloud Rapid Agent Hackathon 2026 (Arize Track).

🛡️ What it does
Doctors enter patient details → Gemini 2.5 Flash recommends the safest antibiotic → a Self-Audit Agent runs Arize Phoenix MCP safety tools → PASS / FLAG / HOLD → physician approves.

🤖 Three Agents
• Clinical Agent — CrCl, AWaRe tier, antibiogram, drug interactions (Gemini 2.5 Flash + tools)
• Self-Audit Agent — Phoenix MCP: detect_hallucination, evaluate_clinical_accuracy, fetch_phoenix_traces, flag_for_review
• Prediction Agent — AMR resistance forecasting

🧰 Tech Stack
• Gemini 2.5 Flash (Vertex AI)
• Google Cloud Agent Builder
• Arize Phoenix MCP + OpenInference tracing
• Google Cloud Run
• Streamlit + FastAPI

🔗 Links
Live demo: https://amrshield-105254876763.us-central1.run.app
GitHub: https://github.com/prakash023-hub/amrshield-agent
License: MIT

🏆 Hackathon
Google Cloud Rapid Agent Hackathon 2026 — Partner Track: Arize

Built by Prakash Raj K | Sri Balaji Vidyapeeth, Puducherry

#GoogleCloud #Gemini #Arize #PhoenixMCP #AgentBuilder #Hackathon #AMR #HealthcareAI
```

---

### YouTube — Settings

| Setting | Value |
|---------|--------|
| **Visibility** | Unlisted |
| **Category** | Science & Technology |
| **Language** | English |
| **Audience** | Not made for kids |
| **Comments** | Optional (can disable) |

### YouTube — Tags (optional, paste in Tags field)

```
AMRShield, Google Cloud, Gemini, Arize Phoenix, MCP, Agent Builder, hackathon, antibiotic stewardship, healthcare AI, Vertex AI, Cloud Run
```

---

## PART B: Devpost Submission

**Submit at:** https://rapid-agent.devpost.com/project/submit

Log in with your Devpost account first.

---

### Project name

```
AMRShield — AI Antibiotic Stewardship with Self-Auditing Agent
```

---

### Elevator pitch / Tagline (one sentence)

```
Multi-agent antibiotic stewardship: Gemini recommends, Arize Phoenix MCP audits every decision before the physician acts.
```

---

### About the project (main description — copy all)

```
## The Problem

Antimicrobial resistance (AMR) kills 1.27 million people per year. AI can help hospitals choose better antibiotics — but only if clinicians trust the AI. Most tools give a recommendation with no proof it was checked for safety.

## Our Solution

AMRShield is a multi-agent clinical decision support system for Antimicrobial Stewardship (AMS). It recommends antibiotics AND audits itself in real time before a physician ever sees the result.

## How It Works

1. **Clinical Agent** (Gemini 2.5 Flash on Vertex AI via Google Cloud Agent Builder)
   - Patient case in → calls 4 tools: Cockcroft-Gault CrCl, WHO AWaRe tier lookup, drug interaction checker, local hospital antibiogram
   - Returns structured JSON: drug, dose, duration, AWaRe tier, rationale, confidence

2. **Self-Audit Agent** (Arize Phoenix MCP — our differentiator)
   - Runs BEFORE clinician approval
   - Invokes Phoenix MCP tools: detect_hallucination, evaluate_clinical_accuracy, fetch_phoenix_traces, flag_for_review
   - Returns PASS / FLAG / HOLD
   - Critical issues (allergy conflicts, renal dosing errors, hallucinations) are HELD automatically

3. **Physician approval gate** — no prescription without review when flagged

4. **Prediction Agent** — AMR resistance trend forecasting using WHO GLASS-style data

## Partner Integration (Arize Track)

We built meaningful Arize Phoenix MCP integration into the agent loop — not just logging:

- Self-Audit Agent dispatches MCP tools as agent actions on every recommendation
- OpenInference auto-traces all Gemini calls to Phoenix
- Audit Console streams live MCP audit traces (PASS/FLAG/HOLD)
- Physician review queue for held recommendations

## Four Dashboards

| Dashboard | Purpose |
|-----------|---------|
| Clinician Console | Point-of-care recommendation + audit verdict |
| Audit Console | Phoenix trace stream, hallucination log, review queue |
| Stewardship Admin | Hospital KPIs, AWaRe compliance, cost savings |
| Surveillance Map | Global AMR choropleth + Gemini forecast |

## Tech Stack

- **AI:** Gemini 2.5 Flash (Vertex AI, google.genai SDK)
- **Orchestration:** Google Cloud Agent Builder (ADK)
- **Observability:** Arize Phoenix MCP + OpenInference GoogleGenAIInstrumentor
- **Hosting:** Google Cloud Run
- **UI:** Streamlit multipage app
- **API:** FastAPI + Pydantic
- **License:** MIT (open source)

## Try It

🌐 Live: https://amrshield-105254876763.us-central1.run.app
📦 GitHub: https://github.com/prakash023-hub/amrshield-agent

## Demo Tip for Judges

In Clinician Console: enter a patient with **penicillin allergy** → Get Recommendation → watch Self-Audit return **HOLD** with Phoenix MCP tools listed on screen → check Audit Console for **LIVE MCP** trace.

## What We Learned

Integrating observability as a first-class agent step — not post-hoc logging — makes clinical AI auditable. Phoenix MCP lets the audit agent query traces and run evaluators as tools, which is the pattern we'd use in production antibiotic stewardship workflows.
```

---

### Built with (technologies — check/select on Devpost if checkboxes)

```
Gemini 2.5 Flash
Google Cloud Agent Builder
Google Cloud Run
Vertex AI
Arize Phoenix MCP
Streamlit
FastAPI
Python
```

---

### Partner track

```
Arize
```

---

### URLs to enter

| Field | URL |
|-------|-----|
| **Project URL** (hosted demo) | https://amrshield-105254876763.us-central1.run.app |
| **Source code / GitHub** | https://github.com/prakash023-hub/amrshield-agent |
| **Demo video** | *(paste your YouTube Unlisted link after upload)* |

---

### Video link placeholder

After YouTube upload, your link will look like:

```
https://youtu.be/XXXXXXXXXXX
```

or

```
https://www.youtube.com/watch?v=XXXXXXXXXXX
```

---

### Additional notes for Devpost (if asked)

**Team size:** 1 (solo) — adjust if team

**Open source license:** MIT

**Platform:** Web

**New project during contest period:** Yes

---

## PART C: Submission checklist

Before you click Submit on Devpost:

- [ ] Video uploaded to YouTube (Unlisted or Public)
- [ ] Video is **3 minutes or less**
- [ ] Video shows app working on live URL
- [ ] Video mentions/shows Arize Phoenix MCP
- [ ] Project URL loads: https://amrshield-105254876763.us-central1.run.app
- [ ] GitHub is public with LICENSE file visible
- [ ] Partner track = **Arize**
- [ ] All required Devpost fields filled
- [ ] Submitted before **June 11, 2026, 2:00 PM PT**

---

## PART D: Quick order of operations

```
1. Record demo video (2:45–2:55)
2. Edit → export MP4
3. Upload to YouTube (Unlisted) → copy link
4. Open Devpost → Enter a Submission
5. Paste all fields from this doc
6. Paste YouTube link in Video field
7. Review preview → Submit
```

Done.
