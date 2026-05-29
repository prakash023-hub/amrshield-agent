# AMRShield — Safety & Ethics Disclaimer

## ⚠️ Clinical Use Disclaimer

**AMRShield is a RESEARCH PROTOTYPE** developed for the Google Cloud Rapid Agent Hackathon (2026). It is:

- **NOT approved** for clinical decision-making without licensed physician oversight
- **NOT validated** against clinical outcomes in real patient populations  
- **NOT a replacement** for hospital pharmacists, infectious disease specialists, or clinical judgment
- **NOT HIPAA-certified** in this hackathon version

Any clinical use would require: IRB approval, clinical validation studies, regulatory clearance (CDSCO/FDA/CE), and formal clinical governance processes.

---

## 🔒 Data Privacy

All patient data used in this project is **entirely synthetic**:
- No real patient health information (PHI) was used
- Synthetic cases were generated computationally
- No MIMIC, EHR, or hospital data was accessed
- All antibiogram data is synthetic and labeled as such

---

## 🤖 AI Safety Measures

1. **Human-in-the-loop**: Every recommendation flagged HIGH/CRITICAL by the Self-Audit Agent is HELD until a physician reviews it
2. **Explainability**: All recommendations include source citations and reasoning traces (via Phoenix)
3. **Confidence calibration**: The system never presents recommendations with false certainty
4. **Audit trail**: Every agent decision is logged and traceable via Arize Phoenix
5. **Hallucination detection**: The Self-Audit Agent actively checks for unsupported claims

---

## 📋 Intended Use (Research Context Only)

AMRShield demonstrates how AI agents can:
- Support antibiotic stewardship education
- Simulate clinical decision workflows for training
- Showcase multi-agent safety architectures
- Illustrate responsible AI observability with Arize Phoenix

---

## 📞 Contact

For questions about this research prototype:  
Prakash Raj K, M.Pharm | Associate Professor, Dept. of Pharmaceutics  
Sri Balaji Vidyapeeth, Puducherry, India
