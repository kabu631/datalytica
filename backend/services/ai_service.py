"""
ai_service.py — Anti-Hallucination AI Core.

Provides a single AIService class that:
  1. Reads provider config (deepseek / ollama) + API key from AppConfig.
  2. Prepends the ANTI_HALLUCINATION_SYSTEM_PROMPT to every call.
  3. Calls DeepSeek first; auto-falls back to Ollama on failure.
"""
import json
import logging
from typing import Optional

import requests
from sqlalchemy.orm import Session

from database import SessionLocal
from models import AppConfig

logger = logging.getLogger(__name__)

# ── Non-negotiable anti-hallucination prompt ──────────────────────────────────

ANTI_HALLUCINATION_SYSTEM_PROMPT = """
You are a data analyst assistant. You ONLY report facts derived from the
computed statistics provided to you. You NEVER infer, guess, extrapolate,
or add any fact that is not explicitly present in the data JSON provided.
If a value is not in the data, say 'not available' — never make it up.
Every claim you make must reference a specific column name or metric from
the provided data. Do not use phrases like 'likely', 'probably', 'seems to',
or 'suggests' unless directly supported by a statistical test result.
"""

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"


class AIService:
    """
    Unified AI completion service.

    Usage::

        ai = AIService()          # reads provider + keys from AppConfig
        text = ai.complete(
            system_prompt="You are a helpful assistant.",
            user_prompt="Summarise the dataset.",
        )
    """

    def __init__(self, db: Optional[Session] = None):
        self._own_session = db is None
        self._db: Session = db or SessionLocal()

        # Read settings from AppConfig (fall back to sensible defaults)
        self.provider: str         = self._cfg("AI_PROVIDER", "deepseek").lower()
        self.deepseek_api_key: str = self._cfg("DEEPSEEK_API_KEY", "")
        self.ollama_model: str     = self._cfg("OLLAMA_MODEL", "mistral")
        self.ollama_url: str       = self._cfg("OLLAMA_GENERATE_URL", OLLAMA_GENERATE_URL)

    # ── Public API ────────────────────────────────────────────────────────────

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """
        Send a completion request.

        The ANTI_HALLUCINATION_SYSTEM_PROMPT is **always** prepended to the
        system prompt — this is non-negotiable and cannot be overridden.

        If all providers fail, returns a human-readable error string instead
        of raising, so callers still get data back with an AI-unavailable note.
        """
        full_system = (
            ANTI_HALLUCINATION_SYSTEM_PROMPT.strip()
            + "\n\n"
            + system_prompt.strip()
        )
        try:
            if self.provider == "deepseek":
                return self._try_deepseek_then_ollama(full_system, user_prompt)
            else:
                return self._try_ollama(full_system, user_prompt)
        except Exception as exc:
            logger.error("AIService: all providers failed: %s", exc)
            return (
                "[AI Unavailable] Could not reach any AI provider. "
                "Go to Settings → AI Configuration and enter a DeepSeek API key "
                "or ensure Ollama is running locally. "
                f"Error detail: {exc}"
            )

    # ── DeepSeek ──────────────────────────────────────────────────────────────

    def _call_deepseek(self, system_prompt: str, user_prompt: str) -> str:
        """POST to DeepSeek chat completions endpoint."""
        if not self.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured in Settings.")

        headers = {
            "Authorization": f"Bearer {self.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "deepseek-chat",
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
        }

        resp = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()

        data = resp.json()
        return data["choices"][0]["message"]["content"]

    # ── Ollama ────────────────────────────────────────────────────────────────

    def _call_ollama(self, system_prompt: str, user_prompt: str) -> str:
        """POST to local Ollama /api/generate endpoint."""
        payload = {
            "model": self.ollama_model,
            "prompt": user_prompt,
            "system": system_prompt,
            "stream": False,
        }

        resp = requests.post(
            self.ollama_url,
            json=payload,
            timeout=300,
        )
        resp.raise_for_status()

        data = resp.json()
        return data.get("response", "")

    # ── Fallback logic ────────────────────────────────────────────────────────

    def _try_deepseek_then_ollama(self, system_prompt: str, user_prompt: str) -> str:
        """Call DeepSeek; if it fails for any reason, fall back to Ollama."""
        try:
            logger.info("AIService: attempting DeepSeek…")
            return self._call_deepseek(system_prompt, user_prompt)
        except Exception as exc:
            logger.warning(
                "AIService: DeepSeek failed (%s), falling back to Ollama (%s).",
                exc,
                self.ollama_model,
            )
            return self._call_ollama(system_prompt, user_prompt)

    def _try_ollama(self, system_prompt: str, user_prompt: str) -> str:
        """Call Ollama directly (no fallback)."""
        logger.info("AIService: calling Ollama (%s)…", self.ollama_model)
        return self._call_ollama(system_prompt, user_prompt)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _cfg(self, key: str, default: str = "") -> str:
        """Read a value from the AppConfig table, or return *default*."""
        try:
            row = self._db.query(AppConfig).filter(AppConfig.key == key).first()
            return row.value if row and row.value else default
        except Exception:
            return default

    def close(self) -> None:
        """Close the DB session if we created it ourselves."""
        if self._own_session:
            self._db.close()

    # Context-manager support
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
