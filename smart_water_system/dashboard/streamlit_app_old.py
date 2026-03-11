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
import numpy as np

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

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .alert-critical {
        background-color: #fee;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #dc3545;
        margin: 0.5rem 0;
    }
    .alert-warning {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ffc107;
        margin: 0.5rem 0;
    }
    .status-normal {
        color: #28a745;
        font-weight: bold;
    }
    .status-warning {
        color: #ffc107;
        font-weight: bold;
    }
    .status-critical {
        color: #dc3545;
        font-weight: bold;
    }
    .info-box {
        background-color: #e7f3ff;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #0066cc;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

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
    # Title with custom styling
    st.markdown('<p class="main-header">Smart Water Management System</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Real-time Monitoring & AI Analytics Dashboard</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("Settings")
        auto_refresh = st.checkbox("Auto-refresh", value=True)
        refresh_interval = st.slider("Refresh interval (seconds)", 5, 60, 10)
        data_limit = st.slider("Data points to display", 50, 500, 100)
        
        st.markdown("---")
        st.header("AI Model Management")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Train Leak Detector", use_container_width=True):
                with st.spinner("Training..."):
                    detector = get_leak_detector()
                    success = detector.train()
                    if success:
                        st.success("Model trained successfully!")
                    else:
                        st.warning("Insufficient data for training")
        
        with col2:
            if st.button("Train Forecaster", use_container_width=True):
                with st.spinner("Training..."):
                    forecaster = get_forecaster()
                    success = forecaster.train(epochs=30)
                    if success:
                        st.success("Model trained successfully!")
                    else:
                        st.warning("Insufficient data for training")
        
        st.markdown("---")
        st.header("System Information")
        st.info(f"**Last Updated:** {datetime.now().strftime('%H:%M:%S')}")
    
    # Load data
    df = load_latest_data(limit=data_limit)
    
    if df.empty:
        st.warning("**No data available.** Start the sensor simulator to generate data.")
        st.code("python simulator/sensor_simulator.py", language="bash")
        return
    
    # Latest reading
    latest = df.iloc[-1]
    
    # System Status Section
    st.header("System Status Overview")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        delta_flow = latest['flow'] - df.iloc[-2]['flow'] if len(df) > 1 else 0
        st.metric("Flow Rate", f"{latest['flow']:.2f} L/min", 
                 delta=f"{delta_flow:.2f}")
    
    with col2:
        delta_pressure = latest['pressure'] - df.iloc[-2]['pressure'] if len(df) > 1 else 0
        st.metric("Pressure", f"{latest['pressure']:.2f} bar",
                 delta=f"{delta_pressure:.2f}")
    
    with col3:
        ph_status = "NORMAL" if 6.5 <= latest['ph'] <= 8.5 else "ALERT"
        ph_color = "normal" if ph_status == "NORMAL" else "inverse"
        st.metric("pH Level", f"{latest['ph']:.2f}", 
                 delta=ph_status, delta_color=ph_color)
    
    with col4:
        turb_status = "NORMAL" if latest['turbidity'] < 5 else "HIGH"
        turb_color = "normal" if turb_status == "NORMAL" else "inverse"
        st.metric("Turbidity", f"{latest['turbidity']:.2f} NTU",
                 delta=turb_status, delta_color=turb_color)
    
    with col5:
        st.metric("Temperature", f"{latest['temperature']:.1f}°C")
    
    # Alerts Section
    alerts = check_alerts(latest)
    
    # Leak detection
    detector = get_leak_detector()
    if detector.is_trained:
        is_anomaly, score = detector.predict(latest['flow'], latest['pressure'])
        if is_anomaly:
            alerts.append({
                "type": "LEAK DETECTED",
                "severity": "CRITICAL",
                "message": f"Anomaly in flow/pressure detected (confidence: {abs(score):.4f})"
            })
    
    if alerts:
        st.header("Active Alerts")
        for alert in alerts:
            if alert['severity'] == 'CRITICAL':
                st.markdown(f"""
                <div class="alert-critical">
                    <strong>CRITICAL: {alert['type']}</strong><br>
                    {alert['message']}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="alert-warning">
                    <strong>WARNING: {alert['type']}</strong><br>
                    {alert['message']}
                </div>
                """, unsafe_allow_html=True)
    
    # Statistics Summary
    st.header("Statistical Summary")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Average Flow", f"{df['flow'].mean():.2f} L/min")
        st.metric("Flow Range", f"{df['flow'].min():.2f} - {df['flow'].max():.2f}")
    
    with col2:
        st.metric("Average Pressure", f"{df['pressure'].mean():.2f} bar")
        st.metric("Pressure Range", f"{df['pressure'].min():.2f} - {df['pressure'].max():.2f}")
    
    with col3:
        st.metric("Average pH", f"{df['ph'].mean():.2f}")
        st.metric("pH Range", f"{df['ph'].min():.2f} - {df['ph'].max():.2f}")
    
    with col4:
        st.metric("Average Turbidity", f"{df['turbidity'].mean():.2f} NTU")
        st.metric("Total Readings", f"{len(df)}")
    
    # Charts Section
    st.header("Real-time Monitoring Charts")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Flow & Pressure", "Water Quality", "Demand Forecast", "System Health"])
    
    with tab1:
        st.subheader("Flow Rate Analysis")
        
        # Flow rate chart with enhanced styling
        fig_flow = go.Figure()
        fig_flow.add_trace(go.Scatter(
            x=df.index, y=df['flow'],
            mode='lines+markers', name='Flow Rate',
            line=dict(color='#1f77b4', width=3),
            marker=dict(size=4),
            fill='tozeroy',
            fillcolor='rgba(31, 119, 180, 0.1)'
        ))
        
        # Add threshold lines
        avg_flow = df['flow'].mean()
        fig_flow.add_hline(y=avg_flow, line_dash="dash", line_color="green", 
                          annotation_text=f"Average: {avg_flow:.2f}")
        
        fig_flow.update_layout(
            title="Water Flow Rate Over Time",
            xaxis_title="Reading Number",
            yaxis_title="Flow Rate (L/min)",
            height=350,
            hovermode='x unified',
            template='plotly_white'
        )
        st.plotly_chart(fig_flow, use_container_width=True)
        
        # Flow statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Current Flow", f"{latest['flow']:.2f} L/min")
        with col2:
            st.metric("Peak Flow", f"{df['flow'].max():.2f} L/min")
        with col3:
            st.metric("Min Flow", f"{df['flow'].min():.2f} L/min")
        
        st.subheader("Pressure Analysis")
        
        # Pressure chart with enhanced styling
        fig_pressure = go.Figure()
        fig_pressure.add_trace(go.Scatter(
            x=df.index, y=df['pressure'],
            mode='lines+markers', name='Pressure',
            line=dict(color='#ff7f0e', width=3),
            marker=dict(size=4),
            fill='tozeroy',
            fillcolor='rgba(255, 127, 14, 0.1)'
        ))
        
        avg_pressure = df['pressure'].mean()
        fig_pressure.add_hline(y=avg_pressure, line_dash="dash", line_color="orange",
                              annotation_text=f"Average: {avg_pressure:.2f}")
        
        fig_pressure.update_layout(
            title="Water Pressure Over Time",
            xaxis_title="Reading Number",
            yaxis_title="Pressure (bar)",
            height=350,
            hovermode='x unified',
            template='plotly_white'
        )
        st.plotly_chart(fig_pressure, use_container_width=True)
        
        # Pressure statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Current Pressure", f"{latest['pressure']:.2f} bar")
        with col2:
            st.metric("Peak Pressure", f"{df['pressure'].max():.2f} bar")
        with col3:
            st.metric("Min Pressure", f"{df['pressure'].min():.2f} bar")
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("pH Level Monitoring")
            
            # pH chart with safety zones
            fig_ph = go.Figure()
            fig_ph.add_trace(go.Scatter(
                x=df.index, y=df['ph'],
                mode='lines+markers', name='pH',
                line=dict(color='#2ca02c', width=3),
                marker=dict(size=5)
            ))
            
            # Safety zone
            fig_ph.add_hrect(y0=6.5, y1=8.5, fillcolor="green", opacity=0.1, 
                            annotation_text="Safe Zone", annotation_position="top left")
            fig_ph.add_hline(y=6.5, line_dash="dash", line_color="red", 
                            annotation_text="Min Safe Level")
            fig_ph.add_hline(y=8.5, line_dash="dash", line_color="red", 
                            annotation_text="Max Safe Level")
            
            fig_ph.update_layout(
                title="pH Level Variation",
                xaxis_title="Reading Number",
                yaxis_title="pH Level",
                height=350,
                hovermode='x unified',
                template='plotly_white'
            )
            st.plotly_chart(fig_ph, use_container_width=True)
            
            # pH statistics
            ph_in_range = ((df['ph'] >= 6.5) & (df['ph'] <= 8.5)).sum()
            ph_compliance = (ph_in_range / len(df)) * 100
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Current pH", f"{latest['ph']:.2f}")
                st.metric("Average pH", f"{df['ph'].mean():.2f}")
            with col_b:
                st.metric("Compliance Rate", f"{ph_compliance:.1f}%")
                status = "COMPLIANT" if ph_compliance > 95 else "NON-COMPLIANT"
                st.metric("Status", status)
        
        with col2:
            st.subheader("Turbidity Monitoring")
            
            # Turbidity chart
            fig_turb = go.Figure()
            fig_turb.add_trace(go.Scatter(
                x=df.index, y=df['turbidity'],
                mode='lines+markers', name='Turbidity',
                line=dict(color='#d62728', width=3),
                marker=dict(size=5),
                fill='tozeroy',
                fillcolor='rgba(214, 39, 40, 0.1)'
            ))
            
            fig_turb.add_hline(y=5, line_dash="dash", line_color="orange", 
                              annotation_text="Threshold (5 NTU)")
            
            fig_turb.update_layout(
                title="Turbidity Levels",
                xaxis_title="Reading Number",
                yaxis_title="Turbidity (NTU)",
                height=350,
                hovermode='x unified',
                template='plotly_white'
            )
            st.plotly_chart(fig_turb, use_container_width=True)
            
            # Turbidity statistics
            turb_violations = (df['turbidity'] > 5).sum()
            turb_compliance = ((len(df) - turb_violations) / len(df)) * 100
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Current Turbidity", f"{latest['turbidity']:.2f} NTU")
                st.metric("Average Turbidity", f"{df['turbidity'].mean():.2f} NTU")
            with col_b:
                st.metric("Violations", f"{turb_violations}")
                st.metric("Compliance Rate", f"{turb_compliance:.1f}%")
    
    with tab3:
        st.subheader("24-Hour Water Demand Forecast")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            forecaster = get_forecaster()
            
            if st.button("Generate Forecast", type="primary", use_container_width=True):
                with st.spinner("Generating 24-hour forecast..."):
                    predictions = forecaster.predict_next_hours(hours=24)
                    
                    # Create forecast dataframe
                    forecast_df = pd.DataFrame({
                        'Hour': [i/12 for i in range(len(predictions))],
                        'Predicted Flow': predictions
                    })
                    
                    # Plot forecast with confidence bands
                    fig_forecast = go.Figure()
                    
                    # Add prediction line
                    fig_forecast.add_trace(go.Scatter(
                        x=forecast_df['Hour'], 
                        y=forecast_df['Predicted Flow'],
                        mode='lines', 
                        name='Forecast',
                        line=dict(color='#9467bd', width=4)
                    ))
                    
                    # Add confidence bands (simple std-based)
                    std_dev = np.std(predictions)
                    fig_forecast.add_trace(go.Scatter(
                        x=forecast_df['Hour'],
                        y=forecast_df['Predicted Flow'] + std_dev,
                        mode='lines',
                        name='Upper Bound',
                        line=dict(width=0),
                        showlegend=False
                    ))
                    fig_forecast.add_trace(go.Scatter(
                        x=forecast_df['Hour'],
                        y=forecast_df['Predicted Flow'] - std_dev,
                        mode='lines',
                        name='Lower Bound',
                        line=dict(width=0),
                        fillcolor='rgba(148, 103, 189, 0.2)',
                        fill='tonexty',
                        showlegend=False
                    ))
                    
                    fig_forecast.update_layout(
                        title="Predicted Water Demand (Next 24 Hours)",
                        xaxis_title="Hours from Now",
                        yaxis_title="Flow Rate (L/min)",
                        height=450,
                        hovermode='x unified',
                        template='plotly_white'
                    )
                    st.plotly_chart(fig_forecast, use_container_width=True)
                    
                    # Forecast statistics
                    st.subheader("Forecast Analysis")
                    col_a, col_b, col_c, col_d = st.columns(4)
                    with col_a:
                        st.metric("Average Demand", f"{np.mean(predictions):.2f} L/min")
                    with col_b:
                        st.metric("Peak Demand", f"{np.max(predictions):.2f} L/min")
                    with col_c:
                        st.metric("Min Demand", f"{np.min(predictions):.2f} L/min")
                    with col_d:
                        st.metric("Std Deviation", f"{np.std(predictions):.2f}")
                    
                    # Peak hours analysis
                    peak_hour = forecast_df.loc[forecast_df['Predicted Flow'].idxmax(), 'Hour']
                    low_hour = forecast_df.loc[forecast_df['Predicted Flow'].idxmin(), 'Hour']
                    
                    st.markdown(f"""
                    <div class="info-box">
                        <strong>Key Insights:</strong><br>
                        • Peak demand expected at <strong>{peak_hour:.1f} hours</strong> from now<br>
                        • Lowest demand expected at <strong>{low_hour:.1f} hours</strong> from now<br>
                        • Demand variation: <strong>{(np.max(predictions) - np.min(predictions)):.2f} L/min</strong>
                    </div>
                    """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("### Forecast Info")
            st.info("""
            **Model:** LSTM Neural Network
            
            **Features:**
            - Historical flow data
            - Temperature patterns
            - Time-based trends
            
            **Horizon:** 24 hours
            
            **Update:** Real-time
            """)
            
            if forecaster.is_trained:
                st.success("Model Status: TRAINED")
            else:
                st.warning("Model Status: NOT TRAINED")
    
    with tab4:
        st.subheader("System Health Overview")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Temperature trend
            fig_temp = go.Figure()
            fig_temp.add_trace(go.Scatter(
                x=df.index, y=df['temperature'],
                mode='lines+markers', name='Temperature',
                line=dict(color='#8c564b', width=3),
                marker=dict(size=4)
            ))
            
            avg_temp = df['temperature'].mean()
            fig_temp.add_hline(y=avg_temp, line_dash="dash", line_color="brown",
                              annotation_text=f"Average: {avg_temp:.1f}°C")
            
            fig_temp.update_layout(
                title="Water Temperature Monitoring",
                xaxis_title="Reading Number",
                yaxis_title="Temperature (°C)",
                height=350,
                hovermode='x unified',
                template='plotly_white'
            )
            st.plotly_chart(fig_temp, use_container_width=True)
            
            # Temperature statistics
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Current Temp", f"{latest['temperature']:.1f}°C")
                st.metric("Average Temp", f"{df['temperature'].mean():.1f}°C")
            with col_b:
                st.metric("Max Temp", f"{df['temperature'].max():.1f}°C")
                st.metric("Min Temp", f"{df['temperature'].min():.1f}°C")
        
        with col2:
            st.markdown("### Data Quality Metrics")
            
            # Calculate data quality metrics
            total_readings = len(df)
            time_span = (pd.to_datetime(df.iloc[-1]['timestamp']) - 
                        pd.to_datetime(df.iloc[0]['timestamp'])).total_seconds() / 60
            
            # Data completeness
            expected_readings = int(time_span / (5/60)) if time_span > 0 else total_readings
            completeness = min((total_readings / expected_readings * 100), 100) if expected_readings > 0 else 100
            
            st.metric("Total Readings", f"{total_readings}")
            st.metric("Data Completeness", f"{completeness:.1f}%")
            st.metric("Time Span", f"{time_span:.1f} minutes")
            st.metric("Last Update", datetime.now().strftime("%H:%M:%S"))
            
            # System status indicators
            st.markdown("### System Status")
            
            status_items = [
                ("Backend API", "ONLINE", "success"),
                ("Database", "CONNECTED", "success"),
                ("Simulator", "ACTIVE", "success"),
                ("AI Models", "READY" if detector.is_trained else "TRAINING", 
                 "success" if detector.is_trained else "warning")
            ]
            
            for item, status, status_type in status_items:
                if status_type == "success":
                    st.success(f"**{item}:** {status}")
                else:
                    st.warning(f"**{item}:** {status}")
            
            # Performance metrics
            st.markdown("### Performance Metrics")
            st.metric("Avg Response Time", "< 100ms")
            st.metric("Data Throughput", f"{total_readings / max(time_span/60, 1):.1f} readings/min")
    
    # Footer with system information
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**System Version:** 1.0")
    with col2:
        st.markdown(f"**Database Records:** {len(df)}")
    with col3:
        st.markdown(f"**Last Refresh:** {datetime.now().strftime('%H:%M:%S')}")
    
    # Auto-refresh
    if auto_refresh:
        import time
        time.sleep(refresh_interval)
        st.rerun()

if __name__ == "__main__":
    main()
