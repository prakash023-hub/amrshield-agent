# AMRShield — 3-Minute Devpost Demo Script

**Track:** Arize  
**Target length:** 2:45–3:00  
**Live URL:** https://amrshield-105254876763.us-central1.run.app  
**Repo:** https://github.com/prakash023-hub/amrshield-agent  

---

## Pre-recording checklist

- [ ] Cloud Run deployed (latest build with Phoenix MCP fixes)
- [ ] Browser zoom at 100%, dark mode off for clarity
- [ ] Close unrelated tabs; hide bookmarks bar
- [ ] Optional (local only): Phoenix UI at http://localhost:6006 + `python -m phoenix.server.main serve`
- [ ] Test one Clinician Console run before recording

---

## Script (with timestamps)

### 0:00–0:20 — Hook + problem

**[Screen: Home page — AMRShield title + 4 metrics]**

> "Antimicrobial resistance kills over a million people a year — but AI recommendations in hospitals only work if clinicians can *trust* them.
>
> I'm Prakash, and this is **AMRShield**: an AI antibiotic stewardship system built for the **Google Cloud Rapid Agent Hackathon**, on the **Arize track**. It doesn't just recommend antibiotics — it **audits itself** before a physician ever sees the result."

**[Click sidebar → Clinician Console]**

---

### 0:20–1:10 — Clinical Agent + tools (Gemini + Agent Builder)

**[Screen: Clinician Console sidebar — patient form]**

> "A doctor enters a patient case — age, renal function, diagnosis, allergies, current medications."

**[Fill in demo case:]**
- Age: **68**, Female, Weight **58 kg**
- Creatinine: **1.8**
- Diagnosis: **UTI**
- Allergies: **penicillin**
- Meds: **warfarin**

**[Click "Get Recommendation"]**

> "The **Clinical Agent** — powered by **Gemini 2.5 Flash on Vertex AI** via **Google Cloud Agent Builder** — calls four tools: Cockcroft-Gault CrCl, WHO AWaRe tier lookup, drug interaction checking, and a local hospital antibiogram."

**[Wait for recommendation card to appear]**

> "It returns a structured recommendation: antibiotic, dose, duration, AWaRe tier, and clinical rationale — with a confidence score."

---

### 1:10–2:00 — Self-Audit Agent + Phoenix MCP (Arize differentiator)

**[Point to Self-Audit banner + MCP tools line]**

> "Before the clinician acts, the **Self-Audit Agent** runs. This is our differentiator for the **Arize track**.
>
> It invokes **Phoenix MCP tools** in sequence: `detect_hallucination`, `evaluate_clinical_accuracy`, `fetch_phoenix_traces`, and if needed, `flag_for_review` to hold the recommendation."

**[Highlight penicillin allergy → HOLD/FLAG if triggered]**

> "Here — penicillin allergy against a penicillin-class drug — the MCP pipeline flags a **critical allergy conflict** and escalates to **HOLD**. You can see exactly which MCP tools ran, and the Phoenix trace ID."

**[Optional local cutaway — 5 sec max: Phoenix UI at localhost:6006 showing a trace]**

> "With Phoenix running locally, every Gemini call is auto-traced via OpenInference — judges can replay the full agent reasoning chain."

---

### 2:00–2:35 — Audit Console + dashboards

**[Sidebar → Audit Console → click Refresh]**

> "The **Audit Console** streams audit verdicts — PASS, FLAG, HOLD — with live traces from our MCP pipeline marked **LIVE MCP**. Hallucination flags and physician review queue are here for the quality team."

**[Quick scroll: Stewardship Admin — 5 sec]**

> "Stewardship Admin tracks hospital-wide AWaRe compliance and cost savings."

**[Quick scroll: Surveillance Map — 5 sec]**

> "And the Surveillance Map shows global AMR resistance with Gemini-powered forecasting."

---

### 2:35–3:00 — Architecture + close

**[Screen: Home page or architecture slide / README diagram]**

> "Architecture: patient input → Clinical Agent with tools → Self-Audit Agent with **Arize Phoenix MCP** → physician approval gate.
>
> Stack: **Gemini 2.5 Flash**, **Google Cloud Agent Builder**, **Arize Phoenix MCP**, **Cloud Run**, open source on GitHub under MIT.
>
> AMRShield — AI that recommends antibiotics *and proves it checked itself*. Thank you."

**[End card — 3 seconds]**

```
AMRShield
https://amrshield-105254876763.us-central1.run.app
github.com/prakash023-hub/amrshield-agent
Google Cloud Rapid Agent Hackathon · Arize Track
```

---

## Devpost submission text (copy-paste)

**Project name:** AMRShield — AI Antibiotic Stewardship with Self-Auditing Agent

**Elevator pitch:**
AMRShield is a multi-agent antibiotic stewardship system for hospitals. Gemini 2.5 Flash recommends the safest antibiotic using clinical tools (CrCl, AWaRe, antibiogram, drug interactions). A Self-Audit Agent then runs Arize Phoenix MCP tools to detect hallucinations, allergy conflicts, and guideline violations — holding unsafe recommendations before physician review.

**Technologies:**
- Gemini 2.5 Flash (Vertex AI)
- Google Cloud Agent Builder / ADK
- Arize Phoenix MCP (detect_hallucination, evaluate_clinical_accuracy, fetch_phoenix_traces, flag_for_review)
- Google Cloud Run
- Streamlit multipage dashboards
- FastAPI backend

**Partner track:** Arize

**What I learned:**
Integrating observability as a first-class agent step — not just logging — makes clinical AI auditable. Phoenix MCP lets the audit agent query traces and run evaluators as tools, which is the pattern I'd use in production AMS workflows.

---

## Recording tips

1. **Speak to the judges** — say "Arize MCP" and "Agent Builder" out loud; they score partner integration.
2. **Show the MCP tools line** on Clinician Console — it's proof of integration.
3. **Use the penicillin allergy demo** — visual HOLD is memorable.
4. **Keep under 3 minutes** — only the first 3 minutes are evaluated.
5. Upload to **YouTube (Unlisted)** or **Vimeo**, add English captions if needed.
