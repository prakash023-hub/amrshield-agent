# XPRIZE Product Evidence Checklist

Screenshot these for Devpost upload. Store in folder `docs/xprize_evidence/`.

---

## Required screenshots

| # | What to capture | Why |
|---|-----------------|-----|
| 1 | Cloud Run console — amrshield service running | Production proof |
| 2 | Clinician Console — patient form filled | Real product |
| 3 | Recommendation result with drug + AWaRe tier | Agent output |
| 4 | Self-Audit HOLD/FLAG + **Phoenix MCP tools invoked** line | AI safety automation |
| 5 | Audit Console — LIVE MCP badge | Agent execution logs |
| 6 | GitHub repo with LICENSE + recent commits | Open development |
| 7 | Invoice + payment proof | Revenue |
| 8 | Customer testimonial email | Customer evidence |

---

## Agent execution narrative (paste in submission)

```
Every production case triggers this automated sequence:

1. User submits patient profile via Clinician Console (Streamlit on Cloud Run)
2. Clinical Agent (Gemini 2.5 Flash) enters tool-calling loop:
   - calculate_crcl
   - lookup_aware_tier
   - check_drug_interactions
   - query_local_antibiogram
3. Structured JSON recommendation returned with trace_id
4. Self-Audit Agent invokes Phoenix MCP pipeline:
   - detect_hallucination
   - evaluate_clinical_accuracy
   - fetch_phoenix_traces
   - flag_for_review (if critical)
5. Verdict PASS/FLAG/HOLD displayed + persisted to audit store
6. Audit Console reflects live trace without manual entry

No human writes code or rules per case — agents execute continuously.
```

---

## Optional: capture from terminal (local demo)

```bash
# Shows MCP pipeline working
cd ~/Downloads/amrshield-agent
python3 -c "
from mcp_tools.phoenix_integration import run_phoenix_mcp_audit_pipeline
rec = {'antibiotic':'amoxicillin','drug_class':'Penicillin','aware_tier':'Access','rationale':'test','confidence_score':0.9}
patient = {'age':68,'sex':'female','weight':58,'serum_creatinine':1.8,'allergies':['penicillin'],'diagnosis':'UTI'}
print(run_phoenix_mcp_audit_pipeline(rec, patient, 'DEMO-001')['phoenix_mcp_tools'])
"
```

Screenshot terminal output showing MCP tools list.

---

## Video additions for XPRIZE (vs hackathon video)

Add 30 seconds showing:
- "We charge ₹35,000 for 14-day pilots"
- Invoice or blurred bank credit
- Customer quote on screen
