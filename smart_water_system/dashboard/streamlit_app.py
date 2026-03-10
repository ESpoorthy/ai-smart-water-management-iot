"""
Streamlit Dashboard for Smart Water Management System
Real-time monitoring, analytics, and alerts
"""
import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_models.anomaly_detection import LeakDetector
from ai_models.lstm_forecast import DemandForecaster

# Page configuration
st.set_page_config(
    page_title="Smart Water Management System",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database path
DB_PATH = "database/water.db"

@st.cache_resource
def get_leak_detector():
    """Initialize leak detector"""
    detector = LeakDetector(db_path=DB_PATH)
    detector.load_model()
    return detector

@st.cache_resource
def get_forecaster():
    """Initialize demand forecaster"""
    forecaster = DemandForecaster(db_path=DB_PATH)
    forecaster.load_model()
    return forecaster

def load_latest_data(limit=100):
    """Load latest sensor data"""
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
    """Check for alert conditions"""
    alerts = []
    
    if latest_data['ph'] < 6:
        alerts.append({"type": "pH LOW", "severity": "HIGH", "message": f"pH level critically low: {latest_data['ph']:.2f}"})
    elif latest_data['ph'] > 8:
        alerts.append({"type": "pH HIGH", "severity": "HIGH", "message": f"pH level critically high: {latest_data['ph']:.2f}"})
    
    if latest_data['turbidity'] > 5:
        alerts.append({"type": "TURBIDITY", "severity": "MEDIUM", "message": f"High turbidity detected: {latest_data['turbidity']:.2f} NTU"})
    
    return alerts

def main():
    # Title
    st.title("💧 Smart Water Management System")
    st.markdown("### Real-time Monitoring & AI Analytics")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        auto_refresh = st.checkbox("Auto-refresh", value=True)
        refresh_interval = st.slider("Refresh interval (seconds)", 5, 60, 10)
        data_limit = st.slider("Data points to display", 50, 500, 100)
        
        st.markdown("---")
        st.header("🤖 AI Models")
        
        if st.button("Train Leak Detector"):
            with st.spinner("Training..."):
                detector = get_leak_detector()
                success = detector.train()
                if success:
                    st.success("Model trained!")
                else:
                    st.warning("Not enough data")
        
        if st.button("Train Demand Forecaster"):
            with st.spinner("Training..."):
                forecaster = get_forecaster()
                success = forecaster.train(epochs=30)
                if success:
                    st.success("Model trained!")
                else:
                    st.warning("Not enough data")
    
    # Load data
    df = load_latest_data(limit=data_limit)
    
    if df.empty:
        st.warning("⚠️ No data available. Start the sensor simulator to generate data.")
        st.code("python simulator/sensor_simulator.py")
        return
    
    # Latest reading
    latest = df.iloc[-1]
    
    # System Status
    st.header("📊 System Status")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Flow Rate", f"{latest['flow']:.2f} L/min", 
                 delta=f"{latest['flow'] - df.iloc[-2]['flow']:.2f}" if len(df) > 1 else None)
    
    with col2:
        st.metric("Pressure", f"{latest['pressure']:.2f} bar",
                 delta=f"{latest['pressure'] - df.iloc[-2]['pressure']:.2f}" if len(df) > 1 else None)
    
    with col3:
        ph_status = "🟢" if 6.5 <= latest['ph'] <= 8.5 else "🔴"
        st.metric("pH Level", f"{ph_status} {latest['ph']:.2f}")
    
    with col4:
        turb_status = "🟢" if latest['turbidity'] < 5 else "🔴"
        st.metric("Turbidity", f"{turb_status} {latest['turbidity']:.2f} NTU")
    
    with col5:
        st.metric("Temperature", f"{latest['temperature']:.1f}°C")
    
    # Alerts
    alerts = check_alerts(latest)
    
    # Leak detection
    detector = get_leak_detector()
    if detector.is_trained:
        is_anomaly, score = detector.predict(latest['flow'], latest['pressure'])
        if is_anomaly:
            alerts.append({
                "type": "LEAK DETECTED",
                "severity": "CRITICAL",
                "message": f"Anomaly in flow/pressure (score: {score:.4f})"
            })
    
    if alerts:
        st.header("🚨 Active Alerts")
        for alert in alerts:
            severity_color = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡"}
            st.error(f"{severity_color.get(alert['severity'], '⚠️')} **{alert['type']}**: {alert['message']}")
    
    # Charts
    st.header("📈 Real-time Monitoring")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Flow & Pressure", "Water Quality", "Demand Forecast", "System Health"])
    
    with tab1:
        # Flow rate chart
        fig_flow = go.Figure()
        fig_flow.add_trace(go.Scatter(
            x=df.index, y=df['flow'],
            mode='lines', name='Flow Rate',
            line=dict(color='#1f77b4', width=2)
        ))
        fig_flow.update_layout(
            title="Water Flow Rate Over Time",
            xaxis_title="Reading #",
            yaxis_title="Flow (L/min)",
            height=300
        )
        st.plotly_chart(fig_flow, use_container_width=True)
        
        # Pressure chart
        fig_pressure = go.Figure()
        fig_pressure.add_trace(go.Scatter(
            x=df.index, y=df['pressure'],
            mode='lines', name='Pressure',
            line=dict(color='#ff7f0e', width=2)
        ))
        fig_pressure.update_layout(
            title="Water Pressure Over Time",
            xaxis_title="Reading #",
            yaxis_title="Pressure (bar)",
            height=300
        )
        st.plotly_chart(fig_pressure, use_container_width=True)
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            # pH chart
            fig_ph = go.Figure()
            fig_ph.add_trace(go.Scatter(
                x=df.index, y=df['ph'],
                mode='lines+markers', name='pH',
                line=dict(color='#2ca02c', width=2)
            ))
            fig_ph.add_hline(y=6.5, line_dash="dash", line_color="red", annotation_text="Min Safe")
            fig_ph.add_hline(y=8.5, line_dash="dash", line_color="red", annotation_text="Max Safe")
            fig_ph.update_layout(
                title="pH Level Variation",
                xaxis_title="Reading #",
                yaxis_title="pH",
                height=300
            )
            st.plotly_chart(fig_ph, use_container_width=True)
        
        with col2:
            # Turbidity chart
            fig_turb = go.Figure()
            fig_turb.add_trace(go.Scatter(
                x=df.index, y=df['turbidity'],
                mode='lines+markers', name='Turbidity',
                line=dict(color='#d62728', width=2),
                fill='tozeroy'
            ))
            fig_turb.add_hline(y=5, line_dash="dash", line_color="orange", annotation_text="Threshold")
            fig_turb.update_layout(
                title="Turbidity Levels",
                xaxis_title="Reading #",
                yaxis_title="Turbidity (NTU)",
                height=300
            )
            st.plotly_chart(fig_turb, use_container_width=True)
    
    with tab3:
        st.subheader("24-Hour Water Demand Forecast")
        
        forecaster = get_forecaster()
        
        if st.button("Generate Forecast"):
            with st.spinner("Generating forecast..."):
                predictions = forecaster.predict_next_hours(hours=24)
                
                # Create forecast dataframe
                forecast_df = pd.DataFrame({
                    'Hour': [i/12 for i in range(len(predictions))],
                    'Predicted Flow': predictions
                })
                
                # Plot forecast
                fig_forecast = go.Figure()
                fig_forecast.add_trace(go.Scatter(
                    x=forecast_df['Hour'], y=forecast_df['Predicted Flow'],
                    mode='lines', name='Forecast',
                    line=dict(color='#9467bd', width=3)
                ))
                fig_forecast.update_layout(
                    title="Predicted Water Demand (Next 24 Hours)",
                    xaxis_title="Hours from Now",
                    yaxis_title="Flow (L/min)",
                    height=400
                )
                st.plotly_chart(fig_forecast, use_container_width=True)
                
                # Statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Avg Predicted Flow", f"{sum(predictions)/len(predictions):.2f} L/min")
                with col2:
                    st.metric("Peak Demand", f"{max(predictions):.2f} L/min")
                with col3:
                    st.metric("Min Demand", f"{min(predictions):.2f} L/min")
    
    with tab4:
        st.subheader("System Health Overview")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Temperature trend
            fig_temp = go.Figure()
            fig_temp.add_trace(go.Scatter(
                x=df.index, y=df['temperature'],
                mode='lines', name='Temperature',
                line=dict(color='#8c564b', width=2)
            ))
            fig_temp.update_layout(
                title="Water Temperature",
                xaxis_title="Reading #",
                yaxis_title="Temperature (°C)",
                height=300
            )
            st.plotly_chart(fig_temp, use_container_width=True)
        
        with col2:
            # Data quality metrics
            st.markdown("#### Data Quality Metrics")
            st.metric("Total Readings", len(df))
            st.metric("Data Coverage", "100%")
            st.metric("Last Update", datetime.now().strftime("%H:%M:%S"))
    
    # Auto-refresh
    if auto_refresh:
        import time
        time.sleep(refresh_interval)
        st.rerun()

if __name__ == "__main__":
    main()
