"""
AMRShield - Dashboard 4: Agent Audit Console
THE DIFFERENTIATOR — Real-time Phoenix traces, hallucination log, drift detection.
Dark mode, developer/ops aesthetic.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

st.set_page_config(
    page_title="AMRShield — Audit Console",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@300;400;600&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #0D1117; color: #E6EDF3; }
    .main { background: #0D1117; }
    
    .trace-card {
        background: #161B22;
        border: 1px solid #30363D;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.5rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
    }
    
    .trace-pass { border-left: 3px solid #3FB950; }
    .trace-flag { border-left: 3px solid #D29922; }
    .trace-hold { border-left: 3px solid #F85149; }
    
    .badge {
        display: inline-block;
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 0.75rem;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
    }
    .badge-pass { background: #1A3B2A; color: #3FB950; }
    .badge-flag { background: #2D1F00; color: #D29922; }
    .badge-hold { background: #3D0000; color: #F85149; }
    .badge-info { background: #1C2B3A; color: #58A6FF; }
    
    .stat-dark {
        background: #161B22;
        border: 1px solid #30363D;
        border-radius: 8px;
        padding: 1rem 1.5rem;
        text-align: center;
    }
    
    .terminal-header {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: #8B949E;
        background: #161B22;
        border: 1px solid #30363D;
        border-radius: 6px 6px 0 0;
        padding: 0.4rem 0.8rem;
    }
    
    .terminal-body {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        background: #0D1117;
        border: 1px solid #30363D;
        border-top: none;
        border-radius: 0 0 6px 6px;
        padding: 0.8rem;
        color: #E6EDF3;
        max-height: 300px;
        overflow-y: auto;
    }
    
    h1, h2, h3, h4 { color: #E6EDF3 !important; }
    p, span, div { color: #C9D1D9; }
    
    .stMetric { background: #161B22; border-radius: 8px; padding: 1rem; border: 1px solid #30363D; }
    
    [data-testid="stSidebarContent"] { background: #161B22; }
    
    .stButton button { background: #21262D; color: #E6EDF3; border: 1px solid #30363D; }
    .stButton button:hover { background: #30363D; }
    
    div[data-testid="metric-container"] { background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 0.8rem; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Synthetic Demo Data Generator
# ─────────────────────────────────────────────

@st.cache_data(ttl=30)
def generate_trace_stream(n=50):
    """Generate synthetic Phoenix trace data for demo."""
    random.seed(42)
    now = datetime.utcnow()
    
    antibiotics = ["nitrofurantoin", "ceftriaxone", "vancomycin", "meropenem", 
                   "ciprofloxacin", "amoxicillin-clavulanate", "piperacillin-tazobactam", "linezolid"]
    diagnoses = ["UTI", "CAP", "HAP", "SSTI", "Sepsis", "IAI"]
    results = (["PASS"] * 35) + (["FLAG"] * 10) + (["HOLD"] * 5)
    random.shuffle(results)
    
    traces = []
    for i in range(n):
        t = now - timedelta(minutes=i * 7)
        result = results[i % len(results)]
        drug = random.choice(antibiotics)
        
        traces.append({
            "trace_id": f"TR-{10000 + i:05d}",
            "timestamp": t.strftime("%H:%M:%S"),
            "date": t.strftime("%Y-%m-%d"),
            "antibiotic": drug,
            "diagnosis": random.choice(diagnoses),
            "audit_result": result,
            "confidence": round(random.uniform(0.55, 0.95), 2),
            "latency_ms": random.randint(380, 1200),
            "hallucination_detected": result == "HOLD",
            "safety_flags": random.randint(0, 3) if result != "PASS" else 0,
            "aware_tier": random.choice(["Access", "Access", "Watch", "Reserve"]),
            "physician_review": result in ["FLAG", "HOLD"],
        })
    
    return pd.DataFrame(traces)


# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────

st.markdown("## 🔍 AMRShield · Agent Audit Console")
st.caption("Real-time observability via Arize Phoenix MCP · Self-Audit Agent decisions")

# Auto-refresh toggle
col_hdr1, col_hdr2, col_hdr3 = st.columns([3, 1, 1])
with col_hdr2:
    auto_refresh = st.toggle("Live Mode", value=True)
with col_hdr3:
    if st.button("⟳ Refresh Now"):
        st.cache_data.clear()

st.divider()

# ─────────────────────────────────────────────
# Top Stats
# ─────────────────────────────────────────────

df = generate_trace_stream(50)

pass_count = len(df[df.audit_result == "PASS"])
flag_count = len(df[df.audit_result == "FLAG"])
hold_count = len(df[df.audit_result == "HOLD"])
pass_rate = round(pass_count / len(df) * 100, 1)
avg_latency = int(df.latency_ms.mean())
avg_confidence = round(df.confidence.mean(), 2)

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Traces", len(df), "↑ 8 today")
c2.metric("✅ Passed", pass_count, f"+{pass_count}")
c3.metric("⚠️ Flagged", flag_count, f"+{flag_count}", delta_color="inverse")
c4.metric("🛑 Held", hold_count, f"+{hold_count}", delta_color="inverse")
c5.metric("Pass Rate", f"{pass_rate}%", "−0.8%", delta_color="inverse")
c6.metric("Avg Latency", f"{avg_latency}ms", "−22ms")

st.divider()

# ─────────────────────────────────────────────
# Main Layout: Trace Stream | Charts
# ─────────────────────────────────────────────

col_traces, col_charts = st.columns([2, 3])

with col_traces:
    st.markdown("#### 📡 Live Trace Stream")
    st.caption("Real-time Self-Audit Agent decisions via Phoenix MCP")
    
    for _, row in df.head(15).iterrows():
        result_class = {"PASS": "trace-pass", "FLAG": "trace-flag", "HOLD": "trace-hold"}.get(row.audit_result, "trace-pass")
        badge_class = {"PASS": "badge-pass", "FLAG": "badge-flag", "HOLD": "badge-hold"}.get(row.audit_result, "badge-pass")
        
        flags_str = ""
        if row.hallucination_detected:
            flags_str += '<span class="badge badge-hold" style="margin-left:6px">HALLUCINATION</span>'
        if row.safety_flags > 0:
            flags_str += f'<span class="badge badge-flag" style="margin-left:6px">{row.safety_flags} FLAGS</span>'
        
        st.markdown(f"""
        <div class='trace-card {result_class}'>
            <span style='color:#8B949E'>{row.timestamp}</span>
            &nbsp;&nbsp;
            <span class='badge {badge_class}'>{row.audit_result}</span>
            {flags_str}
            <br/>
            <span style='color:#58A6FF'>{row.trace_id}</span>
            &nbsp;·&nbsp;
            <strong>{row.antibiotic}</strong>
            &nbsp;·&nbsp;
            {row.diagnosis}
            <br/>
            <span style='color:#8B949E'>conf: {row.confidence} · {row.latency_ms}ms · {row.aware_tier}</span>
        </div>
        """, unsafe_allow_html=True)

with col_charts:
    # Chart 1: Audit results over time
    st.markdown("#### 📈 Audit Results Timeline")
    
    hourly = df.groupby([pd.to_datetime(df.date + " " + df.timestamp).dt.floor("30min"), "audit_result"]).size().reset_index()
    hourly.columns = ["time", "result", "count"]
    
    fig_timeline = go.Figure()
    colors = {"PASS": "#3FB950", "FLAG": "#D29922", "HOLD": "#F85149"}
    for result in ["PASS", "FLAG", "HOLD"]:
        subset = hourly[hourly.result == result]
        fig_timeline.add_trace(go.Scatter(
            x=subset.time, y=subset["count"],
            mode="lines+markers", name=result,
            line=dict(color=colors[result], width=2),
            marker=dict(size=5),
        ))
    
    fig_timeline.update_layout(
        height=200,
        paper_bgcolor="#0D1117",
        plot_bgcolor="#161B22",
        font_color="#C9D1D9",
        legend=dict(bgcolor="#0D1117", font_color="#C9D1D9"),
        margin=dict(t=10, b=30, l=10, r=10),
        xaxis=dict(gridcolor="#21262D"),
        yaxis=dict(gridcolor="#21262D"),
    )
    st.plotly_chart(fig_timeline, use_container_width=True)
    
    # Chart 2: Confidence calibration
    st.markdown("#### 🎯 Confidence Calibration")
    
    fig_conf = px.histogram(
        df, x="confidence", color="audit_result",
        color_discrete_map={"PASS": "#3FB950", "FLAG": "#D29922", "HOLD": "#F85149"},
        nbins=20, barmode="overlay", opacity=0.8,
    )
    fig_conf.update_layout(
        height=180,
        paper_bgcolor="#0D1117",
        plot_bgcolor="#161B22",
        font_color="#C9D1D9",
        legend=dict(bgcolor="#0D1117"),
        margin=dict(t=10, b=30, l=10, r=10),
        xaxis=dict(gridcolor="#21262D", title="Confidence Score"),
        yaxis=dict(gridcolor="#21262D", title="Count"),
    )
    st.plotly_chart(fig_conf, use_container_width=True)
    
    # Chart 3: Drift detection - AWaRe tier over time
    st.markdown("#### 📉 AWaRe Tier Drift Detection")
    
    aware_trend = df.groupby("aware_tier").size().reset_index()
    aware_trend.columns = ["tier", "count"]
    
    aware_colors = {"Access": "#3FB950", "Watch": "#D29922", "Reserve": "#F85149"}
    fig_aware = go.Figure(go.Bar(
        x=aware_trend["count"],
        y=aware_trend["tier"],
        orientation="h",
        marker_color=[aware_colors.get(t, "#58A6FF") for t in aware_trend["tier"]],
    ))
    fig_aware.update_layout(
        height=140,
        paper_bgcolor="#0D1117",
        plot_bgcolor="#161B22",
        font_color="#C9D1D9",
        margin=dict(t=10, b=20, l=10, r=10),
        xaxis=dict(gridcolor="#21262D", title="Count"),
        yaxis=dict(gridcolor="#21262D"),
    )
    st.plotly_chart(fig_aware, use_container_width=True)

# ─────────────────────────────────────────────
# Hallucination Log
# ─────────────────────────────────────────────

st.divider()
st.markdown("#### 🚨 Hallucination Detection Log")

hallucination_df = df[df.hallucination_detected].copy()

if len(hallucination_df) > 0:
    st.markdown("""
    <div class='terminal-header'>● PHOENIX EVALUATOR · Hallucination Detector · Live</div>
    <div class='terminal-body'>""", unsafe_allow_html=True)
    
    log_html = ""
    for _, row in hallucination_df.iterrows():
        log_html += f"""<span style='color:#3FB950'>[{row.timestamp}]</span> <span style='color:#F85149'>HALLUCINATION_DETECTED</span> trace_id={row.trace_id} drug={row.antibiotic} conf={row.confidence}<br/>"""
        log_html += f"""&nbsp;&nbsp;&nbsp;&nbsp;<span style='color:#8B949E'>→ Flagged absolutist language · Held for physician review · Phoenix annotation written</span><br/>"""
    
    st.markdown(log_html + "</div>", unsafe_allow_html=True)
else:
    st.success("No hallucinations detected in the current trace window.")

# ─────────────────────────────────────────────
# Physician Review Queue
# ─────────────────────────────────────────────

st.divider()
st.markdown("#### 🩺 Physician Review Queue")
st.caption("Recommendations held by Self-Audit Agent — require physician sign-off before acting")

review_queue = df[df.physician_review].head(5)

for _, row in review_queue.iterrows():
    badge = "🛑 HOLD" if row.audit_result == "HOLD" else "⚠️ FLAG"
    col_q1, col_q2, col_q3 = st.columns([3, 1, 1])
    with col_q1:
        st.markdown(f"**{badge}** — `{row.trace_id}` · {row.antibiotic.title()} for {row.diagnosis} · {row.safety_flags} safety issue(s)")
    with col_q2:
        st.button("✅ Approve", key=f"approve_{row.trace_id}", use_container_width=True)
    with col_q3:
        st.button("🔄 Override", key=f"override_{row.trace_id}", use_container_width=True)

st.divider()
st.caption("AMRShield Audit Console · Arize Phoenix MCP · Google Cloud Agent Builder · Gemini 3")
