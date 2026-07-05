"""
Decision Intelligence – Alert Dispatcher
=========================================
Standalone module.  Import and call from anywhere — FastAPI routes,
Streamlit pages, the sensor simulator, or a cron job — without editing
any existing file.

SUPPORTED CHANNELS
------------------
  1. Email   – plain SMTP (works with Gmail, Outlook, SendGrid, etc.)
  2. SMS     – Twilio REST API
  3. Console – always-on fallback; useful for demo / offline mode

ENVIRONMENT VARIABLES  (never hardcode credentials)
----------------------------------------------------
  # Email
  ALERT_EMAIL_HOST        SMTP server host           (default: smtp.gmail.com)
  ALERT_EMAIL_PORT        SMTP port                  (default: 587)
  ALERT_EMAIL_USER        Sender address             (required for email)
  ALERT_EMAIL_PASSWORD    Sender password / app-key  (required for email)
  ALERT_EMAIL_TO          Comma-separated recipients (required for email)
  ALERT_EMAIL_USE_TLS     "true" / "false"           (default: true)

  # Twilio SMS
  TWILIO_ACCOUNT_SID      Twilio account SID         (required for SMS)
  TWILIO_AUTH_TOKEN       Twilio auth token          (required for SMS)
  TWILIO_FROM_NUMBER      Twilio "From" phone number (required for SMS)
  ALERT_SMS_TO            Comma-separated E.164 numbers, e.g. +91XXXXXXXXXX

QUICK USAGE
-----------
    from backend.alerts import send_alert, AlertLevel

    # Minimal — works even with no env vars (console only)
    send_alert(
        level=AlertLevel.CRITICAL,
        title="Leak Detected – Zone 3",
        message="Flow dropped to 5.8 L/min (62% below baseline). "
                "Anomaly score: -0.45.",
        zone="Zone-3",
        sensor_values={"flow": 5.8, "pressure": 1.1, "ph": 7.3},
        recommended_action="Inspect pipeline immediately.",
        estimated_impact="~2,300 L/day unaccounted loss.",
    )

    # With root-cause and recommendation objects from Phase 1 modules:
    from ai_models.root_cause_classifier import AnomalyRootCauseClassifier
    clf = AnomalyRootCauseClassifier()
    result = clf.classify(flow=5.8, pressure=1.1, ph=7.3,
                          turbidity=3.0, temperature=26.0)
    send_alert_from_classification(zone="Zone-3", classification=result)

INTEGRATION PATTERN (zero edits to existing files)
---------------------------------------------------
In the existing fastapi_server.py (or the new chat_agent router), after
anomaly detection, add ONE import at the bottom of the import block:

    from backend.alerts import send_alert, AlertLevel

Then call:

    if is_anomaly:
        send_alert(AlertLevel.CRITICAL, "Leak Detected", ..., zone="Zone-X")

NEW DEPENDENCY: twilio==8.13.0
  (only required if SMS is used — already noted in requirements-additions.txt)
  pip install twilio==8.13.0
"""

from __future__ import annotations

import os
import smtplib
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Optional Twilio import — degrade gracefully
# ---------------------------------------------------------------------------
try:
    from twilio.rest import Client as TwilioClient
    _TWILIO_AVAILABLE = True
except ImportError:
    _TWILIO_AVAILABLE = False


# ---------------------------------------------------------------------------
# Alert levels
# ---------------------------------------------------------------------------
class AlertLevel(str, Enum):
    INFO     = "INFO"
    WARNING  = "WARNING"
    CRITICAL = "CRITICAL"


_LEVEL_EMOJI = {
    AlertLevel.INFO:     "ℹ️",
    AlertLevel.WARNING:  "⚠️",
    AlertLevel.CRITICAL: "🚨",
}

_LEVEL_COLOUR = {
    AlertLevel.INFO:     "#3b82f6",
    AlertLevel.WARNING:  "#f59e0b",
    AlertLevel.CRITICAL: "#dc2626",
}


# ---------------------------------------------------------------------------
# Alert result dataclass
# ---------------------------------------------------------------------------
@dataclass
class AlertResult:
    """Returned by send_alert() — records what was sent and any errors."""
    success:        bool
    channels_tried: List[str] = field(default_factory=list)
    channels_ok:    List[str] = field(default_factory=list)
    errors:         Dict[str, str] = field(default_factory=dict)
    sent_at:        str = field(default_factory=lambda: datetime.now().isoformat())

    def __str__(self) -> str:
        ok  = ", ".join(self.channels_ok)  or "none"
        err = "; ".join(f"{k}: {v}" for k, v in self.errors.items()) or "none"
        return f"AlertResult(ok=[{ok}], errors=[{err}])"


# ---------------------------------------------------------------------------
# Primary public function
# ---------------------------------------------------------------------------
def send_alert(
    level: AlertLevel,
    title: str,
    message: str,
    zone: str = "Unknown Zone",
    sensor_values: Optional[Dict[str, Any]] = None,
    recommended_action: str = "",
    estimated_impact: str = "",
    channels: Optional[List[str]] = None,
) -> AlertResult:
    """
    Send an alert through all configured channels.

    Parameters
    ----------
    level               : AlertLevel  – INFO / WARNING / CRITICAL
    title               : str         – short subject / headline
    message             : str         – body of the alert
    zone                : str         – zone or location name
    sensor_values       : dict        – raw sensor readings to include
    recommended_action  : str         – what the operator should do
    estimated_impact    : str         – human-readable impact estimate
    channels            : list[str]   – override channels;
                                        default: ["console", "email", "sms"]
                                        (email/sms only fire if env vars are set)

    Returns
    -------
    AlertResult  with per-channel status
    """
    if channels is None:
        channels = ["console", "email", "sms"]

    payload = _build_payload(
        level=level,
        title=title,
        message=message,
        zone=zone,
        sensor_values=sensor_values or {},
        recommended_action=recommended_action,
        estimated_impact=estimated_impact,
    )

    result = AlertResult(success=False, channels_tried=list(channels))

    for ch in channels:
        try:
            if ch == "console":
                _send_console(payload)
                result.channels_ok.append("console")
            elif ch == "email":
                _send_email(payload)
                result.channels_ok.append("email")
            elif ch == "sms":
                _send_sms(payload)
                result.channels_ok.append("sms")
            else:
                result.errors[ch] = f"Unknown channel '{ch}'"
        except _SkipChannel as e:
            # Channel not configured — not a failure, just skipped
            pass
        except Exception as e:
            result.errors[ch] = str(e)

    result.success = len(result.channels_ok) > 0
    return result


def send_alert_from_classification(
    zone: str,
    classification: Dict[str, Any],
    channels: Optional[List[str]] = None,
) -> AlertResult:
    """
    Convenience wrapper: build an alert directly from the dict returned
    by AnomalyRootCauseClassifier.classify().

    Parameters
    ----------
    zone           : str
    classification : dict  – output of AnomalyRootCauseClassifier.classify()
    channels       : list[str] or None
    """
    confidence = classification.get("confidence", "LOW")
    level_map  = {"HIGH": AlertLevel.CRITICAL, "MEDIUM": AlertLevel.WARNING,
                  "LOW":  AlertLevel.INFO}
    level = level_map.get(confidence, AlertLevel.WARNING)

    root_cause = classification.get("root_cause", "UNKNOWN")
    label      = classification.get("label", root_cause)

    title   = f"{label} — {zone}"
    message = classification.get("explanation", "Anomaly detected.")

    evidence = classification.get("supporting_evidence", [])
    if evidence:
        message += "\n\nEvidence:\n" + "\n".join(f"  • {e}" for e in evidence)

    return send_alert(
        level=level,
        title=title,
        message=message,
        zone=zone,
        sensor_values=classification.get("sensor_values", {}),
        recommended_action=classification.get("recommended_action", ""),
        estimated_impact="",
        channels=channels,
    )


def send_alert_from_recommendation(
    recommendation: Dict[str, Any],
    channels: Optional[List[str]] = None,
) -> AlertResult:
    """
    Convenience wrapper: build an alert directly from one recommendation
    dict returned by WaterRecommendationEngine.recommend_from_reading() or
    recommend_from_model_outputs().
    """
    priority_map = {
        "HIGH":   AlertLevel.CRITICAL,
        "MEDIUM": AlertLevel.WARNING,
        "LOW":    AlertLevel.INFO,
    }
    level = priority_map.get(recommendation.get("priority", "MEDIUM"),
                              AlertLevel.WARNING)
    zone  = recommendation.get("zone", "Unknown Zone")

    return send_alert(
        level=level,
        title=recommendation.get("message", "Water System Alert")[:120],
        message=recommendation.get("message", ""),
        zone=zone,
        sensor_values=recommendation.get("sensor_snapshot", {}),
        recommended_action=recommendation.get("recommended_action", ""),
        estimated_impact=recommendation.get("estimated_impact", ""),
        channels=channels,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class _SkipChannel(Exception):
    """Raised when a channel is not configured — silently skipped."""


def _build_payload(
    level: AlertLevel,
    title: str,
    message: str,
    zone: str,
    sensor_values: Dict[str, Any],
    recommended_action: str,
    estimated_impact: str,
) -> Dict[str, Any]:
    """Assemble a channel-agnostic payload dict."""
    sensor_lines = "\n".join(
        f"  {k}: {v}" for k, v in sensor_values.items()
    ) or "  (not provided)"

    short_text = textwrap.dedent(f"""
        [{level.value}] {title}
        Zone: {zone}
        {message}
        {"Action: " + recommended_action if recommended_action else ""}
        {"Impact: " + estimated_impact   if estimated_impact   else ""}
        Sensor readings:
        {sensor_lines}
        Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """).strip()

    html_body = _build_html(
        level=level,
        title=title,
        message=message,
        zone=zone,
        sensor_values=sensor_values,
        recommended_action=recommended_action,
        estimated_impact=estimated_impact,
    )

    return {
        "level":              level,
        "title":              title,
        "message":            message,
        "zone":               zone,
        "sensor_values":      sensor_values,
        "recommended_action": recommended_action,
        "estimated_impact":   estimated_impact,
        "short_text":         short_text,
        "html_body":          html_body,
        "timestamp":          datetime.now().isoformat(),
    }


def _build_html(
    level: AlertLevel,
    title: str,
    message: str,
    zone: str,
    sensor_values: Dict[str, Any],
    recommended_action: str,
    estimated_impact: str,
) -> str:
    colour = _LEVEL_COLOUR[level]
    emoji  = _LEVEL_EMOJI[level]

    sensor_rows = "".join(
        f"<tr><td style='padding:4px 12px;color:#64748b;'>{k}</td>"
        f"<td style='padding:4px 12px;font-weight:600;'>{v}</td></tr>"
        for k, v in sensor_values.items()
    ) or "<tr><td colspan='2' style='color:#94a3b8;'>Not provided</td></tr>"

    action_block = (
        f"<p style='margin:0 0 8px'><strong>Recommended action:</strong> "
        f"{recommended_action}</p>"
        if recommended_action else ""
    )
    impact_block = (
        f"<p style='margin:0 0 8px'><strong>Estimated impact:</strong> "
        f"{estimated_impact}</p>"
        if estimated_impact else ""
    )

    return f"""
    <html><body style='font-family:Arial,sans-serif;background:#f0f9ff;margin:0;padding:20px;'>
    <div style='max-width:600px;margin:0 auto;background:white;border-radius:12px;
                overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,.1);'>
        <div style='background:{colour};padding:20px 24px;'>
            <h2 style='color:white;margin:0;font-size:1.3rem;'>
                {emoji} {level.value}: {title}
            </h2>
            <p style='color:rgba(255,255,255,.85);margin:6px 0 0;font-size:.9rem;'>
                Zone: {zone} &nbsp;·&nbsp;
                {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </div>
        <div style='padding:24px;'>
            <p style='margin:0 0 16px;color:#1e293b;line-height:1.6;'>{message}</p>
            {action_block}
            {impact_block}
            <h4 style='margin:16px 0 8px;color:#1e293b;'>Sensor Readings</h4>
            <table style='border-collapse:collapse;width:100%;font-size:.9rem;'>
                <tbody>{sensor_rows}</tbody>
            </table>
        </div>
        <div style='background:#f8fafc;padding:12px 24px;border-top:1px solid #e2e8f0;'>
            <p style='margin:0;font-size:.8rem;color:#94a3b8;'>
                AI-Driven Smart Water Management System
                &nbsp;·&nbsp; Alert generated automatically
            </p>
        </div>
    </div>
    </body></html>
    """


# ---------------------------------------------------------------------------
# Channel: Console
# ---------------------------------------------------------------------------

def _send_console(payload: Dict[str, Any]) -> None:
    level  = payload["level"]
    emoji  = _LEVEL_EMOJI[level]
    border = "=" * 70
    print(f"\n{border}")
    print(f"{emoji}  WATER SYSTEM ALERT  [{level.value}]  —  {payload['zone']}")
    print(border)
    print(payload["short_text"])
    print(border)


# ---------------------------------------------------------------------------
# Channel: Email (SMTP)
# ---------------------------------------------------------------------------

def _send_email(payload: Dict[str, Any]) -> None:
    host     = os.getenv("ALERT_EMAIL_HOST",     "smtp.gmail.com")
    port     = int(os.getenv("ALERT_EMAIL_PORT", "587"))
    user     = os.getenv("ALERT_EMAIL_USER",     "").strip()
    password = os.getenv("ALERT_EMAIL_PASSWORD", "").strip()
    to_raw   = os.getenv("ALERT_EMAIL_TO",       "").strip()
    use_tls  = os.getenv("ALERT_EMAIL_USE_TLS",  "true").lower() == "true"

    if not user or not password or not to_raw:
        raise _SkipChannel("Email not configured (ALERT_EMAIL_USER / PASSWORD / TO not set)")

    recipients = [r.strip() for r in to_raw.split(",") if r.strip()]
    if not recipients:
        raise _SkipChannel("ALERT_EMAIL_TO is set but contains no valid addresses")

    level   = payload["level"]
    subject = (
        f"[{level.value}] Smart Water Alert — {payload['title']} "
        f"| {payload['zone']}"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = user
    msg["To"]      = ", ".join(recipients)

    msg.attach(MIMEText(payload["short_text"], "plain", "utf-8"))
    msg.attach(MIMEText(payload["html_body"],  "html",  "utf-8"))

    with smtplib.SMTP(host, port, timeout=15) as server:
        if use_tls:
            server.starttls()
        server.login(user, password)
        server.sendmail(user, recipients, msg.as_string())

    print(f"[Alerts] Email sent to {recipients}")


# ---------------------------------------------------------------------------
# Channel: SMS (Twilio)
# ---------------------------------------------------------------------------

def _send_sms(payload: Dict[str, Any]) -> None:
    if not _TWILIO_AVAILABLE:
        raise _SkipChannel(
            "twilio library not installed — run: pip install twilio==8.13.0"
        )

    sid      = os.getenv("TWILIO_ACCOUNT_SID",  "").strip()
    token    = os.getenv("TWILIO_AUTH_TOKEN",    "").strip()
    from_num = os.getenv("TWILIO_FROM_NUMBER",   "").strip()
    to_raw   = os.getenv("ALERT_SMS_TO",         "").strip()

    if not sid or not token or not from_num or not to_raw:
        raise _SkipChannel(
            "SMS not configured (TWILIO_ACCOUNT_SID / AUTH_TOKEN / "
            "FROM_NUMBER / ALERT_SMS_TO not set)"
        )

    recipients = [r.strip() for r in to_raw.split(",") if r.strip()]
    if not recipients:
        raise _SkipChannel("ALERT_SMS_TO contains no valid numbers")

    # SMS body: keep under 160 chars for a single segment
    level   = payload["level"]
    emoji   = _LEVEL_EMOJI[level]
    sv      = payload["sensor_values"]
    sv_str  = " | ".join(f"{k}:{v}" for k, v in list(sv.items())[:3])

    body = (
        f"{emoji}[{level.value}] {payload['zone']}: {payload['title'][:60]}. "
        f"{sv_str}. "
        f"{payload['recommended_action'][:60]}"
    )
    body = body[:320]  # Twilio max body

    client = TwilioClient(sid, token)
    for number in recipients:
        client.messages.create(body=body, from_=from_num, to=number)
        print(f"[Alerts] SMS sent to {number}")


# ---------------------------------------------------------------------------
# Standalone smoke-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Running alert smoke-test (console channel only)…\n")

    result = send_alert(
        level=AlertLevel.CRITICAL,
        title="Pipe Leak — Zone 3",
        message=(
            "Flow dropped to 5.8 L/min (61% below baseline). "
            "Isolation Forest anomaly score: -0.45."
        ),
        zone="Zone-3",
        sensor_values={
            "flow":        5.8,
            "pressure":    1.1,
            "ph":          7.3,
            "turbidity":   3.0,
            "temperature": 26.5,
        },
        recommended_action="Dispatch field team to inspect pipeline joints and valves.",
        estimated_impact="~2,300 L/day unaccounted water loss.",
        channels=["console"],   # email/sms only if env vars are set
    )
    print(f"\nResult: {result}")

    # Test classification convenience wrapper
    print("\n--- Classification wrapper test ---")
    mock_classification = {
        "root_cause":         "LEAK",
        "label":              "Pipe Leak / Valve Malfunction",
        "confidence":         "HIGH",
        "explanation":        "Dual drop in flow and pressure detected.",
        "recommended_action": "Inspect pipeline joints immediately.",
        "supporting_evidence": [
            "flow=5.8 L/min AND pressure=1.1 bar — both below threshold.",
            "Severe flow drop: >50% below baseline.",
        ],
        "sensor_values": {"flow": 5.8, "pressure": 1.1},
    }
    result2 = send_alert_from_classification(
        zone="Zone-3",
        classification=mock_classification,
        channels=["console"],
    )
    print(f"Result: {result2}")
