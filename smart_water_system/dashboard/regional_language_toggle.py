"""
Decision Intelligence – Regional Language Toggle & SMS Fallback
================================================================
Standalone Streamlit page that provides:

  1. LANGUAGE TOGGLE — sidebar selector switches all key dashboard
     labels between English / Telugu / Hindi. Implemented as a
     drop-in translation dict; no external i18n library needed.

  2. SMS FALLBACK MODULE — a reusable function `send_sms_bulletin()`
     that composes a concise plain-text water status bulletin and
     dispatches it via the existing backend/alerts.py Twilio channel.
     Designed for residents without smartphones or internet access.

USAGE — standalone page
-----------------------
    streamlit run dashboard/regional_language_toggle.py

USAGE — multipage app (drop into pages/ folder)
-----------------------
    dashboard/pages/3_Regional_Language.py   ← copy/rename this file

USAGE — SMS bulletin from any module
-----------------------
    from dashboard.regional_language_toggle import send_sms_bulletin
    send_sms_bulletin(lang="telugu")   # or "hindi" / "english"

NO EXISTING FILES ARE MODIFIED.
NEW DEPENDENCIES: none (uses stdlib + existing streamlit/alerts.py).
"""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime
from typing import Any, Dict, Optional

import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------------------------------
# Translation dictionary
# Keys are canonical English labels used throughout the dashboard.
# Add more keys as new UI strings are needed.
# ---------------------------------------------------------------------------
_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # ── Page / section titles ────────────────────────────────────────────────
    "page_title": {
        "english": "Smart Water Management System",
        "telugu":  "స్మార్ట్ వాటర్ మేనేజ్‌మెంట్ సిస్టమ్",
        "hindi":   "स्मार्ट जल प्रबंधन प्रणाली",
    },
    "realtime_metrics": {
        "english": "Real-Time System Metrics",
        "telugu":  "రియల్-టైమ్ సిస్టమ్ కొలతలు",
        "hindi":   "रियल-टाइम सिस्टम मेट्रिक्स",
    },
    "alerts": {
        "english": "Active Alerts",
        "telugu":  "క్రియాశీల హెచ్చరికలు",
        "hindi":   "सक्रिय अलर्ट",
    },
    "all_normal": {
        "english": "All Systems Normal",
        "telugu":  "అన్నీ సాధారణంగా ఉన్నాయి",
        "hindi":   "सभी प्रणालियाँ सामान्य हैं",
    },
    "recommendations": {
        "english": "AI Recommendations",
        "telugu":  "AI సిఫార్సులు",
        "hindi":   "AI अनुशंसाएं",
    },
    "zone_ranking": {
        "english": "Zone Efficiency Ranking",
        "telugu":  "జోన్ సామర్థ్య ర్యాంకింగ్",
        "hindi":   "ज़ोन दक्षता रैंकिंग",
    },
    "what_if": {
        "english": "What-If Simulator",
        "telugu":  "వాట్-ఇఫ్ సిమ్యులేటర్",
        "hindi":   "क्या-होगा-अगर सिम्युलेटर",
    },
    # ── Sensor labels ────────────────────────────────────────────────────────
    "flow_rate": {
        "english": "Flow Rate",
        "telugu":  "ప్రవాహ రేటు",
        "hindi":   "प्रवाह दर",
    },
    "pressure": {
        "english": "Pressure",
        "telugu":  "పీడనం",
        "hindi":   "दबाव",
    },
    "ph_level": {
        "english": "pH Level",
        "telugu":  "pH స్థాయి",
        "hindi":   "pH स्तर",
    },
    "turbidity": {
        "english": "Turbidity",
        "telugu":  "గందరగోళత",
        "hindi":   "मटमैलापन",
    },
    "temperature": {
        "english": "Temperature",
        "telugu":  "ఉష్ణోగ్రత",
        "hindi":   "तापमान",
    },
    # ── Status words ──────────────────────────────────────────────────────────
    "normal": {
        "english": "Normal",
        "telugu":  "సాధారణ",
        "hindi":   "सामान्य",
    },
    "warning": {
        "english": "Warning",
        "telugu":  "హెచ్చరిక",
        "hindi":   "चेतावनी",
    },
    "critical": {
        "english": "Critical",
        "telugu":  "క్లిష్టమైన",
        "hindi":   "गंभीर",
    },
    "leak_detected": {
        "english": "Leak Detected",
        "telugu":  "లీక్ గుర్తించబడింది",
        "hindi":   "रिसाव का पता चला",
    },
    "contamination": {
        "english": "Contamination Alert",
        "telugu":  "కలుషితం హెచ్చరిక",
        "hindi":   "संदूषण अलर्ट",
    },
    "high_demand": {
        "english": "High Demand",
        "telugu":  "అధిక డిమాండ్",
        "hindi":   "उच्च मांग",
    },
    "sensor_fault": {
        "english": "Sensor Fault",
        "telugu":  "సెన్సార్ లోపం",
        "hindi":   "सेंसर खराबी",
    },
    # ── Actions ───────────────────────────────────────────────────────────────
    "action_inspect": {
        "english": "Inspect pipeline immediately.",
        "telugu":  "వెంటనే పైప్‌లైన్‌ను తనిఖీ చేయండి.",
        "hindi":   "तुरंत पाइपलाइन की जांच करें।",
    },
    "action_quality": {
        "english": "Do not drink. Contact water authority.",
        "telugu":  "తాగవద్దు. జల సంస్థను సంప్రదించండి.",
        "hindi":   "न पीयें। जल प्राधिकरण से संपर्क करें।",
    },
    "action_conserve": {
        "english": "Reduce irrigation. Conserve water.",
        "telugu":  "నీటిపారుదలను తగ్గించండి. నీటిని ఆదా చేయండి.",
        "hindi":   "सिंचाई कम करें। पानी बचाएं।",
    },
    # ── SMS bulletin template ─────────────────────────────────────────────────
    "sms_header": {
        "english": "WATER ALERT",
        "telugu":  "నీటి హెచ్చరిక",
        "hindi":   "जल अलर्ट",
    },
    "sms_normal": {
        "english": "Water supply is normal. Safe to use.",
        "telugu":  "నీటి సరఫరా సాధారణంగా ఉంది. వాడటం సురక్షితం.",
        "hindi":   "जल आपूर्ति सामान्य है। उपयोग के लिए सुरक्षित।",
    },
    "sms_leak": {
        "english": "Low water pressure detected. Possible leak. Avoid use until resolved.",
        "telugu":  "తక్కువ నీటి పీడనం గుర్తించబడింది. లీక్ అవకాశం. పరిష్కారమయ్యే వరకు ఉపయోగించవద్దు.",
        "hindi":   "कम जल दबाव पाया गया। रिसाव संभव। समाधान तक उपयोग से बचें।",
    },
    "sms_contamination": {
        "english": "Water quality issue detected. DO NOT DRINK. Contact 1800-XXX-XXXX.",
        "telugu":  "నీటి నాణ్యత సమస్య గుర్తించబడింది. తాగవద్దు. 1800-XXX-XXXX కి కాల్ చేయండి.",
        "hindi":   "जल गुणवत्ता समस्या पाई गई। न पीयें। 1800-XXX-XXXX पर कॉल करें।",
    },
    "sms_footer": {
        "english": "Smart Water System | Auto-alert",
        "telugu":  "స్మార్ట్ వాటర్ సిస్టమ్ | స్వయంచాలక హెచ్చరిక",
        "hindi":   "स्मार्ट वाटर सिस्टम | स्वचालित अलर्ट",
    },
}


def t(key: str, lang: str) -> str:
    """
    Translate a key to the requested language.
    Falls back to English if key or language is missing.
    """
    lang = lang.lower().strip()
    entry = _TRANSLATIONS.get(key, {})
    return entry.get(lang) or entry.get("english") or key


# ---------------------------------------------------------------------------
# DB helper (read-only)
# ---------------------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "water.db")


@st.cache_data(ttl=15, show_spinner=False)
def _load_latest() -> Optional[Dict[str, Any]]:
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT flow, pressure, ph, turbidity, temperature, timestamp "
            "FROM sensor_data ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if row:
            return dict(zip(
                ["flow", "pressure", "ph", "turbidity", "temperature", "timestamp"],
                row,
            ))
    except Exception:
        pass
    return None


@st.cache_data(ttl=15, show_spinner=False)
def _load_stats() -> Optional[Dict[str, Any]]:
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT ROUND(AVG(flow),2), ROUND(AVG(pressure),2), "
            "ROUND(AVG(ph),2), ROUND(AVG(turbidity),2), COUNT(*) "
            "FROM (SELECT flow,pressure,ph,turbidity "
            "FROM sensor_data ORDER BY id DESC LIMIT 720)"
        ).fetchone()
        conn.close()
        if row:
            return dict(zip(
                ["avg_flow","avg_pressure","avg_ph","avg_turbidity","n"], row
            ))
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# SMS bulletin — importable standalone function
# ---------------------------------------------------------------------------

def send_sms_bulletin(
    lang: str = "english",
    phone_numbers: Optional[list] = None,
    force_status: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compose and dispatch a localised plain-text water status SMS to
    one or more phone numbers.

    Uses backend/alerts.py for the actual Twilio dispatch so no
    duplicate credential handling is needed.

    Parameters
    ----------
    lang          : "english" | "telugu" | "hindi"
    phone_numbers : list of E.164 numbers, e.g. ["+91XXXXXXXXXX"].
                    If None, reads ALERT_SMS_TO env var (same as alerts.py).
    force_status  : override auto-detection; "normal"|"leak"|"contamination"

    Returns
    -------
    dict with keys: status, message_sent, lang, recipients
    """
    from backend.alerts import send_alert, AlertLevel

    # Auto-detect status from DB if not forced
    status = force_status
    latest = _load_latest()

    if status is None and latest:
        if latest["flow"] < 8.0 or latest["pressure"] < 1.5:
            status = "leak"
        elif latest["turbidity"] > 5.0 or latest["ph"] < 6.5 or latest["ph"] > 8.5:
            status = "contamination"
        else:
            status = "normal"
    elif status is None:
        status = "normal"

    # Build localised message
    header  = t("sms_header", lang)
    body_key = {"normal": "sms_normal", "leak": "sms_leak",
                "contamination": "sms_contamination"}.get(status, "sms_normal")
    body    = t(body_key, lang)
    footer  = t("sms_footer", lang)
    ts      = datetime.now().strftime("%d/%m %H:%M")

    message = f"[{header}] {body} ({ts}) {footer}"

    # Map status → AlertLevel
    level_map = {"normal": AlertLevel.INFO,
                 "leak": AlertLevel.CRITICAL,
                 "contamination": AlertLevel.CRITICAL}
    level = level_map.get(status, AlertLevel.WARNING)

    # Override recipients if explicitly provided
    original_env = os.environ.get("ALERT_SMS_TO", "")
    if phone_numbers:
        os.environ["ALERT_SMS_TO"] = ",".join(phone_numbers)

    result = send_alert(
        level=level,
        title=f"{t('sms_header', lang)} — {status.upper()}",
        message=message,
        zone="Community Broadcast",
        channels=["console", "sms"],
    )

    # Restore env var
    if phone_numbers:
        os.environ["ALERT_SMS_TO"] = original_env

    recipients = os.environ.get("ALERT_SMS_TO", "(not configured)")
    return {
        "status":       status,
        "message_sent": message,
        "lang":         lang,
        "recipients":   recipients,
        "alert_result": str(result),
    }


# ---------------------------------------------------------------------------
# Page CSS (mirrors existing app style)
# ---------------------------------------------------------------------------
_CSS = """
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
.sensor-card {
    background: white; border-radius: 14px;
    padding: 1.2rem 1rem; text-align: center;
    box-shadow: 0 4px 12px rgba(0,0,0,.08);
    border-top: 5px solid #3b82f6; margin-bottom: 1rem;
}
.sensor-label { font-size: .85rem; color: #64748b; font-weight: 600;
                text-transform: uppercase; letter-spacing: .05em; }
.sensor-value { font-size: 2rem; font-weight: 800; color: #0284c7; }
.sensor-unit  { font-size: .9rem; color: #94a3b8; }
.status-ok    { background: #d1fae5; color: #065f46; border-radius: 8px;
                padding: .8rem 1rem; font-weight: 700; }
.status-warn  { background: #fef3c7; color: #92400e; border-radius: 8px;
                padding: .8rem 1rem; font-weight: 700; }
.status-crit  { background: #fee2e2; color: #991b1b; border-radius: 8px;
                padding: .8rem 1rem; font-weight: 700; }
.lang-badge   { display:inline-block; padding:.3rem .9rem; border-radius:20px;
                background:#3b82f6; color:white; font-weight:700;
                font-size:.9rem; margin-bottom:1rem; }
.sms-preview  { background:#f8fafc; border:1px solid #e2e8f0;
                border-radius:10px; padding:1rem 1.2rem;
                font-family:monospace; font-size:.9rem; color:#1e293b;
                white-space:pre-wrap; }
</style>
"""


# ---------------------------------------------------------------------------
# Helper: status card
# ---------------------------------------------------------------------------

def _status_card(status: str, lang: str) -> None:
    if status == "normal":
        label = t("all_normal", lang)
        css   = "status-ok"
        icon  = "✅"
    elif status == "leak":
        label = t("leak_detected", lang)
        css   = "status-crit"
        icon  = "💧"
    else:
        label = t("contamination", lang)
        css   = "status-crit"
        icon  = "⚗️"
    st.markdown(
        f'<div class="{css}">{icon} {label}</div>',
        unsafe_allow_html=True,
    )


def _sensor_card(label: str, value: float, unit: str, ok: bool) -> None:
    colour = "#10b981" if ok else "#dc2626"
    st.markdown(f"""
    <div class="sensor-card" style="border-top-color:{colour};">
        <div class="sensor-label">{label}</div>
        <div class="sensor-value" style="color:{colour};">{value}</div>
        <div class="sensor-unit">{unit}</div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main Streamlit page
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="Regional Language | Smart Water",
        page_icon="🌐",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── Sidebar: language selector ────────────────────────────────────────
    with st.sidebar:
        st.markdown("## 🌐 Language / భాష / भाषा")
        lang = st.selectbox(
            "Select language",
            options=["english", "telugu", "hindi"],
            format_func=lambda x: {
                "english": "🇬🇧 English",
                "telugu":  "🇮🇳 తెలుగు",
                "hindi":   "🇮🇳 हिन्दी",
            }[x],
            index=0,
        )
        st.markdown(f'<div class="lang-badge">{lang.upper()}</div>',
                    unsafe_allow_html=True)
        st.markdown("---")
        st.caption("All labels update instantly when you change language.")

    # ── Page title ────────────────────────────────────────────────────────
    st.markdown(
        f'<h1 class="page-title">🌐 {t("page_title", lang)}</h1>',
        unsafe_allow_html=True,
    )
    st.caption(
        {"english": "Regional language view — key metrics in your language.",
         "telugu":  "ప్రాంతీయ భాష వీక్షణ — మీ భాషలో కీలక కొలతలు.",
         "hindi":   "क्षेत्रीय भाषा दृश्य — आपकी भाषा में प्रमुख मेट्रिक्स।",
         }[lang]
    )

    # ── Load data ─────────────────────────────────────────────────────────
    latest = _load_latest()
    stats  = _load_stats()

    if latest is None:
        st.warning(
            {"english": "No data yet. Start the sensor simulator.",
             "telugu":  "డేటా లేదు. సెన్సార్ సిమ్యులేటర్‌ను ప్రారంభించండి.",
             "hindi":   "अभी कोई डेटा नहीं। सेंसर सिम्युलेटर शुरू करें।",
             }[lang]
        )
        st.code("python simulator/sensor_simulator.py")
        return

    # ── Determine live status ─────────────────────────────────────────────
    if latest["flow"] < 8.0 or latest["pressure"] < 1.5:
        status = "leak"
    elif (latest["turbidity"] > 5.0 or
          latest["ph"] < 6.5 or latest["ph"] > 8.5):
        status = "contamination"
    else:
        status = "normal"

    # ── Status banner ─────────────────────────────────────────────────────
    st.markdown(
        f'<div class="section-header">'
        f'{t("alerts", lang)}</div>',
        unsafe_allow_html=True,
    )
    _status_card(status, lang)

    # ── Sensor cards ──────────────────────────────────────────────────────
    st.markdown(
        f'<div class="section-header">'
        f'{t("realtime_metrics", lang)}</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        _sensor_card(
            t("flow_rate", lang),
            round(latest["flow"], 2), "L/min",
            8.0 <= latest["flow"] <= 22.0,
        )
    with c2:
        _sensor_card(
            t("pressure", lang),
            round(latest["pressure"], 2), "bar",
            1.5 <= latest["pressure"] <= 3.5,
        )
    with c3:
        _sensor_card(
            t("ph_level", lang),
            round(latest["ph"], 2), "",
            6.5 <= latest["ph"] <= 8.5,
        )
    with c4:
        _sensor_card(
            t("turbidity", lang),
            round(latest["turbidity"], 2), "NTU",
            latest["turbidity"] < 5.0,
        )
    with c5:
        _sensor_card(
            t("temperature", lang),
            round(latest["temperature"], 2), "°C",
            latest["temperature"] < 35.0,
        )

    # ── Recommended action in local language ──────────────────────────────
    action_key = {
        "normal":        "action_conserve",
        "leak":          "action_inspect",
        "contamination": "action_quality",
    }[status]
    st.info(f"📋 {t(action_key, lang)}")

    # ── Last-hour stats ───────────────────────────────────────────────────
    if stats and stats.get("n", 0) > 0:
        st.markdown("---")
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric(t("flow_rate",    lang), f"{stats['avg_flow']} L/min")
        col_b.metric(t("pressure",     lang), f"{stats['avg_pressure']} bar")
        col_c.metric(t("ph_level",     lang), f"{stats['avg_ph']}")
        col_d.metric(t("turbidity",    lang), f"{stats['avg_turbidity']} NTU")
        st.caption(
            {"english": f"Averages from last {stats['n']:,} readings (~1 hour window).",
             "telugu":  f"చివరి {stats['n']:,} రీడింగ్‌ల సగటులు (~1 గంట విండో).",
             "hindi":   f"पिछली {stats['n']:,} रीडिंग का औसत (~1 घंटे की विंडो)।",
             }[lang]
        )

    # ── SMS Fallback Section ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        f'<div class="section-header">'
        + {"english": "📱 SMS Bulletin for Residents (No Smartphone Needed)",
           "telugu":  "📱 నివాసితులకు SMS బులెటిన్ (స్మార్ట్‌ఫోన్ అవసరం లేదు)",
           "hindi":   "📱 निवासियों के लिए SMS बुलेटिन (स्मार्टफ़ोन की जरूरत नहीं)",
           }[lang]
        + "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        {"english": "Compose and send a plain-text water status bulletin "
                    "to residents' basic phones via SMS.",
         "telugu":  "SMS ద్వారా నివాసితుల బేసిక్ ఫోన్‌లకు నీటి స్థితి "
                    "బులెటిన్‌ను రూపొందించి పంపండి.",
         "hindi":   "SMS के माध्यम से निवासियों के बेसिक फ़ोन पर जल "
                    "स्थिति बुलेटिन तैयार करें और भेजें।",
         }[lang]
    )

    col_sms1, col_sms2 = st.columns([1, 1])

    with col_sms1:
        sms_lang = st.selectbox(
            {"english": "SMS language",
             "telugu":  "SMS భాష",
             "hindi":   "SMS भाषा"}[lang],
            options=["english", "telugu", "hindi"],
            format_func=lambda x: {
                "english": "🇬🇧 English",
                "telugu":  "🇮🇳 తెలుగు",
                "hindi":   "🇮🇳 हिन्दी",
            }[x],
            key="sms_lang_select",
        )
        override_status = st.selectbox(
            {"english": "Status to broadcast",
             "telugu":  "ప్రసారం చేయవలసిన స్థితి",
             "hindi":   "प्रसारित करने की स्थिति"}[lang],
            options=["auto-detect", "normal", "leak", "contamination"],
            index=0,
            key="sms_status_select",
        )
        phone_input = st.text_input(
            {"english": "Phone numbers (comma-separated, E.164)",
             "telugu":  "ఫోన్ నంబర్లు (కామాతో వేరు చేయబడినవి, E.164)",
             "hindi":   "फ़ोन नंबर (अल्पविराम से अलग, E.164)"}[lang],
            placeholder="+91XXXXXXXXXX, +91XXXXXXXXXX",
            key="sms_phones",
        )

    with col_sms2:
        # Live message preview
        preview_status = (
            status if override_status == "auto-detect" else override_status
        )
        header_txt = t("sms_header", sms_lang)
        body_key   = {"normal": "sms_normal", "leak": "sms_leak",
                      "contamination": "sms_contamination"
                      }.get(preview_status, "sms_normal")
        body_txt   = t(body_key,   sms_lang)
        footer_txt = t("sms_footer", sms_lang)
        ts_now     = datetime.now().strftime("%d/%m %H:%M")
        preview_msg = f"[{header_txt}] {body_txt} ({ts_now}) {footer_txt}"

        st.markdown(
            {"english": "**Message preview:**",
             "telugu":  "**సందేశం ప్రివ్యూ:**",
             "hindi":   "**संदेश पूर्वावलोकन:**"}[lang]
        )
        st.markdown(
            f'<div class="sms-preview">{preview_msg}</div>',
            unsafe_allow_html=True,
        )
        char_count = len(preview_msg)
        segments   = (char_count // 160) + 1
        st.caption(f"{char_count} chars · {segments} SMS segment(s)")

    # Send button
    send_label = {"english": "Send SMS Bulletin",
                  "telugu":  "SMS బులెటిన్ పంపండి",
                  "hindi":   "SMS बुलेटिन भेजें"}[lang]

    if st.button(f"📤 {send_label}", type="primary", use_container_width=True):
        phones = (
            [p.strip() for p in phone_input.split(",") if p.strip()]
            if phone_input.strip() else None
        )
        forced = (
            None if override_status == "auto-detect" else override_status
        )
        with st.spinner(
            {"english": "Sending…",
             "telugu":  "పంపుతున్నాం…",
             "hindi":   "भेज रहे हैं…"}[lang]
        ):
            result = send_sms_bulletin(
                lang=sms_lang,
                phone_numbers=phones,
                force_status=forced,
            )

        if "success" in result["alert_result"].lower() or \
           "console" in result["alert_result"].lower():
            st.success(
                {"english": f"Bulletin sent ({result['status'].upper()}) · "
                             f"Lang: {result['lang']}",
                 "telugu":  f"బులెటిన్ పంపబడింది ({result['status'].upper()}) · "
                             f"భాష: {result['lang']}",
                 "hindi":   f"बुलेटिन भेजा गया ({result['status'].upper()}) · "
                             f"भाषा: {result['lang']}",
                 }[lang]
            )
        else:
            st.warning(
                {"english": "Sent to console. Configure TWILIO_* env vars for SMS delivery.",
                 "telugu":  "కన్సోల్‌కి పంపబడింది. SMS డెలివరీ కోసం TWILIO_* env వేరియబుల్స్ సెట్ చేయండి.",
                 "hindi":   "कंसोल पर भेजा गया। SMS डिलीवरी के लिए TWILIO_* env वेरिएबल सेट करें।",
                 }[lang]
            )

        with st.expander(
            {"english": "Full result",
             "telugu":  "పూర్తి ఫలితం",
             "hindi":   "पूरा परिणाम"}[lang]
        ):
            st.json(result)

    # ── Translation reference table ────────────────────────────────────────
    with st.expander(
        {"english": "All translations reference table",
         "telugu":  "అన్ని అనువాదాల సూచన పట్టిక",
         "hindi":   "सभी अनुवादों की संदर्भ तालिका"}[lang],
        expanded=False,
    ):
        import pandas as _pd
        rows = [
            {"Key": k,
             "English": v.get("english",""),
             "Telugu":  v.get("telugu",""),
             "Hindi":   v.get("hindi","")}
            for k, v in _TRANSLATIONS.items()
        ]
        st.dataframe(_pd.DataFrame(rows), use_container_width=True)


if __name__ == "__main__":
    main()
