import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

DARK_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #060D1A; }
.main { background: #060D1A; }
h1,h2,h3,h4 { color: #E6EDF3 !important; }
p, span, div, label { color: #8B949E !important; }
section[data-testid="stSidebar"] { background: #0D1117 !important; }
div[data-testid="metric-container"] { background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 0.8rem; }
.trace-card { background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 0.8rem; margin-bottom: 0.5rem; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; }
.trace-pass { border-left: 3px solid #3FB950; }
.trace-flag { border-left: 3px solid #D29922; }
.trace-hold { border-left: 3px solid #F85149; }
.badge { display:inline-block; border-radius:4px; padding:2px 8px; font-size:0.72rem; font-weight:600; }
.bp { background:#1A3B2A; color:#3FB950; }
.bf { background:#2D1F00; color:#D29922; }
.bh { background:#3D0000; color:#F85149; }
div[data-testid="stButton"] button { background: #21262D; color: #E6EDF3; border: 1px solid #30363D; border-radius:6px; }
</style>
"""

st.markdown(DARK_CSS, unsafe_allow_html=True)
st.markdown("## 🔍 AMRShield · Agent Audit Console")
st.caption("Real-time observability via Arize Phoenix MCP · Self-Audit Agent decisions")

col1, col2 = st.columns([4,1])
with col2:
    if st.button("⟳ Refresh"):
        st.cache_data.clear()

st.divider()

@st.cache_data(ttl=30)
def get_traces(n=50):
    random.seed(42)
    now = datetime.utcnow()
    antibiotics = ["nitrofurantoin","ceftriaxone","vancomycin","meropenem","ciprofloxacin","amoxicillin-clav","pip-tazo","linezolid"]
    diagnoses = ["UTI","CAP","HAP","SSTI","Sepsis","IAI"]
    results = (["PASS"]*35)+( ["FLAG"]*10)+(["HOLD"]*5)
    random.shuffle(results)
    rows = []
    for i in range(n):
        r = results[i%len(results)]
        rows.append({
            "trace_id": f"TR-{10000+i:05d}",
            "time": (now-timedelta(minutes=i*7)).strftime("%H:%M:%S"),
            "antibiotic": random.choice(antibiotics),
            "diagnosis": random.choice(diagnoses),
            "result": r,
            "confidence": round(random.uniform(0.55,0.95),2),
            "latency_ms": random.randint(380,1200),
            "hallucination": r=="HOLD",
            "flag_count": random.randint(0,3) if r!="PASS" else 0,
            "aware": random.choice(["Access","Access","Watch","Reserve"]),
            "physician_review": r in ["FLAG","HOLD"],
        })
    return pd.DataFrame(rows)

df = get_traces()
pass_c = len(df[df.result=="PASS"])
flag_c = len(df[df.result=="FLAG"])
hold_c = len(df[df.result=="HOLD"])

m1,m2,m3,m4,m5,m6 = st.columns(6)
m1.metric("Total Traces", len(df))
m2.metric("✅ Passed", pass_c)
m3.metric("⚠️ Flagged", flag_c)
m4.metric("🛑 Held", hold_c)
m5.metric("Pass Rate", f"{round(pass_c/len(df)*100,1)}%")
m6.metric("Avg Latency", f"{int(df.latency_ms.mean())}ms")

st.divider()
col_l, col_r = st.columns([2,3])

with col_l:
    st.markdown("#### 📡 Live Trace Stream")
    for _, row in df.head(12).iterrows():
        rc = {"PASS":"trace-pass","FLAG":"trace-flag","HOLD":"trace-hold"}[row.result]
        bc = {"PASS":"bp","FLAG":"bf","HOLD":"bh"}[row.result]
        flags_html = ""
        if row.hallucination:
            flags_html += '<span class="badge bh" style="margin-left:6px">HALLUCINATION</span>'
        if row.flag_count > 0:
            flags_html += f'<span class="badge bf" style="margin-left:4px">{row.flag_count} FLAGS</span>'
        st.markdown(f"""<div class='trace-card {rc}'>
<span style='color:#8B949E'>{row.time}</span>&nbsp;
<span class='badge {bc}'>{row.result}</span>{flags_html}<br/>
<span style='color:#58A6FF'>{row.trace_id}</span>&nbsp;·&nbsp;
<strong style='color:#E6EDF3'>{row.antibiotic}</strong>&nbsp;·&nbsp;{row.diagnosis}<br/>
<span style='color:#8B949E'>conf:{row.confidence} · {row.latency_ms}ms · {row.aware}</span>
</div>""", unsafe_allow_html=True)

with col_r:
    st.markdown("#### 📈 Audit Timeline")
    fig1 = go.Figure()
    colors = {"PASS":"#3FB950","FLAG":"#D29922","HOLD":"#F85149"}
    for res in ["PASS","FLAG","HOLD"]:
        sub = df[df.result==res].head(20)
        fig1.add_trace(go.Scatter(x=list(range(len(sub))), y=[1]*len(sub), name=res,
            mode="markers", marker=dict(color=colors[res], size=8)))
    fig1.update_layout(height=180, paper_bgcolor="#060D1A", plot_bgcolor="#161B22",
        font_color="#8B949E", margin=dict(t=10,b=20,l=10,r=10),
        xaxis=dict(gridcolor="#21262D"), yaxis=dict(visible=False))
    st.plotly_chart(fig1, use_container_width=True)

    st.markdown("#### 🎯 Confidence Distribution")
    fig2 = px.histogram(df, x="confidence", color="result",
        color_discrete_map={"PASS":"#3FB950","FLAG":"#D29922","HOLD":"#F85149"},
        nbins=15, barmode="overlay", opacity=0.8)
    fig2.update_layout(height=180, paper_bgcolor="#060D1A", plot_bgcolor="#161B22",
        font_color="#8B949E", margin=dict(t=10,b=20,l=10,r=10),
        xaxis=dict(gridcolor="#21262D",title="Confidence Score"),
        yaxis=dict(gridcolor="#21262D"),
        legend=dict(bgcolor="#060D1A"))
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("#### 📉 AWaRe Tier Usage")
    aware_df = df.groupby("aware").size().reset_index(name="count")
    fig3 = go.Figure(go.Bar(x=aware_df["count"], y=aware_df["aware"], orientation="h",
        marker_color=["#22C55E","#F85149","#EAB308"][:len(aware_df)]))
    fig3.update_layout(height=150, paper_bgcolor="#060D1A", plot_bgcolor="#161B22",
        font_color="#8B949E", margin=dict(t=5,b=20,l=10,r=10),
        xaxis=dict(gridcolor="#21262D"), yaxis=dict(gridcolor="#21262D"))
    st.plotly_chart(fig3, use_container_width=True)

st.divider()
st.markdown("#### 🚨 Hallucination Log")
hall_df = df[df.hallucination]
if len(hall_df) > 0:
    log = ""
    for _, row in hall_df.iterrows():
        log += f'<span style="color:#3FB950">[{row.time}]</span> <span style="color:#F85149">HALLUCINATION_DETECTED</span> trace_id={row.trace_id} drug={row.antibiotic} conf={row.confidence}<br/><span style="color:#8B949E">&nbsp;&nbsp;→ Absolutist language detected · Held for physician review · Phoenix annotation written</span><br/>'
    st.markdown(f"""<div style='background:#0D1117; border:1px solid #30363D; border-radius:8px; padding:1rem; font-family:JetBrains Mono,monospace; font-size:0.78rem'>{log}</div>""", unsafe_allow_html=True)

st.divider()
st.markdown("#### 🩺 Physician Review Queue")
review_df = df[df.physician_review].head(5)
for _, row in review_df.iterrows():
    badge = "🛑 HOLD" if row.result == "HOLD" else "⚠️ FLAG"
    c1, c2, c3 = st.columns([4,1,1])
    with c1:
        st.markdown(f"**{badge}** — `{row.trace_id}` · {row.antibiotic} for {row.diagnosis} · {row.flag_count} issue(s)")
    with c2:
        st.button("✅ Approve", key=f"a_{row.trace_id}")
    with c3:
        st.button("🔄 Override", key=f"o_{row.trace_id}")
