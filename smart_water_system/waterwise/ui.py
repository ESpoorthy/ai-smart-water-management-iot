"""UI styling, SVG assets, and reusable components for WaterWise AI.

Provides a water-inspired design system: deep navy structure, teal/aqua accents,
responsive cards, and informative municipal disclaimers.
"""

from __future__ import annotations

import streamlit as st

# Custom CSS styling tokens
CUSTOM_CSS = """
<style>
/* Main Page Background and typography adjustments */
.main {
    background-color: #f8fafc;
}

/* WaterWise Hero Header Card */
.ww-hero-container {
    background: linear-gradient(135deg, #0a2540 0%, #0f3d64 50%, #0284c7 100%);
    color: #ffffff;
    padding: 2.2rem 2.5rem;
    border-radius: 16px;
    box-shadow: 0 10px 25px -5px rgba(2, 132, 199, 0.25);
    margin-bottom: 1.5rem;
    border: 1px solid rgba(255, 255, 255, 0.12);
}

.ww-hero-title-row {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 0.5rem;
}

.ww-hero-title {
    font-size: 2.4rem;
    font-weight: 800;
    letter-spacing: -0.025em;
    margin: 0;
    color: #ffffff;
}

.ww-hero-tagline {
    font-size: 1.15rem;
    font-weight: 500;
    color: #7dd3fc;
    margin-bottom: 0.8rem;
}

.ww-hero-desc {
    font-size: 0.98rem;
    line-height: 1.6;
    color: #e2e8f0;
    max-width: 860px;
    margin-bottom: 1.2rem;
}

.ww-badge-row {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 0.5rem;
}

.ww-badge {
    display: inline-flex;
    align-items: center;
    padding: 4px 12px;
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}

.ww-badge-teal {
    background: rgba(14, 165, 233, 0.25);
    color: #bae6fd;
    border: 1px solid rgba(56, 189, 248, 0.4);
}

.ww-badge-green {
    background: rgba(16, 185, 129, 0.25);
    color: #a7f3d0;
    border: 1px solid rgba(52, 211, 153, 0.4);
}

.ww-badge-warn {
    background: rgba(245, 158, 11, 0.2);
    color: #fef3c7;
    border: 1px solid rgba(251, 191, 36, 0.35);
}

/* System Notice Banner */
.ww-disclaimer-banner {
    background-color: #f0fdf4;
    border-left: 4px solid #0284c7;
    padding: 12px 18px;
    border-radius: 8px;
    margin-bottom: 1.8rem;
    font-size: 0.88rem;
    color: #1e293b;
    line-height: 1.5;
    border-top: 1px solid #e2e8f0;
    border-right: 1px solid #e2e8f0;
    border-bottom: 1px solid #e2e8f0;
}

/* Topic Card Layout */
.ww-card {
    background: #ffffff;
    border-radius: 12px;
    padding: 1.25rem 1.4rem;
    border: 1px solid #e2e8f0;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
    transition: all 0.2s ease-in-out;
    height: 100%;
    margin-bottom: 0.75rem;
}

.ww-card:hover {
    border-color: #38bdf8;
    box-shadow: 0 6px 16px rgba(2, 132, 199, 0.12);
    transform: translateY(-2px);
}

.ww-card-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #0f294a;
    margin-bottom: 0.35rem;
    display: flex;
    align-items: center;
    gap: 8px;
}

.ww-card-desc {
    font-size: 0.86rem;
    color: #475569;
    line-height: 1.45;
    margin-bottom: 0.75rem;
}

/* Preformatted ASCII Diagrams */
.ww-ascii-box {
    background-color: #0b192c;
    color: #38bdf8;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 0.82rem;
    padding: 1.2rem;
    border-radius: 10px;
    overflow-x: auto;
    line-height: 1.45;
    border: 1px solid #1e3a5f;
    margin: 1rem 0;
}

/* Footer styling */
.ww-footer {
    text-align: center;
    padding: 2.5rem 1rem 1.5rem 1rem;
    font-size: 0.82rem;
    color: #64748b;
    border-top: 1px solid #e2e8f0;
    margin-top: 3rem;
}
</style>
"""


def render_head() -> None:
    """Inject styling tokens into Streamlit."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_header(model_name: str, api_configured: bool) -> None:
    """Render the civic-tech header banner with metadata badges."""
    badge_status = (
        f'<span class="ww-badge ww-badge-teal">Model: {model_name}</span>'
        if api_configured
        else '<span class="ww-badge ww-badge-warn">Learning Mode (Zero-Credential)</span>'
    )

    header_html = f"""
    <div class="ww-hero-container">
        <div class="ww-hero-title-row">
            <span style="font-size: 2.4rem;">💧</span>
            <h1 class="ww-hero-title">WaterWise AI</h1>
        </div>
        <div class="ww-hero-tagline">Understand Every Drop.</div>
        <div class="ww-hero-desc">
            An educational civic explainer clarifying municipal water treatment processes,
            underground distribution networks, hydraulic pressure dynamics, and household conservation practices.
        </div>
        <div class="ww-badge-row">
            <span class="ww-badge ww-badge-teal">Municipal Services Domain</span>
            <span class="ww-badge ww-badge-green">Strict Educational Scope</span>
            {badge_status}
        </div>
    </div>
    <div class="ww-disclaimer-banner">
        <strong>ℹ️ Public Information Notice:</strong> WaterWise AI provides general engineering
        and utility process explanations. It is <strong>not connected to live municipal telemetry</strong>,
        cannot predict local supply arrival schedules, and does not register consumer complaints.
        For localized service emergencies or official schedules, please contact your municipal water department.
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)


def render_footer() -> None:
    """Render the standard public information footer."""
    footer_html = """
    <div class="ww-footer">
        <strong>WaterWise AI</strong> • Project 26: Water Supply & Distribution Process Explainer Bot<br>
        Developed with Streamlit & Google AI Studio (Gemini Flash) • Designed for Responsible Public-Service GenAI<br>
        <em>Educational guidance only. Always consult your local municipality or water authority for official local records.</em>
    </div>
    """
    st.markdown(footer_html, unsafe_allow_html=True)
