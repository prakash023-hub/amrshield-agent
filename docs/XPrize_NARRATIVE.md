# XPRIZE Written Narrative (500–1000 words)

Copy-paste and customize with your real customer names/revenue before submitting.

---

## AMRShield: AI-Native Antibiotic Stewardship as a Service

**Founder:** Prakash Raj K, M.Pharm  
**Business:** AMRShield — Professional antibiotic stewardship guidance powered by Gemini agents  
**Category:** Professional Services Access  
**Website:** https://amrshield-105254876763.us-central1.run.app  

### The business problem

Antimicrobial resistance kills 1.27 million people annually. Hospitals are required to run Antimicrobial Stewardship Programs (AMS), but most lack enough infectious disease specialists and stewardship pharmacists. Expert guidance is expensive, slow, and unevenly distributed — especially in mid-size hospitals and emerging markets.

AMRShield is a real business that sells AI-native stewardship guidance as a professional service. We don't sell software licenses alone — we deliver expert-level antibiotic recommendations with built-in safety auditing, deployed in production on Google Cloud.

### How AI runs our business (AI-native operations)

Every customer case is handled end-to-end by AI agents without manual intervention:

**Clinical Agent (Gemini 2.5 Flash on Vertex AI):** When a clinician enters a patient profile, the agent autonomously calls four clinical tools — renal function calculation (Cockcroft-Gault), WHO AWaRe tier lookup, drug interaction checking, and local antibiogram queries — then produces a structured antibiotic recommendation with dose, duration, and rationale.

**Self-Audit Agent (Arize Phoenix MCP):** Before any recommendation reaches the clinician, a second agent runs Phoenix MCP safety tools — hallucination detection, clinical accuracy evaluation, trace fetching, and automated hold flags. It returns PASS, FLAG, or HOLD. This is not batch review; it executes on every transaction in production.

**Prediction Agent:** Forecasts resistance trends for surveillance dashboards used in stewardship reporting.

Human role: I operate as founder-engineer-clinician liaison. I onboard hospital clients, configure antibiogram data, and handle escalations when the audit agent returns HOLD. AI executes 90%+ of operational decisions — tool calls, safety checks, audit logging, and dashboard updates. I focus on sales, customer success, and clinical governance policy.

### What humans do vs what AI does

| Humans | AI agents |
|--------|-----------|
| Sales, contracts, customer onboarding | Patient case analysis |
| Final physician approval policy | Tool orchestration (CrCl, AWaRe, interactions) |
| Custom antibiogram upload | Recommendation generation |
| Training hospital staff | Self-audit on every case |
| Business accounting | Trace logging and audit console updates |
| Regulatory disclaimer oversight | Resistance forecasting |

### Jobs and economic opportunity created

AMRShield enables hospitals to offer stewardship-grade professional guidance without hiring a full AMS team immediately. Each deployment:

- **Empowers existing pharmacists** to act as stewardship coordinators using AI-augmented workflows
- **Reduces inappropriate antibiotic use**, lowering drug costs (hospitals report 10–20% antimicrobial spend reduction in published AMS programs)
- **Creates demand for clinical oversight roles** — physicians review flagged cases rather than writing every order from scratch
- **Potential to scale** to pharmacy colleges and telehealth platforms training the next generation of stewardship-aware clinicians

As we grow, we plan to hire customer success and clinical implementation specialists in India and UAE — roles enabled because AI handles the repetitive analytical workload.

### Building the business with AI (our story)

I'm a pharmacist (M.Pharm) who built AMRShield solo using Gemini 2.5 Flash, Google Cloud Agent Builder, and Cloud Run. AI accelerated every phase: architecture design, agent prompts, clinical tool logic, dashboard UI, deployment scripts, and audit pipeline integration with Arize Phoenix MCP.

The Google Cloud Rapid Agent Hackathon (Arize track) validated the self-auditing architecture. For XPRIZE, we converted the prototype into a commercial pilot offering — selling 2–4 week deployments to healthcare providers with live production URLs, not slide decks.

We acquired paying customers by pitching a low-friction pilot: deployed dashboard, configured antibiogram, physician training session, and documented audit trail. Revenue is documented via invoices and bank transfers.

### Traction and revenue

*[CUSTOMIZE BEFORE SUBMIT — example format]*

- **Customer 1:** [Hospital/Clinic/College Name], [City] — ₹[AMOUNT] pilot fee, [DATE]
- **Customer 2:** [If applicable]
- **Total revenue (hackathon period):** ₹[TOTAL]
- **Marketing spend:** ₹[AMOUNT or 0]

### Why this matters (category impact)

Professional medical expertise shouldn't be locked behind top-tier hospital budgets. AMRShield democratizes antibiotic stewardship — a professional service — using AI agents that work continuously in production. We're not projecting impact; we're operating a live business where AI executes clinical decision support and safety auditing at scale.

### What's next

Expand paid pilots across South India and UAE polyclinics, integrate FHIR hospital data feeds, and partner with telehealth platforms. AMRShield is a research-support tool requiring physician oversight — and a real AI-native business generating real revenue.

---

**Word count:** ~750 (within 500–1000 limit). Add customer specifics before submit.
