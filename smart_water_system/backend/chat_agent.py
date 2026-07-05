"""
Decision Intelligence - Gemini Natural Language Chat Agent
==========================================================
A self-contained FastAPI router that adds a conversational Q&A endpoint
on top of the existing water management system.

HOW TO REGISTER IN THE EXISTING SERVER (ONE LINE)
--------------------------------------------------
Open ``backend/fastapi_server.py`` and add **at the bottom of the imports
section** (do NOT modify any existing line):

    from backend.chat_agent import router as chat_router

Then, **directly below** the existing ``app = FastAPI(...)`` line, add:

    app.include_router(chat_router)

That is all.  The new endpoint will appear at:

    POST  /api/chat          – ask a natural-language question
    GET   /api/chat/health   – confirm the agent is live and Gemini key is set

ENVIRONMENT VARIABLES
---------------------
Set before running the server:

    GEMINI_API_KEY=<your-key>      # required – get from Google AI Studio
    WATER_DB_PATH=database/water.db  # optional – defaults to the existing path

EXAMPLE REQUEST
---------------
    curl -X POST http://localhost:8000/api/chat \\
         -H "Content-Type: application/json" \\
         -d '{"question": "Was there a leak in the last hour?"}'

EXAMPLE RESPONSE
----------------
    {
      "answer": "Yes. Between 14:32 and 14:41 the flow dropped to 5.8 L/min ...",
      "context_rows_used": 12,
      "model": "gemini-1.5-flash",
      "generated_at": "2026-07-05T14:55:00.123456"
    }

DEPENDENCIES
------------
    pip install google-generativeai==0.7.2

NEW DEPENDENCY: google-generativeai==0.7.2
  (already noted in requirements-additions.txt — add it there and run
   pip install -r requirements-additions.txt)
"""

from __future__ import annotations

import os
import sqlite3
import textwrap
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Optional import – degrade gracefully if library not yet installed
# ---------------------------------------------------------------------------
try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_DB_PATH: str = os.getenv("WATER_DB_PATH", "database/water.db")
_GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# How many recent rows to pull for context (keep prompt size reasonable)
_CONTEXT_ROWS: int = 50
# How many anomaly rows to include separately
_ANOMALY_ROWS: int = 10

# System prompt that frames the model as a water-management assistant
_SYSTEM_PROMPT = textwrap.dedent("""
    You are an expert water network operations assistant embedded in an
    AI-powered Smart Water Management System.

    You have been given a snapshot of recent sensor readings and anomaly
    statistics from the system database. Use ONLY this data to answer
    the user's question. Do not invent numbers not present in the data.

    If the data is insufficient to answer confidently, say so clearly and
    suggest what additional information would help.

    Always include:
    - Specific sensor values when relevant (flow in L/min, pressure in bar,
      pH, turbidity in NTU, temperature in °C).
    - A plain-English interpretation suitable for a field engineer or
      water authority official.
    - If an anomaly is present, state whether it looks like a leak,
      contamination, high usage, or sensor fault.
    - If asked about savings or projections, provide a rough estimate with
      your reasoning.

    Respond concisely but completely.  Use bullet points for lists.
""").strip()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Natural-language question about the water system.",
        examples=["Was there a leak in the last hour?",
                  "What is the current water quality status?",
                  "Which zone has the highest demand right now?"],
    )
    context_rows: Optional[int] = Field(
        default=None,
        ge=1,
        le=200,
        description="Override number of recent DB rows to include in context.",
    )


class ChatResponse(BaseModel):
    answer: str
    context_rows_used: int
    model: str
    generated_at: str


class HealthResponse(BaseModel):
    status: str
    gemini_key_set: bool
    genai_library_installed: bool
    db_accessible: bool
    model: str


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/api/chat", tags=["Chat Agent"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Confirm the chat agent is live and all dependencies are available."""
    key_set = bool(os.getenv("GEMINI_API_KEY"))
    db_ok = _check_db()
    return HealthResponse(
        status="ok" if (key_set and db_ok and _GENAI_AVAILABLE) else "degraded",
        gemini_key_set=key_set,
        genai_library_installed=_GENAI_AVAILABLE,
        db_accessible=db_ok,
        model=_GEMINI_MODEL,
    )


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Accept a natural-language question, enrich it with live DB context,
    and return a Gemini-generated answer.
    """
    # --- Guard: library installed? ---
    if not _GENAI_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail=(
                "google-generativeai is not installed. "
                "Run: pip install google-generativeai==0.7.2"
            ),
        )

    # --- Guard: API key set? ---
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "GEMINI_API_KEY environment variable is not set. "
                "Export it before starting the server."
            ),
        )

    # --- Pull DB context ---
    n_rows = request.context_rows or _CONTEXT_ROWS
    context_text, rows_used = _build_context(n_rows)

    # --- Build prompt ---
    prompt = _build_prompt(request.question, context_text)

    # --- Call Gemini ---
    answer = _call_gemini(api_key, prompt)

    return ChatResponse(
        answer=answer,
        context_rows_used=rows_used,
        model=_GEMINI_MODEL,
        generated_at=datetime.now().isoformat(),
    )


# ---------------------------------------------------------------------------
# DB context builder
# ---------------------------------------------------------------------------
def _check_db() -> bool:
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.execute("SELECT 1 FROM sensor_data LIMIT 1")
        conn.close()
        return True
    except Exception:
        return False


def _build_context(n_rows: int) -> tuple[str, int]:
    """
    Pull recent sensor readings + aggregate stats from the existing DB
    and format them as a compact text block for the prompt.

    Returns (context_text, number_of_rows_included).
    """
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row

        # 1. Recent readings
        rows: List[sqlite3.Row] = conn.execute(
            """
            SELECT timestamp, flow, pressure, ph, turbidity, temperature
            FROM sensor_data
            ORDER BY id DESC
            LIMIT ?
            """,
            (n_rows,),
        ).fetchall()

        # 2. Aggregate stats (last 1 hour ≈ 720 rows at 5-second intervals)
        stats = conn.execute(
            """
            SELECT
                COUNT(*)               AS total_rows,
                ROUND(AVG(flow),2)     AS avg_flow,
                ROUND(MIN(flow),2)     AS min_flow,
                ROUND(MAX(flow),2)     AS max_flow,
                ROUND(AVG(pressure),2) AS avg_pressure,
                ROUND(MIN(pressure),2) AS min_pressure,
                ROUND(MAX(pressure),2) AS max_pressure,
                ROUND(AVG(ph),2)       AS avg_ph,
                ROUND(MIN(ph),2)       AS min_ph,
                ROUND(MAX(ph),2)       AS max_ph,
                ROUND(AVG(turbidity),2) AS avg_turbidity,
                ROUND(MAX(turbidity),2) AS max_turbidity,
                ROUND(AVG(temperature),2) AS avg_temperature
            FROM (
                SELECT flow, pressure, ph, turbidity, temperature
                FROM sensor_data
                ORDER BY id DESC
                LIMIT 720
            )
            """
        ).fetchone()

        # 3. Anomaly candidates: rows where flow < 8 or turbidity > 5
        anomalies = conn.execute(
            """
            SELECT timestamp, flow, pressure, ph, turbidity, temperature
            FROM sensor_data
            WHERE flow < 8.0 OR turbidity > 5.0 OR ph < 6.5 OR ph > 8.5
            ORDER BY id DESC
            LIMIT ?
            """,
            (_ANOMALY_ROWS,),
        ).fetchall()

        conn.close()

    except Exception as exc:
        return f"[DB unavailable: {exc}]", 0

    if not rows:
        return "[No sensor data in database yet.]", 0

    # --- Format recent readings ---
    readings_lines = ["timestamp,flow,pressure,ph,turbidity,temperature"]
    for r in reversed(rows):  # chronological order
        readings_lines.append(
            f"{r['timestamp']},"
            f"{r['flow']:.2f},{r['pressure']:.2f},"
            f"{r['ph']:.2f},{r['turbidity']:.2f},{r['temperature']:.2f}"
        )

    # --- Format stats ---
    s = stats
    stats_block = (
        f"LAST-HOUR STATS (up to 720 readings):\n"
        f"  Total readings : {s['total_rows']}\n"
        f"  Flow      : avg={s['avg_flow']} | min={s['min_flow']} | max={s['max_flow']} L/min\n"
        f"  Pressure  : avg={s['avg_pressure']} | min={s['min_pressure']} | max={s['max_pressure']} bar\n"
        f"  pH        : avg={s['avg_ph']} | min={s['min_ph']} | max={s['max_ph']}\n"
        f"  Turbidity : avg={s['avg_turbidity']} | max={s['max_turbidity']} NTU\n"
        f"  Temperature: avg={s['avg_temperature']} °C"
    )

    # --- Format anomalies ---
    if anomalies:
        anomaly_lines = [
            "RECENT ANOMALOUS READINGS (flow<8 OR turbidity>5 OR pH out of 6.5-8.5):",
            "timestamp,flow,pressure,ph,turbidity,temperature",
        ]
        for a in anomalies:
            anomaly_lines.append(
                f"{a['timestamp']},"
                f"{a['flow']:.2f},{a['pressure']:.2f},"
                f"{a['ph']:.2f},{a['turbidity']:.2f},{a['temperature']:.2f}"
            )
        anomaly_block = "\n".join(anomaly_lines)
    else:
        anomaly_block = "RECENT ANOMALOUS READINGS: none detected in the queried window."

    context_text = "\n\n".join([
        stats_block,
        anomaly_block,
        f"MOST RECENT {len(rows)} SENSOR READINGS (CSV, chronological):\n"
        + "\n".join(readings_lines),
    ])

    return context_text, len(rows)


def _build_prompt(question: str, context: str) -> str:
    return (
        f"{_SYSTEM_PROMPT}\n\n"
        f"=== LIVE DATABASE CONTEXT ===\n"
        f"{context}\n\n"
        f"=== USER QUESTION ===\n"
        f"{question}\n\n"
        f"=== YOUR ANSWER ==="
    )


# ---------------------------------------------------------------------------
# Gemini call
# ---------------------------------------------------------------------------
def _call_gemini(api_key: str, prompt: str) -> str:
    """
    Send the prompt to Gemini and return the text response.
    Raises HTTPException on API errors so FastAPI returns a clean 502.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(_GEMINI_MODEL)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,       # factual, low creativity
                max_output_tokens=1024,
            ),
        )
        # Extract text safely
        if response.text:
            return response.text.strip()
        # Fallback: try candidates
        if response.candidates:
            return response.candidates[0].content.parts[0].text.strip()
        return "Gemini returned an empty response. Please try again."
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini API error: {exc}",
        )


# ---------------------------------------------------------------------------
# Standalone smoke-test (run: python backend/chat_agent.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json

    print("=" * 60)
    print("Chat Agent – standalone smoke test")
    print("=" * 60)

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        print("⚠  GEMINI_API_KEY not set – skipping live Gemini call.")
        print("   Context builder will still run against the local DB.\n")

    ctx, rows_used = _build_context(_CONTEXT_ROWS)
    print(f"DB context built: {rows_used} rows\n")
    print(ctx[:800], "..." if len(ctx) > 800 else "")

    if api_key and _GENAI_AVAILABLE:
        print("\n--- Sending test question to Gemini ---")
        test_q = "Summarise the current water quality status and flag any concerns."
        prompt = _build_prompt(test_q, ctx)
        answer = _call_gemini(api_key, prompt)
        print(f"\nQ: {test_q}\nA: {answer}")
    else:
        print("\nSkipping live API call (key missing or library not installed).")
