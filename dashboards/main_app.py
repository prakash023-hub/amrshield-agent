"""
AMRShield - Unified Main App
All 4 dashboards in one Streamlit app with sidebar navigation.
Run: streamlit run dashboards/main_app.py
"""

import streamlit as st

st.set_page_config(
    page_title="AMRShield — AI Antibiotic Stewardship",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    
    [data-testid="stSidebarContent"] {
        background: linear-gradient(180deg, #0F172A 0%, #1E293B 100%);
    }
    
    .nav-header {
        color: white;
        font-size: 1.3rem;
        font-weight: 700;
        padding: 1rem 0 0.5rem 0;
    }
    
    .nav-sub {
        color: #94A3B8;
        font-size: 0.75rem;
        padding-bottom: 1rem;
    }
    
    .status-badge {
        background: #064E3B;
        color: #6EE7B7;
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Sidebar Navigation
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div class='nav-header'>🛡️ AMRShield</div>
    <div class='nav-sub'>AI Antibiotic Stewardship<br>Powered by Gemini 3 + Arize Phoenix</div>
    <span class='status-badge'>🟢 Agent Online</span>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    page = st.radio(
        "Navigate",
        options=[
            "🏠 Home",
            "🩺 Clinician Console",
            "🔍 Audit Console",
            "🏥 Stewardship Admin",
            "🌍 Surveillance Map",
        ],
        label_visibility="collapsed",
    )
    
    st.divider()
    st.caption("Google Cloud Rapid Agent Hackathon 2026")
    st.caption("Arize Track · MIT License")
    st.caption("[GitHub](https://github.com/prakash023-hub/amrshield-agent)")

# ─────────────────────────────────────────────
# Page Router
# ─────────────────────────────────────────────

if page == "🏠 Home":
    st.markdown("## 🛡️ AMRShield — AI-Powered Antibiotic Stewardship")
    st.markdown("##### Built with Gemini 3 · Google Cloud Agent Builder · Arize Phoenix MCP")
    
    st.warning("⚕️ Research Prototype — Not approved for clinical use without physician oversight.")
    
    st.divider()
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Recommendations", "1,247", "+89")
    c2.metric("Access Tier Usage", "64.8%", "+6.2%")
    c3.metric("Audit Pass Rate", "94.2%", "−0.8%")
    c4.metric("Cost Savings", "₹12.4L", "+₹2.1L")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🤖 Three Specialized Agents")
        st.markdown("""
        **1. Clinical Recommendation Agent**
        Analyzes patient cases → recommends antibiotic with dose, duration, AWaRe tier, rationale.
        
        **2. AMR Prediction Agent**  
        Forecasts resistance trends using WHO GLASS data + Gemini 3 6-month projection.
        
        **3. Self-Audit Agent ⭐**  
        Reviews every recommendation via Arize Phoenix MCP — detects hallucinations, allergy conflicts, renal dosing errors before clinician sees it.
        """)
    
    with col2:
        st.markdown("### 🖥️ Four Dashboards")
        st.markdown("""
        **🩺 Clinician Console**  
        Point-of-care recommendation UI for bedside physicians.
        
        **🔍 Audit Console**  
        Real-time Phoenix trace stream, hallucination log, physician review queue.
        
        **🏥 Stewardship Admin**  
        Hospital-wide KPIs, department compliance, cost savings tracker.
        
        **🌍 Surveillance Map**  
        Geographic AMR resistance + Gemini 3 forecast overlays.
        """)
    
    st.divider()
    st.markdown("### 🏆 Hackathon Submission")
    st.markdown("""
    - **Track:** Arize (Google Cloud Rapid Agent Hackathon 2026)
    - **Tech Stack:** Gemini 3 · Google Cloud Agent Builder · Arize Phoenix MCP · Cloud Run · Streamlit
    - **GitHub:** https://github.com/prakash023-hub/amrshield-agent
    """)

elif page == "🩺 Clinician Console":
    # Import and run clinician dashboard inline
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    
    # Re-render clinician console content
    exec(open(os.path.join(os.path.dirname(__file__), "clinician_console/app.py")).read())

elif page == "🔍 Audit Console":
    exec(open(os.path.join(os.path.dirname(__file__), "audit_console/app.py")).read())

elif page == "🏥 Stewardship Admin":
    exec(open(os.path.join(os.path.dirname(__file__), "stewardship_admin/app.py")).read())

elif page == "🌍 Surveillance Map":
    exec(open(os.path.join(os.path.dirname(__file__), "surveillance_map/app.py")).read())
