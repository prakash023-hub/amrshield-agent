"""
AMRShield - Dashboard 3: AMR Surveillance Geographic Map
Population-level resistance patterns + Holt baseline forecasts (synthetic demo data).
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from agents.prediction_agent.agent import holt_forecast, synthetic_history  # noqa: E402

# Assumed annual change (percentage points) per country — SYNTHETIC demo values
ANNUAL_CHANGE = {
    "India": 2.0, "Bangladesh": 2.2, "Pakistan": 1.8, "China": 0.9, "Brazil": 1.1,
    "Nigeria": 2.1, "South Africa": 1.3, "USA": 0.6, "Germany": 0.3, "UK": 0.2,
    "France": 0.4, "Russia": 1.0, "Japan": 0.1, "Australia": 0.3, "Mexico": 1.2,
    "Egypt": 1.7, "Kenya": 1.9, "Indonesia": 1.4, "Thailand": 1.0, "Iran": 1.5,
}

st.set_page_config(
    page_title="AMRShield — Surveillance Map",
    page_icon="🌍",
    layout="wide",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700&family=DM+Mono:wght@400;500&display=swap');
    html, body, [class*="css"] { font-family: 'Syne', sans-serif; }
    .stApp { background: #070E1A; color: #D4E4F7; }
    .main { background: #070E1A; }
    h1, h2, h3, h4 { color: #D4E4F7 !important; }
    p, span, div { color: #A8C0D6; }
    div[data-testid="metric-container"] { background: #0D1B2A; border: 1px solid #1E3A5F; border-radius: 10px; padding: 1rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 🌍 AMRShield — Global AMR Surveillance Map")
st.caption("Geographic resistance pattern visualization · Holt baseline 6-month forecast · SYNTHETIC WHO GLASS-style demo data")

col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    pathogen_filter = st.selectbox("Pathogen", ["E. coli (ESBL)", "MRSA", "K. pneumoniae (CRE)", "P. aeruginosa (MDR)", "A. baumannii (XDR)"])
with col_f2:
    antibiotic_filter = st.selectbox("Antibiotic Resistance", ["Fluoroquinolones", "3rd gen Cephalosporins", "Carbapenems", "Vancomycin"])
with col_f3:
    view_mode = st.selectbox("View", ["Current Resistance %", "6-Month Forecast (Holt baseline)", "Year-over-Year Change"])

pathogen_key = pathogen_filter

st.divider()

# ── Choropleth Map ──
# WHO GLASS-inspired synthetic global resistance data
countries = {
    "India": (20.5937, 78.9629, 68),
    "Bangladesh": (23.685, 90.356, 72),
    "Pakistan": (30.375, 69.345, 65),
    "China": (35.86, 104.195, 45),
    "Brazil": (-14.235, -51.925, 51),
    "Nigeria": (9.082, 8.675, 73),
    "South Africa": (-30.559, 22.937, 58),
    "USA": (37.09, -95.712, 22),
    "Germany": (51.165, 10.451, 18),
    "UK": (55.378, -3.436, 16),
    "France": (46.227, 2.213, 21),
    "Russia": (61.52, 105.318, 38),
    "Japan": (36.204, 138.252, 12),
    "Australia": (-25.274, 133.775, 19),
    "Mexico": (23.634, -102.552, 43),
    "Egypt": (26.820, 30.802, 61),
    "Kenya": (-0.023, 37.906, 67),
    "Indonesia": (-0.789, 113.921, 55),
    "Thailand": (15.870, 100.992, 48),
    "Iran": (32.427, 53.688, 57),
}

df_map = pd.DataFrame([
    {"country": k, "lat": v[0], "lon": v[1], "resistance_pct": v[2]}
    for k, v in countries.items()
])

if view_mode == "6-Month Forecast (Holt baseline)":
    df_map["resistance_pct"] = [
        holt_forecast(synthetic_history(c, pathogen_key, current=v, annual_change=ANNUAL_CHANGE.get(c, 1.0)), 6)["point"][-1]
        for c, v in zip(df_map["country"], df_map["resistance_pct"])
    ]
    title_suffix = "(Holt baseline forecast)"
elif view_mode == "Year-over-Year Change":
    df_map["resistance_pct"] = [ANNUAL_CHANGE.get(c, 1.0) for c in df_map["country"]]
    title_suffix = "(YoY Change %)"
else:
    title_suffix = "(Current)"

fig_map = go.Figure()

fig_map.add_trace(go.Scattergeo(
    lat=df_map["lat"],
    lon=df_map["lon"],
    text=df_map["country"] + ": " + df_map["resistance_pct"].astype(str) + "%",
    mode="markers",
    marker=dict(
        size=df_map["resistance_pct"] / 4 + 6,
        color=df_map["resistance_pct"],
        colorscale=[[0, "#22C55E"], [0.4, "#EAB308"], [0.7, "#F97316"], [1, "#EF4444"]],
        cmin=0, cmax=80,
        showscale=True,
        colorbar=dict(title="Resistance %", bgcolor="#0D1B2A", tickfont=dict(color="#A8C0D6")),
        opacity=0.85,
        line=dict(width=0),
    ),
    hovertemplate="<b>%{text}</b><extra></extra>",
))

fig_map.update_layout(
    height=450,
    paper_bgcolor="#070E1A",
    geo=dict(
        bgcolor="#070E1A",
        landcolor="#0D1B2A",
        oceancolor="#040C17",
        showocean=True,
        showcountries=True,
        countrycolor="#1E3A5F",
        showframe=False,
        coastlinecolor="#1E3A5F",
        projection_type="natural earth",
    ),
    margin=dict(t=20, b=10, l=0, r=0),
    title=dict(
        text=f"{pathogen_filter} · {antibiotic_filter} Resistance {title_suffix}",
        font=dict(color="#D4E4F7", size=14),
        x=0.01,
    ),
)
st.plotly_chart(fig_map, use_container_width=True)

# ── Bottom Row: Trends + Hotspots ──
col_a, col_b, col_c = st.columns(3)

with col_a:
    st.markdown("#### 📈 Global Resistance Trend")
    hist = synthetic_history("Global", pathogen_key, months=18, current=42, annual_change=1.2)
    fc = holt_forecast(hist, 6)
    months = pd.PeriodIndex(hist.index, freq="M").to_timestamp()
    resistance_trend = hist.values
    forecast_months = pd.period_range(pd.Period(hist.index[-1], freq="M") + 1, periods=6, freq="M").to_timestamp()
    forecast_vals = fc["point"]
    
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(x=months, y=resistance_trend, name="Observed",
                                    line=dict(color="#58A6FF", width=2)))
    fig_trend.add_trace(go.Scatter(x=forecast_months, y=forecast_vals, name="Holt baseline forecast",
                                    line=dict(color="#F97316", width=2, dash="dot")))
    fig_trend.update_layout(height=200, paper_bgcolor="#070E1A", plot_bgcolor="#0D1B2A",
                             font_color="#A8C0D6", margin=dict(t=10,b=20,l=10,r=10),
                             xaxis=dict(gridcolor="#1E3A5F"), yaxis=dict(gridcolor="#1E3A5F", title="Resistance %"))
    st.plotly_chart(fig_trend, use_container_width=True)

with col_b:
    st.markdown("#### 🔥 Top Resistance Hotspots")
    top_5 = df_map.nlargest(5, "resistance_pct")[["country","resistance_pct"]]
    for _, row in top_5.iterrows():
        pct = row["resistance_pct"]
        bar_color = "#EF4444" if pct > 60 else "#F97316" if pct > 45 else "#EAB308"
        st.markdown(f"""
        <div style='margin-bottom:6px'>
        <span style='color:#A8C0D6; display:inline-block; width:120px'>{row["country"]}</span>
        <span style='background:{bar_color}33; border-radius:4px; padding:2px 8px; color:{bar_color}; font-weight:600'>{pct}%</span>
        </div>
        """, unsafe_allow_html=True)

with col_c:
    st.markdown("#### 🌐 WHO GLASS Integration")
    st.info("Demo data: SYNTHETIC, WHO GLASS-style values (no live API connection yet)")
    st.markdown("""
    **Planned data streams:**
    - Blood isolate susceptibility (GLASS 2024)
    - UTI pathogen resistance surveillance  
    - WHO Global Priority Pathogen List
    - ESKAPE pathogens monitoring
    
    **Forecast method:** Holt linear-trend exponential smoothing (baseline).
    **Next step:** ingest real WHO GLASS data and benchmark ARIMA / Prophet
    against this baseline with rolling-origin backtesting.
    """)

st.divider()
st.caption("AMRShield Surveillance · Synthetic WHO GLASS-style data · Holt baseline forecast · Arize Phoenix MCP")
