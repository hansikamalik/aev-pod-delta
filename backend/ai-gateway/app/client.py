"""
AI Gateway client with structured fallback logging and rate-spike alerting.

Features:
- Primary: Google Gemma Cloud API
- Secondary: Live Google Colab Gemma GPU API URL integration
- Safety Fallback: Safe mock mode for local/CI testing with clear metadata
- Structured Fallback Logging (JSON/Standard logger)
- Fallback Spike Alerting (sliding window rate monitor)
- Token usage metadata & error handling
"""

import os
import json
import time
import logging
import urllib.request
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

# Setup structured logger for AI Gateway fallbacks
logger = logging.getLogger("ai_gateway.fallback")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
        '"logger": "%(name)s", "message": "%(message)s"}'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
COLAB_GEMMA_URL = os.getenv("COLAB_GEMMA_URL", "").strip()
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemma-4-31b-it").strip()

USE_COLAB_GEMMA = bool(COLAB_GEMMA_URL)
USE_GEMMA_GOOGLE = bool(GOOGLE_API_KEY)


class FallbackMonitor:
    """Tracks fallback events and triggers alerts on rate spikes."""

    def __init__(self, spike_threshold: int = 3, window_seconds: int = 60):
        self.spike_threshold = spike_threshold
        self.window_seconds = window_seconds
        self.fallback_timestamps: List[float] = []

    def record_fallback(self, from_provider: str, to_provider: str, reason: str):
        """Record a fallback event, log structured info, and check for spikes."""
        now = time.time()
        self.fallback_timestamps.append(now)

        # Prune timestamps older than window_seconds
        self.fallback_timestamps = [
            ts for ts in self.fallback_timestamps
            if now - ts <= self.window_seconds
        ]

        logger.warning(
            f"Fallback triggered: from={from_provider} to={to_provider} "
            f"reason='{reason}' count_in_window={len(self.fallback_timestamps)}"
        )

        # Check if fallback rate exceeds spike threshold
        if len(self.fallback_timestamps) >= self.spike_threshold:
            logger.critical(
                f"[ALERT] Fallback rate spike detected! "
                f"{len(self.fallback_timestamps)} fallbacks in the last "
                f"{self.window_seconds}s (Threshold: {self.spike_threshold})."
            )
            return True
        return False


# Global fallback monitor instance
fallback_monitor = FallbackMonitor(spike_threshold=3, window_seconds=60)


def _extract_usage(response: Any) -> Dict[str, int]:
    """Extract token usage from a model response."""
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        usage = getattr(response, "usage", None)

    if usage is None:
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    prompt_tokens = getattr(
        usage,
        "prompt_token_count",
        getattr(usage, "prompt_tokens", 0),
    )
    completion_tokens = getattr(
        usage,
        "candidates_token_count",
        getattr(usage, "completion_tokens", 0),
    )
    total_tokens = getattr(
        usage,
        "total_token_count",
        getattr(usage, "total_tokens", 0),
    )

    return {
        "prompt_tokens": int(prompt_tokens or 0),
        "completion_tokens": int(completion_tokens or 0),
        "total_tokens": int(total_tokens or 0),
    }


def _build_result(
    answer: str,
    model: str,
    usage: Dict[str, int],
    fallback: bool = False,
    fallback_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a normalized gateway result with explicit fallback indicators."""
    result: Dict[str, Any] = {
        "answer": answer,
        "model": model,
        "usage": usage,
        "fallback": fallback,
    }
    if fallback:
        result["fallback_reason"] = fallback_reason
    return result


def _ask_colab_gemma(question: str) -> Dict[str, Any]:
    """Send a question to Google Colab Gemma GPU API."""
    url = COLAB_GEMMA_URL.rstrip("/") + "/generate"
    payload = json.dumps({"prompt": question}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Bypass-Tunnel-Reminder": "true",
            "User-Agent": "Mozilla/5.0"
        }
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        data = json.loads(res.read().decode("utf-8"))
        ans = data.get("response", "").strip()
        return _build_result(
            answer=ans,
            model="gemma-colab-gpu",
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        )


def _ask_gemma(question: str) -> Dict[str, Any]:
    """Send a question to Google's Gemma model."""
    from google import genai

    client = genai.Client(api_key=GOOGLE_API_KEY)
    response = client.models.generate_content(
        model=GOOGLE_MODEL,
        contents=question,
    )

    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Google Gemma returned an empty response.")

    usage = _extract_usage(response)
    return _build_result(
        answer=text.strip(),
        model=GOOGLE_MODEL,
        usage=usage,
    )


def ask_gpt(question: str) -> Dict[str, Any]:
    """
    Send a question through the AI Gateway with structured fallback hierarchy:
    1. Google Gemma Cloud API (Primary)
    2. Colab Gemma T4 GPU API (Secondary)
    3. Mock response (Safety Fallback with explicit warning metadata)
    """
    if not isinstance(question, str):
        raise TypeError("question must be a string")

    question = question.strip()
    if not question:
        raise ValueError("question cannot be empty")

    fallback_reason: Optional[str] = None

    # --- 1. Primary: Google Cloud Gemma ---
    if USE_GEMMA_GOOGLE:
        try:
            return _ask_gemma(question)
        except Exception as exc:
            fallback_reason = f"Google Gemma failed: {exc}"
            fallback_monitor.record_fallback(
                from_provider="google_gemma",
                to_provider="colab_gemma" if USE_COLAB_GEMMA else "mock",
                reason=str(exc)
            )

    # --- 2. Secondary: Google Colab T4 GPU Gemma ---
    if USE_COLAB_GEMMA:
        try:
            res = _ask_colab_gemma(question)
            if fallback_reason:
                res["fallback"] = True
                res["fallback_reason"] = fallback_reason
            return res
        except Exception as exc:
            colab_error = f"Colab Gemma failed: {exc}"
            if fallback_reason:
                fallback_reason = f"{fallback_reason} | {colab_error}"
            else:
                fallback_reason = colab_error
            fallback_monitor.record_fallback(
                from_provider="colab_gemma",
                to_provider="mock",
                reason=str(exc)
            )

    # --- 3. Safety Fallback: Mock Response with warning metadata ---
    return _build_result(
        answer=(
            f"[MOCK RESPONSE] Simulated answer to: '{question}'. "
            "Configure GOOGLE_API_KEY or COLAB_GEMMA_URL in .env "
            "to use a real AI model."
        ),
        model="mock",
        usage={
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
        fallback=bool(fallback_reason),
        fallback_reason=fallback_reason or "No active LLM credentials configured",
    )
