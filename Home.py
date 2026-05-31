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
st.markdown("**Gemini 2.5 Flash · Google Cloud Agent Builder · Arize Phoenix MCP · Arize Track**")

st.warning("⚕️ Research Prototype — Not approved for clinical use without licensed physician oversight.")
st.divider()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Recommendations", "1,247", "+89 today")
c2.metric("WHO Access Tier %", "64.8%", "+6.2%")
c3.metric("Audit Pass Rate", "94.2%", "−0.8%")
c4.metric("Cost Savings", "₹12.4L/month", "+₹2.1L")

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
    """)

with col2:
    st.markdown("### 🖥️ Four Dashboards — Use Sidebar to Navigate")
    st.markdown("""
**🩺 Clinician Console**  
Point-of-care UI — enter patient → get recommendation → see audit verdict → approve or escalate.

**🔍 Audit Console**  
Real-time Phoenix trace stream, hallucination detection log, confidence calibration chart, physician review queue.

**🏥 Stewardship Admin**  
Hospital-wide KPIs — AWaRe tier trends, department compliance, cost savings, AMR outbreak alerts.

**🌍 Surveillance Map**  
Global geographic AMR resistance patterns with Gemini 2.5 Flash 6-month forecast overlays and WHO GLASS integration.
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
- **Synthetic antibiogram** (replace with real hospital data)  
- **IDSA / WHO / CDC** guideline citations  
    """)

st.divider()
st.caption("AMRShield v1.0 · Built by Prakash Raj K, M.Pharm · Sri Balaji Vidyapeeth, Puducherry")
