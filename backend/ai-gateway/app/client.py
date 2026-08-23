"""
AI Gateway client.

Features:
- Live Google Colab Gemma GPU API URL integration
- Google Gemma 4 integration
- Optional OpenAI fallback
- Safe mock mode for local/CI testing
- Environment-based configuration
- Token usage metadata
- Basic error handling
"""

import os
import json
import urllib.request
from typing import Any, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
COLAB_GEMMA_URL = os.getenv("COLAB_GEMMA_URL", "").strip()

GOOGLE_MODEL = "gemma-4-31b-it"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o").strip()

if OPENAI_API_KEY == "sk-put-your-key-here":
    OPENAI_API_KEY = ""

USE_COLAB_GEMMA = bool(COLAB_GEMMA_URL)
USE_GEMMA_GOOGLE = bool(GOOGLE_API_KEY)
USE_OPENAI = bool(OPENAI_API_KEY)


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
) -> Dict[str, Any]:
    """Build a normalized gateway result."""
    return {
        "answer": answer,
        "model": model,
        "usage": usage,
    }


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
    Send a question through the AI Gateway.

    Priority (current team decision - Google API is the active hosting
    method for now, since Colab's 90min session timeout makes it
    unreliable for ongoing testing. Colab is kept as a secondary option
    so it still works for anyone actively running a live notebook, but
    Google API is tried first so behavior is consistent across
    everyone's machines regardless of their local .env):
    1. Google Gemma Cloud API
    2. Colab Gemma T4 GPU API
    3. OpenAI API
    4. Mock response
    """
    if not isinstance(question, str):
        raise TypeError("question must be a string")

    question = question.strip()
    if not question:
        raise ValueError("question cannot be empty")

    if USE_GEMMA_GOOGLE:
        try:
            print(f"[GEMMA GOOGLE MODE] model={GOOGLE_MODEL} question received")
            return _ask_gemma(question)
        except Exception as exc:
            print(f"[GEMMA GOOGLE ERROR] {exc}")
            if not USE_OPENAI and not USE_COLAB_GEMMA:
                raise RuntimeError(f"Google Gemma request failed: {exc}") from exc

    if USE_COLAB_GEMMA:
        try:
            print(f"[COLAB GEMMA GPU MODE] question received: {question}")
            return _ask_colab_gemma(question)
        except Exception as exc:
            print(f"[COLAB GEMMA ERROR] {exc}")

    if USE_OPENAI:
        try:
            print(f"[OPENAI MODE] model={OPENAI_MODEL} question received")
            return _ask_openai(question)
        except Exception as exc:
            print(f"[OPENAI ERROR] {exc}")
            raise RuntimeError(f"OpenAI request failed: {exc}") from exc

    print("[MOCK MODE] question received")
    return _build_result(
        answer=(
            f"[MOCK RESPONSE] Simulated answer to: '{question}'. "
            "Configure GOOGLE_API_KEY, COLAB_GEMMA_URL, or OPENAI_API_KEY in .env "
            "to use a real AI model."
        ),
        model="mock",
        usage={
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    )
