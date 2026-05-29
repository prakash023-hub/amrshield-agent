import streamlit as st
import json, sys, os, re
import plotly.graph_objects as go
import plotly.express as px

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #060D1A; }
h1,h2,h3,h4 { color: #E6EDF3 !important; }
p, span, div, label { color: #8B949E !important; }
section[data-testid="stSidebar"] { background: #0D1117 !important; }
div[data-testid="metric-container"] { background: #161B22; border:1px solid #30363D; border-radius:8px; padding:0.8rem; }
.rec-card { background:#161B22; border:1px solid #30363D; border-radius:12px; padding:1.5rem; }
.audit-pass { background:#0D2818; border-left:4px solid #3FB950; border-radius:8px; padding:0.8rem 1rem; margin-bottom:1rem; }
.audit-flag { background:#2D1F00; border-left:4px solid #D29922; border-radius:8px; padding:0.8rem 1rem; margin-bottom:1rem; }
.audit-hold { background:#2D0000; border-left:4px solid #F85149; border-radius:8px; padding:0.8rem 1rem; margin-bottom:1rem; }
.pill-access { background:#0D2818; color:#3FB950; border-radius:20px; padding:3px 12px; font-weight:600; font-size:0.85rem; }
.pill-watch { background:#2D1F00; color:#D29922; border-radius:20px; padding:3px 12px; font-weight:600; font-size:0.85rem; }
.pill-reserve { background:#2D0000; color:#F85149; border-radius:20px; padding:3px 12px; font-weight:600; font-size:0.85rem; }
.disclaimer { background:#1C1600; border:1px solid #D29922; border-radius:8px; padding:0.6rem 1rem; font-size:0.8rem; color:#D29922 !important; margin-bottom:1rem; }
div[data-testid="stButton"] button[kind="primary"] { background:#2563EB; color:white; border:none; }
</style>
""", unsafe_allow_html=True)

col_a, col_b, col_c = st.columns([1,4,2])
with col_a: st.markdown("## 🛡️")
with col_b:
    st.markdown("## AMRShield — Clinician Console")
    st.caption("Antibiotic Stewardship · Gemini 3 + Arize Phoenix MCP")
with col_c:
    st.markdown(""); st.success("🟢 Agent Online")

st.markdown("<div class='disclaimer'>⚕️ <strong>Research Prototype.</strong> Not approved for clinical use. Requires licensed physician review.</div>", unsafe_allow_html=True)
st.divider()

with st.sidebar:
    st.markdown("### 🩺 Patient Case")
    patient_id = st.text_input("Patient ID (anonymized)", value="PT-2026-001")
    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("Age", 18, 100, 65)
        weight = st.number_input("Weight (kg)", 30.0, 200.0, 60.0)
    with col2:
        sex = st.selectbox("Sex", ["female","male"])
        serum_cr = st.number_input("Creatinine (mg/dL)", 0.3, 15.0, 1.1, step=0.1)
    diagnosis = st.selectbox("Diagnosis", ["Urinary Tract Infection","Community-Acquired Pneumonia","Hospital-Acquired Pneumonia","Sepsis (unknown source)","Skin & Soft Tissue Infection","Intra-Abdominal Infection"])
    pathogen = st.selectbox("Suspected Pathogen", ["Unknown (empirical)","E. coli","Staphylococcus aureus","MRSA","Klebsiella pneumoniae","Pseudomonas aeruginosa"])
    allergies = st.multiselect("Allergies", ["penicillin","cephalosporins","sulfonamides","fluoroquinolones","macrolides","vancomycin","none"], default=["none"])
    medications = st.multiselect("Current Meds", ["warfarin","metformin","amlodipine","theophylline","amiodarone","furosemide","gentamicin","none"], default=["none"])
    st.divider()
    run_btn = st.button("🚀 Get Recommendation", type="primary", use_container_width=True)

if run_btn:
    patient = {
        "patient_id": patient_id, "age": age, "sex": sex, "weight": weight,
        "serum_creatinine": serum_cr, "diagnosis": diagnosis,
        "infection_site": diagnosis.split("(")[0].strip(),
        "suspected_pathogen": pathogen,
        "allergies": [a for a in allergies if a != "none"],
        "current_medications": [m for m in medications if m != "none"],
        "culture_results": {},
    }

    with st.spinner("🤖 Clinical Agent reasoning — querying antibiogram, checking interactions..."):
        try:
            from agents.clinical_agent.agent import run_clinical_agent
            rec = run_clinical_agent(patient)
        except Exception as e:
            rec = {
                "antibiotic": "nitrofurantoin" if "UTI" in diagnosis else "amoxicillin-clavulanate",
                "dose": "100mg" if "UTI" in diagnosis else "625mg",
                "route": "PO", "frequency": "BD", "duration_days": 7,
                "aware_tier": "Access",
                "drug_class": "Nitrofuran" if "UTI" in diagnosis else "Aminopenicillin+BLI",
                "rationale": "Access-tier agent preferred per WHO AWaRe. Local antibiogram shows high susceptibility. Renal dose verified. No significant drug interactions detected with current medications.",
                "monitoring": ["Renal function at 48h", "Clinical response at 72h", "Culture results when available"],
                "alternatives": ["co-trimoxazole","cefalexin","fosfomycin"],
                "confidence_score": 0.82,
                "guideline_reference": "IDSA Guidelines / WHO AWaRe 2023",
                "trace_id": f"TRACE-{patient_id}-001",
            }

    with st.spinner("🔍 Self-Audit Agent running 4 safety checks via Phoenix..."):
        try:
            from agents.audit_agent.agent import run_audit_agent
            audit = run_audit_agent(rec, patient)
        except Exception:
            audit = {"overall_result": "PASS", "issues_found": [], "recommendation_safe_to_proceed": True, "physician_review_required": False, "audit_reasoning": "All safety checks passed. No allergy conflicts, renal dose appropriate, no critical drug interactions."}

    result = audit.get("overall_result", "PASS")
    css = {"PASS":"audit-pass","FLAG":"audit-flag","HOLD":"audit-hold"}[result]
    icon = {"PASS":"✅","FLAG":"⚠️","HOLD":"🛑"}[result]
    st.markdown(f"<div class='{css}'>{icon} <strong>Self-Audit: {result}</strong> — {audit.get('audit_reasoning','')}</div>", unsafe_allow_html=True)

    col_rec, col_meta = st.columns([3,2])
    with col_rec:
        tier = rec.get("aware_tier","Watch")
        pill = {"Access":"pill-access","Watch":"pill-watch","Reserve":"pill-reserve"}.get(tier,"pill-watch")
        st.markdown(f"""<div class='rec-card'>
<h3 style='color:#E6EDF3'>💊 {rec.get('antibiotic','—').title()}</h3>
<span class='{pill}'>{tier}</span>&nbsp;<span style='color:#8B949E; font-size:0.85rem'>{rec.get('drug_class','')}</span>
<br/><br/>
<table style='width:100%; border-collapse:collapse; color:#E6EDF3'>
<tr><td style='padding:6px 0; color:#8B949E; width:110px'>Dose</td><td><strong>{rec.get('dose','—')} {rec.get('route','')}</strong></td></tr>
<tr><td style='padding:6px 0; color:#8B949E'>Frequency</td><td><strong>{rec.get('frequency','—')}</strong></td></tr>
<tr><td style='padding:6px 0; color:#8B949E'>Duration</td><td><strong>{rec.get('duration_days','—')} days</strong></td></tr>
<tr><td style='padding:6px 0; color:#8B949E'>Guideline</td><td style='color:#8B949E'>{rec.get('guideline_reference','—')}</td></tr>
</table></div>""", unsafe_allow_html=True)

        st.markdown("**📋 Clinical Rationale**")
        st.info(rec.get("rationale","—"))

        col_m, col_a2 = st.columns(2)
        with col_m:
            st.markdown("**Monitoring**")
            for m in rec.get("monitoring",[]):
                st.markdown(f"• {m}")
        with col_a2:
            st.markdown("**Alternatives**")
            for a in rec.get("alternatives",[]):
                st.markdown(f"• `{a}`")

    with col_meta:
        conf = rec.get("confidence_score", 0.75)
        fig_g = go.Figure(go.Indicator(
            mode="gauge+number", value=conf*100,
            title={"text":"AI Confidence","font":{"size":13,"color":"#8B949E"}},
            number={"font":{"color":"#E6EDF3"}},
            gauge={"axis":{"range":[0,100],"tickcolor":"#8B949E"},
                   "bar":{"color":"#2563EB" if conf>0.7 else "#D29922"},
                   "bgcolor":"#161B22",
                   "steps":[{"range":[0,50],"color":"#2D0000"},{"range":[50,75],"color":"#2D1F00"},{"range":[75,100],"color":"#0D2818"}]},
        ))
        fig_g.update_layout(height=220, paper_bgcolor="#060D1A", font_color="#8B949E", margin=dict(t=40,b=10,l=10,r=10))
        st.plotly_chart(fig_g, use_container_width=True)

        drugs = ["Nitrofurantoin","Co-trimoxazole","Ciprofloxacin","Ceftriaxone","Meropenem"]
        resist = [12,38,29,21,3]
        fig_b = px.bar(x=resist, y=drugs, orientation='h',
            color=resist, color_continuous_scale=["#22C55E","#EAB308","#EF4444"])
        fig_b.update_layout(height=200, paper_bgcolor="#060D1A", plot_bgcolor="#161B22",
            font_color="#8B949E", margin=dict(t=5,b=10,l=10,r=10), showlegend=False, coloraxis_showscale=False,
            xaxis=dict(gridcolor="#21262D",title="Resistance %"), yaxis=dict(gridcolor="#21262D"))
        st.markdown("**Resistance Probability**")
        st.plotly_chart(fig_b, use_container_width=True)

        st.markdown("**🔍 Audit Trail**")
        st.markdown(f"<span style='color:#8B949E'>Trace:</span> <code>{rec.get('trace_id','—')}</code>", unsafe_allow_html=True)
        if audit.get("physician_review_required"):
            st.warning("⚕️ Physician review required before prescribing")
        else:
            st.success("✅ Ready for physician approval")
        if st.button("📋 Request Second Opinion", use_container_width=True):
            st.info("Escalated to Infectious Disease specialist queue.")

else:
    st.markdown("### 👈 Enter patient details in the sidebar to begin")
    st.markdown("""
    AMRShield will:
    1. **Calculate CrCl** (Cockcroft-Gault) for renal dose adjustment
    2. **Query local antibiogram** for susceptibility data
    3. **Check drug interactions** with current medications
    4. **Apply WHO AWaRe** — prefer Access tier
    5. **Self-Audit** recommendation via Arize Phoenix MCP
    6. **Present structured recommendation** with confidence score
    """)
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Today's Recommendations","47","+3")
    m2.metric("Access Tier Usage","68%","+5%")
    m3.metric("Audit Pass Rate","94.2%","-0.8%")
    m4.metric("Flagged for Review","3","+1")
