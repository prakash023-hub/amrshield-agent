# AMRShield — Master Guide (Interview + Claude Prompt)

**For:** Prakash Raj K, M.Pharm — solo founder  
**Purpose:** Understand everything built, answer interviews honestly, paste into Claude in chunks  
**Live URL (official):** https://amrshield-105254876763.us-central1.run.app  
**GitHub:** https://github.com/prakash023-hub/amrshield-agent (MIT, public)

---

## HOW TO USE THIS WITH CLAUDE (read this first)

Claude **cannot always open live websites**. That is normal. Do this instead:

1. **Paste Section A** → ask: *"Teach me this like I only know Python data types"*
2. **Paste Section B** → ask: *"Quiz me on interview questions"*
3. **Paste Section C** → ask: *"Explain each file in simple words"*
4. **Paste Section D** → ask: *"Role-play: you are a senior doctor interviewing me"*
5. Upload **one section at a time** — do not paste the whole file at once (token limit).

Optional: upload `README.md` + this file to a **Claude Project** so you do not re-paste every time.

---

# SECTION A — THE STORY IN PLAIN ENGLISH (30-second to 5-minute versions)

## 30-second elevator pitch

> "AMRShield helps doctors choose the right antibiotic. A clinical AI suggests treatment using hospital resistance data and guidelines. A second AI audits that suggestion for errors. Patient names and phone numbers are stripped before cloud AI sees anything. The doctor always signs the order. It is a research prototype on Google Cloud, not an approved medical device."

## What problem are we solving?

- **AMR** = Antimicrobial Resistance. Bacteria become resistant to antibiotics.
- **AMS** = Antimicrobial Stewardship. Hospital programs that reduce wrong antibiotic use.
- Wrong antibiotic → worse outcomes, more resistance, higher cost.
- AI can help — but doctors do not trust black-box AI. **We add a self-audit layer.**

## What did we build? (one sentence per piece)

| Piece | What it is (simple) |
|-------|---------------------|
| **Streamlit app** | Python code that becomes a website (buttons, forms, charts) |
| **Clinical Agent** | Gemini AI that reads patient case → suggests antibiotic |
| **Audit Agent** | Second Gemini pass that checks if first answer is safe/logical |
| **PharmaGuard DLP** | Code that removes Aadhaar, phone, name before AI sees data |
| **RAG (BM25)** | Search our guideline JSON files, then AI uses those snippets |
| **Antibiogram** | Table of "which bugs resist which drugs" — from JSON or hospital upload |
| **Phoenix MCP** | Logging/tracing so we can show judges "here is what the AI did" |
| **Cloud Run** | Google runs our Docker container 24/7 as a public URL |

## Why Gemini 2.5 Flash? (interview answer)

Say this honestly:

> "We use **Gemini 2.5 Flash on Vertex AI** because it is fast and cheap enough for real-time bedside suggestions, supports **tool calling** (the AI can call our Python functions like creatinine clearance), runs on **Google Cloud** (same stack as the hackathon), and is good at structured clinical text. We are not claiming it is the best medical model in the world — we are claiming the **architecture** (stewardship + audit + privacy) is the product."

Do NOT say "Gemini 3" — README still says that in places; **code uses 2.5 Flash**.

## What is MCP? (interview answer — most important)

**MCP = Model Context Protocol.**

Simple analogy: MCP is like **USB for AI tools**. The AI model is the computer; MCP is the standard plug so the model can use:

- Tracing (Phoenix)
- Databases
- Custom hospital tools

In our project, **Phoenix MCP** means: every time the clinical agent runs, we **record traces** (inputs, tool calls, outputs) so the Audit Console can show hallucination checks.

One-liner: *"MCP lets our agents call observability and safety tools in a standard way, not just chat."*

## What is RAG? (interview answer)

**RAG = Retrieval Augmented Generation.**

1. User asks about UTI + E. coli  
2. We **search** `data/guidelines_corpus.json` and case studies (BM25 keyword search)  
3. We **paste** the best 3 snippets into the prompt  
4. Gemini answers **using those snippets** — less made-up guideline text  

We use **BM25** (not vector embeddings) so it works on Cloud Run without extra API costs.

## What is PharmaGuard / DLP?

**DLP = Data Loss Prevention.**

Before patient data goes to Gemini:

- Remove fields like `patient_name`, `aadhaar`, `phone`
- Redact patterns in text (Indian mobile, PAN, email)
- Keep only clinical minimum: age, weight, culture, allergies, etc.

This supports **India DPDP Act** story and hospital trust.

## Architecture flow (memorize this diagram)

```
Doctor fills form (Streamlit Clinician Console)
        ↓
PharmaGuard DLP strips PHI/PII
        ↓
Clinical Agent (Gemini 2.5 Flash)
   → tools: CrCl, antibiogram, drug interactions, RAG guidelines
   → physician_ready: order set, contraindications
        ↓
Audit Agent (Gemini + Phoenix traces)
   → confidence gate, hallucination check
        ↓
Dashboards: Audit Console, Stewardship Admin, Evidence page
```

## What is NOT done yet (be honest in interviews)

| Status | Item |
|--------|------|
| ✅ Built locally | Clinical safety, RAG, Evidence page, expanded sidebar, stewardship alerts |
| ⚠️ **Not deployed** | Live URL may still show older version — run `bash infrastructure/deploy.sh` |
| ⚠️ **Not committed** | Many files still only on your laptop (see git status) |
| ❌ Not done | Real hospital WHONET antibiogram (need microbiology lab) |
| ❌ Not done | CDSCO/FDA clearance (years + trials) |
| ❌ Not done | Paying hospital pilot / revenue |
| ❌ Not done | Doctor login / HIPAA-grade auth (optional for hackathon) |
| 🔴 Security | Delete `whatsapp_bot_v2.py` — has hardcoded API key; rotate key if ever pushed |

## Your honest founder story (use this — it is strong)

> "I am M.Pharm with clinical domain knowledge. I designed the stewardship workflow and safety requirements. I used AI coding assistants and open-source libraries to implement faster than a solo developer could alone. I can explain every component's **purpose** and **data flow**. I am not pretending to be a senior ML engineer — I am a founder who ships a verifiable prototype and partners with hospitals for real data."

This is **better** than pretending you wrote every line from memory.

---

# SECTION B — INTERVIEW Q&A (practice aloud)

### Q: "Walk me through what happens when a doctor clicks Recommend."

**A:** The Clinician Console collects age, infection, cultures, allergies, renal function. PharmaGuard removes identifying fields. The clinical agent calls Gemini with tool definitions. Gemini may call `calculate_crcl`, `query_local_antibiogram`, `retrieve_clinical_evidence`. We format a physician order set with AWaRe tier. The audit agent scores confidence and flags hallucinations. Results show in the UI with pass/flag/hold status.

### Q: "What is AWaRe?"

**A:** WHO classification: **Access** (first-line, narrow), **Watch** ( broader, resistance risk), **Reserve** ( last-line). Stewardship programs try to maximize Access tier use.

### Q: "How do you prevent the AI from inventing guidelines?"

**A:** Three layers: (1) RAG pulls real guideline snippets from our JSON corpus; (2) audit agent checks recommendation against those snippets; (3) low confidence blocks auto-accept — physician must review.

### Q: "Is this safe for patients?"

**A:** "It is **decision support only**, not autonomous prescribing. Research prototype. Physician attestation required. Not CDSCO-cleared. For pilots we need hospital ethics/IRB and labeled as investigational."

### Q: "Why Streamlit and not React?"

**A:** "Speed. One Python codebase, fast iteration for hackathon and hospital demos. Production hospitals might later wrap the same `api/main.py` FastAPI backend in a EMR-integrated UI."

### Q: "What's on Cloud Run?"

**A:** Docker image runs `streamlit run Home.py` on port 8080. Google scales it. `min-instances=1` keeps it warm (~$30–80/month). Deploy script: `infrastructure/deploy.sh`.

### Q: "What data do you use?"

**A:** Reference antibiogram aligned to ICMR/WHO GLASS patterns in `data/india_reference_antibiogram.json` — **not** a substitute for a real hospital lab. Hospitals can upload JSON on Evidence page (local code; deploy to make live).

### Q: "What would you do with ₹25k pilot money?"

**A:** Load hospital antibiogram, 4-week shadow mode (recommendations not acted on), weekly ID physician review, export audit logs, iterate on override workflow.

---

# SECTION C — CODE MAP (where everything lives)

## Folder structure

```
amrshield-agent/
├── Home.py                    # App entry — landing metrics
├── pages/                     # Streamlit multi-page UI
│   ├── 1_🩺_Clinician_Console.py   # Main doctor workflow
│   ├── 2_🔍_Audit_Console.py       # Phoenix traces, hallucination log
│   ├── 3_🏥_Stewardship_Admin.py   # Alerts, timeouts, overrides
│   ├── 4_🌍_Surveillance_Map.py    # AMR maps / trends
│   ├── 5_🔐_PharmaGuard_Trust.py   # Cyber SOC + DLP detail
│   └── 6_📚_Evidence_Case_Studies.py  # RAG corpus, antibiogram upload
├── agents/
│   ├── clinical_agent/
│   │   ├── agent.py           # Gemini client + tool loop
│   │   ├── tools.py           # CrCl, antibiogram, interactions
│   │   ├── guideline_rag.py   # LangChain BM25 over JSON
│   │   ├── evidence_store.py  # Metrics + hospital upload storage
│   │   ├── clinical_safety.py # IBW, dialysis, confidence rules
│   │   └── physician_ready.py # Order sets, attestation text
│   ├── audit_agent/agent.py   # Self-audit logic
│   └── prediction_agent/      # AMR forecast (surveillance)
├── mcp_tools/
│   ├── phoenix_integration.py # Tracing hooks
│   ├── pharmaguard_dlp.py     # PHI stripping
│   ├── pharmaguard_trust.py   # Trust chain reports
│   ├── pharmaguard_cyber.py   # Security narrative for hospitals
│   ├── stewardship_store.py   # Alert escalation, overrides
│   └── audit_store.py         # Persist audit events
├── data/
│   ├── india_reference_antibiogram.json
│   ├── guidelines_corpus.json
│   └── published_case_studies.json
├── api/main.py                # FastAPI (optional REST layer)
├── infrastructure/deploy.sh   # gcloud run deploy
├── Dockerfile                 # streamlit run Home.py
└── requirements.txt           # Python packages
```

## File types (what each kind of code does)

| Type | Extension | Role | Example |
|------|-----------|------|---------|
| UI page | `pages/*.py`, `Home.py` | What user sees | Forms, buttons, charts |
| Agent | `agents/*/agent.py` | AI brain + tool loop | Calls Gemini |
| Tool | `agents/clinical_agent/tools.py` | Deterministic math/lookup | CrCl formula |
| MCP/Security | `mcp_tools/*.py` | Privacy, tracing, storage | DLP redaction |
| Data | `data/*.json` | Knowledge without training | Guidelines, antibiogram |
| Deploy | `Dockerfile`, `deploy.sh` | Put app on internet | Cloud Run |
| API | `api/main.py` | HTTP endpoints | Future EMR integration |

## Key Python concepts used (learn these 8)

1. **dict / list** — patient case is a Python dictionary  
2. **import** — connect files together  
3. **function** — `calculate_crcl(age, weight, ...)`  
4. **os.getenv** — read secrets from environment (not hardcoded)  
5. **json.load** — read JSON data files  
6. **Streamlit** — `st.button`, `st.text_input`, `st.session_state`  
7. **Tool calling** — AI returns JSON "call this function" → we run Python → return result to AI  
8. **Docker** — box that runs the same app on Google servers  

You do **not** need to memorize every line. Know **what each file is for**.

## Python packages (requirements.txt — what they do)

| Package | Why |
|---------|-----|
| streamlit | Web UI |
| google-genai | Gemini on Vertex AI |
| langchain-core, langchain-community | RAG framework |
| rank-bm25 | Keyword search for guidelines |
| plotly | Charts in dashboards |
| fastapi, uvicorn | REST API (optional) |
| pandas | Tables / data |

---

# SECTION D — OPEN URL & THEFT (honest security)

## If I share the URL, can someone steal it?

**Partially correct — clarify three different "thefts":**

| What they can steal | Can they? | How bad? |
|---------------------|-----------|----------|
| **Use your demo** | Yes — URL is public (`--allow-unauthenticated`) | Low — expected for hackathon |
| **Copy your UI idea** | Yes — anyone can screenshot | Medium — normal for startups |
| **Copy your source code** | **Yes — GitHub is public MIT license** | **High — this is the real risk, not the URL** |
| **Steal your Google Cloud account** | No — unless you leak API keys | Critical |
| **Steal hospital patient data** | No — demo uses fake/sample cases; DLP blocks PHI in pilot design |
| **Download your trained model weights** | N/A — we use Gemini API, not a custom trained model |

**Bottom line:** The URL being open is **not** the main problem. **Public repo + MIT license** means anyone can legally fork and rebrand. That is a **business risk**, not a security bug.

## What we CAN do to protect

| Action | Effect |
|--------|--------|
| **Never commit API keys** | Prevents account hijack |
| **Rotate Gemini key** if `whatsapp_bot_v2.py` was ever pushed | Stops billing abuse |
| **Remove `whatsapp_bot_v2.py`** from repo | Closes known leak |
| **Use `.env` + Secret Manager** on Cloud Run | Keys only on server |
| **Optional: Cloud Run IAM** — require Google login to access | Stops random public use (bad for hackathon judges) |
| **Private GitHub repo** for hospital-specific configs | Hides pilot customization |
| **Trademark "AMRShield"** | Legal brand protection (long-term) |
| **Hospital contracts** | Real moat = their antibiogram data + trust + integration |

## What we CANNOT fully prevent

- Someone reimplements "AI + audit + stewardship" from scratch  
- Someone forks MIT code and changes the name  
- Competitors with more engineers  

**Your moat is:** hospital pilots, real microbiology data, physician relationships, audit evidence, India DPDP compliance story — not hiding the demo URL.

## Is sharing the URL safe for hackathon?

**Yes.** Judges expect a public demo. Share only:

- https://amrshield-105254876763.us-central1.run.app  

Do **not** share GenoFingerprint + Streamlit Space in the same email (confusing).

---

# SECTION E — CLAUDE COPY-PASTE PROMPTS (use exactly)

## Prompt 1 — Learn from zero

```
I am M.Pharm, beginner Python (data types only). I built AMRShield with AI help.
Read SECTION A and B below. Teach me one concept at a time.
After each concept, ask me one quiz question.
Use simple analogies. No jargon without definition.

[Paste SECTION A + SECTION B only]
```

## Prompt 2 — Mock interview

```
You are a senior infectious disease doctor and a Google hackathon judge.
Ask me 10 hard questions about AMRShield.
After I answer, score me 1-10 and give the correct answer I should say.
Be strict but fair.

[Paste SECTION A + SECTION B]
```

## Prompt 3 — Code walkthrough

```
I cannot show you the live app. Here is my codebase map.
Explain each folder in 2 sentences for a beginner.
Then tell me which 5 files I should read first to understand the clinical flow.

[Paste SECTION C]
```

## Prompt 4 — Security briefing

```
I am worried someone will steal my project because the Cloud Run URL is public.
Explain what is actually at risk and give me a priority-ordered checklist.

[Paste SECTION D]
```

## Prompt 5 — Deploy gap

```
My live Cloud Run may be behind my laptop code.
Here is what is pending. Give me step-by-step: git commit message idea,
deploy command, and how to verify page 6 exists on live site.

Pending: clinical_safety.py, guideline_rag.py, evidence page, stewardship_store.py
Deploy: bash infrastructure/deploy.sh from repo root
```

---

# SECTION F — GLOSSARY (flash cards)

| Term | Meaning |
|------|---------|
| AMR | Antimicrobial resistance |
| AMS | Antimicrobial stewardship |
| AWaRe | WHO antibiotic access/watch/reserve classes |
| Antibiogram | Lab table of bug vs drug resistance % |
| CrCl | Creatinine clearance — kidney function for dosing |
| PHI | Protected health info (name, phone, Aadhaar) |
| DPDP | India data protection law |
| Vertex AI | Google Cloud hosted Gemini |
| Cloud Run | Serverless container hosting |
| Streamlit | Python → web app framework |
| MCP | Standard protocol for AI tool + observability plugins |
| Phoenix | Arize platform for LLM tracing/evals |
| RAG | Retrieve documents then generate answer |
| BM25 | Classic keyword search ranking |
| Hallucination | AI states false clinical "facts" |
| IRB | Ethics board for human research |
| WHONET | Global microbiology lab data format |

---

# SECTION G — YOUR WEEKLY LEARNING PLAN (2 hours/day)

| Day | Task |
|-----|------|
| 1 | Read Section A aloud 3 times; record yourself |
| 2 | Open `pages/1_🩺_Clinician_Console.py` — only read button → agent call |
| 3 | Open `agents/clinical_agent/agent.py` — find `CLINICAL_MODEL` and tools list |
| 4 | Open `mcp_tools/pharmaguard_dlp.py` — see what gets redacted |
| 5 | Claude Prompt 2 — mock interview |
| 6 | Run app locally: `pip install -r requirements.txt` then `streamlit run Home.py` |
| 7 | Deploy + verify live URL has Evidence page |

---

**Last updated:** Conversation session — local code ahead of production deploy.
