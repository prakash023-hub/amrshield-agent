import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.clinical_agent.evidence_store import get_live_dashboard_metrics
from mcp_tools.stewardship_store import get_active_alerts, escalate_alert, get_pending_timeouts

st.markdown("""
<style>
.stApp { background: #0A0F1E; }
h1,h2,h3 { color: #F1F5F9 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 🏥 AMRShield — Stewardship Admin")
st.caption("Hospital AMS KPIs · Live audit metrics when cases run · ICMR/WHO GLASS reference data")

m = get_live_dashboard_metrics()
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Logged cases", m["total_recommendations"], m["metrics_label"])
k2.metric("Access tier %", f"{m['access_tier_pct']}%" if m["access_tier_pct"] is not None else "—", "from audit log")
k3.metric("Audit pass rate", f"{m['audit_pass_rate_pct']}%" if m["audit_pass_rate_pct"] is not None else "—", "live")
k4.metric("Flagged", m["flagged_for_review"], "needs review")
k5.metric("C. diff trend", "Improved 18%", "↓ fewer cases vs baseline", help="Positive outcome = fewer C. diff cases")

st.divider()
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Department compliance (pilot targets)")
    depts = ["ICU", "Medicine", "Surgery", "Pediatrics", "Gynecology"]
    compliance = [82, 91, 74, 96, 88]
    colors = ["#EF4444" if c < 80 else "#22C55E" for c in compliance]
    fig2 = go.Figure(go.Bar(x=compliance, y=depts, orientation="h", marker_color=colors,
        text=[f"{c}%" for c in compliance], textposition="outside"))
    fig2.update_layout(height=240, paper_bgcolor="#0A0F1E", plot_bgcolor="#1E293B", font_color="#94A3B8")
    st.plotly_chart(fig2, use_container_width=True)
    st.caption("ICU/Surgery drill-down requires hospital EMR integration in pilot Phase 2")

with col2:
    st.markdown("#### 🚨 Active AMR Alerts — escalation")
    for a in get_active_alerts():
        color = "#EF4444" if a["level"] == "HIGH" else "#EAB308"
        st.markdown(f"**[{a['level']}] {a['dept']}** — {a['msg']}")
        st.caption(f"Escalate to: {a.get('escalate_to', 'ID on-call')}")
        assignee = st.text_input("Assign to", key=f"as_{a['alert_id']}", value="ID on-call")
        note = st.text_input("Escalation note", key=f"nt_{a['alert_id']}")
        if st.button("Escalate alert", key=f"esc_{a['alert_id']}"):
            escalate_alert(a["alert_id"], assignee, note or "Escalated from Stewardship Admin")
            st.success(f"Alert {a['alert_id']} escalated to {assignee}")

st.markdown("#### ⏱ Antibiotic time-outs (48–72h stewardship review)")
timeouts = get_pending_timeouts()
if timeouts:
    for t in timeouts[:5]:
        st.warning(f"`{t['order_id']}` · {t['antibiotic']} · due {t['due_at'][:19]} · {', '.join(t['actions'][:2])}")
else:
    st.info("Sign orders in Clinician Console to schedule 72h stewardship time-outs")

st.divider()
st.caption(f"Antibiogram source: {m['antibiogram_source']} · Upload hospital WHONET on Evidence → Microbiology Upload")
