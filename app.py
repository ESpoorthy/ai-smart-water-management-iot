"""
Complete Enhanced Interactive Dashboard for Smart Water Management System
Crystal-clear visualization with colorful, user-friendly interface
Based on research paper requirements
"""
import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import sys
import os
import numpy as np
from plotly.subplots import make_subplots

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "smart_water_system"))

from ai_models.anomaly_detection import LeakDetector
from ai_models.lstm_forecast import DemandForecaster
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

# Page configuration
st.set_page_config(
    page_title="AI-Driven Smart Water Management System",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced Custom CSS
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(to bottom, #f0f9ff, #e0f2fe);
    }
    
    .main-title {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(120deg, #0c4a6e, #0284c7, #0ea5e9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    .sub-title {
        font-size: 1.3rem;
        color: #475569;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 500;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-left: 5px solid #3b82f6;
        margin: 1rem 0;
    }
    
    .alert-critical {
        background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 6px solid #dc2626;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(220, 38, 38, 0.2);
    }
    
    .alert-warning {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 6px solid #f59e0b;
        margin: 1rem 0;
    }
    
    .alert-success {
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 6px solid #10b981;
        margin: 1rem 0;
    }
    
    .status-badge {
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
        color: white;
    }
    
    .section-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1e293b;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #3b82f6;
    }
</style>
""", unsafe_allow_html=True)

# Absolute paths — safe regardless of which directory Streamlit is launched from
_ROOT       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smart_water_system")
DB_PATH     = os.path.join(_ROOT, "database", "water.db")
_LEAK_MODEL = os.path.join(_ROOT, "ai_models", "leak_model.pkl")
_LSTM_MODEL = os.path.join(_ROOT, "ai_models", "lstm_model.h5")

def _demand_factor(step: int, total: int) -> float:
    """Return a 0-1 demand factor mapping step onto a full daily cycle."""
    hour = (step / total) * 24.0
    if hour < 6:
        return 0.35 + 0.05 * np.sin(np.pi * hour / 6)
    elif hour < 9:
        return 0.35 + 0.65 * ((hour - 6) / 3)
    elif hour < 12:
        return 0.90 + 0.10 * np.sin(np.pi * (hour - 9) / 3)
    elif hour < 17:
        return 0.70 + 0.10 * np.sin(np.pi * (hour - 12) / 5)
    elif hour < 20:
        return 0.75 + 0.25 * np.sin(np.pi * (hour - 17) / 3)
    elif hour < 22:
        return 0.75 - 0.40 * ((hour - 20) / 2)
    else:
        return 0.35 + 0.05 * np.cos(np.pi * (hour - 22) / 2)

@st.cache_resource
def init_db_with_demo_data():
    """
    Create the sensor_data table if it doesn't exist and seed 200 demo
    readings with a realistic daily demand pattern if the table is empty.
    Runs once per Streamlit process (cached by st.cache_resource).
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT    NOT NULL,
            flow      REAL    NOT NULL,
            pressure  REAL    NOT NULL,
            ph        REAL    NOT NULL,
            turbidity REAL    NOT NULL,
            temperature REAL  NOT NULL
        )
    """)
    conn.commit()

    # Seed only when empty
    count = cursor.execute("SELECT COUNT(*) FROM sensor_data").fetchone()[0]
    if count == 0:
        rng = np.random.default_rng(42)
        NUM = 200
        from datetime import timedelta
        base_time = datetime.now() - timedelta(minutes=NUM * 5)
        rows = []
        for i in range(NUM):
            d = _demand_factor(i, NUM)
            flow        = max(0.1, 5.0 + d * 20.0 + rng.normal(0, 0.6))
            pressure    = max(0.5, 2.8 - d * 0.6 + rng.normal(0, 0.08))
            ph          = float(np.clip(7.5 + rng.normal(0, 0.2), 6.5, 8.5))
            turbidity   = max(0.1, 1.5 + d * 1.2 + rng.normal(0, 0.3))
            hour        = (i / NUM) * 24.0
            temperature = 24.5 + 1.5 * np.sin(np.pi * (hour - 6) / 12) + rng.normal(0, 0.3)
            ts          = (base_time + timedelta(minutes=i * 5)).isoformat()
            rows.append((ts, round(float(flow), 3), round(float(pressure), 3),
                         round(ph, 3), round(float(turbidity), 3), round(float(temperature), 3)))

        cursor.executemany(
            "INSERT INTO sensor_data (timestamp, flow, pressure, ph, turbidity, temperature) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows
        )
        conn.commit()

    conn.close()
    return True

@st.cache_resource
def get_leak_detector():
    detector = LeakDetector(db_path=DB_PATH, model_path=_LEAK_MODEL)
    detector.load_model()
    return detector

@st.cache_resource
def get_forecaster():
    forecaster = DemandForecaster(db_path=DB_PATH, model_path=_LSTM_MODEL)
    forecaster.load_model()
    return forecaster

@st.cache_resource
def get_recommendation_engine():
    if not RECOMMENDATIONS_AVAILABLE:
        return None
    return WaterRecommendationEngine(db_path=DB_PATH)

def load_latest_data(limit=100):
    try:
        conn = sqlite3.connect(DB_PATH)
        query = f"SELECT * FROM sensor_data ORDER BY id DESC LIMIT {limit}"
        df = pd.read_sql_query(query, conn)
        conn.close()
        df = df.iloc[::-1].reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def check_alerts(latest_data):
    alerts = []
    
    if latest_data['ph'] < 6:
        alerts.append({
            "type": "pH CRITICALLY LOW",
            "severity": "CRITICAL",
            "message": f"pH level is {latest_data['ph']:.2f} (Safe range: 6.5-8.5)",
            "recommendation": "Immediate water quality assessment required"
        })
    elif latest_data['ph'] > 8.5:
        alerts.append({
            "type": "pH CRITICALLY HIGH",
            "severity": "CRITICAL",
            "message": f"pH level is {latest_data['ph']:.2f} (Safe range: 6.5-8.5)",
            "recommendation": "Check for contamination sources"
        })
    
    if latest_data['turbidity'] > 5:
        alerts.append({
            "type": "HIGH TURBIDITY",
            "severity": "WARNING",
            "message": f"Turbidity is {latest_data['turbidity']:.2f} NTU (Threshold: 5 NTU)",
            "recommendation": "Check for sediment or contamination"
        })
    
    return alerts

def create_gauge_chart(value, title, min_val, max_val, threshold_low, threshold_high, unit=""):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': f"<b>{title}</b>", 'font': {'size': 18}},
        number = {'suffix': f" {unit}", 'font': {'size': 28, 'color': '#1e40af'}},
        gauge = {
            'axis': {'range': [min_val, max_val], 'tickwidth': 2},
            'bar': {'color': "#3b82f6", 'thickness': 0.8},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#cbd5e1",
            'steps': [
                {'range': [min_val, threshold_low], 'color': '#fecaca'},
                {'range': [threshold_low, threshold_high], 'color': '#a7f3d0'},
                {'range': [threshold_high, max_val], 'color': '#fecaca'}
            ],
            'threshold': {
                'line': {'color': "#dc2626", 'width': 4},
                'thickness': 0.75,
                'value': value
            }
        }
    ))
    
    fig.update_layout(
        height=280,
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        font={'family': "Arial, sans-serif"}
    )
    
    return fig

def main():
    # Title
    st.markdown('<h1 class="main-title">AI-Driven Smart Water Management System</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Real-Time Monitoring & Predictive Analytics Dashboard</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### Dashboard Controls")
        auto_refresh = st.checkbox("Auto-refresh", value=True)
        refresh_interval = st.slider("Refresh (seconds)", 5, 60, 10)
        data_limit = st.slider("Data points", 50, 500, 100)
        
        st.markdown("---")
        st.markdown("### AI Model Training")
        
        if st.button("Train Leak Detector", use_container_width=True):
            with st.spinner("Training..."):
                detector = get_leak_detector()
                if detector.train():
                    st.success("Model trained successfully!")
                else:
                    st.warning("Need more data (50+ readings)")
        
        if st.button("Train Forecaster", use_container_width=True):
            with st.spinner("Training forecaster…"):
                try:
                    get_forecaster.clear()
                    # Use absolute paths so training works regardless of CWD
                    forecaster = DemandForecaster(db_path=DB_PATH, model_path=_LSTM_MODEL)
                    df_check = forecaster.load_data(limit=200)
                    if len(df_check) < 100:
                        st.warning(f"Need at least 100 readings — only {len(df_check)} in DB. "
                                   "Wait for the simulator to collect more data.")
                    elif forecaster.train(epochs=30):
                        from ai_models.lstm_forecast import TENSORFLOW_AVAILABLE as _TF_CHECK
                        tf_note = "" if _TF_CHECK else " (statistical model — TensorFlow not installed)"
                        # Refresh cache with the newly trained instance
                        get_forecaster.clear()
                        st.success(f"Forecaster trained successfully!{tf_note}")
                    else:
                        st.error("Training returned False — check terminal logs.")
                except Exception as _train_err:
                    st.error(f"Training error: {_train_err}")
                    import traceback
                    st.code(traceback.format_exc())
        
        st.markdown("---")
        st.markdown("### System Info")
        st.info(f"**Time:** {datetime.now().strftime('%H:%M:%S')}")
        
        detector = get_leak_detector()
        forecaster = get_forecaster()
        
        if detector.is_trained:
            st.success("Leak Detector: ACTIVE")
        else:
            st.warning("Leak Detector: INACTIVE")
        
        if forecaster.is_trained:
            from ai_models.lstm_forecast import TENSORFLOW_AVAILABLE as _TF
            model_type = "LSTM" if _TF else "Statistical"
            st.success(f"Forecaster: ACTIVE ({model_type})")
        else:
            st.warning("Forecaster: INACTIVE — click Train Forecaster")
    
    # Ensure DB exists and has demo data on first run (important for cloud deployments)
    init_db_with_demo_data()

    # Load data
    df = load_latest_data(limit=data_limit)
    
    if df.empty:
        st.warning("No data available. Start the sensor simulator.")
        st.code("python simulator/sensor_simulator.py", language="bash")
        return
    
    latest = df.iloc[-1]
    
    # Alerts
    alerts = check_alerts(latest)
    detector = get_leak_detector()
    
    if detector.is_trained:
        is_anomaly, score = detector.predict(latest['flow'], latest['pressure'])
        if is_anomaly:
            alerts.append({
                "type": "LEAK DETECTED",
                "severity": "CRITICAL",
                "message": f"Anomaly in flow/pressure (Confidence: {abs(score):.2%})",
                "recommendation": "Immediate inspection required"
            })
    
    if alerts:
        st.markdown('<h2 class="section-header">Active Alerts</h2>', unsafe_allow_html=True)
        for alert in alerts:
            if alert['severity'] == 'CRITICAL':
                st.markdown(f"""
                <div class="alert-critical">
                    <h3 style="color: #dc2626; margin-top: 0;">CRITICAL: {alert['type']}</h3>
                    <p><strong>Issue:</strong> {alert['message']}</p>
                    <p><strong>Action:</strong> {alert['recommendation']}</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="alert-warning">
                    <h3 style="color: #f59e0b; margin-top: 0;">WARNING: {alert['type']}</h3>
                    <p><strong>Issue:</strong> {alert['message']}</p>
                    <p><strong>Action:</strong> {alert['recommendation']}</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="alert-success">
            <h3 style="color: #10b981; margin-top: 0;">All Systems Normal</h3>
            <p>No alerts detected. All parameters within optimal range.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Gauges
    st.markdown('<h2 class="section-header">Real-Time System Metrics</h2>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fig = create_gauge_chart(latest['flow'], "Flow Rate", 0, 30, 10, 20, "L/min")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = create_gauge_chart(latest['ph'], "pH Level", 0, 14, 6.5, 8.5, "")
        st.plotly_chart(fig, use_container_width=True)
    
    with col3:
        fig = create_gauge_chart(latest['turbidity'], "Turbidity", 0, 10, 1, 5, "NTU")
        st.plotly_chart(fig, use_container_width=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = create_gauge_chart(latest['pressure'], "Pressure", 0, 5, 2.0, 3.0, "bar")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = create_gauge_chart(latest['temperature'], "Temperature", 0, 40, 15, 30, "°C")
        st.plotly_chart(fig, use_container_width=True)
    
    # Trend Charts
    st.markdown('<h2 class="section-header">Historical Trends & Analysis</h2>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["Flow & Pressure Analysis", "Water Quality Monitoring", "AI Predictions", "Decision Intelligence"])
    
    with tab1:
        # Combined Flow and Pressure
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=("Water Flow Rate Over Time", "Water Pressure Over Time"),
            vertical_spacing=0.15
        )
        
        fig.add_trace(
            go.Scatter(x=df.index, y=df['flow'], name="Flow Rate",
                      line=dict(color='#3b82f6', width=3),
                      fill='tozeroy', fillcolor='rgba(59, 130, 246, 0.1)'),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(x=df.index, y=df['pressure'], name="Pressure",
                      line=dict(color='#f59e0b', width=3),
                      fill='tozeroy', fillcolor='rgba(245, 158, 11, 0.1)'),
            row=2, col=1
        )
        
        fig.update_xaxes(title_text="Reading Number", row=2, col=1)
        fig.update_yaxes(title_text="Flow (L/min)", row=1, col=1)
        fig.update_yaxes(title_text="Pressure (bar)", row=2, col=1)
        
        fig.update_layout(height=600, showlegend=True, hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
        
        # Statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Avg Flow", f"{df['flow'].mean():.2f} L/min")
        with col2:
            st.metric("Peak Flow", f"{df['flow'].max():.2f} L/min")
        with col3:
            st.metric("Avg Pressure", f"{df['pressure'].mean():.2f} bar")
        with col4:
            st.metric("Peak Pressure", f"{df['pressure'].max():.2f} bar")
    
    with tab2:
        # pH and Turbidity
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=("pH Level Monitoring", "Turbidity Monitoring"),
            vertical_spacing=0.15
        )
        
        fig.add_trace(
            go.Scatter(x=df.index, y=df['ph'], name="pH Level",
                      line=dict(color='#10b981', width=3),
                      mode='lines+markers'),
            row=1, col=1
        )
        
        fig.add_hline(y=6.5, line_dash="dash", line_color="red", row=1, col=1)
        fig.add_hline(y=8.5, line_dash="dash", line_color="red", row=1, col=1)
        
        fig.add_trace(
            go.Scatter(x=df.index, y=df['turbidity'], name="Turbidity",
                      line=dict(color='#dc2626', width=3),
                      fill='tozeroy', fillcolor='rgba(220, 38, 38, 0.1)'),
            row=2, col=1
        )
        
        fig.add_hline(y=5, line_dash="dash", line_color="orange", row=2, col=1)
        
        fig.update_xaxes(title_text="Reading Number", row=2, col=1)
        fig.update_yaxes(title_text="pH Level", row=1, col=1)
        fig.update_yaxes(title_text="Turbidity (NTU)", row=2, col=1)
        
        fig.update_layout(height=600, showlegend=True, hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
        
        # Compliance
        ph_compliance = ((df['ph'] >= 6.5) & (df['ph'] <= 8.5)).sum() / len(df) * 100
        turb_compliance = (df['turbidity'] < 5).sum() / len(df) * 100
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("pH Compliance Rate", f"{ph_compliance:.1f}%")
        with col2:
            st.metric("Turbidity Compliance", f"{turb_compliance:.1f}%")
    
    with tab3:
        st.subheader("24-Hour Water Demand Forecast")

        forecaster = get_forecaster()

        if not forecaster.is_trained:
            st.info("Forecaster not trained yet. Click **Train Forecaster** in the sidebar to get started.")

        if st.button("Generate AI Forecast", type="primary"):
            with st.spinner("Generating 24-hour forecast..."):
                predictions = forecaster.predict_next_hours(hours=24)

                from ai_models.lstm_forecast import TENSORFLOW_AVAILABLE as _TF
                model_label = "LSTM Neural Network" if _TF else "Statistical (daily pattern)"

                forecast_df = pd.DataFrame({
                    'Hour': [i/12 for i in range(len(predictions))],
                    'Predicted Flow': predictions
                })

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=forecast_df['Hour'], y=forecast_df['Predicted Flow'],
                    mode='lines', name='Forecast',
                    line=dict(color='#8b5cf6', width=4),
                    fill='tozeroy', fillcolor='rgba(139, 92, 246, 0.2)'
                ))

                fig.update_layout(
                    title=f"Predicted Water Demand — Next 24 Hours ({model_label})",
                    xaxis_title="Hours from Now",
                    yaxis_title="Flow Rate (L/min)",
                    height=450,
                    hovermode='x unified'
                )
                st.plotly_chart(fig, use_container_width=True)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Average Demand", f"{np.mean(predictions):.2f} L/min")
                with col2:
                    st.metric("Peak Demand", f"{np.max(predictions):.2f} L/min")
                with col3:
                    st.metric("Min Demand", f"{np.min(predictions):.2f} L/min")
    
    with tab4:
        st.subheader("🧠 AI Decision Intelligence — Actionable Recommendations")
        st.markdown(
            "The recommendation engine analyses live sensor readings, anomaly scores, "
            "and demand forecasts to produce **prioritised, quantified actions** — "
            "not just alerts."
        )

        engine = get_recommendation_engine()
        if engine is None:
            st.info("Decision Intelligence module not available in this deployment. Run locally for full features.")
            st.stop()
        forecaster = get_forecaster()
        detector = get_leak_detector()
        classifier = AnomalyRootCauseClassifier() if ROOT_CAUSE_AVAILABLE else None

        # Determine anomaly status from latest reading
        anomaly_result = None
        if detector.is_trained:
            is_anomaly, score = detector.predict(latest['flow'], latest['pressure'])
            anomaly_result = {
                "is_anomaly": is_anomaly,
                "score": float(score),
                "flow": float(latest['flow']),
                "pressure": float(latest['pressure']),
                "ph": float(latest['ph']),
                "turbidity": float(latest['turbidity']),
                "temperature": float(latest['temperature']),
            }

        # Get forecast if available
        forecast = None
        if forecaster.is_trained:
            forecast = forecaster.predict_next_hours(hours=24)

        zone = st.selectbox(
            "Zone / Area",
            ["Zone-1 Main Supply", "Zone-2 Residential", "Zone-3 Industrial",
             "Zone-4 Agricultural", "Zone-5 Municipal"],
            key="rec_zone",
        )

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            run_recs = st.button("🔍 Generate Recommendations", type="primary", use_container_width=True)
        with col_btn2:
            send_alerts = st.button("🔔 Send Console Alerts for HIGH priority", use_container_width=True)

        if run_recs or send_alerts:
            with st.spinner("Analysing sensor data and generating recommendations…"):
                recs = engine.recommend_from_model_outputs(
                    zone=zone,
                    anomaly_result=anomaly_result,
                    forecast=forecast,
                )

            if not recs:
                st.success("✅ No actionable recommendations — all parameters within normal operating range.")
            else:
                # Summary KPIs
                high_count = sum(1 for r in recs if r["priority"] == "HIGH")
                med_count  = sum(1 for r in recs if r["priority"] == "MEDIUM")
                low_count  = sum(1 for r in recs if r["priority"] == "LOW")
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Total Recommendations", len(recs))
                k2.metric("🔴 HIGH Priority", high_count)
                k3.metric("🟡 MEDIUM Priority", med_count)
                k4.metric("🟢 LOW Priority", low_count)

                st.markdown("---")

                for rec in recs:
                    pri = rec["priority"]
                    colour = {"HIGH": "#dc2626", "MEDIUM": "#f59e0b", "LOW": "#10b981"}.get(pri, "#64748b")
                    icon   = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(pri, "⚪")

                    st.markdown(f"""
                    <div style="background:white;border-radius:12px;padding:1.2rem 1.5rem;
                                border-left:6px solid {colour};margin-bottom:1rem;
                                box-shadow:0 2px 8px rgba(0,0,0,.07);">
                        <div style="font-weight:700;font-size:1rem;color:{colour};">
                            {icon} [{pri}] {rec.get('category','').replace('_',' ').title()}
                        </div>
                        <div style="color:#1e293b;margin:.4rem 0;">{rec['message']}</div>
                        <div><strong>Action:</strong> {rec['recommended_action']}</div>
                        <div style="color:#10b981;font-weight:600;margin-top:.3rem;">
                            💰 {rec['estimated_impact']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Root cause classification for anomaly-flagged items
                    if classifier and rec.get("category") in ("leak_risk", "anomaly_flagged") and anomaly_result:
                        clf_result = classifier.classify(
                            flow=anomaly_result.get("flow"),
                            pressure=anomaly_result.get("pressure"),
                            ph=anomaly_result.get("ph"),
                            turbidity=anomaly_result.get("turbidity"),
                            temperature=anomaly_result.get("temperature"),
                            anomaly_score=anomaly_result.get("score"),
                        )
                        st.markdown(
                            f"&nbsp;&nbsp;&nbsp;🔎 **Root cause:** {clf_result['label']} "
                            f"({clf_result['confidence']} confidence) — "
                            f"*{clf_result['explanation']}*"
                        )

                    # Fire console alert for HIGH priority items when button clicked
                    if send_alerts and pri == "HIGH" and ALERTS_AVAILABLE:
                        send_alert(
                            level=AlertLevel.CRITICAL,
                            title=rec["message"][:100],
                            message=rec["message"],
                            zone=zone,
                            sensor_values=rec.get("sensor_snapshot", {}),
                            recommended_action=rec["recommended_action"],
                            estimated_impact=rec["estimated_impact"],
                            channels=["console"],
                        )

                if send_alerts and high_count > 0:
                    st.success(f"✅ {high_count} console alert(s) fired — check terminal output.")
                elif send_alerts:
                    st.info("No HIGH priority items to alert on.")

    # Auto-refresh
    if auto_refresh:
        import time
        time.sleep(refresh_interval)
        st.rerun()

if __name__ == "__main__":
    main()
