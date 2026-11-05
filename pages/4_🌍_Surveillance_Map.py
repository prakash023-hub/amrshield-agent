import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.prediction_agent.agent import holt_forecast, synthetic_history  # noqa: E402

# Assumed annual change (percentage points) per country — SYNTHETIC demo values
ANNUAL_CHANGE = {
    "India": 2.0, "Bangladesh": 2.2, "Pakistan": 1.8, "China": 0.9, "Brazil": 1.1,
    "Nigeria": 2.1, "South Africa": 1.3, "USA": 0.6, "Germany": 0.3, "UK": 0.2,
    "France": 0.4, "Russia": 1.0, "Japan": 0.1, "Australia": 0.3, "Mexico": 1.2,
    "Egypt": 1.7, "Kenya": 1.9, "Indonesia": 1.4, "Thailand": 1.0, "Iran": 1.5,
}
from datetime import datetime

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #060B18; }
.main { background: #060B18; }
h1,h2,h3,h4 { color: #E2EDF7 !important; }
p, label, caption { color: #94A3B8 !important; }
section[data-testid="stSidebar"] { background: #0D1B2A !important; }
div[data-testid="metric-container"] { background: #0D1B2A; border: 1px solid #1E3A5F; border-radius: 10px; padding: 1rem; }
/* Fix dropdown text */
div[data-testid="stSelectbox"] div[data-baseweb="select"] { background: #1E293B !important; }
div[data-testid="stSelectbox"] span { color: #E2EDF7 !important; }
div[data-baseweb="select"] span { color: #E2EDF7 !important; }
div[data-baseweb="popover"] li { color: #E2EDF7 !important; background: #1E293B !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 🌍 AMRShield — Global AMR Surveillance")
st.caption("Geographic resistance · Holt baseline 6-month forecast · SYNTHETIC WHO GLASS-style demo data")

col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    pathogen = st.selectbox("Pathogen", ["E. coli (ESBL)", "MRSA", "K. pneumoniae (CRE)", "P. aeruginosa (MDR)"])
with col_f2:
    antibiotic = st.selectbox("Antibiotic Class", ["Fluoroquinolones", "3rd gen Cephalosporins", "Carbapenems", "Vancomycin"])
with col_f3:
    view = st.selectbox("View", ["Current Resistance %", "6-Month Forecast (Holt baseline)", "Year-over-Year Change"])

pathogen_key = pathogen

st.divider()

countries = {
    "India": (20.59, 78.96, 68), "Bangladesh": (23.68, 90.35, 72),
    "Pakistan": (30.37, 69.34, 65), "China": (35.86, 104.19, 45),
    "Brazil": (-14.23, -51.92, 51), "Nigeria": (9.08, 8.67, 73),
    "South Africa": (-30.55, 22.93, 58), "USA": (37.09, -95.71, 22),
    "Germany": (51.16, 10.45, 18), "UK": (55.37, -3.43, 16),
    "France": (46.22, 2.21, 21), "Russia": (61.52, 105.31, 38),
    "Japan": (36.20, 138.25, 12), "Australia": (-25.27, 133.77, 19),
    "Mexico": (23.63, -102.55, 43), "Egypt": (26.82, 30.80, 61),
    "Kenya": (-0.02, 37.90, 67), "Indonesia": (-0.78, 113.92, 55),
    "Thailand": (15.87, 100.99, 48), "Iran": (32.42, 53.68, 57),
}

df = pd.DataFrame([{"country": k, "lat": v[0], "lon": v[1], "resistance": v[2]} for k, v in countries.items()])

if view == "6-Month Forecast (Holt baseline)":
    df["resistance"] = [
        holt_forecast(synthetic_history(c, pathogen_key, current=v, annual_change=ANNUAL_CHANGE.get(c, 1.0)), 6)["point"][-1]
        for c, v in zip(df["country"], df["resistance"])
    ]
elif view == "Year-over-Year Change":
    df["resistance"] = [ANNUAL_CHANGE.get(c, 1.0) for c in df["country"]]

fig = go.Figure()
fig.add_trace(go.Scattergeo(
    lat=df["lat"], lon=df["lon"],
    text=df["country"] + ": " + df["resistance"].astype(str) + "%",
    mode="markers",
    marker=dict(
        size=df["resistance"] / 4 + 6,
        color=df["resistance"],
        colorscale=[[0, "#22C55E"], [0.4, "#EAB308"], [0.7, "#F97316"], [1, "#EF4444"]],
        cmin=0, cmax=80,
        showscale=True,
        colorbar=dict(title="Resistance %", bgcolor="#0D1B2A"),
        opacity=0.85,
        line=dict(width=0),
    ),
    hovertemplate="<b>%{text}</b><extra></extra>",
))

fig.update_layout(
    height=520,
    paper_bgcolor="#060B18",
    geo=dict(
        bgcolor="#060B18",
        landcolor="#0D1B2A",
        oceancolor="#030810",
        showocean=True, showcountries=True,
        countrycolor="#1E3A5F", showframe=False,
        coastlinecolor="#1E3A5F",
        projection_type="natural earth",
    ),
    margin=dict(t=10, b=10, l=0, r=0),
)
st.caption(f"🗺️ Showing: **{pathogen}** · **{antibiotic}** · **{view}**")
st.plotly_chart(fig, use_container_width=True)

col_a, col_b, col_c = st.columns(3)

with col_a:
    st.markdown("#### 📈 Resistance Trend")
    hist = synthetic_history("Global", pathogen_key, months=18, current=42, annual_change=1.2)
    fc = holt_forecast(hist, 6)
    months = pd.PeriodIndex(hist.index, freq="M").to_timestamp()
    vals = hist.values
    fcast_months = pd.period_range(pd.Period(hist.index[-1], freq="M") + 1, periods=6, freq="M").to_timestamp()
    fcast_vals = fc["point"]
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=months, y=vals, name="Observed", line=dict(color="#58A6FF", width=2)))
    fig2.add_trace(go.Scatter(x=fcast_months, y=fcast_vals, name="Holt baseline forecast", line=dict(color="#F97316", width=2, dash="dot")))
    fig2.update_layout(height=200, paper_bgcolor="#060B18", plot_bgcolor="#0D1B2A",
                        font_color="#C9D1D9", margin=dict(t=10,b=20,l=10,r=10),
                        xaxis=dict(gridcolor="#1E3A5F"), yaxis=dict(gridcolor="#1E3A5F", title="Resistance %"),
                        legend=dict(bgcolor="#060B18"))
    st.plotly_chart(fig2, use_container_width=True)

with col_b:
    st.markdown("#### 🔥 Top Hotspots")
    top5 = df.nlargest(5, "resistance")[["country","resistance"]]
    for _, row in top5.iterrows():
        pct = row["resistance"]
        color = "#EF4444" if pct > 60 else "#F97316" if pct > 45 else "#EAB308"
        st.markdown(f"""<div style='margin-bottom:8px; padding:8px 12px; background:#0D1B2A; border-left:3px solid {color}; border-radius:6px'>
        <span style='color:#94A3B8'>{row["country"]}</span>
        <span style='float:right; color:{color}; font-weight:700'>{pct}%</span></div>""", unsafe_allow_html=True)

with col_c:
    st.markdown("#### 🌐 WHO GLASS Data (planned)")
    st.markdown("""<div style='background:#0D1B2A; border:1px solid #1E3A5F; border-radius:8px; padding:1rem'>
    <p style='color:#94A3B8; font-size:0.85rem'>
    ◻ Blood isolate susceptibility (GLASS 2024)<br>
    ◻ UTI pathogen resistance surveillance<br>
    ◻ WHO Priority Pathogen List<br>
    ◻ ESKAPE pathogens monitoring<br><br>
    <strong style='color:#58A6FF'>Data status:</strong> all values are SYNTHETIC, WHO GLASS-style demo data. Forecast = Holt linear-trend smoothing baseline; real GLASS ingestion and ARIMA/Prophet benchmarking are the next step.
    </p></div>""", unsafe_allow_html=True)

st.divider()
st.caption("AMRShield Surveillance · Synthetic WHO GLASS-style data · Holt baseline forecast · Arize Phoenix MCP")
