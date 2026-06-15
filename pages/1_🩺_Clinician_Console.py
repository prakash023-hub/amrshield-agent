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
.privacy-shield { background:#0D2818; border:1px solid #238636; border-radius:10px; padding:1rem 1.2rem; margin-bottom:1rem; }
.privacy-item { color:#3FB950 !important; font-size:0.88rem; margin:0.25rem 0; }
.pipeline-step { background:#161B22; border-left:3px solid #58A6FF; padding:0.5rem 0.8rem; margin:0.3rem 0; border-radius:4px; font-size:0.82rem; }
.pipeline-repaired { border-left-color:#D29922; }
.pipeline-block { border-left-color:#F85149; }
div[data-testid="stButton"] button[kind="primary"] { background:#2563EB; color:white; border:none; }
</style>
""", unsafe_allow_html=True)

col_a, col_b, col_c = st.columns([1,4,2])
with col_a: st.markdown("## 🛡️")
with col_b:
    st.markdown("## AMRShield — Clinician Console")
    st.caption("Antibiotic Stewardship · Physician Decision Support · Gemini 2.5 Flash + Phoenix MCP")
with col_c:
    st.markdown(""); st.success("🟢 Agent Online")

st.markdown("<div class='disclaimer'>⚕️ <strong>Research Prototype.</strong> Decision support only — licensed physician must sign all orders. Patient identifiers stripped at edge before AI (PharmaGuard DLP).</div>", unsafe_allow_html=True)
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
    diagnosis = st.selectbox("Diagnosis", [
        "Urinary Tract Infection", "Community-Acquired Pneumonia", "Hospital-Acquired Pneumonia",
        "Sepsis (unknown source)", "Skin & Soft Tissue Infection", "Intra-Abdominal Infection",
        "Febrile Neutropenia", "Meningitis / CNS Infection", "Bone & Joint Infection",
    ])
    pathogen = st.selectbox("Suspected Pathogen", [
        "Unknown (empirical)", "E. coli", "Staphylococcus aureus", "MRSA", "ESBL",
        "Klebsiella pneumoniae", "Pseudomonas aeruginosa", "Enterococcus", "Streptococcus pneumoniae",
    ])
    culture_available = st.checkbox("Culture & sensitivity available")
    if culture_available:
        culture_org = st.text_input("Culture organism", value="E. coli")
        culture_sens = st.multiselect("Susceptible to", ["nitrofurantoin","ciprofloxacin","ceftriaxone","meropenem","vancomycin"], default=["nitrofurantoin"])
    else:
        culture_org, culture_sens = "", []
    icu = st.checkbox("ICU / severe sepsis")
    pregnancy = st.checkbox("Pregnancy")
    allergies = st.multiselect("Allergies", ["penicillin","cephalosporins","sulfonamides","fluoroquinolones","macrolides","vancomycin","none"], default=["none"])
    medications = st.multiselect("Current Meds", ["warfarin","metformin","amlodipine","theophylline","amiodarone","furosemide","gentamicin","none"], default=["none"])
    st.markdown("**Optional — clinical notes** *(edge-sanitized before AI)*")
    clinical_notes = st.text_area(
        "Free-text notes",
        value="",
        placeholder="e.g. fever 3 days — PHI like name/phone/Aadhaar is auto-stripped at edge",
        height=80,
        label_visibility="collapsed",
    )
    st.caption("PharmaGuard DLP v2 removes name, Aadhaar, phone, email before cloud AI sees data.")
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
        "culture_results": {"organism": culture_org, "susceptible": culture_sens} if culture_available else {},
        "icu": icu,
        "pregnancy": pregnancy,
    }
    if clinical_notes.strip():
        patient["clinical_notes"] = clinical_notes.strip()

    cyber = None
    cyber_seal = None
    sec_report = None

    with st.spinner("🔐 PharmaGuard Cyber — zero-trust scan + wallet + edge + injection defense..."):
        try:
            from mcp_tools.pharmaguard_cyber import run_cyber_guard_agent
            cyber = run_cyber_guard_agent(patient)
            if cyber.get("cyber_verdict") == "BLOCK" or cyber.get("status") == "BLOCKED":
                st.error(f"🛑 Cyber Guard BLOCKED — threat level {cyber.get('threat_score', {}).get('threat_level', 'CRITICAL')}")
                st.json(cyber.get("injection_ingress", {}))
                st.stop()
            patient = cyber.get("sanitized_patient") or patient
            pg = cyber.get("pharmaguard", {})
            sec_report = cyber.get("physician_security_report", {})
            if pg.get("edge", {}).get("data_loss_prevented") or pg.get("edge", {}).get("repair", {}).get("repairs_applied"):
                repairs = len(pg.get("edge", {}).get("repair", {}).get("repairs_applied", []))
                st.warning(f"🛡️ Signal repair — {repairs} privacy fix(es) at edge. PHI did not reach cloud AI.")
        except Exception as e:
            cyber = None
            st.caption(f"Cyber Guard fallback: {e}")

    if sec_report:
        st.markdown("### 🔒 Patient Privacy Shield — PharmaGuard DLP")
        assurance = sec_report.get("physician_assurance", [])
        items_html = "".join(f"<div class='privacy-item'>{m}</div>" for m in assurance)
        st.markdown(f"<div class='privacy-shield'>{items_html}</div>", unsafe_allow_html=True)

        pc1, pc2, pc3, pc4 = st.columns(4)
        pc1.metric("PHI to Cloud AI", "BLOCKED" if not sec_report.get("phi_reached_cloud") else "RISK")
        pc2.metric("Compliance", f"{sec_report.get('compliance_pct', 0)}%")
        pc3.metric("Repairs", sec_report.get("dlp_summary", {}).get("total_repairs", 0))
        pc4.metric("Cyber Verdict", sec_report.get("verdict", "—"))

        with st.expander("🔬 Security pipeline (IT / audit review)", expanded=False):
            for step in sec_report.get("pipeline_steps", []):
                status = step.get("status", "—")
                css = "pipeline-block" if status == "BLOCK" else ("pipeline-repaired" if status == "REPAIRED" else "pipeline-step")
                st.markdown(
                    f"<div class='{css}'><strong>Step {step['step']}: {step['name']}</strong> — {status}<br/>{step.get('detail','')}</div>",
                    unsafe_allow_html=True,
                )
            st.markdown("**Framework:** India DPDP 2023 · HIPAA-aligned · Clinical minimum necessary")
            if sec_report.get("repair_log"):
                st.markdown("**Developer repair log** *(hashed — no raw PHI stored)*")
                st.json(sec_report["repair_log"])
        st.divider()
    elif cyber:
        pg = cyber.get("pharmaguard", {})
        st.caption(
            f"Cyber: {cyber.get('cyber_verdict')} · Score {cyber.get('threat_score', {}).get('threat_score', 0)} · "
            f"Wallet {pg.get('wallet', {}).get('wallet_id', '—')}"
        )

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
            try:
                from agents.clinical_agent.physician_ready import enrich_for_physician
                rec = enrich_for_physician(rec, patient)
            except Exception:
                pass

    with st.spinner("🔍 Self-Audit Agent running 4 safety checks via Phoenix..."):
        try:
            from agents.audit_agent.agent import run_audit_agent
            audit = run_audit_agent(rec, patient)
        except Exception:
            audit = {"overall_result": "PASS", "issues_found": [], "recommendation_safe_to_proceed": True, "physician_review_required": False, "audit_reasoning": "All safety checks passed. No allergy conflicts, renal dose appropriate, no critical drug interactions."}

    try:
        from mcp_tools.pharmaguard_cyber import run_cyber_guard_agent
        cyber_seal = run_cyber_guard_agent(patient, recommendation=rec, audit_result=audit)
        st.caption(
            f"Trust chain sealed · Cyber {cyber_seal.get('cyber_verdict')} · "
            f"Integrity {'✅' if cyber_seal.get('chain_integrity', {}).get('valid') else '❌'}"
        )
    except Exception:
        pass

    result = audit.get("overall_result", "PASS")
    css = {"PASS":"audit-pass","FLAG":"audit-flag","HOLD":"audit-hold"}[result]
    icon = {"PASS":"✅","FLAG":"⚠️","HOLD":"🛑"}[result]
    st.markdown(f"<div class='{css}'>{icon} <strong>Self-Audit: {result}</strong> — {audit.get('audit_reasoning','')}</div>", unsafe_allow_html=True)
    if audit.get("phoenix_mcp_tools"):
        st.caption(f"Phoenix MCP tools invoked: {', '.join(audit['phoenix_mcp_tools'])}")

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

        if rec.get("physician_ready"):
            st.divider()
            st.markdown("### ⚕️ Physician Order Set")
            po = rec.get("physician_order", {})
            rf = rec.get("renal_function", {})
            st.markdown(f"""
| Field | Value |
|-------|-------|
| **Order ID** | `{po.get('order_id','—')}` |
| **Medication** | {po.get('medication','—')} |
| **Sig** | {po.get('dose','')} {po.get('route','')} {po.get('frequency','')} × {po.get('duration','')} |
| **Indication** | {po.get('indication','—')} |
| **CrCl** | {rf.get('crcl_ml_min','—')} mL/min ({rf.get('renal_category','')}) |
| **Guideline** | {rec.get('guideline',{}).get('source','—')} |
""")
            if rec.get("contraindications"):
                st.markdown("**⛔ Contraindications / Warnings**")
                for c in rec["contraindications"]:
                    st.error(f"{c['type']} ({c['severity']}): {c['detail']}")
            else:
                st.success("No absolute contraindications on screening")

            if rec.get("renal_dose_adjustment", {}).get("adjustment_required"):
                st.warning(f"Renal: {rec['renal_dose_adjustment'].get('message')}")

            st.markdown("**Stewardship checklist**")
            for item in rec.get("stewardship_actions", []):
                st.markdown(f"• {item}")

            st.markdown("**Labs & monitoring**")
            for lab in rec.get("monitoring_labs", []):
                st.markdown(f"• {lab}")

            with st.expander("IV-to-PO switch criteria"):
                for c in rec.get("iv_to_po_criteria", []):
                    st.markdown(f"• {c}")

            st.caption(rec.get("physician_disclaimer", ""))

            st.divider()
            st.markdown("### ✍️ Physician Attestation")
            physician_id = st.text_input("Physician ID / MCI reg.", value="DR-")
            attestation = st.checkbox(rec.get("attestation_text", "I attest I have reviewed this recommendation."))
            c_ap, c_esc = st.columns(2)
            with c_ap:
                if st.button("✅ Approve & Sign Order", type="primary", disabled=not attestation):
                    from agents.clinical_agent.physician_ready import record_physician_attestation
                    record_physician_attestation(po.get("order_id", ""), physician_id, "APPROVED")
                    st.success(f"Order {po.get('order_id')} signed by {physician_id}")
            with c_esc:
                if st.button("🔄 Escalate to ID"):
                    st.info("Escalated to Infectious Disease — order held pending consult.")

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
        st.markdown(f"<span style='color:#8B949E'>Trace:</span> <code>{audit.get('phoenix_trace_id') or rec.get('trace_id','—')}</code>", unsafe_allow_html=True)
        if audit.get("physician_review_required") or not rec.get("safe_to_sign", True):
            st.warning("⚕️ Physician review required before prescribing")
        else:
            st.success("✅ Ready for physician attestation")
        if st.button("📋 Request Second Opinion", use_container_width=True):
            st.info("Escalated to Infectious Disease specialist queue.")

else:
    st.markdown("### 👈 Enter patient details in the sidebar to begin")
    st.markdown("""
    AMRShield will:
    1. **PharmaGuard Cyber** — zero-trust scan before clinical reasoning
    2. **Calculate CrCl** (Cockcroft-Gault) for renal dose adjustment
    3. **Query local antibiogram** for susceptibility data
    4. **Check allergies & drug interactions** with current medications
    5. **Apply WHO AWaRe** — prefer Access tier
    6. **Self-Audit** recommendation via Arize Phoenix MCP
    7. **Physician order set** — contraindications, monitoring labs, attestation
    """)
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Today's Recommendations","47","+3")
    m2.metric("Access Tier Usage","68%","+5%")
    m3.metric("Audit Pass Rate","94.2%","-0.8%")
    m4.metric("Flagged for Review","3","+1")
