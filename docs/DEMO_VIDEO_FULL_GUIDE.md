# AMRShield — Complete Demo Video Guide (Record → Edit → Submit)

Everything you need for the **Google Cloud Rapid Agent Hackathon** Devpost video.

---

## Part 1: What judges require

| Requirement | What it means for you |
|-------------|------------------------|
| **Length** | Max **3 minutes**. Only the **first 3 minutes** are judged. Aim for **2:45–2:55**. |
| **Platform** | Must show the app **working** (web is fine). Use your **live Cloud Run URL**. |
| **Hosting** | Upload to **YouTube** (Unlisted or Public) or **Vimeo**. Paste the link on Devpost. |
| **Language** | **English** narration (or English subtitles). |
| **Content** | Show **Gemini**, **Google Cloud Agent Builder**, and **Arize Phoenix MCP** clearly. |
| **Track** | Select **Arize** on Devpost. |

**You do NOT need:** Hollywood editing, face cam (optional), or Phoenix running locally (nice bonus only).

---

## Part 2: What you need before recording

### Software (pick one screen recorder)

| Tool | Mac | Free? | Best for |
|------|-----|-------|----------|
| **QuickTime Player** | ✅ | ✅ | Simplest — File → New Screen Recording |
| **OBS Studio** | ✅ | ✅ | Clean full-screen capture |
| **Loom** | ✅ | Free tier | Easy + auto-upload |
| **CapCut** | ✅ | ✅ | Record + edit in one app |

### Browser setup

1. Open **Chrome** or **Edge** (full screen optional).
2. Zoom: **100%** (Cmd+0).
3. Close extra tabs; hide bookmarks bar.
4. Open: https://amrshield-105254876763.us-central1.run.app
5. **Practice once** before you record (see Part 4).

### Optional (stronger Arize story — only if you have 10 extra min)

```bash
# Terminal 1
python -m phoenix.server.main serve
# Open http://localhost:6006 in another tab
```

You can cut in **5 seconds** of Phoenix UI in editing. Not required for Cloud Run-only demo.

---

## Part 3: Demo patient case (memorize this)

Use this case every time — it triggers **HOLD** via Phoenix MCP (penicillin allergy):

| Field | Value |
|-------|--------|
| Age | **68** |
| Sex | **female** |
| Weight | **58** kg |
| Creatinine | **1.8** mg/dL |
| Diagnosis | **Urinary Tract Infection** |
| Pathogen | Unknown (empirical) |
| Allergies | **penicillin** (remove "none") |
| Current meds | **warfarin** (remove "none") |

Then click **🚀 Get Recommendation** and wait 15–40 seconds.

**You must show on screen:**
- Recommendation card (drug, dose, AWaRe tier)
- **Self-Audit: HOLD** (or FLAG) banner
- Line: **"Phoenix MCP tools invoked: detect_hallucination, evaluate_clinical_accuracy, …"**
- Trace ID

---

## Part 4: Shot list (what to record — in order)

Record as **one continuous take** if possible. If you mess up, stop and restart — easier than heavy editing.

| Shot | Time | Screen | Action |
|------|------|--------|--------|
| 1 | 0:00–0:20 | Home page | Read hook; point at title + metrics |
| 2 | 0:20 | Sidebar | Click **Clinician Console** |
| 3 | 0:25–0:45 | Clinician sidebar | Fill patient form (table above) |
| 4 | 0:45–1:10 | Clinician main | Click Get Recommendation; wait; show result |
| 5 | 1:10–1:50 | Clinician main | Zoom/read audit banner + MCP tools line + HOLD |
| 6 | 1:50–2:15 | Audit Console | Sidebar → Audit Console → **Refresh** → LIVE MCP |
| 7 | 2:15–2:25 | Stewardship Admin | Quick scroll (5 sec) |
| 8 | 2:25–2:35 | Surveillance Map | Quick scroll (5 sec) |
| 9 | 2:35–3:00 | Home or README | Architecture + thank you + URLs |

---

## Part 5: Full narration script (read this while recording)

Speak clearly, slightly slower than normal conversation.

---

### [0:00–0:20] HOOK — Home page

> "Antimicrobial resistance kills over one million people every year. But AI in hospitals only works if doctors can **trust** the recommendation.
>
> I'm Prakash. This is **AMRShield** — built for the **Google Cloud Rapid Agent Hackathon**, on the **Arize track**.
>
> It doesn't just suggest antibiotics. It **audits itself** with **Arize Phoenix MCP** before a physician ever acts."

**[Click: Clinician Console in sidebar]**

---

### [0:20–1:10] CLINICAL AGENT — Clinician Console

> "Here's the Clinician Console. A doctor enters the patient: age, kidney function, diagnosis, allergies, and medications."

**[Type/select the demo case from Part 3]**

> "I'll click **Get Recommendation**.
>
> The **Clinical Agent** uses **Gemini 2.5 Flash on Vertex AI**, orchestrated with **Google Cloud Agent Builder**. It calls four tools: renal CrCl, WHO AWaRe classification, drug interactions, and our local antibiogram."

**[Wait for loading to finish]**

> "We get a structured output: drug, dose, duration, AWaRe tier, rationale, and a confidence score."

---

### [1:10–2:00] SELF-AUDIT + PHOENIX MCP — same screen

**[Point cursor at yellow/red audit banner]**

> "Before anyone prescribes this, the **Self-Audit Agent** runs. This is our **Arize** differentiator.
>
> It calls **Phoenix MCP tools** in order: **detect_hallucination**, **evaluate_clinical_accuracy**, **fetch_phoenix_traces**, and **flag_for_review** if the case is unsafe."

**[Point at MCP tools line under the banner]**

> "This patient has a **penicillin allergy**, and the recommendation conflicts — so the pipeline returns **HOLD**. You can see exactly which MCP tools ran, and the trace ID for observability."

---

### [2:00–2:35] OTHER DASHBOARDS

**[Sidebar → Audit Console → Refresh]**

> "The Audit Console shows PASS, FLAG, and HOLD over time. Live runs from our MCP pipeline are tagged **LIVE MCP**. There's a hallucination log and a physician review queue."

**[Sidebar → Stewardship Admin — scroll 5 sec]**

> "Stewardship Admin tracks hospital-wide AWaRe compliance and savings."

**[Sidebar → Surveillance Map — scroll 5 sec]**

> "The Surveillance Map shows global resistance and forecasting."

---

### [2:35–3:00] CLOSE — Home or GitHub README

> "Pipeline: patient in, Clinical Agent with tools, Self-Audit with **Phoenix MCP**, then physician approval.
>
> Stack: **Gemini 2.5 Flash**, **Agent Builder**, **Arize Phoenix MCP**, **Cloud Run**, open source on GitHub, MIT license.
>
> **AMRShield** — AI that recommends antibiotics and proves it checked itself. Thank you."

**[Hold on screen for 3 seconds:]**

```
AMRShield
https://amrshield-105254876763.us-central1.run.app
github.com/prakash023-hub/amrshield-agent
Arize Track · Google Cloud Rapid Agent Hackathon 2026
```

---

## Part 6: How to record (Mac — QuickTime)

1. Open **QuickTime Player** → **File** → **New Screen Recording**.
2. Click **Options** → select microphone (built-in or AirPods).
3. Click **Record** → select browser window (or full screen).
4. Follow **Part 5** script and **Part 4** shot list.
5. Press **Stop** in menu bar → save as `AMRShield_Demo_Raw.mov`.

**Tips:**
- Do **2–3 takes**; pick the best one.
- If Gemini is slow on Cloud Run, **keep talking** while it loads ("The agent is calling tools now…").
- Move the **mouse slowly** when pointing at MCP text.

---

## Part 7: How to edit (simple — CapCut or iMovie)

### Goal
- **2:45–2:55** final length (under 3:00 always).
- Trim mistakes at start/end.
- Optional: title card + end card.

### Steps (CapCut desktop or mobile)

1. **Import** `AMRShield_Demo_Raw.mov`.
2. **Trim** dead time at beginning (desktop clutter) and end.
3. **Cut** any long waits:
   - If loading > 10 sec, cut middle and add 1 sec transition OR voiceover "Agent reasoning…".
4. **Add text overlays** (optional but professional):
   - 0:03 — Title: `AMRShield · Arize Track`
   - 1:15 — `Phoenix MCP: detect_hallucination → evaluate_clinical_accuracy → flag_for_review`
   - 2:50 — End card with URLs (see Part 5)
5. **Export:** 1080p, MP4, 30fps.
6. **Watch once** — confirm MCP tools line is readable.

### You do NOT need
- Background music (can distract judges).
- Fancy transitions.
- Video longer than 3 minutes.

---

## Part 8: Upload & Devpost

### YouTube (recommended)

1. Go to https://studio.youtube.com → **Create** → **Upload video**.
2. File: `AMRShield_Demo_Final.mp4`.
3. Title: `AMRShield — AI Antibiotic Stewardship | Google Cloud Hackathon | Arize Track`
4. Visibility: **Unlisted** (judges with link can view).
5. Copy the video URL.

### Devpost fields

| Field | Paste |
|-------|--------|
| **Video URL** | Your YouTube/Vimeo link |
| **Project URL** | https://amrshield-105254876763.us-central1.run.app |
| **GitHub** | https://github.com/prakash023-hub/amrshield-agent |
| **Partner track** | **Arize** |

Use description from `docs/demo_video_script.md` (Devpost section) or README.

---

## Part 9: Troubleshooting during recording

| Problem | Fix |
|---------|-----|
| Recommendation never loads | Cloud Run cold start — wait 60s or retry; mention "cold start" in voiceover |
| Audit says PASS not HOLD | Ensure **penicillin** allergy is selected and not "none" |
| No "Phoenix MCP tools" line | Redeploy latest image; hard-refresh browser (Cmd+Shift+R) |
| Audit Console no LIVE MCP | Run one case in Clinician Console first, then Refresh Audit Console |
| Video over 3 min | Trim Stewardship/Surveillance to 3 sec each |

---

## Part 10: One-page cheat sheet (print this)

```
URL:     https://amrshield-105254876763.us-central1.run.app
GitHub:  github.com/prakash023-hub/amrshield-agent
Track:   Arize
Length:  under 3:00 (aim 2:50)

DEMO CASE: 68F, 58kg, Cr 1.8, UTI, allergy=penicillin, warfarin

MUST SHOW:  Get Recommendation → HOLD/FLAG → MCP tools line → Audit Console LIVE MCP

SAY OUT LOUD: Gemini 2.5 Flash · Agent Builder · Arize Phoenix MCP · Cloud Run

UPLOAD: YouTube Unlisted → paste link on Devpost
```

---

## Quick checklist before you submit

- [ ] Video ≤ 3 minutes
- [ ] English audio
- [ ] Live app URL shown/working
- [ ] Arize MCP mentioned and shown on screen
- [ ] Agent Builder + Gemini mentioned
- [ ] GitHub public + MIT license
- [ ] Devpost track = **Arize**
- [ ] Submit before **June 11, 2026, 2:00 PM PT**
