import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp_tools.phoenix_integration import ensure_phoenix_tracing, get_audit_traces

ensure_phoenix_tracing()

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

col1, col2 = st.columns([4, 1])
with col2:
    if st.button("⟳ Refresh"):
        st.cache_data.clear()

st.divider()


def _synthetic_traces(n=20):
    """Demo history only — labeled; PASS requires confidence ≥ 0.75."""
    random.seed(42)
    now = datetime.utcnow()
    antibiotics = ["nitrofurantoin", "ceftriaxone", "vancomycin", "meropenem", "ciprofloxacin"]
    diagnoses = ["UTI", "CAP", "HAP", "SSTI", "Sepsis"]
    rows = []
    for i in range(n):
        conf = round(random.uniform(0.62, 0.96), 2)
        if conf >= 0.75:
            r = random.choice(["PASS"] * 7 + ["FLAG"] * 2)
        else:
            r = random.choice(["FLAG", "HOLD"])
        hall = r == "HOLD" or (r == "FLAG" and conf < 0.70)
        hall_detail = {
            "findings": [{"category": "INDICATION_MISMATCH", "detail": "Carbapenem for UTI without ESBL — verify indication"}]
        } if hall and "meropenem" in antibiotics[i % len(antibiotics)] else {"findings": []}
        rows.append({
            "trace_id": f"TR-DEMO-{10000 + i:05d}",
            "time": (now - timedelta(minutes=i * 7)).strftime("%H:%M:%S"),
            "antibiotic": antibiotics[i % len(antibiotics)],
            "diagnosis": diagnoses[i % len(diagnoses)],
            "result": r,
            "confidence": conf,
            "latency_ms": random.randint(380, 1200),
            "hallucination": hall,
            "hallucination_details": hall_detail,
            "flag_count": len(hall_detail.get("findings", [])) + (1 if r != "PASS" else 0),
            "aware": random.choice(["Access", "Access", "Watch"]),
            "physician_review": r in ["FLAG", "HOLD"],
            "queued_at": (now - timedelta(minutes=i * 7)).isoformat(),
            "source": "demo_seed_labeled",
        })
    return rows


@st.cache_data(ttl=15)
def load_traces(n=50):
    live = get_audit_traces(limit=n)
    if live:
        for row in live:
            row.setdefault("source", "live")
        if len(live) < n:
            padding = _synthetic_traces(n - len(live))
            live.extend(padding)
        return pd.DataFrame(live[:n])

    return pd.DataFrame(_synthetic_traces(n))


df = load_traces()
if "source" in df.columns:
    live_count = int((df["source"] != "demo_seed").sum())
else:
    live_count = 0
if live_count > 0:
    st.success(f"📡 {live_count} live audit trace(s) from Phoenix MCP pipeline")
else:
    st.info("Run a case in **Clinician Console** for live traces. Demo rows below are **labeled synthetic** — not clinical outcomes.")

# Exclude demo from pass-rate headline when live data exists
rate_df = df[df.get("source", pd.Series(["live"] * len(df))) != "demo_seed_labeled"] if "source" in df.columns else df
if len(rate_df) == 0:
    rate_df = df

pass_c = len(rate_df[rate_df.result == "PASS"])
flag_c = len(rate_df[rate_df.result == "FLAG"])
hold_c = len(rate_df[rate_df.result == "HOLD"])

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Traces shown", len(df))
m2.metric("✅ Passed", pass_c)
m3.metric("⚠️ Flagged", flag_c)
m4.metric("🛑 Held", hold_c)
m5.metric("Pass Rate", f"{round(pass_c / max(len(rate_df), 1) * 100, 1)}%", help="Live cases only when available")
m6.metric("Release threshold", "≥75% conf")

st.divider()
col_l, col_r = st.columns([2, 3])

with col_l:
    st.markdown("#### 📡 Live Trace Stream")
    for _, row in df.head(12).iterrows():
        rc = {"PASS": "trace-pass", "FLAG": "trace-flag", "HOLD": "trace-hold"}[row.result]
        bc = {"PASS": "bp", "FLAG": "bf", "HOLD": "bh"}[row.result]
        flags_html = ""
        if row.hallucination:
            flags_html += '<span class="badge bh" style="margin-left:6px">HALLUCINATION</span>'
        if row.flag_count > 0:
            flags_html += f'<span class="badge bf" style="margin-left:4px">{int(row.flag_count)} FLAGS</span>'
        live_badge = ""
        if row.get("source") == "live" or (isinstance(row.get("phoenix_mcp_tools"), list) and row.get("phoenix_mcp_tools")):
            live_badge = '<span class="badge bp" style="margin-left:6px">LIVE MCP</span>'
        st.markdown(f"""<div class='trace-card {rc}'>
<span style='color:#8B949E'>{row.time}</span>&nbsp;
<span class='badge {bc}'>{row.result}</span>{flags_html}{live_badge}<br/>
<span style='color:#58A6FF'>{row.trace_id}</span>&nbsp;·&nbsp;
<strong style='color:#E6EDF3'>{row.antibiotic}</strong>&nbsp;·&nbsp;{row.diagnosis}<br/>
<span style='color:#8B949E'>conf:{row.confidence} · {row.latency_ms}ms · {row.aware}</span>
</div>""", unsafe_allow_html=True)

with col_r:
    st.markdown("#### 📈 Audit Timeline")
    fig1 = go.Figure()
    colors = {"PASS": "#3FB950", "FLAG": "#D29922", "HOLD": "#F85149"}
    for res in ["PASS", "FLAG", "HOLD"]:
        sub = df[df.result == res].head(20)
        fig1.add_trace(go.Scatter(
            x=list(range(len(sub))), y=[1] * len(sub), name=res,
            mode="markers", marker=dict(color=colors[res], size=8),
        ))
    fig1.update_layout(
        height=180, paper_bgcolor="#060D1A", plot_bgcolor="#161B22",
        font_color="#8B949E", margin=dict(t=10, b=20, l=10, r=10),
        xaxis=dict(gridcolor="#21262D"), yaxis=dict(visible=False),
    )
    st.plotly_chart(fig1, use_container_width=True)

    st.markdown("#### 🎯 Confidence Distribution")
    fig2 = px.histogram(
        df, x="confidence", color="result",
        color_discrete_map={"PASS": "#3FB950", "FLAG": "#D29922", "HOLD": "#F85149"},
        nbins=15, barmode="overlay", opacity=0.8,
    )
    fig2.update_layout(
        height=180, paper_bgcolor="#060D1A", plot_bgcolor="#161B22",
        font_color="#8B949E", margin=dict(t=10, b=20, l=10, r=10),
        xaxis=dict(gridcolor="#21262D", title="Confidence Score"),
        yaxis=dict(gridcolor="#21262D"),
        legend=dict(bgcolor="#060D1A"),
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("#### 📉 AWaRe Tier Usage")
    aware_df = df.groupby("aware").size().reset_index(name="count")
    fig3 = go.Figure(go.Bar(
        x=aware_df["count"], y=aware_df["aware"], orientation="h",
        marker_color=["#22C55E", "#F85149", "#EAB308"][: len(aware_df)],
    ))
    fig3.update_layout(
        height=150, paper_bgcolor="#060D1A", plot_bgcolor="#161B22",
        font_color="#8B949E", margin=dict(t=5, b=20, l=10, r=10),
        xaxis=dict(gridcolor="#21262D"), yaxis=dict(gridcolor="#21262D"),
    )
    st.plotly_chart(fig3, use_container_width=True)

st.divider()
st.markdown("#### 🚨 Hallucination & quality detail log")
hall_df = df[(df.hallucination) | (df.result != "PASS")]
if len(hall_df) > 0:
    for _, row in hall_df.head(10).iterrows():
        details = row.get("hallucination_details") or {}
        if isinstance(details, str):
            try:
                import json
                details = json.loads(details)
            except Exception:
                details = {}
        findings = details.get("findings", []) if isinstance(details, dict) else []
        detail_txt = "; ".join(f.get("detail", "") for f in findings) or row.get("audit_reasoning", "See issues list")
        st.markdown(f"""<div class='trace-card trace-hold'>
<strong>{row.trace_id}</strong> · {row.antibiotic} · {row.diagnosis} · conf {row.confidence}<br/>
<span style='color:#F85149'>Issue:</span> {detail_txt}
</div>""", unsafe_allow_html=True)
else:
    st.success("No hallucination flags in current view")

st.divider()
st.markdown("#### 🩺 Physician Review Queue")
st.caption("Override requires ≥20 characters clinical justification (medico-legal)")
review_df = df[df.physician_review].head(8)
for _, row in review_df.iterrows():
    badge = "🛑 HOLD" if row.result == "HOLD" else "⚠️ FLAG"
    st.markdown(f"**{badge}** `{row.trace_id}` · {row.antibiotic} for {row.diagnosis} · conf {row.confidence}")
    justification = st.text_area("Override justification", key=f"j_{row.trace_id}", placeholder="Clinical rationale for overriding audit flag...")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("✅ Approve", key=f"a_{row.trace_id}"):
            st.success("Approved with audit trail")
    with c2:
        if st.button("🔄 Override", key=f"o_{row.trace_id}"):
            from mcp_tools.stewardship_store import record_override
            r = record_override(row.trace_id, "PHYSICIAN", justification)
            if r.get("error"):
                st.error(r["error"])
            else:
                st.success("Override recorded with justification")
    with c3:
        st.caption(f"Queued: {str(row.get('queued_at', '—'))[:19]}")
