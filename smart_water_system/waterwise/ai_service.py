"""AI service module for WaterWise AI.

Handles Google Gen AI SDK client lifecycle, generation requests, chat history management,
and robust provider error handling. Enforces pre-flight application safety checks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from waterwise import config
from waterwise import prompts
from waterwise import safety

logger = logging.getLogger("waterwise.ai_service")

# Bound chat context to prevent unbounded token expansion
MAX_HISTORY_MESSAGES = 10


@dataclass
class ExplanationResponse:
    """Standardized response from the AI service."""
    content: str
    is_refusal: bool = False
    refusal_reason: Optional[str] = None
    is_live_ai: bool = False
    model_used: Optional[str] = None
    error_detail: Optional[str] = None


class GeminiExplainerService:
    """Manages Gemini Flash client and content generation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        from_config_if_none: bool = True,
    ):
        if api_key is None and from_config_if_none:
            self._api_key = config.get_api_key()
        else:
            self._api_key = api_key
        self._model_name = model_name or config.get_model_name()
        self._client: Any = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize the Google Gen AI client if credentials exist."""
        if not self._api_key:
            self._client = None
            return

        try:
            from google import genai
            self._client = genai.Client(api_key=self._api_key)
        except Exception as exc:
            logger.warning("Failed to initialize Google GenAI client: %s", type(exc).__name__)
            self._client = None

    def is_ready(self) -> bool:
        """Check whether the client is instantiated and ready for requests."""
        return self._client is not None

    def get_configured_model(self) -> str:
        """Return the currently configured model identifier."""
        return self._model_name

    def explain(
        self,
        user_query: str,
        chat_history: Optional[list[dict[str, str]]] = None,
    ) -> ExplanationResponse:
        """Process a user query, enforce safety, and generate an educational explanation.
        
        This method strictly performs safety validation BEFORE attempting any API call.
        """
        # Step 1: Pre-flight Safety Enforcement (BEFORE API CALL)
        safety_eval = safety.check_safety(user_query)
        if not safety_eval.is_allowed:
            return ExplanationResponse(
                content=safety_eval.refusal_message or safety.REFUSAL_GENERAL_OPERATIONAL,
                is_refusal=True,
                refusal_reason=safety_eval.reason,
                is_live_ai=False,
                model_used=None,
            )

        # Step 2: Check API Key and Client Availability
        if not self._client or not self._api_key:
            return ExplanationResponse(
                content=(
                    "**API Configuration Notice**\n\n"
                    "Google AI Studio API key is not configured. Live Gemini generation is disabled.\n\n"
                    "**To enable live explanations:**\n"
                    "1. Obtain a free API key from [Google AI Studio](https://aistudio.google.com/).\n"
                    "2. Set the environment variable: `export GEMINI_API_KEY='your_api_key'`\n"
                    "   or create `.streamlit/secrets.toml` with `GEMINI_API_KEY = \"your_api_key\"`.\n\n"
                    "You can still explore all curated topics in the **Educational Knowledge Centre** below."
                ),
                is_refusal=False,
                is_live_ai=False,
                model_used=None,
                error_detail="API credentials missing.",
            )

        # Step 3: Prepare Bounded History and Messages
        bounded_history: list[dict[str, str]] = []
        if chat_history:
            # Bound history to last N messages
            recent_history = chat_history[-MAX_HISTORY_MESSAGES:]
            for msg in recent_history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    bounded_history.append({"role": role, "content": content})

        # Step 4: Call Gemini via official google-genai SDK
        try:
            from google.genai import types

            # Build generation config with system instruction and conservative settings
            gen_config = types.GenerateContentConfig(
                system_instruction=prompts.SYSTEM_INSTRUCTION,
                temperature=0.4,
                max_output_tokens=1024,
            )

            # Build contents list from history + current prompt
            contents: list[Any] = []
            for item in bounded_history:
                c_role = "user" if item["role"] == "user" else "model"
                contents.append(
                    types.Content(
                        role=c_role,
                        parts=[types.Part.from_text(text=item["content"])],
                    )
                )

            # Add current user prompt
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompts.format_user_prompt(user_query))],
                )
            )

            response = self._client.models.generate_content(
                model=self._model_name,
                contents=contents,
                config=gen_config,
            )

            # Validate response text
            if response and response.text and response.text.strip():
                return ExplanationResponse(
                    content=response.text.strip(),
                    is_refusal=False,
                    is_live_ai=True,
                    model_used=self._model_name,
                )
            else:
                return ExplanationResponse(
                    content=(
                        "I received an empty response from the AI provider. "
                        "Please try phrasing your educational question slightly differently."
                    ),
                    is_refusal=False,
                    is_live_ai=False,
                    model_used=self._model_name,
                    error_detail="Empty response text returned by provider.",
                )

        except Exception as exc:
            return self._handle_provider_exception(exc)

    def _handle_provider_exception(self, exc: Exception) -> ExplanationResponse:
        """Translate provider exceptions into safe, actionable user messages."""
        err_str = str(exc)
        err_type = type(exc).__name__

        # Model Not Found / Inaccessible (e.g., 404 or NOT_FOUND)
        if "404" in err_str or "NOT_FOUND" in err_str or "not found" in err_str.lower():
            msg = (
                f"**Configured Model Inaccessible ({self._model_name})**\n\n"
                f"The model `{self._model_name}` could not be accessed using the configured API project.\n\n"
                "**Actionable Resolution:**\n"
                "- Verify if your Google AI Studio project has access to this model version.\n"
                "- You can switch models by setting `GEMINI_MODEL=gemini-3.6-flash` or "
                "`GEMINI_MODEL=gemini-2.5-flash` in your `.env` file or Streamlit secrets.\n"
                "- Restart the application after changing the model setting."
            )
            return ExplanationResponse(
                content=msg,
                is_refusal=False,
                is_live_ai=False,
                model_used=self._model_name,
                error_detail=f"Model {self._model_name} returned 404/NotFound.",
            )

        # Authentication / Invalid API Key (401 / 403 / UNAUTHENTICATED / PERMISSION_DENIED)
        if "401" in err_str or "403" in err_str or "PERMISSION_DENIED" in err_str or "API_KEY_INVALID" in err_str:
            msg = (
                "**Authentication Failed**\n\n"
                "The configured Gemini API key appears invalid or expired. "
                "Please verify your API key in [Google AI Studio](https://aistudio.google.com/) and update your configuration."
            )
            return ExplanationResponse(
                content=msg,
                is_refusal=False,
                is_live_ai=False,
                model_used=self._model_name,
                error_detail="Authentication/Permission error from API provider.",
            )

        # Rate Limit / Quota Exceeded (429 / RESOURCE_EXHAUSTED)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
            msg = (
                "**Rate Limit / Quota Exceeded**\n\n"
                "The API quota for your Google AI Studio account has been temporarily reached. "
                "Please wait a few moments before submitting another question."
            )
            return ExplanationResponse(
                content=msg,
                is_refusal=False,
                is_live_ai=False,
                model_used=self._model_name,
                error_detail="API rate limit or quota exceeded.",
            )

        # Network / Timeout / Connection issues
        if "timeout" in err_str.lower() or "connection" in err_str.lower() or "dns" in err_str.lower():
            msg = (
                "**Network Connection Issue**\n\n"
                "Unable to reach the Google AI Studio service. Please check your internet connection "
                "or proxy settings and try again."
            )
            return ExplanationResponse(
                content=msg,
                is_refusal=False,
                is_live_ai=False,
                model_used=self._model_name,
                error_detail="Network connection error.",
            )

        # General unexpected provider error (safe, no secret leakage)
        msg = (
            f"**Service Notice**\n\n"
            f"An unexpected provider error occurred ({err_type}). "
            "Your existing conversation has been preserved. Please try again shortly."
        )
        return ExplanationResponse(
            content=msg,
            is_refusal=False,
            is_live_ai=False,
            model_used=self._model_name,
            error_detail=f"Provider exception: {err_type}",
        )


# Global cached service helper for Streamlit session
_CACHED_SERVICE: Optional[GeminiExplainerService] = None


def get_ai_service(force_refresh: bool = False) -> GeminiExplainerService:
    """Retrieve or create a reusable GeminiExplainerService singleton instance."""
    global _CACHED_SERVICE
    if _CACHED_SERVICE is None or force_refresh:
        _CACHED_SERVICE = GeminiExplainerService()
    return _CACHED_SERVICE
