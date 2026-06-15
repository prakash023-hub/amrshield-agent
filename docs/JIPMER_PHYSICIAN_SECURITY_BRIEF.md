# AMRShield + PharmaGuard — Physician & Hospital Security Brief
**For:** JIPMER / hospital antibiotic stewardship pilots  
**Author:** Prakash Raj K, M.Pharm · Sri Balaji Vidyapeeth, Puducherry  
**Live demo:** https://amrshield-105254876763.us-central1.run.app

---

## What doctors should know (60 seconds)

AMRShield is **decision support only** — a licensed physician always signs the final order.

**Privacy:** Patient name, Aadhaar, phone, email, and address **never reach the cloud AI**. PharmaGuard strips them at the hospital edge before Gemini processes the case. Only clinical minimum necessary fields are used (age, diagnosis, allergies, creatinine, etc.) with a **pseudonymous wallet ID**.

**Safety:** A second AI agent audits every recommendation (allergies, renal dose, drug interactions, AWaRe tier). Phoenix MCP logs every step for audit.

**Security:** Prompt injection and data exfiltration attempts are blocked. Every case is sealed in an **immutable hash chain** — audit trail without storing PHI on the chain.

---

## Signal Repair — how patient data leakage is prevented

| Layer | What it does | Physician-visible outcome |
|-------|----------------|---------------------------|
| **Consent Wallet** | Pseudonymous ID, scoped consent, revocable | No real name on AI path |
| **Evil Tracker Scan** | Detects Aadhaar, PAN, mobile, email, ad trackers | Alerts if PHI detected in payload |
| **Signal Repair (DLP v2)** | Removes forbidden keys + redacts PHI in text values | Green "PHI to Cloud AI: BLOCKED" badge |
| **Edge Sanitization** | Only stewardship fields forwarded | Notes with phone numbers stripped |
| **Prompt Injection Defense** | Blocks "ignore instructions / export data" attacks | Case blocked if hijack detected |
| **Agent Output Scan** | Ensures AI reply doesn't leak PHI | Post-recommendation exfil check |
| **Trust Chain** | SHA-256 hash chain, tamper-evident | Audit for medico-legal review |

---

## Compliance alignment (demo / pilot framing)

- **India DPDP Act 2023** — purpose limitation (stewardship only), data minimization, consent scope
- **HIPAA-aligned controls** — minimum necessary, audit trail, access boundaries (demo implementation)
- **WHO AWaRe** — antibiotic tier stewardship
- **IDSA guidelines** — indication-based recommendations (reference only)

*This is a research prototype — not a certified medical device or legally compliant production EMR integration without hospital IRB/ethics review and formal DPA.*

---

## Demo script for JIPMER meeting (5 min)

1. **Clinician Console** — Enter UTI case with anonymized ID `PT-JIPMER-001`
2. **Optional:** Paste in clinical notes: `Patient contact 9876543210` — show Signal Repair banner
3. **Privacy Shield panel** — Point to "PHI to Cloud AI: BLOCKED" and compliance %
4. **Recommendation** — Access-tier antibiotic, renal check, rationale
5. **Physician Order Set** — Order ID, contraindications, monitoring labs
6. **Attestation** — Physician signs with MCI reg. number
7. **PharmaGuard Cyber SOC** — Show Signal Repair tab with repair log (hashed, no raw PHI)
8. **Audit Console** — Phoenix trace for the case

---

## What we need from JIPMER for a real pilot

1. De-identified or synthetic antibiogram (organism × drug susceptibility %)
2. Formulary list (hospital-preferred antibiotics)
3. Named physician champion (Infectious Disease / Microbiology)
4. Ethics/IRB pathway for decision-support pilot (no autonomous prescribing)
5. 4–8 week evaluation: Access-tier usage, audit flag rate, physician time saved

**Pilot offer:** ₹25,000–35,000 research pilot · 4 weeks · includes antibiogram onboarding + weekly stewardship report

---

## Technical stack (for IT / CISO)

```
Streamlit UI → PharmaGuard Cyber Guard Agent → Clinical Agent (Gemini 2.5 Flash)
            → Self-Audit Agent (Phoenix MCP) → Trust Chain (SHA-256)
Deploy: Google Cloud Run · Region: us-central1 · Edge node: edge-india-south-01 (configurable)
```

**MCP tools invoked per case:**
`create_consent_wallet` · `detect_evil_trackers` · `repair_signal` · `detect_prompt_injection` ·
`scan_agent_output_for_exfil` · `calculate_threat_score` · `append_trust_chain`

---

## Contact

Prakash Raj K · prakash023-hub@github · Demo: https://amrshield-105254876763.us-central1.run.app
