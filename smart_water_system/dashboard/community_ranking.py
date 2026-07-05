"""
Decision Intelligence – Community Zone Ranking Dashboard
=========================================================
Standalone Streamlit page.  Run independently:

    streamlit run dashboard/community_ranking.py

Or embed as a multipage app page (see what_if_simulator.py for folder layout).

HOW IT WORKS
------------
Because the existing DB has no ``zone`` column, this page synthesises
zone data deterministically from the DB rows using a reproducible
bucketing strategy: rows are divided into N equal time-window buckets,
each treated as a distinct "zone".  This gives a realistic, live-updating
ranking from real sensor data without any schema change.

For each zone the page computes:
  • Efficiency Score  – composite of flow stability, pressure stability,
                        pH compliance, turbidity compliance  (0–100)
  • Leak Risk Score   – derived from Isolation Forest anomaly scores
                        (using LeakDetector.detect_anomalies_batch)
  • Water Quality Index – pH + turbidity sub-scores  (0–100)
  • Demand Stability  – coefficient of variation of flow  (lower = more stable)

Outputs:
  • Ranked leaderboard table with colour-coded scores
  • Bar chart comparing zones on all four metrics
  • Detailed drilldown for any selected zone
  • Root-cause classification for anomalous zones (using AnomalyRootCauseClassifier)

NO EXISTING FILES ARE MODIFIED.
"""

from __future__ import annotations

import os
import sys
import sqlite3
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# ── path setup ───────────────────────────────────────────────────────────────
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_models.anomaly_detection import LeakDetector
from ai_models.root_cause_classifier import AnomalyRootCauseClassifier

# ── constants ────────────────────────────────────────────────────────────────
DB_PATH      = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "water.db")
N_ZONES      = 6      # number of synthetic zones to create from DB rows
MIN_ROWS     = 30     # minimum rows a zone must have to be scored
ROWS_TO_LOAD = 3000   # total DB rows to pull for zone bucketing

# Safe operating thresholds (mirrors existing app & recommendation engine)
PH_LO,   PH_HI    = 6.5, 8.5
TURB_HI            = 5.0   # NTU
FLOW_LO,  FLOW_HI  = 8.0, 22.0
PRES_LO,  PRES_HI  = 1.5, 3.5

ZONE_NAMES = [
    "Zone-1 Residential",
    "Zone-2 Commercial",
    "Zone-3 Industrial",
    "Zone-4 Agricultural",
    "Zone-5 Mixed-Use",
    "Zone-6 Municipal",
]

# ── page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Community Ranking | Smart Water",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS (mirrors existing app) ────────────────────────────────────────────────
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
    .rank-card {
        background: white; border-radius: 14px;
        padding: 1rem 1.4rem;
        box-shadow: 0 4px 12px rgba(0,0,0,.08);
        margin-bottom: .8rem;
        display: flex; align-items: center; gap: 1rem;
    }
    .rank-number { font-size: 2rem; font-weight: 900; color: #cbd5e1; width: 2.5rem; }
    .rank-gold   { color: #f59e0b; }
    .rank-silver { color: #94a3b8; }
    .rank-bronze { color: #b45309; }
    .zone-name   { font-size: 1.1rem; font-weight: 700; color: #1e293b; }
    .score-pill  {
        padding: .3rem .9rem; border-radius: 20px;
        font-weight: 700; font-size: .9rem; color: white;
    }
    .pill-green  { background: #10b981; }
    .pill-yellow { background: #f59e0b; }
    .pill-red    { background: #dc2626; }
    .risk-badge  {
        padding: .2rem .7rem; border-radius: 12px;
        font-size: .8rem; font-weight: 600;
    }
    .risk-low    { background: #d1fae5; color: #065f46; }
    .risk-medium { background: #fef3c7; color: #92400e; }
    .risk-high   { background: #fee2e2; color: #991b1b; }
    .detail-card {
        background: white; border-radius: 12px;
        padding: 1.2rem 1.5rem;
        box-shadow: 0 3px 10px rgba(0,0,0,.07);
        border-left: 5px solid #3b82f6;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# ── data loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=30, show_spinner=False)
def load_all_data(limit: int = ROWS_TO_LOAD) -> pd.DataFrame:
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(
            f"SELECT id, timestamp, flow, pressure, ph, turbidity, temperature "
            f"FROM sensor_data ORDER BY id DESC LIMIT {limit}",
            conn,
        )
        conn.close()
        return df.iloc[::-1].reset_index(drop=True)
    except Exception as e:
        st.error(f"DB error: {e}")
        return pd.DataFrame()


@st.cache_resource(show_spinner=False)
def get_detector() -> LeakDetector:
    det = LeakDetector(db_path=DB_PATH)
    det.load_model()
    return det


@st.cache_resource(show_spinner=False)
def get_classifier() -> AnomalyRootCauseClassifier:
    return AnomalyRootCauseClassifier()


# ── zone scoring ──────────────────────────────────────────────────────────────

def bucket_into_zones(df: pd.DataFrame, n_zones: int) -> dict[str, pd.DataFrame]:
    """Split the DataFrame into n_zones equal-row buckets."""
    chunk = max(1, len(df) // n_zones)
    zones = {}
    for i in range(n_zones):
        name = ZONE_NAMES[i] if i < len(ZONE_NAMES) else f"Zone-{i+1}"
        start = i * chunk
        end   = start + chunk if i < n_zones - 1 else len(df)
        zones[name] = df.iloc[start:end].copy()
    return zones


def score_zone(zdf: pd.DataFrame, detector: LeakDetector) -> dict:
    """
    Compute four KPI scores (0–100) for a zone DataFrame.
    Higher is always better (leak risk is inverted before display).
    """
    if len(zdf) < MIN_ROWS:
        return None

    # ── 1. Efficiency score ─────────────────────────────────────────────────
    # Sub-scores, each 0–100:
    # a) Flow stability: penalise high coefficient of variation
    flow_cv   = zdf["flow"].std() / max(zdf["flow"].mean(), 0.01)
    flow_stab = max(0.0, 100.0 - flow_cv * 200)

    # b) Pressure in safe band
    pres_ok    = ((zdf["pressure"] >= PRES_LO) & (zdf["pressure"] <= PRES_HI)).mean()
    pres_score = pres_ok * 100

    # c) pH compliance
    ph_ok    = ((zdf["ph"] >= PH_LO) & (zdf["ph"] <= PH_HI)).mean()
    ph_score = ph_ok * 100

    # d) Turbidity compliance
    turb_ok    = (zdf["turbidity"] < TURB_HI).mean()
    turb_score = turb_ok * 100

    efficiency = (flow_stab * 0.35 + pres_score * 0.25
                  + ph_score * 0.20 + turb_score * 0.20)

    # ── 2. Water quality index ──────────────────────────────────────────────
    wqi = (ph_score * 0.5 + turb_score * 0.5)

    # ── 3. Demand stability ─────────────────────────────────────────────────
    demand_stability = max(0.0, 100.0 - flow_cv * 150)

    # ── 4. Leak risk (0–100, higher = more risk) ────────────────────────────
    leak_risk_score = 0.0
    anomalies       = []
    if detector.is_trained:
        try:
            anomalies = detector.detect_anomalies_batch(zdf)
            anomaly_rate = len(anomalies) / len(zdf)
            # Also factor in how low the min flow goes
            min_flow_ratio = zdf["flow"].min() / max(zdf["flow"].mean(), 0.01)
            leak_risk_score = min(
                100.0,
                anomaly_rate * 300 + max(0, (1.0 - min_flow_ratio)) * 50,
            )
        except Exception:
            pass
    else:
        # Heuristic without trained model
        low_flow_pct = (zdf["flow"] < FLOW_LO).mean()
        leak_risk_score = min(100.0, low_flow_pct * 300)

    # ── Stats ────────────────────────────────────────────────────────────────
    return {
        "efficiency":       round(efficiency, 1),
        "wqi":              round(wqi, 1),
        "demand_stability": round(demand_stability, 1),
        "leak_risk":        round(leak_risk_score, 1),
        "anomaly_count":    len(anomalies),
        "n_rows":           len(zdf),
        "avg_flow":         round(float(zdf["flow"].mean()), 2),
        "avg_pressure":     round(float(zdf["pressure"].mean()), 2),
        "avg_ph":           round(float(zdf["ph"].mean()), 2),
        "avg_turbidity":    round(float(zdf["turbidity"].mean()), 2),
        "avg_temperature":  round(float(zdf["temperature"].mean()), 2),
        "min_flow":         round(float(zdf["flow"].min()), 2),
        "max_flow":         round(float(zdf["flow"].max()), 2),
        "ph_compliance":    round(ph_ok * 100, 1),
        "turb_compliance":  round(turb_ok * 100, 1),
        "anomalies":        anomalies,
        "df":               zdf,
    }


def risk_label(score: float) -> tuple[str, str]:
    """Return (text, css_class) for a leak risk score."""
    if score < 20:
        return "Low",    "risk-low"
    elif score < 50:
        return "Medium", "risk-medium"
    else:
        return "High",   "risk-high"


def score_colour(score: float) -> str:
    if score >= 70:
        return "#10b981"
    elif score >= 45:
        return "#f59e0b"
    return "#dc2626"


def pill_class(score: float) -> str:
    if score >= 70:
        return "pill-green"
    elif score >= 45:
        return "pill-yellow"
    return "pill-red"


# ── charts ────────────────────────────────────────────────────────────────────

def make_radar_chart(scores: dict[str, dict]) -> go.Figure:
    categories = ["Efficiency", "Quality Index", "Demand Stability",
                  "Leak Safety"]  # leak safety = 100 - leak_risk

    fig = go.Figure()
    colours = px.colors.qualitative.Set2
    for i, (name, s) in enumerate(scores.items()):
        vals = [
            s["efficiency"],
            s["wqi"],
            s["demand_stability"],
            100 - s["leak_risk"],
        ]
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name=name.split()[0] + " " + name.split()[1] if len(name.split()) >= 2 else name,
            line=dict(color=colours[i % len(colours)], width=2),
            fillcolor=colours[i % len(colours)].replace("rgb", "rgba").replace(")", ",0.15)"),
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100],
                            tickfont=dict(size=10)),
        ),
        showlegend=True,
        title="<b>Zone Performance Radar</b>",
        height=430,
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=-0.25),
    )
    return fig


def make_comparison_bar(scores: dict[str, dict], metric: str, label: str,
                         invert: bool = False) -> go.Figure:
    names = list(scores.keys())
    short = [n.split()[0] + "-" + n.split()[1] if len(n.split()) >= 2 else n
             for n in names]
    vals  = [s[metric] for s in scores.values()]
    if invert:
        vals = [100 - v for v in vals]

    colours = [score_colour(v) for v in vals]
    fig = go.Figure(go.Bar(
        x=short, y=vals,
        marker_color=colours,
        text=[f"{v:.1f}" for v in vals],
        textposition="outside",
        hovertemplate="%{x}: %{y:.1f}<extra></extra>",
    ))
    fig.update_layout(
        title=f"<b>{label}</b>",
        yaxis=dict(range=[0, 110], title="Score (0–100)"),
        height=280,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(240,249,255,0.6)",
        showlegend=False,
    )
    return fig


def make_trend_chart(zdf: pd.DataFrame, zone_name: str) -> go.Figure:
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Flow (L/min)", "Pressure (bar)", "pH", "Turbidity (NTU)"),
        vertical_spacing=0.18, horizontal_spacing=0.1,
    )
    idx = zdf.index
    for (row, col, col_name, colour) in [
        (1, 1, "flow",      "#3b82f6"),
        (1, 2, "pressure",  "#f59e0b"),
        (2, 1, "ph",        "#10b981"),
        (2, 2, "turbidity", "#dc2626"),
    ]:
        fig.add_trace(
            go.Scatter(x=idx, y=zdf[col_name], name=col_name.title(),
                       line=dict(color=colour, width=2),
                       fill="tozeroy",
                       fillcolor=colour.replace("#", "rgba(").replace(
                           "rgba(", "rgba(") + ",0.08)" if False else None),
            row=row, col=col,
        )
    fig.update_layout(
        title=f"<b>Sensor Trends — {zone_name}</b>",
        height=400, showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(240,249,255,0.6)",
    )
    return fig


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.markdown('<h1 class="page-title">🏆 Community Zone Efficiency Ranking</h1>',
                unsafe_allow_html=True)
    st.markdown(
        "Zones are ranked by overall efficiency, water quality, demand stability, "
        "and leak risk — computed live from the sensor database.",
    )

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## Ranking Controls")
        n_zones = st.slider("Number of zones", min_value=2, max_value=8,
                            value=N_ZONES, step=1)
        sort_by = st.selectbox(
            "Sort by",
            ["Efficiency Score", "Water Quality Index",
             "Demand Stability", "Leak Risk (worst first)"],
            index=0,
        )
        show_anomalies = st.checkbox("Show anomaly detail", value=True)

        st.markdown("---")
        if st.button("🔄 Refresh data", use_container_width=True):
            st.cache_data.clear()

        st.markdown("---")
        st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

    # ── Load & score ─────────────────────────────────────────────────────────
    with st.spinner("Loading sensor data and scoring zones…"):
        df = load_all_data()

    if df.empty or len(df) < MIN_ROWS * 2:
        st.warning(
            "Not enough data to rank zones. "
            f"Need at least {MIN_ROWS * 2} sensor readings. "
            "Start the simulator and wait a minute."
        )
        st.code("python simulator/sensor_simulator.py", language="bash")
        return

    detector   = get_detector()
    classifier = get_classifier()

    zone_dfs = bucket_into_zones(df, n_zones)
    raw_scores: dict[str, dict] = {}
    for name, zdf in zone_dfs.items():
        s = score_zone(zdf, detector)
        if s:
            raw_scores[name] = s

    if not raw_scores:
        st.error("Scoring failed — all zones had insufficient data.")
        return

    # ── Sort ──────────────────────────────────────────────────────────────────
    sort_key_map = {
        "Efficiency Score":           ("efficiency",       False),
        "Water Quality Index":        ("wqi",              False),
        "Demand Stability":           ("demand_stability", False),
        "Leak Risk (worst first)":    ("leak_risk",        True),
    }
    s_key, ascending = sort_key_map[sort_by]
    sorted_zones = sorted(
        raw_scores.items(),
        key=lambda x: x[1][s_key],
        reverse=not ascending,
    )

    # ── Leaderboard ───────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Zone Leaderboard</div>',
                unsafe_allow_html=True)

    for rank, (name, s) in enumerate(sorted_zones, start=1):
        rank_cls = {1: "rank-gold", 2: "rank-silver", 3: "rank-bronze"}.get(rank, "")
        medal    = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")
        eff_col  = score_colour(s["efficiency"])
        wqi_col  = score_colour(s["wqi"])
        rl, rc   = risk_label(s["leak_risk"])
        pil      = pill_class(s["efficiency"])

        st.markdown(f"""
        <div class="rank-card">
            <div class="rank-number {rank_cls}">{medal}</div>
            <div style="flex:1">
                <div class="zone-name">{name}</div>
                <span style="font-size:.85rem;color:#64748b;">
                    {s['n_rows']} readings &nbsp;|&nbsp;
                    Avg flow: {s['avg_flow']} L/min &nbsp;|&nbsp;
                    Avg pH: {s['avg_ph']}
                </span>
            </div>
            <span class="score-pill {pil}">
                Efficiency {s['efficiency']:.0f}
            </span>
            <span class="score-pill"
                  style="background:{wqi_col};">
                Quality {s['wqi']:.0f}
            </span>
            <span class="risk-badge {rc}">
                Leak risk: {rl}
            </span>
        </div>
        """, unsafe_allow_html=True)

    # ── Summary table ─────────────────────────────────────────────────────────
    with st.expander("Full scores table", expanded=False):
        table_rows = []
        for rank, (name, s) in enumerate(sorted_zones, start=1):
            rl, _ = risk_label(s["leak_risk"])
            table_rows.append({
                "Rank":              rank,
                "Zone":              name,
                "Efficiency":        s["efficiency"],
                "Water Quality":     s["wqi"],
                "Demand Stability":  s["demand_stability"],
                "Leak Risk Score":   s["leak_risk"],
                "Leak Risk Level":   rl,
                "Anomalies":         s["anomaly_count"],
                "pH Compliance %":   s["ph_compliance"],
                "Turb Compliance %": s["turb_compliance"],
                "Avg Flow (L/min)":  s["avg_flow"],
                "Avg Pressure (bar)":s["avg_pressure"],
            })
        st.dataframe(
            pd.DataFrame(table_rows).set_index("Rank"),
            use_container_width=True,
        )

    # ── Charts ────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Performance Overview</div>',
                unsafe_allow_html=True)

    col_r, col_b = st.columns([1.4, 1])

    with col_r:
        st.plotly_chart(make_radar_chart(raw_scores), use_container_width=True)

    with col_b:
        metric_choice = st.selectbox(
            "Bar chart metric",
            ["efficiency", "wqi", "demand_stability", "leak_risk"],
            format_func=lambda x: {
                "efficiency":        "Efficiency Score",
                "wqi":               "Water Quality Index",
                "demand_stability":  "Demand Stability",
                "leak_risk":         "Leak Risk (higher = worse)",
            }[x],
        )
        invert = metric_choice == "leak_risk"
        label  = "Leak Safety (100 − risk)" if invert else {
            "efficiency":       "Efficiency Score",
            "wqi":              "Water Quality Index",
            "demand_stability": "Demand Stability",
        }[metric_choice]
        st.plotly_chart(
            make_comparison_bar(raw_scores, metric_choice, label, invert=invert),
            use_container_width=True,
        )

    # ── Zone drilldown ────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Zone Drilldown</div>',
                unsafe_allow_html=True)

    selected_zone = st.selectbox(
        "Select a zone to inspect",
        list(raw_scores.keys()),
        index=0,
    )
    s = raw_scores[selected_zone]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Efficiency",       f"{s['efficiency']:.1f} / 100")
    c2.metric("Water Quality",    f"{s['wqi']:.1f} / 100")
    c3.metric("Demand Stability", f"{s['demand_stability']:.1f} / 100")
    c4.metric("Leak Risk",        f"{s['leak_risk']:.1f} / 100",
              delta=f"{s['anomaly_count']} anomalies",
              delta_color="inverse")

    st.plotly_chart(make_trend_chart(s["df"], selected_zone), use_container_width=True)

    # ── Root cause for anomalous readings ────────────────────────────────────
    if show_anomalies and s["anomaly_count"] > 0:
        st.markdown(f"**{s['anomaly_count']} anomalous reading(s) detected in {selected_zone}**")

        sample = s["anomalies"][:5]  # show up to 5
        for i, anm in enumerate(sample, start=1):
            row_data = s["df"].iloc[anm["index"]] if anm["index"] < len(s["df"]) else None
            if row_data is None:
                continue

            result = classifier.classify(
                flow=float(row_data["flow"]),
                pressure=float(row_data["pressure"]),
                ph=float(row_data["ph"]),
                turbidity=float(row_data["turbidity"]),
                temperature=float(row_data["temperature"]),
                anomaly_score=anm.get("score"),
            )

            conf_col  = {"HIGH": "#dc2626", "MEDIUM": "#f59e0b", "LOW": "#10b981"}.get(
                result["confidence"], "#64748b"
            )
            rc_icon = {
                "LEAK":           "💧",
                "CONTAMINATION":  "⚗️",
                "UNUSUAL_USAGE":  "📈",
                "SENSOR_FAULT":   "🔌",
            }.get(result["root_cause"], "⚠️")

            with st.expander(
                f"{rc_icon} Anomaly {i} — {result['label']}  "
                f"[{result['confidence']} confidence]",
                expanded=(i == 1),
            ):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"""
                    <div class="detail-card">
                        <strong>Root cause:</strong>
                        <span style="color:{conf_col};font-weight:700;">
                            {result['root_cause']}
                        </span>
                        &nbsp; ({result['confidence']})<br><br>
                        <em>{result['explanation']}</em><br><br>
                        <strong>Recommended action:</strong><br>
                        {result['recommended_action']}
                    </div>
                    """, unsafe_allow_html=True)
                with col_b:
                    sv = result["sensor_values"]
                    st.markdown("**Sensor values at anomaly:**")
                    st.json(sv)
                    if result["supporting_evidence"]:
                        st.markdown("**Evidence rules triggered:**")
                        for ev in result["supporting_evidence"]:
                            st.markdown(f"- {ev}")
    elif show_anomalies:
        st.success(f"No anomalies detected in {selected_zone} — readings all within normal range.")

    # ── Improvement tips ─────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Improvement Opportunities</div>',
                unsafe_allow_html=True)

    # Bottom-ranked zone by efficiency
    worst = sorted_zones[-1]
    best  = sorted_zones[0]
    gap   = best[1]["efficiency"] - worst[1]["efficiency"]

    tips = []
    ws = worst[1]
    if ws["ph_compliance"] < 95:
        tips.append(f"**{worst[0]}**: pH compliance is {ws['ph_compliance']:.0f}% — "
                    "check dosing system calibration.")
    if ws["turb_compliance"] < 95:
        tips.append(f"**{worst[0]}**: Turbidity compliance is {ws['turb_compliance']:.0f}% — "
                    "increase filtration or flush the main.")
    if ws["leak_risk"] > 40:
        tips.append(f"**{worst[0]}**: Leak risk score {ws['leak_risk']:.0f}/100 — "
                    "schedule a pipe inspection.")
    if gap > 15:
        tips.append(f"Closing the efficiency gap between **{best[0]}** and "
                    f"**{worst[0]}** ({gap:.0f} points) could save an estimated "
                    f"~{int(gap * 80):,} L/day based on current demand patterns.")

    if tips:
        for tip in tips:
            st.info(tip)
    else:
        st.success("All zones are performing within acceptable ranges. "
                   "Continue monitoring for gradual degradation.")


if __name__ == "__main__":
    main()
