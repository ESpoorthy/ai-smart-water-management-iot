"""Configuration management for WaterWise AI.

Handles API keys, model selection, and environment settings following
strict security priorities without leaking credentials.
"""

from __future__ import annotations

import os
from typing import Optional

# Optional dotenv support if .env file exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DEFAULT_MODEL = "gemini-3.6-flash"
ALLOWED_MODELS = (
    "gemini-3.6-flash",
    "gemini-3.8-flash",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
)


def _get_streamlit_secret(key: str) -> Optional[str]:
    """Safely inspect Streamlit secrets if running within Streamlit context."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            val = st.secrets[key]
            if isinstance(val, str) and val.strip():
                return val.strip()
    except Exception:
        pass
    return None


def get_api_key() -> Optional[str]:
    """Retrieve Gemini API key based on priority rules:
    
    1. GEMINI_API_KEY environment variable.
    2. GEMINI_API_KEY in Streamlit secrets.
    3. GOOGLE_API_KEY environment variable (fallback).
    4. GOOGLE_API_KEY in Streamlit secrets (fallback).
    """
    # 1. GEMINI_API_KEY env
    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key

    # 2. GEMINI_API_KEY in Streamlit secrets
    st_secret = _get_streamlit_secret("GEMINI_API_KEY")
    if st_secret:
        return st_secret

    # 3. GOOGLE_API_KEY env fallback
    fallback_env = os.environ.get("GOOGLE_API_KEY", "").strip()
    if fallback_env:
        return fallback_env

    # 4. GOOGLE_API_KEY in Streamlit secrets fallback
    fallback_st = _get_streamlit_secret("GOOGLE_API_KEY")
    if fallback_st:
        return fallback_st

    return None


def get_model_name() -> str:
    """Retrieve configured Gemini Flash model name.
    
    Defaults to 'gemini-3.6-flash' unless explicitly overridden by
    GEMINI_MODEL environment variable or Streamlit secret.
    """
    env_model = os.environ.get("GEMINI_MODEL", "").strip()
    if env_model:
        return env_model

    st_model = _get_streamlit_secret("GEMINI_MODEL")
    if st_model:
        return st_model

    return DEFAULT_MODEL


def is_api_configured() -> bool:
    """Check whether a non-empty API key is available."""
    key = get_api_key()
    return bool(key and len(key) > 5)


def get_masked_api_key() -> str:
    """Return a safely masked string representation of the active API key."""
    key = get_api_key()
    if not key:
        return "Not Configured"
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"


def get_config_summary() -> dict[str, str]:
    """Return a safe summary dictionary for UI and diagnostics without secret leakage."""
    return {
        "model": get_model_name(),
        "api_configured": "Yes" if is_api_configured() else "No (Offline / Learning Mode)",
        "key_preview": get_masked_api_key(),
    }
