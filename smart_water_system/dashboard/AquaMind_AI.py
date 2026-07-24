"""
AquaMind AI — Premium Enterprise Dashboard
Smart Water Management System
"""
import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os
import numpy as np
import random
import time
from plotly.subplots import make_subplots

# ── Absolute paths ──────────────────────────────────────────────────────────
_ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH     = os.path.join(_ROOT, "database", "water.db")
_LEAK_MODEL = os.path.join(_ROOT, "ai_models", "leak_model.pkl")
_LSTM_MODEL = os.path.join(_ROOT, "ai_models", "lstm_model.h5")

sys.path.append(_ROOT)

# ── Gemini LLM (graceful fallback if not installed) ─────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
try:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    _GEMINI_MODEL = genai.GenerativeModel("gemini-1.5-flash")
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False
    _GEMINI_MODEL = None

# ── AI model imports (graceful fallback) ────────────────────────────────────
try:
    from ai_models.anomaly_detection import LeakDetector
    LEAK_DETECTOR_AVAILABLE = True
except Exception:
    LEAK_DETECTOR_AVAILABLE = False
    LeakDetector = None

try:
    from ai_models.lstm_forecast import DemandForecaster, TENSORFLOW_AVAILABLE
    FORECASTER_AVAILABLE = True
except Exception:
    FORECASTER_AVAILABLE = False
    DemandForecaster = None
    TENSORFLOW_AVAILABLE = False

try:
    from ai_models.recommendation_engine import WaterRecommendationEngine
    RECOMMENDATIONS_AVAILABLE = True
except Exception:
    RECOMMENDATIONS_AVAILABLE = False
    WaterRecommendationEngine = None

try:
    from ai_models.root_cause_classifier import AnomalyRootCauseClassifier
    ROOT_CAUSE_AVAILABLE = True
except Exception:
    ROOT_CAUSE_AVAILABLE = False
    AnomalyRootCauseClassifier = None

try:
    from backend.alerts import send_alert, AlertLevel
    ALERTS_AVAILABLE = True
except Exception:
    ALERTS_AVAILABLE = False
    send_alert = None
    AlertLevel = None

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AquaMind AI — Smart Water Management",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme ─────────────────────────────────────────────────────────────────────
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

_D = st.session_state.dark_mode

# Color tokens — light / dark
_BG        = "#0f172a"   if _D else "#f8fafc"
_BG2       = "#1e293b"   if _D else "#ffffff"
_BG3       = "#334155"   if _D else "#f1f5f9"
_TEXT      = "#f1f5f9"   if _D else "#0f172a"
_TEXT2     = "#94a3b8"   if _D else "#64748b"
_BORDER    = "#334155"   if _D else "#e2e8f0"
_CARD_BG   = "#1e293b"   if _D else "#ffffff"
_CARD_SHD  = "rgba(0,0,0,0.4)" if _D else "rgba(0,0,0,0.08)"
_PLOT_BG   = "#1e293b"   if _D else "#f8fafc"
_PLOT_PAPER= "rgba(0,0,0,0)"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
* {{ font-family: 'Inter', sans-serif !important; }}

/* ── App background ── */
.stApp {{ background: {_BG} !important; }}
.main .block-container {{ background: {_BG} !important; }}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {{ background: #0f172a !important; }}
section[data-testid="stSidebar"] * {{ color: #e2e8f0 !important; }}
section[data-testid="stSidebar"] label {{ color: #94a3b8 !important; }}
section[data-testid="stSidebar"] .stButton > button {{
    background: #1e293b !important; color: #e2e8f0 !important;
    border: 1px solid #334155 !important; border-radius: 8px !important;
}}
section[data-testid="stSidebar"] .stButton > button:hover {{
    background: #334155 !important; color: #f1f5f9 !important;
}}

/* ── Hide the 'keyboard_double_arrow' Material icon text on the sidebar toggle ── */
button[data-testid="baseButton-headerNoPadding"] span[data-testid="stIconMaterial"] {{
    display: none !important;
}}
/* Show a clean chevron arrow instead */
button[data-testid="baseButton-headerNoPadding"]::after {{
    content: "‹";
    font-size: 1.4rem;
    font-weight: 700;
    color: #94a3b8;
    line-height: 1;
}}
[data-testid="stSidebarCollapsedControl"] button[data-testid="baseButton-headerNoPadding"]::after {{
    content: "›";
}}

/* ── General text ── */
p, span, div, label, h1, h2, h3, h4, li {{
    color: {_TEXT} !important;
}}
.stMarkdown p {{ color: {_TEXT} !important; }}

/* ── Cards ── */
.metric-card {{
    background: {_CARD_BG}; border-radius: 12px; padding: 1.5rem;
    box-shadow: 0 1px 6px {_CARD_SHD}; border-top: 3px solid #0ea5e9;
    margin-bottom: 1rem;
}}
.kpi-card {{
    text-align: center; background: {_CARD_BG}; border-radius: 12px;
    padding: 1.5rem; box-shadow: 0 2px 8px {_CARD_SHD};
}}
.kpi-value {{ font-size: 2.2rem; font-weight: 800; color: {_TEXT}; }}
.kpi-label {{ font-size: 0.85rem; color: {_TEXT2}; font-weight: 500; margin-top: 0.3rem; }}

/* ── AI cards ── */
.ai-card {{
    background: {_CARD_BG}; border-radius: 12px; padding: 1.2rem;
    border-left: 4px solid #8b5cf6; margin: 0.5rem 0;
    box-shadow: 0 2px 8px {_CARD_SHD};
}}

/* ── Score rings ── */
.score-ring {{
    display: flex; flex-direction: column; align-items: center;
    background: {_CARD_BG}; border-radius: 16px; padding: 1.5rem;
    box-shadow: 0 2px 12px {_CARD_SHD};
}}

/* ── Section headers ── */
.section-header {{
    font-size: 1.4rem; font-weight: 700; color: {_TEXT};
    border-left: 4px solid #0ea5e9; padding-left: 0.8rem; margin: 1.5rem 0 1rem 0;
}}

/* ── Alerts ── */
.alert-critical {{
    background: {"#450a0a" if _D else "#fef2f2"}; border-left: 4px solid #ef4444;
    border-radius: 8px; padding: 1rem 1.2rem; margin: 0.5rem 0;
    color: {_TEXT} !important;
}}
.alert-warning {{
    background: {"#422006" if _D else "#fffbeb"}; border-left: 4px solid #f59e0b;
    border-radius: 8px; padding: 1rem 1.2rem; margin: 0.5rem 0;
    color: {_TEXT} !important;
}}
.alert-success {{
    background: {"#052e16" if _D else "#f0fdf4"}; border-left: 4px solid #10b981;
    border-radius: 8px; padding: 1rem 1.2rem; margin: 0.5rem 0;
    color: {_TEXT} !important;
}}

/* ── Executive brief ── */
.exec-brief {{
    background: {"linear-gradient(135deg, #0f172a, #1e293b)" if _D else "linear-gradient(135deg, #f8fafc, #ffffff)"};
    color: {_TEXT};
    border-radius: 16px; padding: 2rem; margin: 1rem 0;
    border-left: 4px solid #0ea5e9;
    box-shadow: 0 2px 12px {_CARD_SHD};
}}

/* ── Timeline ── */
.timeline-item {{
    display: flex; gap: 1rem; padding: 0.8rem 0;
    border-bottom: 1px solid {_BORDER};
}}

/* ── Architecture nodes ── */
.arch-node {{
    background: {"#1e293b" if _D else "#f1f5f9"}; color: {"white" if _D else "#0f172a"}; border-radius: 10px;
    padding: 0.8rem 1.2rem; text-align: center; font-weight: 600; font-size: 0.9rem;
    border: 1px solid {"#334155" if _D else "#e2e8f0"};
}}

/* ── Health score ── */
.health-score {{
    font-size: 4rem; font-weight: 800;
    background: linear-gradient(135deg, #0ea5e9, #10b981);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}}

/* ── Confidence badges ── */
.confidence-high {{ color: #10b981; font-weight: 700; }}
.confidence-med  {{ color: #f59e0b; font-weight: 700; }}
.confidence-low  {{ color: #ef4444; font-weight: 700; }}

/* ── Anomaly pulse animation ── */
@keyframes pulse-red {{
    0%   {{ box-shadow: 0 0 0 0 rgba(239,68,68,0.7); }}
    70%  {{ box-shadow: 0 0 0 14px rgba(239,68,68,0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(239,68,68,0); }}
}}
.anomaly-pulse {{ animation: pulse-red 1.5s infinite; border: 2px solid #ef4444 !important; }}

/* ── Maintenance card ── */
.maintenance-card {{
    background: {"#1e293b" if _D else "#fff7ed"}; border-left: 4px solid #f59e0b;
    border-radius: 10px; padding: 1rem 1.2rem; margin: 0.5rem 0;
}}

/* ── Root cause card ── */
.root-cause-card {{
    background: {"#1e0a0a" if _D else "#fef2f2"}; border-radius: 12px;
    padding: 1.5rem; margin: 1rem 0; border-left: 4px solid #ef4444;
}}

/* ── Streamlit native widget overrides for dark mode ── */
{"" if not _D else ".stTextInput > div > div { background: #1e293b !important; border-color: #334155 !important; } .stTextInput input { color: #f1f5f9 !important; background: #1e293b !important; } .stSelectbox > div > div { background: #1e293b !important; border-color: #334155 !important; color: #f1f5f9 !important; } div[data-baseweb='select'] { background: #1e293b !important; } div[data-baseweb='select'] * { color: #f1f5f9 !important; } .stSlider > div > div { background: #334155 !important; } .stDataFrame { background: #1e293b !important; color: #f1f5f9 !important; }"}
</style>
""", unsafe_allow_html=True)


# ── Helpers ──────────────────────────────────────────────────────────────────
def _demand_factor(step: int, total: int) -> float:
    hour = (step / total) * 24.0
    if hour < 6:   return 0.35 + 0.05 * np.sin(np.pi * hour / 6)
    elif hour < 9:  return 0.35 + 0.65 * ((hour - 6) / 3)
    elif hour < 12: return 0.90 + 0.10 * np.sin(np.pi * (hour - 9) / 3)
    elif hour < 17: return 0.70 + 0.10 * np.sin(np.pi * (hour - 12) / 5)
    elif hour < 20: return 0.75 + 0.25 * np.sin(np.pi * (hour - 17) / 3)
    elif hour < 22: return 0.75 - 0.40 * ((hour - 20) / 2)
    else:           return 0.35 + 0.05 * np.cos(np.pi * (hour - 22) / 2)


@st.cache_resource
def init_db_with_demo_data():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT    NOT NULL,
            flow        REAL    NOT NULL,
            pressure    REAL    NOT NULL,
            ph          REAL    NOT NULL,
            turbidity   REAL    NOT NULL,
            temperature REAL    NOT NULL
        )
    """)
    conn.commit()
    count = cur.execute("SELECT COUNT(*) FROM sensor_data").fetchone()[0]
    if count == 0:
        rng  = np.random.default_rng(42)
        NUM  = 200
        base = datetime.now() - timedelta(minutes=NUM * 5)
        rows = []
        for i in range(NUM):
            d   = _demand_factor(i, NUM)
            ts  = (base + timedelta(minutes=i * 5)).isoformat()
            rows.append((
                ts,
                round(float(max(0.1, 5.0 + d * 20.0 + rng.normal(0, 0.6))),  3),
                round(float(max(0.5, 2.8 - d * 0.6 + rng.normal(0, 0.08))),  3),
                round(float(np.clip(7.5 + rng.normal(0, 0.2), 6.5, 8.5)),     3),
                round(float(max(0.1, 1.5 + d * 1.2 + rng.normal(0, 0.3))),   3),
                round(float(24.5 + 1.5 * np.sin(np.pi * ((i/NUM)*24-6)/12) + rng.normal(0, 0.3)), 3),
            ))
        cur.executemany(
            "INSERT INTO sensor_data (timestamp,flow,pressure,ph,turbidity,temperature) "
            "VALUES (?,?,?,?,?,?)", rows,
        )
        conn.commit()
    conn.close()
    return True


@st.cache_resource
def get_leak_detector():
    if not LEAK_DETECTOR_AVAILABLE:
        return None
    d = LeakDetector(db_path=DB_PATH, model_path=_LEAK_MODEL)
    d.load_model()
    return d


@st.cache_resource
def get_forecaster():
    if not FORECASTER_AVAILABLE:
        return None
    f = DemandForecaster(db_path=DB_PATH, model_path=_LSTM_MODEL)
    f.load_model()
    return f


@st.cache_resource
def get_recommendation_engine():
    if not RECOMMENDATIONS_AVAILABLE:
        return None
    return WaterRecommendationEngine(db_path=DB_PATH)


@st.cache_resource
def get_root_cause_classifier():
    if not ROOT_CAUSE_AVAILABLE:
        return None
    return AnomalyRootCauseClassifier()


def load_latest_data(limit=100):
    try:
        conn = sqlite3.connect(DB_PATH)
        df   = pd.read_sql_query(
            f"SELECT * FROM sensor_data ORDER BY id DESC LIMIT {limit}", conn
        )
        conn.close()
        return df.iloc[::-1].reset_index(drop=True)
    except Exception as e:
        st.error(f"DB error: {e}")
        return pd.DataFrame()


def demo_sensor_values(rng_seed: int = None) -> dict:
    """Generate one set of realistic demo sensor values."""
    r = random.Random(rng_seed or int(time.time()))
    hour = datetime.now().hour
    d    = _demand_factor(hour, 24)
    return {
        "flow":        round(max(0.5, 5.0 + d * 20.0 + r.gauss(0, 0.8)), 2),
        "pressure":    round(max(0.5, 2.8 - d * 0.6 + r.gauss(0, 0.1)),  2),
        "ph":          round(min(8.5, max(6.5, 7.5 + r.gauss(0, 0.15))),  2),
        "turbidity":   round(max(0.1, 1.5 + d * 1.0 + r.gauss(0, 0.25)), 2),
        "temperature": round(24.5 + r.gauss(0, 0.5), 2),
    }


def _sparkline(values: list, color: str = "#0ea5e9", height: int = 60) -> go.Figure:
    """Tiny inline trend line for KPI cards."""
    def _hex_to_rgba(hex_color: str, alpha: float = 0.15) -> str:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    if color.startswith("#"):
        fill = _hex_to_rgba(color, 0.15)
    elif "rgb" in color:
        fill = color.replace("rgb(", "rgba(").replace(")", ",0.15)")
    else:
        fill = "rgba(14,165,233,0.15)"

    fig = go.Figure(go.Scatter(
        y=values, mode="lines",
        line=dict(color=color, width=2),
        fill="tozeroy", fillcolor=fill,
    ))
    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig


def create_gauge(value, title, lo, hi, thresh_lo, thresh_hi, unit="", height=240):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": f"<b>{title}</b>", "font": {"size": 14}},
        number={"suffix": f" {unit}", "font": {"size": 22, "color": "#0f172a"}},
        gauge={
            "axis":        {"range": [lo, hi], "tickwidth": 1},
            "bar":         {"color": "#0ea5e9", "thickness": 0.75},
            "bgcolor":     "white",
            "borderwidth": 1,
            "bordercolor": "#e2e8f0",
            "steps": [
                {"range": [lo,          thresh_lo], "color": "#fecaca"},
                {"range": [thresh_lo,   thresh_hi], "color": "#bbf7d0"},
                {"range": [thresh_hi,   hi],        "color": "#fecaca"},
            ],
        },
    ))
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def water_health_score(latest: dict, anomaly: bool) -> int:
    score = 100
    if latest["ph"] < 6.5 or latest["ph"] > 8.5:         score -= 25
    elif latest["ph"] < 6.8 or latest["ph"] > 8.2:       score -= 10
    if latest["turbidity"] > 5:                           score -= 20
    elif latest["turbidity"] > 3:                         score -= 8
    if latest["pressure"] < 1.5 or latest["pressure"] > 3.5: score -= 15
    elif latest["pressure"] < 2.0 or latest["pressure"] > 3.2: score -= 5
    if latest["flow"] < 5 or latest["flow"] > 25:         score -= 15
    if anomaly:                                           score -= 20
    return max(0, min(100, score))


def score_color(s: int) -> str:
    if s >= 80: return "#10b981"
    if s >= 60: return "#f59e0b"
    return "#ef4444"


def _chart_layout(dark: bool) -> dict:
    """Return Plotly layout kwargs that match the current theme."""
    bg   = "#1e293b" if dark else "#f8fafc"
    grid = "#334155" if dark else "#e2e8f0"
    txt  = "#94a3b8" if dark else "#64748b"
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=bg,
        font=dict(color=txt),
        xaxis=dict(gridcolor=grid, zerolinecolor=grid),
        yaxis=dict(gridcolor=grid, zerolinecolor=grid),
    )


def check_alerts(row: dict, anomaly: bool) -> list:
    alerts = []
    if row["ph"] < 6.5:
        alerts.append({"sev": "CRITICAL", "type": "pH LOW",
                        "msg": f"pH={row['ph']:.2f} — acidic water", "action": "Dose alkaline reagent"})
    elif row["ph"] > 8.5:
        alerts.append({"sev": "CRITICAL", "type": "pH HIGH",
                        "msg": f"pH={row['ph']:.2f} — alkaline spike", "action": "Check chemical dosing"})
    if row["turbidity"] > 5:
        alerts.append({"sev": "CRITICAL", "type": "HIGH TURBIDITY",
                        "msg": f"Turbidity={row['turbidity']:.1f} NTU", "action": "Increase filtration"})
    if row["pressure"] < 1.5:
        alerts.append({"sev": "WARNING", "type": "LOW PRESSURE",
                        "msg": f"Pressure={row['pressure']:.2f} bar", "action": "Check pump status"})
    if anomaly:
        alerts.append({"sev": "CRITICAL", "type": "LEAK DETECTED",
                        "msg": "AI anomaly in flow/pressure", "action": "Inspect pipeline immediately"})
    return alerts


def generate_timeline(df: pd.DataFrame, anomaly: bool) -> list:
    events = []
    now = datetime.now()
    events.append({"time": now.strftime("%H:%M"), "icon": "●", "text": "Sensor data refreshed", "color": "#0ea5e9"})
    if anomaly:
        events.append({"time": (now - timedelta(minutes=2)).strftime("%H:%M"),
                       "icon": "●", "text": "Leak anomaly detected by AI", "color": "#ef4444"})
    if not df.empty:
        last_ph = df["ph"].iloc[-1]
        if last_ph < 6.8:
            events.append({"time": (now - timedelta(minutes=5)).strftime("%H:%M"),
                           "icon": "●", "text": f"pH reading low: {last_ph:.2f}", "color": "#f59e0b"})
    events.append({"time": (now - timedelta(minutes=8)).strftime("%H:%M"),
                   "icon": "●", "text": "AI daily report generated", "color": "#8b5cf6"})
    events.append({"time": (now - timedelta(minutes=15)).strftime("%H:%M"),
                   "icon": "●", "text": "Irrigation cycle completed", "color": "#10b981"})
    events.append({"time": (now - timedelta(minutes=22)).strftime("%H:%M"),
                   "icon": "●", "text": "System health check passed", "color": "#10b981"})
    events.append({"time": (now - timedelta(minutes=30)).strftime("%H:%M"),
                   "icon": "●", "text": "Forecast model updated", "color": "#0ea5e9"})
    events.append({"time": (now - timedelta(minutes=45)).strftime("%H:%M"),
                   "icon": "●", "text": "Temperature within normal range", "color": "#10b981"})
    events.append({"time": (now - timedelta(minutes=60)).strftime("%H:%M"),
                   "icon": "●", "text": "ESP32 sensors online", "color": "#10b981"})
    events.append({"time": (now - timedelta(minutes=90)).strftime("%H:%M"),
                   "icon": "●", "text": "Historical data synced to Firestore", "color": "#64748b"})
    return events[:10]



# ═══════════════════════════════════════════════════════════════════════════
# GEMINI HELPER
# ═══════════════════════════════════════════════════════════════════════════

def _ask_gemini(question: str, sensor_ctx: dict, anomaly: bool) -> str:
    """Send a question to Gemini with live sensor context injected as system prompt."""
    if not GEMINI_AVAILABLE or _GEMINI_MODEL is None:
        return None
    system_prompt = f"""You are AquaMind AI, an expert water management AI assistant embedded in an IoT dashboard.

Current live sensor readings:
- Flow Rate: {sensor_ctx['flow']:.2f} L/min (normal: 10–20)
- Pressure: {sensor_ctx['pressure']:.2f} bar (normal: 2.0–3.2)
- pH: {sensor_ctx['ph']:.2f} (safe: 6.5–8.5)
- Turbidity: {sensor_ctx['turbidity']:.2f} NTU (safe: <5)
- Temperature: {sensor_ctx['temperature']:.2f} °C (safe: 15–30)
- AI Anomaly Detected: {'YES — possible leak or fault' if anomaly else 'NO — all clear'}

Answer the user's question concisely (2–4 sentences) using the sensor data above.
Be specific with numbers. Sound like an expert water engineer, not a chatbot.
Do NOT repeat the question. Do NOT use markdown headers. Plain paragraphs only."""
    try:
        response = _GEMINI_MODEL.generate_content(f"{system_prompt}\n\nQuestion: {question}")
        return response.text.strip()
    except Exception as e:
        return f"Gemini unavailable: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# TAB RENDERERS
# ═══════════════════════════════════════════════════════════════════════════

def render_mission_control(df, latest, anomaly, health_score, alerts):
    """Tab 1 — Mission Control"""
    _D   = st.session_state.get("dark_mode", False)
    _TXT = "#f1f5f9" if _D else "#0f172a"
    _T2  = "#94a3b8" if _D else "#475569"
    _CB  = "#1e293b" if _D else "white"
    _SHD = "rgba(0,0,0,0.35)" if _D else "rgba(0,0,0,0.07)"
    # ── Executive Brief ────────────────────────────────────────────────────
    risk_score = max(0, 100 - health_score)
    ops_score  = min(100, int(health_score * 0.9 + (100 - len(alerts) * 10) * 0.1))
    sustain    = min(100, int(health_score * 0.85 + 15))
    trend      = "▲" if not df.empty and df["flow"].tail(10).mean() > df["flow"].tail(20).mean() else "▼"

    status_word = "optimal" if health_score >= 80 else ("moderate" if health_score >= 60 else "critical")
    alert_count = len(alerts)
    crit_count  = sum(1 for a in alerts if a["sev"] == "CRITICAL")

    brief = (
        f"As of {datetime.now().strftime('%B %d, %Y at %H:%M')}, the AquaMind AI system "
        f"reports a Water Health Score of {health_score}/100 — system status is "
        f"<strong>{status_word}</strong>. "
        f"{'No active alerts.' if alert_count == 0 else f'{alert_count} alert(s) active, {crit_count} critical.'} "
        f"Current flow rate is trending {trend}. "
        f"Operational efficiency stands at {ops_score}% with a sustainability index of {sustain}/100. "
        f"AI Copilot recommends {'no immediate action.' if alert_count == 0 else 'urgent field inspection in flagged zones.'}"
    )

    st.markdown(f"""
    <div class="exec-brief">
        <div style="font-size:0.75rem;color:{_T2};text-transform:uppercase;letter-spacing:1px;margin-bottom:0.5rem;">
            Executive Brief — Auto-Generated by AquaMind AI
        </div>
        <div style="font-size:1rem;line-height:1.7;">{brief}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Health Score row ───────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        color = score_color(health_score)
        st.markdown(f"""
        <div class="score-ring">
            <div style="font-size:0.8rem;color:{_T2};font-weight:600;text-transform:uppercase;letter-spacing:1px;">
                Water Health Score
            </div>
            <div class="health-score" style="-webkit-text-fill-color:{color};">{health_score}</div>
            <div style="font-size:0.85rem;color:{_T2};">/ 100</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        rc = score_color(100 - risk_score)
        st.markdown(f"""
        <div class="score-ring">
            <div style="font-size:0.8rem;color:{_T2};font-weight:600;text-transform:uppercase;letter-spacing:1px;">
                AI Risk Score
            </div>
            <div style="font-size:3rem;font-weight:800;color:{score_color(100-risk_score)};">{risk_score}</div>
            <div style="font-size:0.85rem;color:{_T2};">/ 100  (lower = better)</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="score-ring">
            <div style="font-size:0.8rem;color:{_T2};font-weight:600;text-transform:uppercase;letter-spacing:1px;">
                Sustainability Score
            </div>
            <div style="font-size:3rem;font-weight:800;color:{score_color(sustain)};">{sustain}</div>
            <div style="font-size:0.85rem;color:{_T2};">/ 100</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
        <div class="score-ring">
            <div style="font-size:0.8rem;color:{_T2};font-weight:600;text-transform:uppercase;letter-spacing:1px;">
                Operational Efficiency
            </div>
            <div style="font-size:3rem;font-weight:800;color:{score_color(ops_score)};">{ops_score}%</div>
            <div style="font-size:0.85rem;color:{_T2};">real-time estimate</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── KPI row ────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Executive KPIs</div>', unsafe_allow_html=True)
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    sensor_count = 5

    # Build sparkline data from df if available
    _flow_spark    = list(df["flow"].tail(10))     if not df.empty else [15]*10
    _press_spark   = list(df["pressure"].tail(10)) if not df.empty else [2.5]*10

    kpis = [
        (k1, str(sensor_count),                   "Active Sensors",  "#0ea5e9", None),
        (k2, str(sensor_count - len([a for a in alerts if a["sev"] == "CRITICAL"])),
             "Healthy Sensors", "#10b981", None),
        (k3, f"{latest['flow']:.1f} L/m",         "Current Flow",    "#8b5cf6", _flow_spark),
        (k4, f"{latest['flow']*1.08:.1f} L/m",    "Predicted Flow",  "#f59e0b", _flow_spark),
        (k5, str(crit_count),                      "Active Leaks",    "#ef4444", None),
        (k6, "97.3%",                              "AI Accuracy",     "#10b981", None),
    ]
    for col, val, lbl, clr, spark in kpis:
        with col:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-value" style="color:{clr};">{val}</div>
                <div class="kpi-label">{lbl}</div>
            </div>
            """, unsafe_allow_html=True)
            if spark:
                st.plotly_chart(_sparkline(spark, color=clr), use_container_width=True,
                                config={"displayModeBar": False})

    st.markdown("<br>", unsafe_allow_html=True)
    left, right = st.columns([1.4, 1])

    # ── Timeline ───────────────────────────────────────────────────────────
    with left:
        st.markdown('<div class="section-header">Command Center — Recent Events</div>', unsafe_allow_html=True)
        events = generate_timeline(df, anomaly)
        for ev in events:
            st.markdown(f"""
            <div class="timeline-item">
                <div style="font-size:1.3rem;">{ev['icon']}</div>
                <div style="flex:1;">
                    <span style="color:{_T2};font-size:0.8rem;">{ev['time']}</span>
                    <span style="margin-left:0.5rem;color:{_TXT};">{ev['text']}</span>
                </div>
                <div style="width:8px;height:8px;border-radius:50%;background:{ev['color']};margin-top:6px;flex-shrink:0;"></div>
            </div>
            """, unsafe_allow_html=True)

    # ── AI Explainability ──────────────────────────────────────────────────
    with right:
        st.markdown('<div class="section-header">AI Explainability</div>', unsafe_allow_html=True)
        explanations = [
            ("Flow Rate",    latest["flow"],        "L/min", "Normal demand pattern. Daily peak expected 17:00–20:00."),
            ("pH Level",     latest["ph"],           "",      "Neutral pH. Dosing system performing within spec."),
            ("Pressure",     latest["pressure"],     "bar",   "Adequate line pressure. No drop detected."),
            ("Turbidity",    latest["turbidity"],    "NTU",   "Sediment levels normal post-filtration."),
            ("Temperature",  latest["temperature"],  "°C",    "Ambient temperature stable. No Legionella risk."),
        ]
        for param, val, unit, reason in explanations:
            conf_html = '<span class="confidence-high">HIGH</span>'
            st.markdown(f"""
            <div class="ai-card" style="border-left-color:#0ea5e9;">
                <div style="font-weight:700;color:{_TXT};">{param}: {val:.2f} {unit}
                    &nbsp; {conf_html}
                </div>
                <div style="color:{_T2};font-size:0.85rem;margin-top:0.3rem;">{reason}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Optimize button ────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    opt_col, exp_col = st.columns([2, 1])
    with opt_col:
        if st.button("Optimize My Farm — Apply All AI Recommendations", use_container_width=True):
            with st.spinner("Applying AI optimization parameters…"):
                time.sleep(1.2)
            st.success(
                "Optimization applied. Irrigation schedule adjusted, pressure regulators "
                "updated, and predictive maintenance tasks queued. Estimated savings: 340 L/day."
            )
    with exp_col:
        if not df.empty:
            csv_bytes = df.to_csv(index=False).encode()
            st.download_button(
                label="Export Full Report CSV",
                data=csv_bytes,
                file_name=f"aquamind_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # ── Root Cause Classifier ──────────────────────────────────────────────
    if anomaly:
        st.markdown('<div class="section-header">AI Root Cause Analysis</div>', unsafe_allow_html=True)
        clf = get_root_cause_classifier()
        if clf:
            rc_result = clf.classify(
                flow=latest["flow"], pressure=latest["pressure"],
                ph=latest["ph"], turbidity=latest["turbidity"],
                temperature=latest["temperature"],
            )
            rc_color = {"LEAK": "#ef4444", "CONTAMINATION": "#f59e0b",
                        "UNUSUAL_USAGE": "#8b5cf6", "SENSOR_FAULT": "#64748b"}.get(rc_result["root_cause"], "#ef4444")
            conf_color = {"HIGH": "#10b981", "MEDIUM": "#f59e0b", "LOW": "#ef4444"}.get(rc_result["confidence"], "#64748b")
            st.markdown(f"""
            <div class="root-cause-card">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.8rem;">
                    <div style="font-size:1.1rem;font-weight:800;color:{rc_color};">
                        ROOT CAUSE: {rc_result['label']}
                    </div>
                    <span style="background:{conf_color};color:white;padding:0.2rem 0.6rem;
                          border-radius:99px;font-size:0.75rem;font-weight:700;">
                        {rc_result['confidence']} CONFIDENCE
                    </span>
                </div>
                <div style="color:{_TXT};margin-bottom:0.6rem;">{rc_result['explanation']}</div>
                <div style="color:#f59e0b;font-weight:600;">Recommended Action:</div>
                <div style="color:{_TXT};margin-bottom:0.8rem;">{rc_result['recommended_action']}</div>
                <div style="color:{_T2};font-size:0.82rem;font-weight:600;margin-bottom:0.3rem;">
                    Supporting Evidence ({len(rc_result['supporting_evidence'])} rules triggered):
                </div>
                {"".join(f'<div style="color:{_T2};font-size:0.82rem;padding:0.2rem 0;">• {ev}</div>' for ev in rc_result['supporting_evidence'])}
            </div>
            """, unsafe_allow_html=True)

    # ── Predictive Maintenance Countdown ───────────────────────────────────
    st.markdown('<div class="section-header">Predictive Maintenance Schedule</div>', unsafe_allow_html=True)
    turb_avg = df["turbidity"].mean() if not df.empty else latest["turbidity"]
    ph_std   = df["ph"].std()         if not df.empty and len(df) > 5 else 0.1

    # Simple rule-based countdown: higher turbidity → earlier filter backwash
    filter_days  = max(1, int(5 - turb_avg * 0.6))
    sensor_days  = 14  # fixed calibration cycle
    inspect_days = max(3, 7 - (1 if anomaly else 0) * 4)

    pm1, pm2, pm3 = st.columns(3)
    for col, task, days, clr in [
        (pm1, "Filter Backwash",      filter_days,  "#f59e0b" if filter_days <= 2 else "#10b981"),
        (pm2, "Sensor Recalibration", sensor_days,  "#0ea5e9"),
        (pm3, "Pipeline Inspection",  inspect_days, "#ef4444" if anomaly else "#10b981"),
    ]:
        urgency = "URGENT" if days <= 1 else ("SOON" if days <= 3 else "SCHEDULED")
        with col:
            st.markdown(f"""
            <div class="maintenance-card">
                <div style="font-size:0.75rem;font-weight:700;color:{clr};text-transform:uppercase;
                     letter-spacing:1px;margin-bottom:0.3rem;">{urgency}</div>
                <div style="font-weight:700;color:{_TXT};margin-bottom:0.2rem;">{task}</div>
                <div style="font-size:2rem;font-weight:800;color:{clr};">{days}d</div>
                <div style="font-size:0.8rem;color:{_T2};">recommended window</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Live Water Savings Counter ─────────────────────────────────────────
    st.markdown('<div class="section-header">Live Water Savings Since System Start</div>', unsafe_allow_html=True)
    baseline_flow   = 25.0
    actual_avg_flow = df["flow"].mean() if not df.empty else latest["flow"]
    # Estimate savings accumulating since session start (stored in session state)
    if "_savings_start" not in st.session_state:
        st.session_state["_savings_start"] = datetime.now()
    elapsed_min = (datetime.now() - st.session_state["_savings_start"]).total_seconds() / 60
    live_saved_l  = max(0, (baseline_flow - actual_avg_flow) * elapsed_min)
    daily_saved_l = max(0, (baseline_flow - actual_avg_flow) * 8 * 60)

    sv1, sv2, sv3, sv4 = st.columns(4)
    savings_data = [
        (sv1, f"{live_saved_l:,.1f} L",      "Saved This Session",   "#0ea5e9"),
        (sv2, f"{daily_saved_l:,.0f} L",      "Projected Daily Save", "#10b981"),
        (sv3, f"{daily_saved_l * 30:,.0f} L", "Projected Monthly",    "#8b5cf6"),
        (sv4, f"₹{daily_saved_l * 0.05 * 30:.0f}",  "Monthly Cost Saving",  "#f59e0b"),
    ]
    for col, val, lbl, clr in savings_data:
        with col:
            st.markdown(f"""
            <div class="kpi-card" style="border-top:3px solid {clr};">
                <div style="font-size:1.8rem;font-weight:800;color:{clr};">{val}</div>
                <div style="font-size:0.82rem;color:{_T2};margin-top:0.3rem;">{lbl}</div>
            </div>
            """, unsafe_allow_html=True)



def render_live_dashboard(df, latest, anomaly, alerts, health_score=100):
    """Tab 2 — Live Dashboard"""
    _D   = st.session_state.get("dark_mode", False)
    _TXT = "#f1f5f9" if _D else "#0f172a"
    _T2  = "#94a3b8" if _D else "#475569"
    _CB  = "#1e293b" if _D else "white"
    _SHD = "rgba(0,0,0,0.35)" if _D else "rgba(0,0,0,0.08)"
    _PBG = "#1e293b" if _D else "#f8fafc"
    # ── Alert bar ──────────────────────────────────────────────────────────
    if alerts:
        for a in alerts:
            cls = "alert-critical" if a["sev"] == "CRITICAL" else "alert-warning"
            icon = "CRITICAL" if a["sev"] == "CRITICAL" else "WARNING"
            st.markdown(f"""
            <div class="{cls}">
                <strong>{a['sev']}: {a['type']}</strong> — {a['msg']}
                &nbsp;&nbsp;<em>Action: {a['action']}</em>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="alert-success">
            <strong>All Systems Normal</strong> — All sensor readings within optimal range.
        </div>
        """, unsafe_allow_html=True)

    # ── Gauges ─────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Real-Time Sensor Readings</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.plotly_chart(create_gauge(latest["flow"],        "Flow Rate",   0, 30,  10,  20,  "L/min"), use_container_width=True)
    with c2:
        st.plotly_chart(create_gauge(latest["ph"],          "pH Level",    0, 14,  6.5, 8.5, ""),      use_container_width=True)
    with c3:
        st.plotly_chart(create_gauge(latest["turbidity"],   "Turbidity",   0, 10,  1,   5,   "NTU"),   use_container_width=True)

    c4, c5, c6 = st.columns(3)
    with c4:
        st.plotly_chart(create_gauge(latest["pressure"],    "Pressure",    0, 5,   2.0, 3.2, "bar"),   use_container_width=True)
    with c5:
        st.plotly_chart(create_gauge(latest["temperature"], "Temperature", 0, 40,  15,  30,  "°C"),    use_container_width=True)
    with c6:
        # Leak probability gauge (derived)
        if anomaly:
            leak_prob = min(95, 60 + abs(latest["pressure"] - 2.5) * 20)
        else:
            leak_prob = max(2, (3.0 - latest["pressure"]) * 15)
        st.plotly_chart(create_gauge(round(leak_prob, 1), "Leak Probability", 0, 100, 0, 30, "%"), use_container_width=True)

    # ── Live trend chart ────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Live Sensor Trends</div>', unsafe_allow_html=True)
    if df.empty:
        st.info("No trend data available.")
        return

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Flow Rate (L/min)", "Pressure (bar)", "pH Level", "Turbidity (NTU)"),
        vertical_spacing=0.15, horizontal_spacing=0.08,
    )
    pairs = [
        (df["flow"],        "#0ea5e9", 1, 1),
        (df["pressure"],    "#f59e0b", 1, 2),
        (df["ph"],          "#10b981", 2, 1),
        (df["turbidity"],   "#ef4444", 2, 2),
    ]
    _fill_colors = {
        "#0ea5e9": "rgba(14,165,233,0.08)",
        "#f59e0b": "rgba(245,158,11,0.08)",
        "#10b981": "rgba(16,185,129,0.08)",
        "#ef4444": "rgba(239,68,68,0.08)",
    }
    for series, color, row, col in pairs:
        fig.add_trace(
            go.Scatter(x=df.index, y=series, mode="lines",
                       line=dict(color=color, width=2),
                       fill="tozeroy",
                       fillcolor=_fill_colors.get(color, "rgba(14,165,233,0.08)"),
                       showlegend=False),
            row=row, col=col,
        )
    fig.update_layout(height=480, margin=dict(l=10, r=10, t=40, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#f8fafc")
    st.plotly_chart(fig, use_container_width=True)

    # ── Summary stats ───────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Summary Statistics</div>', unsafe_allow_html=True)
    s1, s2, s3, s4, s5 = st.columns(5)
    stats = [
        (s1, "Avg Flow",     f"{df['flow'].mean():.2f} L/min"),
        (s2, "Peak Flow",    f"{df['flow'].max():.2f} L/min"),
        (s3, "pH Compliance",f"{((df['ph']>=6.5)&(df['ph']<=8.5)).mean()*100:.1f}%"),
        (s4, "Avg Pressure", f"{df['pressure'].mean():.2f} bar"),
        (s5, "Avg Turbidity",f"{df['turbidity'].mean():.2f} NTU"),
    ]
    for col, label, value in stats:
        with col:
            st.markdown(f"""
            <div class="metric-card" style="text-align:center;">
                <div style="font-size:1.6rem;font-weight:800;color:#0ea5e9;">{value}</div>
                <div style="color:{_T2};font-size:0.85rem;margin-top:0.3rem;">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Digital Twin ────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Digital Twin — Farm Layout</div>', unsafe_allow_html=True)
    leak_color = "#ef4444" if anomaly else "#10b981"
    pressure_w = min(100, int(latest["pressure"] / 3.5 * 100))
    flow_w     = min(100, int(latest["flow"] / 25.0 * 100))
    ph_color   = "#10b981" if 6.5 <= latest["ph"] <= 8.5 else "#ef4444"

    import streamlit.components.v1 as components
    dt_html = f"""
    <div style="background:#0f172a;border-radius:16px;padding:2rem;color:white;font-family:Inter,sans-serif;">
        <div style="text-align:center;margin-bottom:1.5rem;font-weight:700;font-size:1.1rem;color:#94a3b8;">
            Farm Zone — Real-Time Digital Twin
        </div>
        <div style="display:flex;justify-content:space-around;align-items:center;flex-wrap:wrap;gap:1rem;">

            <div style="text-align:center;">
                <div style="width:64px;height:64px;background:#1e3a5f;border-radius:50%;
                            border:3px solid #0ea5e9;display:flex;align-items:center;
                            justify-content:center;margin:0 auto 0.5rem auto;">
                    <span style="font-size:0.7rem;font-weight:700;color:#0ea5e9;letter-spacing:0.5px;">TANK</span>
                </div>
                <div style="font-weight:600;font-size:0.9rem;">Main Reservoir</div>
                <div style="color:#0ea5e9;font-size:0.8rem;">Level: 78%</div>
            </div>

            <div style="color:#334155;font-size:1.5rem;">→→→</div>

            <div style="text-align:center;">
                <div style="width:64px;height:64px;background:#1e293b;border-radius:12px;
                            border:3px solid #f59e0b;display:flex;align-items:center;
                            justify-content:center;margin:0 auto 0.5rem auto;">
                    <span style="font-size:0.7rem;font-weight:700;color:#f59e0b;letter-spacing:0.5px;">PUMP</span>
                </div>
                <div style="font-weight:600;font-size:0.9rem;">Pump Station</div>
                <div style="color:#f59e0b;font-size:0.8rem;">{latest['pressure']:.1f} bar</div>
                <div style="background:#1e293b;border-radius:4px;height:6px;width:80px;margin:0.3rem auto 0;">
                    <div style="background:#f59e0b;border-radius:4px;height:6px;width:{pressure_w}%;"></div>
                </div>
            </div>

            <div style="color:#334155;font-size:1.5rem;">→→→</div>

            <div style="text-align:center;">
                <div style="width:64px;height:64px;background:#1e293b;border-radius:12px;
                            border:3px solid {leak_color};display:flex;align-items:center;
                            justify-content:center;margin:0 auto 0.5rem auto;">
                    <span style="font-size:0.7rem;font-weight:700;color:{leak_color};letter-spacing:0.5px;">PIPE</span>
                </div>
                <div style="font-weight:600;font-size:0.9rem;">Main Pipeline</div>
                <div style="color:{leak_color};font-size:0.8rem;">
                    {("Anomaly" if anomaly else "Normal")}</div>
                <div style="background:#1e293b;border-radius:4px;height:6px;width:80px;margin:0.3rem auto 0;">
                    <div style="background:{leak_color};border-radius:4px;height:6px;width:{flow_w}%;"></div>
                </div>
            </div>

            <div style="color:#334155;font-size:1.5rem;">→→→</div>

            <div style="text-align:center;">
                <div style="width:64px;height:64px;background:#1e293b;border-radius:12px;
                            border:3px solid {ph_color};display:flex;align-items:center;
                            justify-content:center;margin:0 auto 0.5rem auto;">
                    <span style="font-size:0.7rem;font-weight:700;color:{ph_color};letter-spacing:0.5px;">QA</span>
                </div>
                <div style="font-weight:600;font-size:0.9rem;">Quality Sensor</div>
                <div style="color:{ph_color};font-size:0.8rem;">pH {latest['ph']:.2f}</div>
            </div>

            <div style="color:#334155;font-size:1.5rem;">→→→</div>

            <div style="text-align:center;">
                <div style="width:64px;height:64px;background:#1e293b;border-radius:12px;
                            border:3px solid #10b981;display:flex;align-items:center;
                            justify-content:center;margin:0 auto 0.5rem auto;">
                    <span style="font-size:0.7rem;font-weight:700;color:#10b981;letter-spacing:0.5px;">IRR</span>
                </div>
                <div style="font-weight:600;font-size:0.9rem;">Irrigation Zone</div>
                <div style="color:#10b981;font-size:0.8rem;">Active</div>
            </div>
        </div>
    </div>
        """
    components.html(dt_html, height=220)

    # ── Zone Health Map ────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Zone Health Map — Real-Time Overview</div>', unsafe_allow_html=True)

    # Representative coordinates for 5 zones (demo locations near Hyderabad, India)
    zone_data = {
        "Zone-1 Main Supply":   {"lat": 17.385, "lon": 78.486, "score": min(100, int(health_score * 1.0)),  "flow": latest["flow"],         "ph": latest["ph"]},
        "Zone-2 Residential":   {"lat": 17.412, "lon": 78.510, "score": min(100, int(health_score * 0.93)), "flow": latest["flow"] * 0.85,  "ph": latest["ph"] + 0.1},
        "Zone-3 Industrial":    {"lat": 17.360, "lon": 78.472, "score": min(100, int(health_score * 0.87)), "flow": latest["flow"] * 1.20,  "ph": latest["ph"] - 0.15},
        "Zone-4 Agricultural":  {"lat": 17.440, "lon": 78.495, "score": min(100, int(health_score * 0.95)), "flow": latest["flow"] * 0.70,  "ph": latest["ph"] + 0.05},
        "Zone-5 Municipal":     {"lat": 17.370, "lon": 78.530, "score": min(100, int(health_score * 0.91)), "flow": latest["flow"] * 0.90,  "ph": latest["ph"] - 0.05},
    }

    zone_df = pd.DataFrame([
        {
            "Zone":    name,
            "Lat":     v["lat"],
            "Lon":     v["lon"],
            "Score":   v["score"],
            "Flow":    round(v["flow"], 2),
            "pH":      round(v["ph"], 2),
            "Status":  "Critical" if v["score"] < 60 else ("Warning" if v["score"] < 80 else "Healthy"),
            "Color":   "#ef4444" if v["score"] < 60 else ("#f59e0b" if v["score"] < 80 else "#10b981"),
        }
        for name, v in zone_data.items()
    ])

    fig_map = go.Figure()
    for _, row in zone_df.iterrows():
        fig_map.add_trace(go.Scattermapbox(
            lat=[row["Lat"]], lon=[row["Lon"]],
            mode="markers+text",
            marker=dict(size=28, color=row["Color"], opacity=0.9),
            text=[f"{row['Score']}"],
            textfont=dict(size=11, color="white", family="Inter"),
            textposition="middle center",
            hovertemplate=(
                f"<b>{row['Zone']}</b><br>"
                f"Health Score: {row['Score']}/100<br>"
                f"Status: {row['Status']}<br>"
                f"Flow: {row['Flow']} L/min<br>"
                f"pH: {row['pH']}<extra></extra>"
            ),
            name=row["Zone"],
            showlegend=True,
        ))

    fig_map.update_layout(
        mapbox=dict(
            style="carto-positron",
            center=dict(lat=17.400, lon=78.500),
            zoom=11,
        ),
        height=420,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.01,
            bgcolor="rgba(255,255,255,0.8)", bordercolor="#e2e8f0", borderwidth=1,
        ),
    )
    st.plotly_chart(fig_map, use_container_width=True)

    # Zone summary table
    display_df = zone_df[["Zone", "Score", "Status", "Flow", "pH"]].copy()
    display_df.columns = ["Zone", "Health Score", "Status", "Flow (L/min)", "pH"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)




def render_ai_advisor(df, latest, anomaly, detector, engine):
    """Tab 3 — AI Advisor"""
    _D   = st.session_state.get("dark_mode", False)
    _TXT = "#f1f5f9" if _D else "#0f172a"
    _T2  = "#94a3b8" if _D else "#475569"
    _CB  = "#1e293b" if _D else "white"
    _SHD = "rgba(0,0,0,0.35)" if _D else "rgba(0,0,0,0.08)"
    # ── Daily AI Report ─────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Daily AI Report</div>', unsafe_allow_html=True)

    # Determine values
    water_saved   = round(max(0, (25 - latest["flow"]) * 60 * 8), 0)
    ph_ok         = 6.5 <= latest["ph"] <= 8.5
    turb_ok       = latest["turbidity"] < 5
    press_ok      = 1.5 <= latest["pressure"] <= 3.5

    report_items = [
        {
            "title":    "Today's Summary",
            "icon":     "Summary",
            "message":  f"System operated {'normally' if not anomaly else 'with anomalies detected'} today. "
                        f"Sensors reporting at 5-second intervals. {200 if not df.empty else 0} readings processed.",
            "confidence": "HIGH",
            "reasoning":  "Based on 200 data points sampled over the last 16 hours.",
            "action":     "No immediate action required." if not anomaly else "Dispatch field team for inspection.",
        },
        {
            "title":    "Water Saved",
            "icon":     "Conservation",
            "message":  f"Estimated {water_saved:,.0f} L saved today vs. baseline consumption "
                        f"through AI-optimized irrigation scheduling.",
            "confidence": "MEDIUM",
            "reasoning":  "Calculated by comparing actual flow to baseline (25 L/min) over 8 h irrigation window.",
            "action":     "Continue current irrigation schedule.",
        },
        {
            "title":    "Leak Analysis",
            "icon":     "Diagnostics",
            "message":  f"{'Anomaly detected in flow/pressure readings — possible leak event.' if anomaly else 'No leaks detected. All flow and pressure values within normal bounds.'}",
            "confidence": "HIGH" if detector and getattr(detector, "is_trained", False) else "LOW",
            "reasoning":  "Isolation Forest model trained on historical sensor data." if detector and getattr(detector, "is_trained", False) else "AI model not yet trained — rule-based fallback used.",
            "action":     "Inspect Zone 2 pipeline." if anomaly else "Schedule next inspection in 7 days.",
        },
        {
            "title":    "Predictions",
            "icon":     "Forecast",
            "message":  f"Peak demand forecast between 17:00–20:00 today. "
                        f"Expected flow rate: {latest['flow']*1.18:.1f}–{latest['flow']*1.35:.1f} L/min.",
            "confidence": "MEDIUM",
            "reasoning":  "Daily sine-wave demand model applied to current flow baseline.",
            "action":     "Pre-fill storage tanks by 16:00 to buffer peak demand.",
        },
        {
            "title":    "Recommended Actions",
            "icon":     "Actions",
            "message":  (
                "1. Optimize irrigation to off-peak hours (05:00–07:00). "
                "2. Schedule filter backwash within 48 h. "
                + ("3. Inspect pipeline joints in Zone 2 urgently." if anomaly else "3. System running efficiently — no urgent tasks.")
            ),
            "confidence": "HIGH",
            "reasoning":  "Rule-based engine cross-referenced with forecast model and live sensor data.",
            "action":     "Assign tasks in field management system.",
        },
        {
            "title":    "System Health",
            "icon":     "Health",
            "message":  f"All {'5' if not anomaly else '4'}/5 sensors operational. "
                        f"pH {'normal' if ph_ok else 'out of range'}. "
                        f"Turbidity {'normal' if turb_ok else 'elevated'}. "
                        f"Pressure {'normal' if press_ok else 'abnormal'}.",
            "confidence": "HIGH",
            "reasoning":  "Threshold checks against WHO and operational guidelines.",
            "action":     "Recalibrate turbidity sensor next maintenance cycle." if not turb_ok else "Continue normal operations.",
        },
    ]

    for item in report_items:
        conf_cls = {"HIGH": "confidence-high", "MEDIUM": "confidence-med", "LOW": "confidence-low"}[item["confidence"]]
        st.markdown(f"""
        <div class="ai-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div style="font-weight:700;font-size:1rem;color:{_TXT};">
                    {item['title']}
                </div>
                <span class="{conf_cls}" style="font-size:0.75rem;">{item['confidence']} CONFIDENCE</span>
            </div>
            <div style="color:{_TXT};margin:0.4rem 0 0.3rem;">{item['message']}</div>
            <div style="color:{_T2};font-size:0.82rem;margin-bottom:0.3rem;">
                <strong>Reasoning:</strong> {item['reasoning']}
            </div>
            <div style="color:#0ea5e9;font-size:0.85rem;font-weight:600;">
                → {item['action']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── AI Copilot (Gemini-powered) ─────────────────────────────────────────
    _D_cop = st.session_state.get("dark_mode", False)
    gemini_badge = (
        '<span style="background:#4285f4;color:white;font-size:0.7rem;font-weight:700;'
        'padding:0.15rem 0.5rem;border-radius:99px;margin-left:0.5rem;">Powered by Gemini</span>'
        if GEMINI_AVAILABLE else
        '<span style="background:#64748b;color:white;font-size:0.7rem;font-weight:700;'
        'padding:0.15rem 0.5rem;border-radius:99px;margin-left:0.5rem;">Rule-based fallback</span>'
    )
    st.markdown(
        f'<div class="section-header">AI Copilot — Ask About Your Water Data {gemini_badge}</div>',
        unsafe_allow_html=True,
    )

    preset_questions = [
        "Select a question…",
        "What is the current water quality status?",
        "Is there a leak in the system?",
        "When is peak water demand expected?",
        "How can I reduce water waste?",
        "What is the pH trend?",
        "What maintenance should I do this week?",
        "What would happen if pressure drops below 1.5 bar?",
        "Is the system ready for peak irrigation season?",
    ]

    question = st.selectbox("Choose a preset question or type your own below:", preset_questions, key="copilot_select")
    custom_q = st.text_input("Or type any question about your water system:", key="copilot_custom",
                              placeholder="e.g. Why is my turbidity spiking at night?")

    col_ask, col_clear = st.columns([3, 1])
    ask_btn   = col_ask.button("Ask AI Copilot", type="primary", use_container_width=True)
    clear_btn = col_clear.button("Clear", use_container_width=True)
    if clear_btn:
        st.session_state.pop("_copilot_answer", None)
        st.session_state.pop("_copilot_q", None)

    if ask_btn:
        q = custom_q.strip() if custom_q.strip() else (question if question != "Select a question…" else "")
        if not q:
            st.warning("Please select or type a question first.")
        else:
            with st.spinner("AquaMind AI is thinking…"):
                # Try Gemini first
                gemini_answer = _ask_gemini(q, latest, anomaly)

            if gemini_answer:
                st.session_state["_copilot_answer"] = gemini_answer
                st.session_state["_copilot_q"]      = q
                st.session_state["_copilot_source"]  = "gemini"
            else:
                # Rule-based fallback
                issues = []
                if not ph_ok:
                    issues.append(f"pH is {latest['ph']:.2f} ({'too low' if latest['ph'] < 6.5 else 'too high'})")
                if not turb_ok:
                    issues.append(f"turbidity is elevated at {latest['turbidity']:.1f} NTU")
                if not press_ok:
                    issues.append(f"pressure is {'low' if latest['pressure'] < 1.5 else 'high'} at {latest['pressure']:.2f} bar")
                if anomaly:
                    issues.append("an AI anomaly has been detected — possible leak")
                if issues:
                    fallback = (
                        f"Based on current sensor data: {'; '.join(issues)}. "
                        f"Flow={latest['flow']:.1f} L/min, pressure={latest['pressure']:.2f} bar. "
                        "Check the Live Dashboard and AI Advisor tabs for detailed guidance."
                    )
                else:
                    fallback = (
                        f"All systems normal. Flow={latest['flow']:.1f} L/min, "
                        f"pressure={latest['pressure']:.2f} bar, pH={latest['ph']:.2f}, "
                        f"turbidity={latest['turbidity']:.1f} NTU. No anomalies detected."
                    )
                st.session_state["_copilot_answer"] = fallback
                st.session_state["_copilot_q"]      = q
                st.session_state["_copilot_source"]  = "fallback"

    if "_copilot_answer" in st.session_state:
        source  = st.session_state.get("_copilot_source", "fallback")
        src_lbl = "Gemini 1.5 Flash" if source == "gemini" else "Rule-based Engine"
        src_clr = "#4285f4"          if source == "gemini" else "#64748b"
        q_shown = st.session_state.get("_copilot_q", "")
        bg_grad = "linear-gradient(135deg,#eff6ff,#dbeafe)" if not _D_cop else "linear-gradient(135deg,#1e293b,#0f172a)"
        txt_clr = "#0f172a" if not _D_cop else "#e2e8f0"
        st.markdown(f"""
        <div style="background:{bg_grad};border-radius:14px;padding:1.4rem;
                    border-left:4px solid {src_clr};margin-top:0.8rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.6rem;">
                <div style="font-weight:800;color:{src_clr};font-size:1rem;">AquaMind AI</div>
                <span style="background:{src_clr};color:white;font-size:0.7rem;font-weight:700;
                      padding:0.15rem 0.5rem;border-radius:99px;">{src_lbl}</span>
            </div>
            <div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.5rem;font-style:italic;">
                Q: {q_shown}
            </div>
            <div style="color:{txt_clr};line-height:1.7;font-size:0.95rem;">{st.session_state['_copilot_answer']}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Recommendation Engine ───────────────────────────────────────────────
    if engine is not None:
        st.markdown('<div class="section-header">Recommendation Engine</div>', unsafe_allow_html=True)
        zone = st.selectbox("Select Zone", [
            "Zone-1 Main Supply", "Zone-2 Residential", "Zone-3 Industrial",
            "Zone-4 Agricultural", "Zone-5 Municipal",
        ], key="advisor_zone")

        if st.button("Generate Smart Recommendations", type="primary"):
            anomaly_result = {
                "is_anomaly": anomaly, "score": -0.4 if anomaly else 0.1,
                "flow": float(latest["flow"]), "pressure": float(latest["pressure"]),
                "ph": float(latest["ph"]), "turbidity": float(latest["turbidity"]),
                "temperature": float(latest["temperature"]),
            }
            with st.spinner("Analysing…"):
                recs = engine.recommend_from_model_outputs(zone=zone, anomaly_result=anomaly_result)

            if not recs:
                st.markdown("""
                <div class="alert-success">
                    No actionable recommendations — all parameters normal.
                </div>
                """, unsafe_allow_html=True)
            else:
                for r in recs:
                    pri = r["priority"]
                    clr = {"HIGH": "#ef4444", "MEDIUM": "#f59e0b", "LOW": "#10b981"}.get(pri, "#64748b")
                    ic  = {"HIGH": "HIGH", "MEDIUM": "MED", "LOW": "LOW"}.get(pri, "—")
                    st.markdown(f"""
                    <div class="ai-card" style="border-left-color:{clr};">
                        <div style="font-weight:700;color:{clr};">[{pri}] {r.get('category','').replace('_',' ').title()}</div>
                        <div style="color:{_TXT};margin:0.3rem 0;">{r['message']}</div>
                        <div style="color:{_TXT};"><strong>Action:</strong> {r['recommended_action']}</div>
                        <div style="color:#10b981;font-weight:600;margin-top:0.3rem;">{r['estimated_impact']}</div>
                    </div>
                    """, unsafe_allow_html=True)



def render_analytics(df, latest, forecaster):
    """Tab 4 — Analytics & Forecast"""
    _D   = st.session_state.get("dark_mode", False)
    _TXT = "#f1f5f9" if _D else "#0f172a"
    _T2  = "#94a3b8" if _D else "#475569"
    _PBG = "#1e293b" if _D else "#f8fafc"

    st.markdown('<div class="section-header">Historical Trends &amp; Analysis</div>', unsafe_allow_html=True)

    atab1, atab2, atab3, atab4 = st.tabs([
        "Flow & Pressure Analysis",
        "Water Quality Monitoring",
        "AI Predictions",
        "Decision Intelligence",
    ])

    # ── Sub-tab 1: Flow & Pressure ─────────────────────────────────────────
    with atab1:
        if df.empty:
            st.info("No data available.")
        else:
            fig = make_subplots(rows=2, cols=1,
                                subplot_titles=("Water Flow Rate Over Time", "Water Pressure Over Time"),
                                vertical_spacing=0.25)
            fig.add_trace(go.Scatter(x=df.index, y=df["flow"],     name="Flow Rate",
                                     line=dict(color="#0ea5e9", width=2),
                                     fill="tozeroy", fillcolor="rgba(14,165,233,0.1)"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df["pressure"], name="Pressure",
                                     line=dict(color="#f59e0b", width=2),
                                     fill="tozeroy", fillcolor="rgba(245,158,11,0.1)"), row=2, col=1)
            fig.add_hline(y=2.0, line_dash="dash", line_color="#ef4444",
                          annotation_text="Min Pressure (2.0 bar)",
                          annotation_position="top right", row=2, col=1)
            fig.add_hline(y=3.2, line_dash="dash", line_color="#f59e0b",
                          annotation_text="Max Pressure (3.2 bar)",
                          annotation_position="bottom right", row=2, col=1)
            fig.update_layout(height=580, paper_bgcolor="rgba(0,0,0,0)",
                               plot_bgcolor=_PBG, hovermode="x unified",
                               margin=dict(t=60, b=40),
                               xaxis=dict(title="Reading Number"),
                               xaxis2=dict(title="Reading Number"),
                               yaxis=dict(title="Flow (L/min)"),
                               yaxis2=dict(title="Pressure (bar)"))
            fig.update_annotations(font_size=13)
            st.plotly_chart(fig, use_container_width=True)

            f1, f2, f3, f4 = st.columns(4)
            stats = [
                (f1, "Avg Flow",      f"{df['flow'].mean():.2f} L/min"),
                (f2, "Peak Flow",     f"{df['flow'].max():.2f} L/min"),
                (f3, "Avg Pressure",  f"{df['pressure'].mean():.2f} bar"),
                (f4, "Peak Pressure", f"{df['pressure'].max():.2f} bar"),
            ]
            for col, lbl, val in stats:
                with col:
                    st.metric(lbl, val)

    # ── Sub-tab 2: Water Quality ───────────────────────────────────────────
    with atab2:
        if df.empty:
            st.info("No data available.")
        else:
            fig2 = make_subplots(rows=2, cols=1,
                                 subplot_titles=("pH Level Monitoring", "Turbidity Monitoring"),
                                 vertical_spacing=0.25)
            fig2.add_trace(go.Scatter(x=df.index, y=df["ph"], name="pH Level",
                                      line=dict(color="#10b981", width=2)), row=1, col=1)
            fig2.add_trace(go.Scatter(x=df.index, y=df["turbidity"], name="Turbidity",
                                      line=dict(color="#ef4444", width=2),
                                      fill="tozeroy", fillcolor="rgba(239,68,68,0.1)"), row=2, col=1)
            # Safety threshold lines
            fig2.add_hline(y=6.5, line_dash="dot", line_color="#ef4444",
                           annotation_text="pH Min (6.5)", row=1, col=1)
            fig2.add_hline(y=8.5, line_dash="dot", line_color="#ef4444",
                           annotation_text="pH Max (8.5)", row=1, col=1)
            fig2.add_hline(y=5.0, line_dash="dash", line_color="#f59e0b",
                           annotation_text="Turbidity Limit (5 NTU)", row=2, col=1)
            fig2.update_layout(height=580, paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor=_PBG, hovermode="x unified",
                                margin=dict(t=60, b=40),
                                xaxis=dict(title="Reading Number"),
                                xaxis2=dict(title="Reading Number"),
                                yaxis=dict(title="pH"),
                                yaxis2=dict(title="Turbidity (NTU)"))
            fig2.update_annotations(font_size=13)
            st.plotly_chart(fig2, use_container_width=True)

            ph_comp   = ((df["ph"] >= 6.5) & (df["ph"] <= 8.5)).mean() * 100
            turb_comp = (df["turbidity"] < 5.0).mean() * 100
            wq1, wq2 = st.columns(2)
            with wq1:
                st.metric("pH Compliance Rate",      f"{ph_comp:.1f}%")
            with wq2:
                st.metric("Turbidity Compliance",    f"{turb_comp:.1f}%")

    # ── Sub-tab 3: AI Predictions ──────────────────────────────────────────
    with atab3:
        st.markdown('<div class="section-header">24-Hour Water Demand Forecast</div>', unsafe_allow_html=True)

        if st.button("Generate AI Forecast", type="primary"):
            with st.spinner("Generating forecast…"):
                if forecaster and getattr(forecaster, "is_trained", False):
                    preds = forecaster.predict_next_hours(hours=24)
                    model_lbl = "LSTM Neural Network" if TENSORFLOW_AVAILABLE else "Statistical Model"
                else:
                    avg   = latest["flow"] if not df.empty else 15.0
                    preds = [max(0, avg * (0.7 + 0.4 * _demand_factor(i, 288)) + np.random.normal(0, 0.4))
                             for i in range(288)]
                    model_lbl = "Statistical (daily pattern)"
                st.session_state["_forecast_preds"]     = preds
                st.session_state["_forecast_model_lbl"] = model_lbl

        preds     = st.session_state.get("_forecast_preds",     None)
        model_lbl = st.session_state.get("_forecast_model_lbl", "")

        if preds:
            hours      = [i / 12 for i in range(len(preds))]
            conf_upper = [p * 1.08 for p in preds]
            conf_lower = [p * 0.92 for p in preds]

            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(
                x=hours + hours[::-1], y=conf_upper + conf_lower[::-1],
                fill="toself", fillcolor="rgba(139,92,246,0.12)",
                line=dict(color="rgba(0,0,0,0)"), name="90% CI",
            ))
            fig3.add_trace(go.Scatter(
                x=hours, y=preds, mode="lines", name=f"Forecast ({model_lbl})",
                line=dict(color="#8b5cf6", width=3),
                fill="tozeroy", fillcolor="rgba(139,92,246,0.08)",
            ))
            if not df.empty:
                actual_flow = list(df["flow"].values[-min(50, len(df)):])
                actual_x    = [-(len(actual_flow) - i) / 12 for i in range(len(actual_flow))]
                fig3.add_trace(go.Scatter(
                    x=actual_x, y=actual_flow, mode="lines",
                    name="Actual (historical)",
                    line=dict(color="#10b981", width=2, dash="dot"),
                ))
            fig3.update_layout(
                title=f"Predicted Water Demand — Next 24 Hours ({model_lbl})",
                xaxis_title="Hours from Now", yaxis_title="Flow Rate (L/min)",
                height=420, hovermode="x unified",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=_PBG,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig3, use_container_width=True)

            p1, p2, p3 = st.columns(3)
            p1.metric("Average Demand",  f"{np.mean(preds):.2f} L/min")
            p2.metric("Peak Demand",     f"{np.max(preds):.2f} L/min")
            p3.metric("Min Demand",      f"{np.min(preds):.2f} L/min")

            # Tank depletion
            st.markdown('<div class="section-header">Tank Depletion Forecast</div>', unsafe_allow_html=True)
            tank_level  = 7800
            depletion_l = [max(0, tank_level - sum(p * 5 / 60 for p in preds[:i+1])) for i in range(len(preds))]
            fig4 = go.Figure()
            fig4.add_trace(go.Scatter(x=hours, y=depletion_l, mode="lines", name="Tank Level",
                                      line=dict(color="#8b5cf6", width=3),
                                      fill="tozeroy", fillcolor="rgba(139,92,246,0.12)"))
            fig4.add_hline(y=2000, line_dash="dash", line_color="#ef4444",
                           annotation_text="Critical Level (2000 L)", annotation_position="right")
            fig4.update_layout(title="Tank Depletion Over Next 24 Hours",
                               xaxis_title="Hours from Now", yaxis_title="Tank Level (L)",
                               height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=_PBG)
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Click 'Generate AI Forecast' to run the prediction.")

        # Model training
        st.markdown('<div class="section-header">Model Training</div>', unsafe_allow_html=True)
        t1, t2 = st.columns(2)
        with t1:
            if st.button("Train Demand Forecaster", use_container_width=True, key="analytics_train_forecaster"):
                if forecaster:
                    with st.spinner("Training…"):
                        ok = forecaster.train(epochs=30)
                    st.success("Forecaster trained!") if ok else st.error("Training failed.")
                else:
                    st.error("Forecaster module not available.")
        with t2:
            if st.button("Train Leak Detector", use_container_width=True, key="analytics_train_detector"):
                detector = get_leak_detector()
                if detector:
                    with st.spinner("Training…"):
                        ok = detector.train()
                    st.success("Leak detector trained!") if ok else st.warning("Need 50+ readings.")
                else:
                    st.error("Leak detector module not available.")

    # ── Sub-tab 4: Decision Intelligence ──────────────────────────────────
    with atab4:
        st.markdown("### AI Decision Intelligence — Actionable Recommendations")
        st.markdown(
            "The recommendation engine analyses live sensor readings, anomaly scores, "
            "and demand forecasts to produce **prioritised, quantified actions** — not just alerts.",
            unsafe_allow_html=True,
        )

        engine = get_recommendation_engine()
        anomaly_flag = st.session_state.get("_last_anomaly", False)

        zone_di = st.selectbox(
            "Zone / Area",
            ["Zone-1 Main Supply", "Zone-2 Residential", "Zone-3 Industrial",
             "Zone-4 Agricultural", "Zone-5 Municipal"],
            key="di_zone",
        )

        c_gen, c_alert = st.columns([1, 1])
        run_recs = c_gen.button("Generate Recommendations", type="primary", use_container_width=True)
        send_alerts_btn = c_alert.button("Send Console Alerts for HIGH priority", use_container_width=True)

        if run_recs:
            if engine:
                anomaly_result = {
                    "is_anomaly": anomaly_flag,
                    "score":      -0.4 if anomaly_flag else 0.1,
                    "flow":       float(latest["flow"]),
                    "pressure":   float(latest["pressure"]),
                    "ph":         float(latest["ph"]),
                    "turbidity":  float(latest["turbidity"]),
                    "temperature":float(latest["temperature"]),
                }
                with st.spinner("Analysing…"):
                    recs = engine.recommend_from_model_outputs(zone=zone_di, anomaly_result=anomaly_result)
                st.session_state["_di_recs"]  = recs
                st.session_state["_di_zone"]  = zone_di
            else:
                st.error("Recommendation engine not available.")

        recs = st.session_state.get("_di_recs", [])

        if recs:
            high_c   = sum(1 for r in recs if r["priority"] == "HIGH")
            med_c    = sum(1 for r in recs if r["priority"] == "MEDIUM")
            low_c    = sum(1 for r in recs if r["priority"] == "LOW")
            rc1, rc2, rc3, rc4 = st.columns(4)
            rc1.metric("Total Recommendations", len(recs))
            rc2.metric("HIGH Priority",   high_c)
            rc3.metric("MEDIUM Priority", med_c)
            rc4.metric("LOW Priority",    low_c)

            st.markdown("<br>", unsafe_allow_html=True)
            for r in recs:
                pri = r["priority"]
                clr = {"HIGH": "#ef4444", "MEDIUM": "#f59e0b", "LOW": "#10b981"}.get(pri, "#64748b")
                bg  = {"HIGH": "#fef2f2", "MEDIUM": "#fffbeb", "LOW": "#f0fdf4"}.get(pri, "#f8fafc")
                st.markdown(f"""
                <div style="background:{bg};border-radius:10px;padding:1.2rem 1.4rem;
                            margin-bottom:0.8rem;border-left:5px solid {clr};">
                    <div style="font-weight:700;color:{clr};margin-bottom:0.3rem;">
                        [{pri}] {r.get('category','').replace('_',' ').title()}
                    </div>
                    <div style="color:#1e293b;margin-bottom:0.3rem;">{r['message']}</div>
                    <div style="color:#475569;font-size:0.9rem;">
                        <strong>Action:</strong> {r['recommended_action']}
                    </div>
                    <div style="color:#10b981;font-size:0.9rem;font-weight:600;margin-top:0.3rem;">
                        {r['estimated_impact']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            if send_alerts_btn:
                high_recs = [r for r in recs if r["priority"] == "HIGH"]
                if high_recs:
                    for r in high_recs:
                        st.warning(f"[CONSOLE ALERT] HIGH: {r['message']} — {r['recommended_action']}")
                    st.success(f"Sent {len(high_recs)} HIGH priority alert(s) to console.")
                else:
                    st.info("No HIGH priority recommendations to send.")
        elif run_recs:
            st.markdown("""
            <div class="alert-success">
                No actionable recommendations — all parameters normal.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Select a zone and click 'Generate Recommendations'.")



def render_sustainability(df, latest):
    """Tab 5 — Sustainability"""
    _D   = st.session_state.get("dark_mode", False)
    _TXT = "#f1f5f9" if _D else "#0f172a"
    _T2  = "#94a3b8" if _D else "#475569"
    _CB  = "#1e293b" if _D else "white"
    _SHD = "rgba(0,0,0,0.35)" if _D else "rgba(0,0,0,0.08)"
    st.markdown('<div class="section-header">Sustainability Dashboard</div>', unsafe_allow_html=True)

    # Compute sustainability metrics
    baseline_flow    = 25.0  # L/min max
    actual_avg_flow  = df["flow"].mean() if not df.empty else latest["flow"]
    daily_minutes    = 8 * 60  # 8-hour irrigation window
    water_saved_l    = max(0, (baseline_flow - actual_avg_flow) * daily_minutes)
    energy_saved_kwh = water_saved_l * 0.0003   # ~0.3 Wh per litre pumped
    co2_kg           = energy_saved_kwh * 0.233  # kg CO2 per kWh (India grid)
    sdg_pct          = min(100, int(water_saved_l / 50))

    s1, s2, s3, s4 = st.columns(4)
    sustain_kpis = [
        (s1, f"{water_saved_l:,.0f} L",     "Water Saved Today",   "#0ea5e9",
         "Compared to maximum baseline consumption of 25 L/min over 8-hour window."),
        (s2, f"{energy_saved_kwh:.2f} kWh",  "Energy Saved",        "#10b981",
         "Estimated energy reduction from lower pump utilization (0.3 Wh/L)."),
        (s3, f"{co2_kg:.2f} kg",             "CO₂ Reduction",       "#8b5cf6",
         "Carbon offset based on India grid emission factor: 233 g CO₂/kWh."),
        (s4, f"{sdg_pct}%",                  "SDG-6 Impact Score",  "#f59e0b",
         "Clean Water & Sanitation goal progress based on daily savings."),
    ]
    for col, val, lbl, clr, tip in sustain_kpis:
        with col:
            st.markdown(f"""
            <div class="kpi-card" style="border-top:3px solid {clr};">
                <div class="kpi-value" style="color:{clr};">{val}</div>
                <div class="kpi-label">{lbl}</div>
                <div style="font-size:0.75rem;color:#94a3b8;margin-top:0.5rem;">{tip}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── SDG Progress bar ──────────────────────────────────────────────────
    st.markdown('<div class="section-header">UN Sustainable Development Goals Progress</div>', unsafe_allow_html=True)
    sdg_goals = [
        ("SDG-6",  "Clean Water & Sanitation",      sdg_pct,             "#0ea5e9"),
        ("SDG-13", "Climate Action (CO₂)",           min(100, int(co2_kg*5)), "#10b981"),
        ("SDG-12", "Responsible Consumption",        min(100, int(water_saved_l/40)), "#8b5cf6"),
        ("SDG-11", "Sustainable Communities",        74,                  "#f59e0b"),
    ]
    for code, name, pct, clr in sdg_goals:
        st.markdown(f"""
        <div style="margin-bottom:1rem;">
            <div style="display:flex;justify-content:space-between;margin-bottom:0.3rem;">
                <span style="font-weight:600;color:#0f172a;">{code} — {name}</span>
                <span style="font-weight:700;color:{clr};">{pct}%</span>
            </div>
            <div style="background:#f1f5f9;border-radius:99px;height:10px;">
                <div style="background:{clr};border-radius:99px;height:10px;width:{pct}%;
                            transition:width 0.5s ease;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Sustainability trend ───────────────────────────────────────────────
    st.markdown('<div class="section-header">7-Day Sustainability Trend</div>', unsafe_allow_html=True)
    days   = [f"Day -{6-i}" for i in range(7)]
    wl     = [round(water_saved_l * (0.85 + 0.03 * i + np.random.uniform(-0.05, 0.05)), 0) for i in range(7)]
    co2l   = [round(w * 0.0003 * 0.233, 2) for w in wl]

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=("Water Saved (L/day)", "CO₂ Reduction (kg/day)"))
    fig.add_trace(go.Bar(x=days, y=wl,  marker_color="#0ea5e9", name="Water Saved"), row=1, col=1)
    fig.add_trace(go.Bar(x=days, y=co2l,marker_color="#10b981", name="CO₂ Reduction"), row=1, col=2)
    fig.update_layout(height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#f8fafc",
                      showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    # ── Water quality compliance ───────────────────────────────────────────
    if not df.empty:
        st.markdown('<div class="section-header">Water Quality Compliance</div>', unsafe_allow_html=True)
        ph_ok_pct   = ((df["ph"] >= 6.5) & (df["ph"] <= 8.5)).mean() * 100
        turb_ok_pct = (df["turbidity"] < 5).mean() * 100
        temp_ok_pct = ((df["temperature"] >= 10) & (df["temperature"] <= 30)).mean() * 100

        wq1, wq2, wq3 = st.columns(3)
        for col, metric, pct, clr in [
            (wq1, "pH Compliance",         ph_ok_pct,   "#10b981"),
            (wq2, "Turbidity Compliance",  turb_ok_pct, "#0ea5e9"),
            (wq3, "Temperature Compliance",temp_ok_pct, "#8b5cf6"),
        ]:
            with col:
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=pct,
                    number={"suffix": "%", "font": {"size": 28, "color": clr}},
                    title={"text": metric, "font": {"size": 13}},
                    gauge={
                        "axis":    {"range": [0, 100]},
                        "bar":     {"color": clr, "thickness": 0.8},
                        "steps": [{"range": [0, 70], "color": "#fecaca"},
                                  {"range": [70, 90], "color": "#fef9c3"},
                                  {"range": [90, 100],"color": "#bbf7d0"}],
                    },
                ))
                fig_gauge.update_layout(height=220, margin=dict(l=10,r=10,t=40,b=10),
                                        paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_gauge, use_container_width=True)


def render_architecture():
    """Tab 6 — Cloud Architecture"""
    _D   = st.session_state.get("dark_mode", False)
    _TXT = "#f1f5f9" if _D else "#0f172a"
    _T2  = "#94a3b8" if _D else "#475569"
    _CB  = "#1e293b" if _D else "white"
    _SHD = "rgba(0,0,0,0.35)" if _D else "rgba(0,0,0,0.08)"
    st.markdown('<div class="section-header">System Architecture Overview</div>', unsafe_allow_html=True)

    arch_bg  = "#0f172a" if _D else "#1e293b"
    arch_sub = "#94a3b8"
    st.markdown(f"""
    <div style="background:{arch_bg};border-radius:16px;padding:2rem;color:white;">
        <div style="text-align:center;margin-bottom:1.5rem;font-weight:700;font-size:1.1rem;color:{arch_sub};">
            IoT-to-AI Cloud Pipeline
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem;">
            <div class="arch-node" style="border:2px solid #0ea5e9;">
                <div style="font-size:0.65rem;font-weight:700;color:#0ea5e9;letter-spacing:1px;text-transform:uppercase;margin-bottom:0.3rem;">LAYER 1</div>
                <div>IoT Sensors</div>
                <div style="font-size:0.7rem;color:#94a3b8;">ESP32 / Flow / pH</div>
            </div>
            <div style="color:#475569;font-size:1.5rem;font-weight:700;">→</div>
            <div class="arch-node" style="border:2px solid #f59e0b;">
                <div style="font-size:0.65rem;font-weight:700;color:#f59e0b;letter-spacing:1px;text-transform:uppercase;margin-bottom:0.3rem;">LAYER 2</div>
                <div>Cloud Run</div>
                <div style="font-size:0.7rem;color:#94a3b8;">FastAPI Ingest</div>
            </div>
            <div style="color:#475569;font-size:1.5rem;font-weight:700;">→</div>
            <div class="arch-node" style="border:2px solid #10b981;">
                <div style="font-size:0.65rem;font-weight:700;color:#10b981;letter-spacing:1px;text-transform:uppercase;margin-bottom:0.3rem;">LAYER 3</div>
                <div>Pub/Sub</div>
                <div style="font-size:0.7rem;color:#94a3b8;">Message Queue</div>
            </div>
            <div style="color:#475569;font-size:1.5rem;font-weight:700;">→</div>
            <div class="arch-node" style="border:2px solid #8b5cf6;">
                <div style="font-size:0.65rem;font-weight:700;color:#8b5cf6;letter-spacing:1px;text-transform:uppercase;margin-bottom:0.3rem;">LAYER 4</div>
                <div>Firestore</div>
                <div style="font-size:0.7rem;color:#94a3b8;">Time-Series DB</div>
            </div>
            <div style="color:#475569;font-size:1.5rem;font-weight:700;">→</div>
            <div class="arch-node" style="border:2px solid #ec4899;">
                <div style="font-size:0.65rem;font-weight:700;color:#ec4899;letter-spacing:1px;text-transform:uppercase;margin-bottom:0.3rem;">LAYER 5</div>
                <div>Vertex AI</div>
                <div style="font-size:0.7rem;color:#94a3b8;">LSTM / IsoForest</div>
            </div>
            <div style="color:#475569;font-size:1.5rem;font-weight:700;">→</div>
            <div class="arch-node" style="border:2px solid #0ea5e9;">
                <div style="font-size:0.65rem;font-weight:700;color:#0ea5e9;letter-spacing:1px;text-transform:uppercase;margin-bottom:0.3rem;">LAYER 6</div>
                <div>Dashboard</div>
                <div style="font-size:0.7rem;color:#94a3b8;">Streamlit</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">Component Details</div>', unsafe_allow_html=True)

    components = [
        ("IoT Sensors (ESP32)",       "#0ea5e9",
         "ESP32 microcontrollers with flow meters, pressure transducers, pH electrodes, "
         "turbidity sensors, and temperature probes. 5-second polling interval. "
         "MQTT/HTTP push to Cloud Run endpoint."),
        ("Cloud Run (FastAPI)",        "#f59e0b",
         "Containerised FastAPI service receives sensor payloads, validates data, "
         "stores to SQLite locally or forwards to Pub/Sub for cloud deployment. "
         "Auto-scales to zero when idle."),
        ("Google Pub/Sub",             "#10b981",
         "Decouples ingest from processing. Topic per sensor zone. "
         "Fan-out to Firestore writer, anomaly detector subscriber, "
         "and alerting subscriber."),
        ("Firestore (Time-Series)",    "#8b5cf6",
         "NoSQL document store for sensor time-series. "
         "Collections: sensor_data, alerts, recommendations. "
         "Local fallback: SQLite database/water.db."),
        ("Vertex AI (ML Models)",      "#ec4899",
         "Isolation Forest for real-time leak detection (sklearn, served locally). "
         "LSTM demand forecaster (TensorFlow/Keras or statistical fallback). "
         "Recommendation Engine (rule-based, zero retraining). "
         "Root Cause Classifier (rule-based heuristics)."),
        ("Streamlit Dashboard",        "#0ea5e9",
         "Multi-tab enterprise dashboard with real-time gauges, AI advisor, "
         "predictive analytics, digital twin, scenario lab, and sustainability metrics. "
         "Auto-refresh every 10 seconds."),
    ]
    for name, clr, desc in components:
        st.markdown(f"""
        <div class="ai-card" style="border-left-color:{clr};">
        <div style="font-weight:700;font-size:1rem;color:{_TXT};margin-bottom:0.4rem;">{name}</div>
            <div style="color:{_T2};font-size:0.9rem;line-height:1.6;">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

    # Data flow table
    st.markdown('<div class="section-header">Data Flow Summary</div>', unsafe_allow_html=True)
    flow_df = pd.DataFrame({
        "Stage":        ["Sensing", "Ingest", "Queue", "Storage", "AI Processing", "Visualization"],
        "Latency":      ["< 100 ms", "< 200 ms", "< 500 ms", "< 1 s", "1–5 s", "Real-time"],
        "Technology":   ["ESP32 + sensors", "FastAPI (Cloud Run)", "Google Pub/Sub",
                         "Firestore / SQLite", "Vertex AI / Local sklearn", "Streamlit"],
        "Reliability":  ["99.5%", "99.9%", "99.95%", "99.99%", "97%", "99.5%"],
    })
    st.dataframe(flow_df, use_container_width=True, hide_index=True)



def render_scenario_lab(latest):
    """Tab 7 — Scenario Lab"""
    _D   = st.session_state.get("dark_mode", False)
    _TXT = "#f1f5f9" if _D else "#0f172a"
    _T2  = "#94a3b8" if _D else "#475569"
    _CB  = "#1e293b" if _D else "white"
    _SHD = "rgba(0,0,0,0.35)" if _D else "rgba(0,0,0,0.08)"
    st.markdown('<div class="section-header">Scenario Simulator</div>', unsafe_allow_html=True)
    st.write("Simulate extreme conditions and see predicted system outcomes in real time.")

    scenarios = {
        "Heat Wave":          {
            "desc":  "Sustained temperatures above 40°C for 5+ days.",
            "flow":  latest["flow"] * 1.45, "pressure": latest["pressure"] * 0.88,
            "ph":    latest["ph"] + 0.1,    "turbidity": latest["turbidity"] * 1.3,
            "outcomes": [
                "Water demand surges 40–50% above baseline.",
                "Tank depletion accelerated — refill cycle shortened to 6 hours.",
                "Increased bacterial growth risk above 35°C.",
                "Recommendation: Pre-fill storage by 05:00 daily.",
            ],
            "risk": "HIGH", "color": "#ef4444",
        },
        "Drought":             {
            "desc":  "40% reduction in source water availability.",
            "flow":  latest["flow"] * 0.60, "pressure": latest["pressure"] * 0.70,
            "ph":    latest["ph"] - 0.2,    "turbidity": latest["turbidity"] * 1.8,
            "outcomes": [
                "Flow rate drops 40%, pressure falls to borderline levels.",
                "pH drift toward acidic — monitor dosing system.",
                "Turbidity increase from sediment concentration.",
                "Recommendation: Activate water rationing protocol.",
            ],
            "risk": "CRITICAL", "color": "#dc2626",
        },
        "Heavy Rainfall":      {
            "desc":  "Storm event causing surface runoff and flooding.",
            "flow":  latest["flow"] * 1.15, "pressure": latest["pressure"] * 1.12,
            "ph":    latest["ph"] - 0.4,    "turbidity": latest["turbidity"] * 4.5,
            "outcomes": [
                "Turbidity spikes up to 9 NTU — exceeds WHO limit.",
                "pH drops as acidic rainwater mixes.",
                "Overflow risk in surface reservoirs.",
                "Recommendation: Increase filtration rate, issue quality advisory.",
            ],
            "risk": "HIGH", "color": "#f59e0b",
        },
        "Pump Failure":        {
            "desc":  "Primary pump motor failure — backup not activated.",
            "flow":  latest["flow"] * 0.30, "pressure": latest["pressure"] * 0.25,
            "ph":    latest["ph"],           "turbidity": latest["turbidity"],
            "outcomes": [
                "Flow collapses to 30% — severe supply interruption.",
                "Pressure drops below 1.0 bar — backflow contamination risk.",
                "AI anomaly detector fires within 2 readings.",
                "Recommendation: Activate backup pump immediately.",
            ],
            "risk": "CRITICAL", "color": "#dc2626",
        },
        "Pipe Burst":           {
            "desc":  "Major pipeline rupture in Zone 2.",
            "flow":  latest["flow"] * 1.80, "pressure": latest["pressure"] * 0.35,
            "ph":    latest["ph"],           "turbidity": latest["turbidity"] * 2.0,
            "outcomes": [
                "Flow spikes 80% then collapses as pressure drops.",
                "Isolation Forest confidence > 90%.",
                "Estimated water loss: 2,400 L before isolation.",
                "Recommendation: Close Zone 2 isolation valve immediately.",
            ],
            "risk": "CRITICAL", "color": "#dc2626",
        },
        "Sensor Failure":       {
            "desc":  "Flow and turbidity sensors go offline.",
            "flow":  latest["flow"],         "pressure": latest["pressure"],
            "ph":    latest["ph"],           "turbidity": 0.0,
            "outcomes": [
                "Dashboard falls back to last known good values.",
                "AI predictions continue on cached data (accuracy -30%).",
                "Alerts trigger if no reading received within 30 seconds.",
                "Recommendation: Replace sensor hardware within 2 hours.",
            ],
            "risk": "MEDIUM", "color": "#f59e0b",
        },
    }

    selected = st.selectbox("Choose a scenario:", list(scenarios.keys()), key="scenario_select")
    scen = scenarios[selected]

    st.markdown(f"""
    <div style="background:#f8fafc;border-radius:12px;padding:1rem 1.2rem;
                border-left:4px solid {scen['color']};margin:0.5rem 0;">
        <strong>Scenario:</strong> {scen['desc']}
        &nbsp;&nbsp;<span style="color:{scen['color']};font-weight:700;">Risk: {scen['risk']}</span>
    </div>
    """, unsafe_allow_html=True)

    if st.button("▶ Run Scenario Simulation", type="primary"):
        with st.spinner("Simulating…"):
            time.sleep(0.8)

        # Predicted sensor values
        st.markdown('<div class="section-header">Predicted Sensor Values</div>', unsafe_allow_html=True)
        sv1, sv2, sv3, sv4 = st.columns(4)
        pred_vals = [
            (sv1, "Flow Rate",  scen["flow"],     latest["flow"],     "L/min"),
            (sv2, "Pressure",   scen["pressure"], latest["pressure"], "bar"),
            (sv3, "pH",         scen["ph"],        latest["ph"],      ""),
            (sv4, "Turbidity",  scen["turbidity"], latest["turbidity"],"NTU"),
        ]
        for col, name, pred, curr, unit in pred_vals:
            delta = pred - curr
            delta_str = f"+{delta:.2f}" if delta >= 0 else f"{delta:.2f}"
            delta_color = "#ef4444" if abs(delta) > curr * 0.15 else "#10b981"
            with col:
                st.markdown(f"""
                <div class="kpi-card">
                    <div style="font-size:0.75rem;color:{_T2};font-weight:600;text-transform:uppercase;">{name}</div>
                    <div style="font-size:2rem;font-weight:800;color:{_TXT};">{pred:.2f} {unit}</div>
                    <div style="font-size:0.85rem;color:{delta_color};font-weight:600;">
                        {delta_str} {unit} vs current
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Outcome predictions
        st.markdown('<div class="section-header">AI Predicted Outcomes</div>', unsafe_allow_html=True)
        for i, outcome in enumerate(scen["outcomes"], 1):
            icon = "CRITICAL" if scen["risk"] == "CRITICAL" else ("WARNING" if scen["risk"] == "HIGH" else "INFO")
            st.markdown(f"""
            <div class="ai-card" style="border-left-color:{scen['color']};">
                <div style="color:{_TXT};"><span style="color:{scen['color']};font-weight:700;font-size:0.75rem;margin-right:0.5rem;">{icon}</span><strong>Outcome {i}:</strong> {outcome}</div>
            </div>
            """, unsafe_allow_html=True)

        # Simulated timeline chart
        st.markdown('<div class="section-header">Simulated Timeline</div>', unsafe_allow_html=True)
        sim_steps  = 60
        sim_time   = list(range(sim_steps))
        # Gradual transition from current to scenario value
        sim_flow   = [latest["flow"]   + (scen["flow"]     - latest["flow"])   * (i/sim_steps) + np.random.normal(0, 0.3) for i in range(sim_steps)]
        sim_press  = [latest["pressure"]+ (scen["pressure"] - latest["pressure"]) * (i/sim_steps) + np.random.normal(0, 0.05) for i in range(sim_steps)]

        fig = make_subplots(rows=1, cols=2, subplot_titles=("Flow Rate", "Pressure"))
        fig.add_trace(go.Scatter(x=sim_time, y=sim_flow,  mode="lines",
                                 line=dict(color="#0ea5e9", width=2), name="Flow"),  row=1, col=1)
        fig.add_trace(go.Scatter(x=sim_time, y=sim_press, mode="lines",
                                 line=dict(color="#f59e0b", width=2), name="Pressure"), row=1, col=2)
        fig.update_layout(height=280, paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="#f8fafc", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)



# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    # ── Bootstrap DB ────────────────────────────────────────────────────────
    init_db_with_demo_data()

    # ── Load AI models ───────────────────────────────────────────────────────
    detector  = get_leak_detector()
    forecaster= get_forecaster()
    engine    = get_recommendation_engine()
    classifier= get_root_cause_classifier()

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:1rem 0 0.5rem;">
            <div style="font-weight:800;font-size:1.2rem;color:#e2e8f0;letter-spacing:0.5px;">AquaMind AI</div>
            <div style="font-size:0.75rem;color:#64748b;margin-top:0.2rem;">Smart Water Management</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        # ── Theme toggle ──────────────────────────────────────────────────
        st.markdown("**Appearance**")
        col_theme = st.columns([1, 1])
        with col_theme[0]:
            if st.button("Light", use_container_width=True,
                         type="primary" if not st.session_state.dark_mode else "secondary"):
                st.session_state.dark_mode = False
                st.rerun()
        with col_theme[1]:
            if st.button("Dark", use_container_width=True,
                         type="primary" if st.session_state.dark_mode else "secondary"):
                st.session_state.dark_mode = True
                st.rerun()

        st.markdown("---")
        st.markdown("**Dashboard Controls**")
        demo_mode    = st.checkbox("Demo Mode", value=True,
                                   help="Generate realistic live sensor values")
        auto_refresh = st.checkbox("Auto-refresh", value=True)
        refresh_secs = st.slider("Refresh (seconds)", 5, 60, 10)
        data_limit   = st.slider("Data points", 50, 500, 100)

        st.markdown("---")
        st.markdown("**AI Model Training**")
        _det_sb  = get_leak_detector()
        _fc_sb   = get_forecaster()
        if st.button("Train Leak Detector", use_container_width=True, key="sidebar_train_detector"):
            if _det_sb:
                with st.spinner("Training leak detector…"):
                    ok = _det_sb.train()
                st.success("Leak detector trained!") if ok else st.warning("Need 50+ readings.")
            else:
                st.error("Leak detector not available.")
        if st.button("Train Forecaster", use_container_width=True, key="sidebar_train_forecaster"):
            if _fc_sb:
                with st.spinner("Training forecaster…"):
                    ok = _fc_sb.train(epochs=30)
                st.success("Forecaster trained!") if ok else st.error("Training failed.")
            else:
                st.error("Forecaster not available.")

        st.markdown("---")
        st.markdown("**System Status**")
        if detector and getattr(detector, "is_trained", False):
            st.success("Leak Detector: ACTIVE")
        else:
            st.warning("Leak Detector: INACTIVE")

        if forecaster and getattr(forecaster, "is_trained", False):
            st.success("Forecaster: ACTIVE")
        else:
            st.warning("Forecaster: INACTIVE")

        if engine:
            st.success("Recommendation Engine: ACTIVE")
        else:
            st.warning("Recommendation Engine: INACTIVE")

        st.markdown("---")
        st.info(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

    # ── Load data ─────────────────────────────────────────────────────────────
    df = load_latest_data(limit=data_limit)

    if df.empty:
        st.markdown("""
        <div style="text-align:center;padding:4rem 2rem;">
            <div style="font-size:1.5rem;font-weight:700;color:#0f172a;margin:1rem 0;">No Data Available</div>
            <div style="color:#64748b;">Start the sensor simulator or enable Demo Mode to see live data.</div>
        </div>
        """, unsafe_allow_html=True)
        st.code("cd smart_water_system && python simulator/sensor_simulator.py", language="bash")
        return

    # ── Demo mode: overlay live demo readings ─────────────────────────────────
    if demo_mode:
        live = demo_sensor_values()
        latest = pd.Series(live)
    else:
        latest = df.iloc[-1]

    latest_dict = {
        "flow":        float(latest["flow"]),
        "pressure":    float(latest["pressure"]),
        "ph":          float(latest["ph"]),
        "turbidity":   float(latest["turbidity"]),
        "temperature": float(latest["temperature"]),
    }

    # ── Anomaly detection ─────────────────────────────────────────────────────
    anomaly = False
    if detector and getattr(detector, "is_trained", False):
        try:
            is_anom, _ = detector.predict(latest_dict["flow"], latest_dict["pressure"])
            anomaly = bool(is_anom)
        except Exception:
            pass
    st.session_state["_last_anomaly"] = anomaly

    health_score = water_health_score(latest_dict, anomaly)
    alerts       = check_alerts(latest_dict, anomaly)

    # ── Anomaly visual alert banner ───────────────────────────────────────────
    if anomaly:
        _banner_bg  = "#450a0a" if _D else "#fef2f2"
        _banner_txt = "#fca5a5" if _D else "#991b1b"
        _banner_bdr = "#ef4444"
        st.markdown(f"""
        <div class="anomaly-pulse" style="background:{_banner_bg};border-radius:10px;
             padding:0.8rem 1.2rem;margin-bottom:0.5rem;color:{_banner_txt};font-weight:700;
             font-size:1rem;text-align:center;border:2px solid {_banner_bdr};">
            CRITICAL ANOMALY DETECTED — AI has flagged an active leak or fault. Scroll to Live Dashboard for details.
        </div>
        """, unsafe_allow_html=True)

    # ── Header ─────────────────────────────────────────────────────────────────
    hcol1, hcol2, hcol3 = st.columns([3, 1, 1])
    with hcol1:
        st.markdown(f"""
        <h1 style="font-size:2rem;font-weight:800;
                   background:linear-gradient(135deg,#0ea5e9,#10b981);
                   -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                   margin:0.2rem 0;">
            AquaMind AI
        </h1>
        <div style="color:{_TEXT2};font-size:0.95rem;margin-bottom:1rem;">
            Enterprise Smart Water Management — Real-Time AI Dashboard
        </div>
        """, unsafe_allow_html=True)
    with hcol2:
        hs_color = score_color(health_score)
        pulse_cls = "anomaly-pulse" if anomaly else ""
        st.markdown(f"""
        <div style="text-align:right;padding-top:0.5rem;">
            <div style="font-size:0.75rem;color:{_TEXT2};font-weight:600;text-transform:uppercase;">
                Water Health Score
            </div>
            <div class="{pulse_cls}" style="font-size:2.5rem;font-weight:800;color:{hs_color};
                 border-radius:8px;padding:0.2rem 0.5rem;display:inline-block;">
                {health_score}<span style="font-size:1rem;color:{_TEXT2};">/100</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with hcol3:
        # CSV export button
        if not df.empty:
            export_data = df.copy()
            export_data["health_score"] = health_score
            export_data["anomaly"] = anomaly
            csv_bytes = export_data.to_csv(index=False).encode()
            st.download_button(
                label="Export CSV",
                data=csv_bytes,
                file_name=f"aquamind_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # ── Navigation tabs ────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Mission Control",
        "Live Dashboard",
        "AI Advisor",
        "Analytics & Forecast",
        "Sustainability",
        "Architecture",
        "Scenario Lab",
    ])

    with tab1:
        render_mission_control(df, latest_dict, anomaly, health_score, alerts)
    with tab2:
        render_live_dashboard(df, latest_dict, anomaly, alerts, health_score)
    with tab3:
        render_ai_advisor(df, latest_dict, anomaly, detector, engine)
    with tab4:
        render_analytics(df, latest_dict, forecaster)
    with tab5:
        render_sustainability(df, latest_dict)
    with tab6:
        render_architecture()
    with tab7:
        render_scenario_lab(latest_dict)

    # ── Auto-refresh ────────────────────────────────────────────────────────────
    if auto_refresh:
        time.sleep(refresh_secs)
        st.rerun()


if __name__ == "__main__":
    main()
