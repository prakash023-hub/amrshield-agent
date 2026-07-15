import streamlit as st

st.set_page_config(
    page_title="AMRShield — AI Antibiotic Stewardship",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from mcp_tools.phoenix_integration import ensure_phoenix_tracing

ensure_phoenix_tracing()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); }
.main { background: transparent; }
h1,h2,h3,h4 { color: #F1F5F9 !important; }
p, span, div, label, caption { color: #CBD5E1 !important; }
section[data-testid="stSidebar"] { background: #0F172A !important; border-right: 1px solid #1E3A5F; }
div[data-testid="metric-container"] { background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 1rem; }
.stButton button { background: #2563EB; color: white; border: none; border-radius: 8px; }
.stAlert { border-radius: 8px; }
hr { border-color: #334155; }
</style>
""", unsafe_allow_html=True)

st.markdown("# 🛡️ AMRShield")
st.markdown("### AI-Powered Antibiotic Stewardship with Self-Auditing Agent")
st.markdown("**Gemini 2.5 Flash · Phoenix MCP · PharmaGuard Cyber (Zero-Trust)**")

st.warning("⚕️ Research Prototype — Not CDSCO/FDA cleared. Decision support only; physician must sign all orders.")

from agents.clinical_agent.evidence_store import get_live_dashboard_metrics

metrics = get_live_dashboard_metrics()

st.divider()

c1, c2, c3, c4 = st.columns(4)
if metrics["is_live_data"]:
    c1.metric("Recommendations (audit log)", metrics["total_recommendations"], f"+{metrics['today_recommendations']} today")
    c2.metric("Access Tier %", f"{metrics['access_tier_pct']}%", metrics["metrics_label"])
    c3.metric("Audit Pass Rate", f"{metrics['audit_pass_rate_pct']}%", metrics["metrics_label"])
    c4.metric("Flagged for Review", metrics["flagged_for_review"], metrics["metrics_label"])
else:
    c1.metric("Recommendations", "0", "Run Clinician Console")
    c2.metric("Antibiogram", "ICMR/GLASS ref", metrics["antibiogram_dataset_id"])
    c3.metric("RAG Corpus", "Guidelines + cases", "LangChain BM25")
    c4.metric("Audit Pass Rate", "—", "No cases logged yet")

st.divider()

col1, col2 = st.columns(2)
with col1:
    st.markdown("### 🤖 Three Specialized Agents")
    st.markdown("""
**1. 🩺 Clinical Recommendation Agent**  
Analyzes patient profile → recommends antibiotic with dose, duration, AWaRe tier, clinical rationale. Uses CrCl calculation, local antibiogram, drug interaction checking.

**2. 📈 AMR Prediction Agent**  
Forecasts resistance trends using WHO GLASS data. Gemini 2.5 Flash generates 6-month resistance projections per pathogen/region.

**3. 🔍 Self-Audit Agent ⭐ (The Differentiator)**  
Reviews EVERY recommendation via Arize Phoenix MCP before the clinician sees it. Detects hallucinations, allergy conflicts, renal dosing errors, guideline deviations. HOLDS dangerous recommendations automatically.

**4. 🔐 PharmaGuard Cyber (Ignite Track)**  
Healthcare zero-trust: consent wallets, edge sanitization, evil-tracker + prompt-injection defense, signal repair, immutable trust chain. Cyber Guard Agent protects every clinical AI call.
    """)

with col2:
    st.markdown("### 🖥️ Six Dashboards — Use Sidebar to Navigate")
    st.markdown("""
**🩺 Clinician Console**  
Point-of-care UI — enter patient → get recommendation → see audit verdict → approve or escalate.

**🔍 Audit Console**  
Real-time Phoenix trace stream, hallucination detection log, confidence calibration chart, physician review queue.

**🏥 Stewardship Admin**  
Hospital-wide KPIs — AWaRe tier trends, department compliance, cost savings, AMR outbreak alerts.

**🌍 Surveillance Map**  
Global geographic AMR resistance patterns with Gemini 2.5 Flash 6-month forecast overlays and WHO GLASS integration.

**🔐 PharmaGuard Cyber SOC**  
Live threat log, trust chain viewer, prompt-injection scanner, compliance score — healthcare cybersecurity command center.

**📚 Evidence & Case Studies**  
ICMR/WHO GLASS reference antibiogram, LangChain RAG over IDSA/WHO guidelines, published case studies, JIPMER WHONET upload.
    """)

st.divider()

col3, col4 = st.columns(2)
with col3:
    st.markdown("### 🏆 Hackathon Submission")
    st.markdown("""
- **Competition:** Google Cloud Rapid Agent Hackathon 2026  
- **Track:** Arize (observability + self-auditing)  
- **Stack:** Gemini 2.5 Flash · Agent Builder · Phoenix MCP · Cloud Run · Streamlit  
- **GitHub:** [prakash023-hub/amrshield-agent](https://github.com/prakash023-hub/amrshield-agent)  
- **License:** MIT  
    """)

with col4:
    st.markdown("### 💊 Clinical Coverage")
    st.markdown("""
- **60+ antibiotics** in WHO AWaRe database  
- **5 clinical trap cases** in Phoenix evaluation dataset  
- **Cockcroft-Gault CrCl** calculator built-in  
- **Drug interaction checker** for 40+ combinations  
- **India ICMR/WHO GLASS reference antibiogram** (JIPMER WHONET upload in pilot)
- **LangChain RAG** — IDSA/WHO guidelines + published case studies
- **IDSA / WHO / ICMR** evidence citations with sources
    """)

st.divider()
st.caption("AMRShield v1.0 · Built by Prakash Raj K, M.Pharm · Sri Balaji Vidyapeeth, Puducherry")
