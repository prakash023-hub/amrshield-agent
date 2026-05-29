import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #0A0F1E; }
h1,h2,h3,h4 { color: #F1F5F9 !important; }
p, span, div, label { color: #94A3B8 !important; }
section[data-testid="stSidebar"] { background: #0F172A !important; }
div[data-testid="metric-container"] { background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 1rem; }
.alert-card { border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 0.5rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 🏥 AMRShield — Stewardship Admin Dashboard")
st.caption("Hospital-wide antibiotic stewardship KPIs · 500-bed tertiary hospital · Real-time via Gemini 3")

col_d, _ = st.columns([2,3])
with col_d:
    period = st.selectbox("Period", ["Last 30 days","Last 7 days","Last 90 days"])

st.divider()
k1,k2,k3,k4,k5 = st.columns(5)
k1.metric("Total Recommendations", "1,247", "+89")
k2.metric("Access Tier %", "64.8%", "+6.2%")
k3.metric("Cost Savings", "₹12.4L", "+₹2.1L")
k4.metric("C. diff Reduction", "−18.3%", "−3.1%")
k5.metric("IV→PO Switches", "342", "+28")

st.divider()
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### AWaRe Tier Trends")
    dates = pd.date_range(end=datetime.now(), periods=30, freq="D")
    access = np.clip(58 + np.cumsum(np.random.randn(30)*0.5), 50, 75)
    watch = np.clip(35 - np.cumsum(np.random.randn(30)*0.3), 20, 45)
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=dates, y=access, name="Access ✅", fill="tozeroy",
        line=dict(color="#22C55E",width=2), fillcolor="rgba(34,197,94,0.15)"))
    fig1.add_trace(go.Scatter(x=dates, y=watch, name="Watch ⚠️", fill="tozeroy",
        line=dict(color="#EAB308",width=2), fillcolor="rgba(234,179,8,0.15)"))
    fig1.update_layout(height=240, paper_bgcolor="#0A0F1E", plot_bgcolor="#1E293B",
        font_color="#94A3B8", margin=dict(t=10,b=20,l=10,r=10),
        xaxis=dict(gridcolor="#334155"), yaxis=dict(gridcolor="#334155",title="% Usage"),
        legend=dict(bgcolor="#0A0F1E"))
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.markdown("#### Department Compliance")
    depts = ["ICU","Medicine","Surgery","Pediatrics","Gynecology","Oncology"]
    compliance = [82,91,74,96,88,78]
    colors = ["#EF4444" if c<80 else "#22C55E" for c in compliance]
    fig2 = go.Figure(go.Bar(x=compliance, y=depts, orientation="h",
        marker_color=colors, text=[f"{c}%" for c in compliance], textposition="outside"))
    fig2.update_layout(height=240, paper_bgcolor="#0A0F1E", plot_bgcolor="#1E293B",
        font_color="#94A3B8", margin=dict(t=10,b=20,l=10,r=10),
        xaxis=dict(range=[0,110],gridcolor="#334155"), yaxis=dict(gridcolor="#334155"))
    st.plotly_chart(fig2, use_container_width=True)

col3, col4 = st.columns(2)
with col3:
    st.markdown("#### Top Antibiotics Prescribed")
    drugs_df = pd.DataFrame({
        "Antibiotic": ["Ceftriaxone","Amox-Clav","Nitrofurantoin","Pip-Tazo","Vancomycin","Metronidazole","Ciprofloxacin","Meropenem"],
        "Count": [187,152,134,98,87,76,65,43],
        "AWaRe": ["Watch","Access","Access","Watch","Watch","Access","Watch","Watch"],
    })
    color_map = {"Access":"#22C55E","Watch":"#EAB308","Reserve":"#EF4444"}
    fig3 = px.bar(drugs_df, x="Count", y="Antibiotic", orientation="h",
        color="AWaRe", color_discrete_map=color_map)
    fig3.update_layout(height=260, paper_bgcolor="#0A0F1E", plot_bgcolor="#1E293B",
        font_color="#94A3B8", margin=dict(t=10,b=20,l=10,r=10),
        xaxis=dict(gridcolor="#334155"), yaxis=dict(gridcolor="#334155"),
        legend=dict(bgcolor="#0A0F1E"))
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.markdown("#### 🚨 Active AMR Alerts")
    alerts = [
        {"level":"HIGH","dept":"ICU","msg":"MRSA cluster — 3 cases in 7 days","time":"2h ago"},
        {"level":"HIGH","dept":"Surgery","msg":"ESBL E. coli rising — 34% this month","time":"6h ago"},
        {"level":"MEDIUM","dept":"Medicine","msg":"Fluoroquinolone use exceeded threshold","time":"1d ago"},
    ]
    for a in alerts:
        color = {"HIGH":"#EF4444","MEDIUM":"#EAB308","LOW":"#3B82F6"}[a["level"]]
        bg = {"HIGH":"#2D0000","MEDIUM":"#2D1F00","LOW":"#1C2B3A"}[a["level"]]
        st.markdown(f"""<div style='background:{bg}; border-left:3px solid {color}; border-radius:8px; padding:0.8rem; margin-bottom:8px'>
<strong style='color:{color}'>[{a["level"]}]</strong> <strong style='color:#F1F5F9'>{a["dept"]}</strong><br/>
<span style='color:#CBD5E1'>{a["msg"]}</span><br/>
<span style='color:#64748B; font-size:0.8rem'>{a["time"]}</span></div>""", unsafe_allow_html=True)

    st.markdown("#### 💰 Monthly Cost Savings")
    months = ["Jan","Feb","Mar","Apr","May"]
    savings = [8.2,9.1,10.4,11.8,12.4]
    fig4 = go.Figure(go.Bar(x=months, y=savings, marker_color="#22C55E",
        text=[f"₹{s}L" for s in savings], textposition="outside"))
    fig4.update_layout(height=160, paper_bgcolor="#0A0F1E", plot_bgcolor="#1E293B",
        font_color="#94A3B8", margin=dict(t=10,b=20,l=10,r=10),
        xaxis=dict(gridcolor="#334155"), yaxis=dict(gridcolor="#334155",title="Lakhs ₹"))
    st.plotly_chart(fig4, use_container_width=True)

st.divider()
st.caption("AMRShield Stewardship Admin · Google Cloud Agent Builder · Gemini 3 · Arize Phoenix MCP")
