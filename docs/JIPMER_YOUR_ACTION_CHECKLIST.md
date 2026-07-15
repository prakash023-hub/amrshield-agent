# JIPMER — What YOU Must Do (AMRShield cannot do for you)

AMRShield now has **real-world reference data** (ICMR/WHO GLASS patterns), **LangChain RAG** (IDSA/WHO guidelines + published case studies), and **hospital antibiogram upload**. To make it **sellable to JIPMER**, you still need these **human steps**.

---

## ✅ Already built (show doctors)

| Feature | Where |
|---------|--------|
| India reference antibiogram (ICMR/GLASS) | Clinician Console → resistance chart |
| LangChain RAG evidence | Clinician Console → Evidence panel · Page 6 |
| Published case studies (WHO, ICMR, IDSA, CDC) | Page 6 → Case Studies tab |
| JIPMER upload slot | Page 6 → JIPMER Upload tab |
| Real metrics (no fake numbers) | Home + Clinician Console (from audit log) |
| Privacy / PharmaGuard DLP | Clinician Console → Privacy Shield |

**Live demo:** https://amrshield-105254876763.us-central1.run.app

---

## 🔴 YOU must get from JIPMER (Week 1 of pilot)

### 1. Antibiogram CSV/JSON (most important)
- **Who:** Microbiology HOD or WHONET operator  
- **What:** Last 12 months, organism × antibiotic × % susceptible/resistant  
- **Format:** WHONET export or Excel → paste JSON in **Evidence page → JIPMER Upload**  
- **Why:** Doctors only trust **their** susceptibility data  

**Email line:**  
> “We need de-identified aggregate antibiogram (no patient IDs) for stewardship pilot — WHONET export preferred.”

### 2. Named physician champion
- **Who:** Infectious Disease / Microbiology / Medicine HOD  
- **What:** 30-min demo + agrees to 4-week research pilot  
- **Why:** No hospital buys without an internal doctor sponsor  

### 3. Ethics / IRB pathway
- **Who:** JIPMER research ethics committee  
- **What:** Decision-support pilot — no autonomous prescribing, de-identified cases  
- **Why:** Required before real patient workflow (even de-identified)  

### 4. Formulary list (optional Week 2)
- Hospital-preferred antibiotics (what pharmacy actually stocks)  
- Load into pilot config manually  

### 5. Invoice / MOU for ₹25,000–35,000
- **Who:** Pharmacy dept or research fund  
- **What:** Signed pilot MOU + payment = XPRIZE revenue proof  

---

## 📧 Who to email at JIPMER (find on jipmer.edu.in)

| Role | Search on website |
|------|-------------------|
| Microbiology HOD | “Department of Microbiology JIPMER” |
| Pharmacology / Pharmacy | “Hospital pharmacy JIPMER” |
| Medicine / ID | “Infectious diseases JIPMER” |
| Research / Dean | “Research JIPMER ethics” |

**Subject:** Research pilot — AI antibiotic stewardship tool (pharmacist-led, physician sign-off)

---

## 🎬 5-min JIPMER demo script (updated)

1. **Evidence page** — show ICMR/WHO GLASS antibiogram + case studies (WHO 1.27M deaths, India FQ resistance)  
2. **Clinician Console** — UTI, E. coli, age 65, Cr 1.4  
3. **Privacy Shield** — PHI blocked  
4. **Recommendation** — nitrofurantoin (Access tier) — cite RAG IDSA UTI guideline  
5. **Resistance chart** — real ICMR reference numbers (FQ 72% resistance for E. coli UTI)  
6. **Physician order + attestation**  
7. **Say:** “Week 1 we load **your** WHONET antibiogram — this reference data is replaced.”  

---

## 📚 Real-world sources already in the product

| Source | Used for |
|--------|----------|
| WHO GLASS Report 2023 | India resistance context |
| ICMR AMRSN | Indian hospital patterns |
| IDSA UTI / CAP / SSTI guidelines | RAG corpus |
| CDC Core Elements ASP | Case study — hospital pilot model |
| Surviving Sepsis Campaign | Sepsis empiric therapy RAG |

**Not included (you add in pilot):** JIPMER-specific isolate counts, patient outcomes, EMR integration.

---

## ❌ Do not claim until you have proof

- “JIPMER validated” — until JIPMER signs pilot  
- “FDA/CDSCO approved” — never for prototype  
- “100% accurate” — say “decision support + physician review”  
- “Replaces stewardship pharmacist” — say “augments under physician oversight”  

---

## Your priority this week

1. Email Microbiology HOD JIPMER — ask for antibiogram meeting  
2. Practice demo with **Evidence page** first  
3. Close **1 paid pilot** (college HOD is faster backup if JIPMER slow)  
4. Deploy latest code: `cd amrshield-agent && bash infrastructure/deploy.sh`  

---

**Contact for pilot:** Prakash Raj K, M.Pharm · Demo: https://amrshield-105254876763.us-central1.run.app
