"""Safety enforcement module for WaterWise AI.

Implements strict, deterministic application-side safety boundaries before
any LLM invocation. Differentiates legitimate educational queries from prohibited
operational requests, local arrival predictions, complaint filings, and
prompt injection attempts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

MAX_INPUT_LENGTH = 2000

# Required standard refusal strings
REFUSAL_ARRIVAL_PREDICTION = (
    "I can explain how water supply schedules generally work, but I cannot predict "
    "or verify the arrival time for your area. Please check the official local water "
    "authority's published schedule for accurate information."
)

REFUSAL_COMPLAINT_REGISTRATION = (
    "I can explain common causes of low water pressure, but I cannot register complaints "
    "or submit service requests. Please use your local water authority's official "
    "complaint channel."
)

REFUSAL_INFRASTRUCTURE_CONTROL = (
    "I am an educational explainer and cannot operate or control municipal water "
    "infrastructure, pumps, valves, meters, or telemetry systems."
)

REFUSAL_PROMPT_INJECTION = (
    "I am WaterWise AI, an educational assistant dedicated to explaining water "
    "treatment and distribution processes. I cannot alter my core instructions, "
    "bypass safety guidelines, or execute operational tasks."
)

REFUSAL_GENERAL_OPERATIONAL = (
    "I am an educational explainer for water utility processes. I cannot provide "
    "live localized operational tracking, dispatch service personnel, or log "
    "work orders. Please contact your municipal water authority directly."
)

REFUSAL_OVERSIZED_INPUT = (
    f"Your message exceeds the maximum allowed length of {MAX_INPUT_LENGTH} characters. "
    "Please shorten your query to continue."
)

REFUSAL_EMPTY_INPUT = (
    "Please enter a valid question or select one of the suggested educational topics."
)


@dataclass
class SafetyResult:
    """Represents the outcome of a pre-flight safety analysis."""
    is_allowed: bool
    refusal_message: Optional[str] = None
    category: str = "educational"
    reason: Optional[str] = None


# Patterns for prompt injection / instruction overriding
PROMPT_INJECTION_PATTERNS = [
    r"\bignore\s+(all\s+)?(previous|prior|above)\s+instructions\b",
    r"\bdisregard\s+(all\s+)?(previous|prior|above)\b",
    r"\breveal\s+(the\s+)?(hidden\s+)?(system\s+)?(prompt|instruction)\b",
    r"\bshow\s+(me\s+)?(the\s+)?(system\s+)?prompt\b",
    r"\bprint\s+(the\s+)?(system\s+)?(prompt|instructions)\b",
    r"\bjailbreak\b",
    r"\bDAN\s+mode\b",
    r"\bbypass\s+(all\s+)?(safety|security|rules)\b",
    r"\byou\s+are\s+now\s+an\s+unrestricted\b",
    r"\bact\s+as\s+(an\s+)?unrestricted\b",
    r"\bpretend\s+to\s+have\s+root\b",
    r"\boverride\s+safety\b",
]

# Prohibited: Arrival prediction / local schedule inquiry for specific location/time
# Matches: "when will water arrive in my area", "what time will water come tomorrow",
# "is water coming to Sector 4", "check water supply time for my house"
ARRIVAL_PREDICTION_PATTERNS = [
    r"\bwhen\s+will\s+(the\s+)?water\s+(supply\s+)?(arrive|come|reach|turn\s+on)\b",
    r"\bwhat\s+time\s+(does|will|is)\s+(the\s+)?water\s+(coming|come|arrive|turn\s+on)\b",
    r"\bis\s+water\s+(running|coming|arrived|available)\s+(in|at)\s+(my\s+area|my\s+neighborhood|my\s+house|my\s+street|zone\s+\d+|sector\s+\d+|ward\s+\d+)\b",
    r"\bcheck\s+(my\s+)?(water\s+)?(arrival|timing|schedule)\s+for\s+(my\s+area|my\s+house|my\s+street|sector\s+\d+|zone\s+\d+)\b",
    r"\bwhen\s+is\s+(the\s+)?(next\s+)?water\s+release\s+in\s+my\b",
    r"\bpredict\s+(the\s+)?(water\s+)?arrival\b",
]

# Prohibited: Complaint registration / reporting a live local issue / service booking
# Matches: "register a complaint", "file a complaint", "log a ticket", "book a technician",
# "report a leak at 5th street", "submit service request"
COMPLAINT_REGISTRATION_PATTERNS = [
    r"\b(register|file|submit|lodge|log|raise)\s+(a\s+)?(new\s+)?(complaint|grievance|ticket|service\s+request|issue|dispute)\b",
    r"\b(book|schedule|request)\s+(a\s+)?(maintenance|repair|technician|plumber|inspection|engineer|visit)\b",
    r"\breport\s+(a\s+)?(burst\s+pipe|pipe\s+leak|water\s+leak|sewer\s+backup|low\s+pressure|contamination)\s+(at|on|in\s+my)\b",
    r"\bfix\s+my\s+(low\s+pressure|water\s+supply|meter|pipe|tap)\b",
    r"\bsend\s+(someone|technician|help|a\s+plumber)\s+to\s+(fix|check)\b",
]

# Prohibited: Infrastructure manipulation / IoT / SCADA control
INFRASTRUCTURE_CONTROL_PATTERNS = [
    r"\b(turn\s+(on|off)|shut\s+down|start|stop|open|close|calibrate|switch)\s+(the\s+)?(pump|valve|meter|turbine|sluice|pipeline|gate|reservoir)\b",
    r"\b(increase|decrease|adjust|override)\s+(the\s+)?(water\s+)?(pressure|flow\s+rate|chlorine\s+dosage)\s+now\b",
    r"\bcontrol\s+(the\s+)?(scada|telemetry|plc|pumps|valves)\b",
    r"\bcut\s+off\s+water\s+(supply\s+)?to\b",
]

# Prohibited: General local operational tracking & non-water unrelated requests
GENERAL_OPERATIONAL_PATTERNS = [
    r"\btrack\s+(live|real-?time)\s+(water\s+supply|pipeline|tanker|truck)\b",
    r"\bdispatch\s+(a\s+)?(tanker|water\s+truck|crew)\b",
    r"\bforecast\s+crop\s+irrigation\b",
    r"\bsmart\s+agriculture\s+scheduling\b",
]

# Explicit allowed educational phrases even if they contain words like "schedule" or "complaint"
EDUCATIONAL_ALLOWLIST_PATTERNS = [
    r"\bhow\s+do\s+(municipal\s+)?(water\s+)?(distribution\s+)?schedules\s+(generally\s+)?work\b",
    r"\bexplain\s+(how\s+)?(municipal\s+)?(water\s+)?(distribution\s+)?schedules\s+work\b",
    r"\bwhy\s+do\s+cities\s+have\s+(water\s+)?schedules\b",
    r"\bhow\s+do\s+(water\s+)?utilities\s+(generally\s+)?handle\s+complaints\b",
    r"\bexplain\s+(the\s+)?(general\s+)?complaint\s+(process|procedure|handling)\b",
    r"\bwhat\s+is\s+the\s+procedure\s+for\s+water\s+complaints\b",
    r"\bhow\s+do\s+citizens\s+locate\s+official\s+utility\s+information\b",
]


def check_safety(user_input: str) -> SafetyResult:
    """Analyze a user's prompt and enforce deterministic application safety boundaries.
    
    Returns a SafetyResult indicating if the prompt is allowed and provides
    the appropriate refusal message if prohibited.
    """
    if not user_input or not user_input.strip():
        return SafetyResult(
            is_allowed=False,
            refusal_message=REFUSAL_EMPTY_INPUT,
            category="empty_input",
            reason="User input is empty or contains only whitespace.",
        )

    clean_text = user_input.strip()

    # Bounded input check
    if len(clean_text) > MAX_INPUT_LENGTH:
        return SafetyResult(
            is_allowed=False,
            refusal_message=REFUSAL_OVERSIZED_INPUT,
            category="oversized_input",
            reason=f"Input length {len(clean_text)} exceeds {MAX_INPUT_LENGTH} characters.",
        )

    lower_text = clean_text.lower()

    # Check 1: Prompt Injection Defense
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, lower_text, re.IGNORECASE):
            return SafetyResult(
                is_allowed=False,
                refusal_message=REFUSAL_PROMPT_INJECTION,
                category="prompt_injection",
                reason="Input triggered prompt-injection or instruction-override protection.",
            )

    # Check 2: Explicit educational questions about schedules and complaints take precedence
    # over operational triggers if framed educationally (e.g. "How do municipal water distribution schedules generally work?")
    is_educational_override = any(
        re.search(pat, lower_text, re.IGNORECASE) for pat in EDUCATIONAL_ALLOWLIST_PATTERNS
    )

    # Check 3: Arrival predictions
    if not is_educational_override:
        for pattern in ARRIVAL_PREDICTION_PATTERNS:
            if re.search(pattern, lower_text, re.IGNORECASE):
                return SafetyResult(
                    is_allowed=False,
                    refusal_message=REFUSAL_ARRIVAL_PREDICTION,
                    category="arrival_prediction",
                    reason="Input requests local water arrival prediction or real-time local timing.",
                )

    # Check 4: Complaint registration / maintenance booking
    if not is_educational_override:
        for pattern in COMPLAINT_REGISTRATION_PATTERNS:
            if re.search(pattern, lower_text, re.IGNORECASE):
                return SafetyResult(
                    is_allowed=False,
                    refusal_message=REFUSAL_COMPLAINT_REGISTRATION,
                    category="complaint_registration",
                    reason="Input requests registering a municipal complaint, service ticket, or dispatch.",
                )

    # Check 5: Infrastructure & SCADA control
    for pattern in INFRASTRUCTURE_CONTROL_PATTERNS:
        if re.search(pattern, lower_text, re.IGNORECASE):
            return SafetyResult(
                is_allowed=False,
                refusal_message=REFUSAL_INFRASTRUCTURE_CONTROL,
                category="infrastructure_control",
                reason="Input requests operational manipulation of physical water infrastructure.",
            )

    # Check 6: General prohibited operational requests
    if not is_educational_override:
        for pattern in GENERAL_OPERATIONAL_PATTERNS:
            if re.search(pattern, lower_text, re.IGNORECASE):
                return SafetyResult(
                    is_allowed=False,
                    refusal_message=REFUSAL_GENERAL_OPERATIONAL,
                    category="general_operational",
                    reason="Input requests operational tracking or unsupported dispatch functionality.",
                )

    # Passed all safety checks
    return SafetyResult(
        is_allowed=True,
        refusal_message=None,
        category="educational",
        reason="Input is a legitimate educational or utility process question.",
    )
