"""
Decision Intelligence – What-If Demand & Savings Simulator
===========================================================
Standalone Streamlit page.  Run independently:

    streamlit run dashboard/what_if_simulator.py

Or embed as a multipage app by placing this file inside a
``pages/`` sub-folder next to streamlit_app.py:

    dashboard/
        streamlit_app.py        ← existing (untouched)
        pages/
            1_What_If_Simulator.py   ← symlink or copy of this file
            2_Community_Ranking.py   ← symlink or copy of community_ranking.py

HOW IT WORKS
------------
1. Loads the most recent LSTM forecast from DemandForecaster
   (falls back to the simple moving-average forecast if TF is absent).
2. User adjusts scenario sliders:
       • Irrigation reduction  (0 – 60 %)
       • Industrial curtailment (0 – 40 %)
       • Leak repair factor     (0 – 30 % unaccounted-water recovery)
       • Time horizon           (1 – 24 h)
3. The simulator applies the scenario to the baseline forecast in real-time,
   then shows:
       • Adjusted vs baseline forecast chart
       • Cumulative savings (Litres & cost estimate)
       • Carbon / energy co-benefit estimate
       • Recommendation cards from WaterRecommendationEngine

NO EXISTING FILES ARE MODIFIED.
"""

from __future__ import annotations

import os
import sys
import sqlite3
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# ── path setup ──────────────────────────────────────────────────────────────
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_models.lstm_forecast import DemandForecaster
from ai_models.recommendation_engine import WaterRecommendationEngine

# ── constants ────────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "water.db")
STEPS_PER_HOUR = 12          # one reading every 5 seconds → 12/min → 720/hour
                              # but forecaster returns ~12 per hour in practice
LITRES_PER_STEP = 60 / 12    # L/min × 5 s ÷ 60 = 5 L per step  (approx)
COST_PER_1000L = 3.50        # ₹ per kilolitre (configurable)
KG_CO2_PER_1000L = 0.35      # kg CO₂ equivalent per kL pumped

# ── page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="What-If Simulator | Smart Water",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── shared CSS (mirrors existing app style) ──────────────────────────────────
st.markdown("""
<style>
    .stApp { background: linear-gradient(to bottom, #f0f9ff, #e0f2fe); }
    .page-title {
        font-size: 2.4rem; font-weight: 800;
        background: linear-gradient(120deg, #0c4a6e, #0284c7, #0ea5e9);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: .3rem;
    }
    .section-header {
        font-size: 1.5rem; font-weight: 700; color: #1e293b;
        margin: 1.8rem 0 .8rem; padding-bottom: .4rem;
        border-bottom: 3px solid #3b82f6;
    }
    .kpi-card {
        background: white; border-radius: 14px;
        padding: 1.2rem 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,.08);
        border-left: 5px solid #3b82f6;
        margin-bottom: 1rem;
    }
    .kpi-label { font-size: .85rem; color: #64748b; font-weight: 600;
                 text-transform: uppercase; letter-spacing: .05em; }
    .kpi-value { font-size: 2rem; font-weight: 800; color: #0284c7; }
    .kpi-unit  { font-size: 1rem; color: #94a3b8; font-weight: 500; }
    .saving-positive { color: #10b981; }
    .saving-negative { color: #dc2626; }
    .rec-card {
        background: white; border-radius: 10px;
        padding: 1rem 1.2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,.07);
        border-left: 5px solid #f59e0b;
        margin-bottom: .8rem;
    }
    .rec-high   { border-left-color: #dc2626; }
    .rec-medium { border-left-color: #f59e0b; }
    .rec-low    { border-left-color: #10b981; }
</style>
""", unsafe_allow_html=True)


# ── helpers ──────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_forecaster() -> DemandForecaster:
    fc = DemandForecaster(db_path=DB_PATH)
    fc.load_model()
    return fc


@st.cache_resource(show_spinner=False)
def get_engine() -> WaterRecommendationEngine:
    return WaterRecommendationEngine(db_path=DB_PATH)


@st.cache_data(ttl=30, show_spinner=False)
def load_baseline_forecast(hours: int = 24) -> list[float]:
    fc = get_forecaster()
    return fc.predict_next_hours(hours=hours)


@st.cache_data(ttl=30, show_spinner=False)
def load_recent_stats() -> dict:
    """Return avg/min/max for the most recent 720 DB rows (~1 hour)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("""
            SELECT
                ROUND(AVG(flow),2)      AS avg_flow,
                ROUND(MIN(flow),2)      AS min_flow,
                ROUND(MAX(flow),2)      AS max_flow,
                ROUND(AVG(pressure),2)  AS avg_pressure,
                ROUND(AVG(ph),2)        AS avg_ph,
                ROUND(AVG(turbidity),2) AS avg_turbidity,
                COUNT(*)                AS n
            FROM (SELECT flow, pressure, ph, turbidity
                  FROM sensor_data ORDER BY id DESC LIMIT 720)
        """).fetchone()
        conn.close()
        return dict(zip(
            ["avg_flow","min_flow","max_flow","avg_pressure",
             "avg_ph","avg_turbidity","n"],
            row
        )) if row else {}
    except Exception:
        return {}


def apply_scenario(
    baseline: np.ndarray,
    irrigation_cut_pct: float,
    industrial_cut_pct: float,
    leak_recovery_pct: float,
    horizon_steps: int,
) -> np.ndarray:
    """
    Apply the what-if scenario to the baseline forecast array.

    Irrigation and industrial reductions are applied only to the
    supplied horizon; leak recovery is applied uniformly (unaccounted
    water that disappears before reaching the meter).
    """
    adjusted = baseline.copy()

    # Irrigation runs primarily in daytime hours (steps 0–horizon)
    irrigation_factor = 1.0 - (irrigation_cut_pct / 100.0)
    industrial_factor = 1.0 - (industrial_cut_pct / 100.0)
    # Leak recovery adds flow back (water that was being lost)
    leak_factor = 1.0 + (leak_recovery_pct / 100.0)

    adjusted[:horizon_steps] *= irrigation_factor * industrial_factor
    adjusted *= leak_factor       # leak recovery applies to all steps

    return np.maximum(adjusted, 0)


def compute_savings(
    baseline: np.ndarray,
    adjusted: np.ndarray,
    cost_per_kl: float,
    co2_per_kl: float,
) -> dict:
    """
    Compute cumulative savings in litres, cost, and CO₂.
    Positive = reduction (saving), Negative = increase (more demand).
    """
    steps = len(baseline)
    # Each step = 5 seconds; flow in L/min → L per step = flow × (5/60)
    seconds_per_step = 5.0
    baseline_litres = float(np.sum(baseline * seconds_per_step / 60.0))
    adjusted_litres = float(np.sum(adjusted * seconds_per_step / 60.0))
    saved_litres    = baseline_litres - adjusted_litres

    saved_kl    = saved_litres / 1000.0
    saved_cost  = saved_kl * cost_per_kl
    saved_co2   = saved_kl * co2_per_kl

    return {
        "baseline_litres": baseline_litres,
        "adjusted_litres": adjusted_litres,
        "saved_litres":    saved_litres,
        "saved_kl":        saved_kl,
        "saved_cost":      saved_cost,
        "saved_co2":       saved_co2,
        "pct_change":      (saved_litres / baseline_litres * 100)
                           if baseline_litres > 0 else 0.0,
    }


def make_forecast_chart(
    baseline: np.ndarray,
    adjusted: np.ndarray,
    horizon_steps: int,
    hours: int,
) -> go.Figure:
    n = len(baseline)
    # Build time axis: one tick per hour
    x_hours = np.linspace(0, hours, n)
    now_label = datetime.now().strftime("%H:%M")

    fig = go.Figure()

    # Baseline shaded area
    fig.add_trace(go.Scatter(
        x=x_hours, y=baseline,
        name="Baseline Forecast",
        line=dict(color="#94a3b8", width=2, dash="dot"),
        fill="tozeroy",
        fillcolor="rgba(148, 163, 184, 0.15)",
        hovertemplate="Hour %{x:.1f}: %{y:.2f} L/min<extra>Baseline</extra>",
    ))

    # Adjusted line
    fig.add_trace(go.Scatter(
        x=x_hours, y=adjusted,
        name="Scenario Forecast",
        line=dict(color="#0284c7", width=3),
        fill="tozeroy",
        fillcolor="rgba(2, 132, 199, 0.12)",
        hovertemplate="Hour %{x:.1f}: %{y:.2f} L/min<extra>Scenario</extra>",
    ))

    # Horizon marker
    horizon_hours = horizon_steps / (n / hours) if n > 0 else 0
    fig.add_vline(
        x=horizon_hours,
        line_dash="dash",
        line_color="#f59e0b",
        annotation_text="Intervention horizon",
        annotation_position="top right",
        annotation_font_color="#f59e0b",
    )

    # Savings fill between curves
    diff = baseline - adjusted
    pos_mask = diff >= 0
    fig.add_trace(go.Scatter(
        x=np.concatenate([x_hours, x_hours[::-1]]),
        y=np.concatenate([
            np.where(pos_mask, adjusted, baseline),
            np.where(pos_mask, baseline, baseline)[::-1],
        ]),
        fill="toself",
        fillcolor="rgba(16, 185, 129, 0.2)",
        line=dict(width=0),
        name="Savings area",
        hoverinfo="skip",
        showlegend=True,
    ))

    fig.update_layout(
        title=dict(
            text=f"<b>Demand Forecast</b>  ·  Baseline vs Scenario  ·  Starting {now_label}",
            font=dict(size=16),
        ),
        xaxis_title="Hours from now",
        yaxis_title="Flow rate (L/min)",
        height=420,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(240,249,255,0.6)",
    )
    return fig


def make_cumulative_chart(
    baseline: np.ndarray,
    adjusted: np.ndarray,
    hours: int,
) -> go.Figure:
    n = len(baseline)
    x_hours = np.linspace(0, hours, n)
    secs_per_step = 5.0

    cum_baseline = np.cumsum(baseline * secs_per_step / 60.0)
    cum_adjusted = np.cumsum(adjusted * secs_per_step / 60.0)
    cum_saved    = cum_baseline - cum_adjusted

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_hours, y=cum_baseline / 1000,
        name="Baseline (kL)", line=dict(color="#94a3b8", width=2, dash="dot"),
    ))
    fig.add_trace(go.Scatter(
        x=x_hours, y=cum_adjusted / 1000,
        name="Scenario (kL)", line=dict(color="#0284c7", width=3),
        fill="tonexty", fillcolor="rgba(16,185,129,0.15)",
    ))
    fig.add_trace(go.Scatter(
        x=x_hours, y=cum_saved / 1000,
        name="Cumulative savings (kL)",
        line=dict(color="#10b981", width=2),
        yaxis="y2",
    ))

    fig.update_layout(
        title="<b>Cumulative Water Volume</b>",
        xaxis_title="Hours from now",
        yaxis=dict(title="Volume (kL)", side="left"),
        yaxis2=dict(title="Savings (kL)", overlaying="y", side="right",
                    showgrid=False, zeroline=True,
                    zerolinecolor="#10b981"),
        height=350,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(240,249,255,0.6)",
    )
    return fig


def kpi_card(label: str, value: str, unit: str = "", colour: str = "#0284c7") -> None:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <span class="kpi-value" style="color:{colour};">{value}</span>
        <span class="kpi-unit"> {unit}</span>
    </div>
    """, unsafe_allow_html=True)


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    st.markdown('<h1 class="page-title">🔧 What-If Demand & Savings Simulator</h1>',
                unsafe_allow_html=True)
    st.markdown(
        "Adjust the scenario sliders to see how operational changes would reshape "
        "the LSTM demand forecast and calculate projected water / cost / CO₂ savings.",
        unsafe_allow_html=False,
    )

    # ── Sidebar: scenario controls ──────────────────────────────────────────
    with st.sidebar:
        st.markdown("## Scenario Controls")

        zone = st.selectbox(
            "Zone / Area",
            ["Zone-1", "Zone-2", "Zone-3", "Zone-4", "Zone-5",
             "Residential Block A", "Industrial Block B", "Agricultural Sector C"],
            index=0,
        )

        st.markdown("---")
        st.markdown("### Demand Levers")

        irrigation_cut = st.slider(
            "Reduce irrigation by",
            min_value=0, max_value=60, value=20, step=5, format="%d%%",
            help="Percentage reduction applied to irrigation schedule during the chosen horizon.",
        )
        industrial_cut = st.slider(
            "Industrial curtailment",
            min_value=0, max_value=40, value=0, step=5, format="%d%%",
            help="Temporary reduction in industrial water draw.",
        )
        leak_recovery = st.slider(
            "Leak repair recovery",
            min_value=0, max_value=30, value=0, step=5, format="%d%%",
            help="Percentage of flow recovered by repairing detected leaks "
                 "(adds water back into the supply, reducing apparent demand deficit).",
        )

        st.markdown("---")
        st.markdown("### Horizon & Economics")

        horizon_hours = st.slider(
            "Intervention horizon (hours)",
            min_value=1, max_value=24, value=8, step=1,
            help="How many hours ahead the demand-reduction measures are applied.",
        )
        total_hours = st.slider(
            "Forecast window (hours)",
            min_value=6, max_value=24, value=24, step=6,
        )
        cost_per_kl = st.number_input(
            "Water tariff (₹ per kL)",
            min_value=0.5, max_value=50.0, value=float(COST_PER_1000L), step=0.5,
            format="%.2f",
        )
        co2_per_kl = st.number_input(
            "CO₂ factor (kg per kL pumped)",
            min_value=0.0, max_value=5.0, value=float(KG_CO2_PER_1000L), step=0.05,
            format="%.3f",
        )

        st.markdown("---")
        refresh = st.button("🔄 Refresh forecast", use_container_width=True)
        if refresh:
            st.cache_data.clear()

    # ── Load / compute ───────────────────────────────────────────────────────
    with st.spinner("Loading LSTM forecast…"):
        baseline_raw = load_baseline_forecast(hours=total_hours)

    if not baseline_raw:
        st.warning("No forecast data available. Make sure the simulator is running "
                   "and the DB has at least 50 sensor readings.")
        st.code("python simulator/sensor_simulator.py", language="bash")
        return

    baseline = np.array(baseline_raw, dtype=float)
    n_steps  = len(baseline)

    # Map horizon_hours → steps (proportional to total_hours)
    horizon_steps = max(1, int(horizon_hours / total_hours * n_steps))

    adjusted = apply_scenario(
        baseline, irrigation_cut, industrial_cut, leak_recovery, horizon_steps
    )

    savings = compute_savings(baseline, adjusted, cost_per_kl, co2_per_kl)

    # ── KPI row ──────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Scenario Impact Summary</div>',
                unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    sv = savings["saved_litres"]
    pct = savings["pct_change"]
    colour_sv = "#10b981" if sv >= 0 else "#dc2626"
    sign      = "" if sv < 0 else "+"

    with col1:
        kpi_card(
            "Water saved",
            f"{sign}{sv:,.0f}",
            "L",
            colour=colour_sv,
        )
    with col2:
        kpi_card(
            "Cost saving",
            f"{sign}₹{savings['saved_cost']:,.2f}",
            f"({sign}{pct:.1f}%)",
            colour=colour_sv,
        )
    with col3:
        kpi_card(
            "CO₂ reduction",
            f"{sign}{savings['saved_co2']:,.2f}",
            "kg CO₂",
            colour=colour_sv,
        )
    with col4:
        kpi_card(
            "Peak adjusted flow",
            f"{float(adjusted.max()):,.1f}",
            "L/min",
            colour="#0284c7",
        )

    # ── Charts ───────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Forecast Charts</div>',
                unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Demand Forecast", "Cumulative Volume"])

    with tab1:
        st.plotly_chart(
            make_forecast_chart(baseline, adjusted, horizon_steps, total_hours),
            use_container_width=True,
        )

    with tab2:
        st.plotly_chart(
            make_cumulative_chart(baseline, adjusted, total_hours),
            use_container_width=True,
        )

    # ── Hourly breakdown table ────────────────────────────────────────────────
    with st.expander("Hourly breakdown table", expanded=False):
        steps_per_h = max(1, n_steps // total_hours)
        rows = []
        for h in range(total_hours):
            sl = slice(h * steps_per_h, (h + 1) * steps_per_h)
            b_mean = float(baseline[sl].mean()) if len(baseline[sl]) else 0
            a_mean = float(adjusted[sl].mean()) if len(adjusted[sl]) else 0
            secs   = len(baseline[sl]) * 5.0
            b_vol  = b_mean * secs / 60.0
            a_vol  = a_mean * secs / 60.0
            rows.append({
                "Hour":               f"H+{h+1:02d}",
                "Baseline (L/min)":   round(b_mean, 2),
                "Scenario (L/min)":   round(a_mean, 2),
                "Baseline vol (L)":   round(b_vol, 0),
                "Scenario vol (L)":   round(a_vol, 0),
                "Saved (L)":          round(b_vol - a_vol, 0),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

    # ── Recommendations ───────────────────────────────────────────────────────
    st.markdown('<div class="section-header">AI Recommendations for This Scenario</div>',
                unsafe_allow_html=True)

    engine = get_engine()
    recs = engine.recommend_from_model_outputs(
        zone=zone,
        forecast=list(adjusted),
    )

    if not recs:
        st.success("No alerts for this scenario — system within normal operating range.")
    else:
        for rec in recs:
            pri   = rec.get("priority", "MEDIUM")
            cls   = {"HIGH": "rec-high", "MEDIUM": "rec-medium", "LOW": "rec-low"}.get(pri, "rec-medium")
            icon  = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(pri, "🟡")
            st.markdown(f"""
            <div class="rec-card {cls}">
                <strong>{icon} [{pri}] {rec.get('category','').replace('_',' ').title()}</strong><br>
                {rec.get('message','')}<br>
                <em>Action:</em> {rec.get('recommended_action','')}<br>
                <em>Impact:</em> <strong>{rec.get('estimated_impact','')}</strong>
            </div>
            """, unsafe_allow_html=True)

    # ── Current stats sidebar card ────────────────────────────────────────────
    stats = load_recent_stats()
    if stats and stats.get("n", 0) > 0:
        with st.sidebar:
            st.markdown("---")
            st.markdown("### Live DB snapshot")
            st.caption(f"{stats['n']} readings in last-hour window")
            st.metric("Avg flow",     f"{stats['avg_flow']} L/min")
            st.metric("Avg pressure", f"{stats['avg_pressure']} bar")
            st.metric("Avg pH",       f"{stats['avg_ph']}")
            st.metric("Avg turbidity",f"{stats['avg_turbidity']} NTU")


if __name__ == "__main__":
    main()
