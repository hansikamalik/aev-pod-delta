"""Comprehensive tests for client.py fallback paths and error scenarios."""

import json
from unittest.mock import MagicMock, patch
import pytest

import app.client as client
from app.client import (
    ask_gpt,
    _extract_usage,
    _ask_colab_gemma,
    _ask_gemma,
)


def test_ask_gpt_type_and_value_errors():
    with pytest.raises(TypeError, match="question must be a string"):
        ask_gpt(123)  # type: ignore

    with pytest.raises(ValueError, match="question cannot be empty"):
        ask_gpt("   ")


def test_extract_usage_variations():
    # None response
    assert _extract_usage(None) == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    # usage attribute dict or obj
    class UsageObj:
        prompt_tokens = 15
        completion_tokens = 25
        total_tokens = 40

    class RespObj:
        usage = UsageObj()

    res = _extract_usage(RespObj())
    assert res == {"prompt_tokens": 15, "completion_tokens": 25, "total_tokens": 40}

    # usage_metadata attribute
    class UsageMeta:
        prompt_token_count = 50
        candidates_token_count = 30
        total_token_count = 80

    class RespMeta:
        usage_metadata = UsageMeta()

    res2 = _extract_usage(RespMeta())
    assert res2 == {"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80}


def test_ask_gemma_success():
    mock_genai = MagicMock()
    mock_model_resp = MagicMock()
    mock_model_resp.text = "Gemma cloud response"
    mock_model_resp.usage_metadata.prompt_token_count = 10
    mock_model_resp.usage_metadata.candidates_token_count = 20
    mock_model_resp.usage_metadata.total_token_count = 30

    mock_genai.Client.return_value.models.generate_content.return_value = mock_model_resp

    with patch.dict("sys.modules", {"google.genai": mock_genai}):
        result = _ask_gemma("Hello Gemma")
        assert result["answer"] == "Gemma cloud response"
        assert result["model"] == client.GOOGLE_MODEL
        assert result["usage"]["total_tokens"] == 30


def test_ask_gemma_empty_response_raises():
    mock_genai = MagicMock()
    mock_model_resp = MagicMock()
    mock_model_resp.text = None

    mock_genai.Client.return_value.models.generate_content.return_value = mock_model_resp

    with patch.dict("sys.modules", {"google.genai": mock_genai}):
        with pytest.raises(RuntimeError, match="Google Gemma returned an empty response"):
            _ask_gemma("Hello Gemma")


def test_ask_colab_gemma_success():
    fake_body = json.dumps({"response": "Colab GPU response"}).encode("utf-8")
    mock_res = MagicMock()
    mock_res.read.return_value = fake_body
    mock_res.__enter__.return_value = mock_res

    with patch.object(client, "COLAB_GEMMA_URL", "https://colab-tunnel.example.com"), \
         patch("urllib.request.urlopen", return_value=mock_res):
        result = _ask_colab_gemma("Test colab")
        assert result["answer"] == "Colab GPU response"
        assert result["model"] == "gemma-colab-gpu"


def test_ask_gpt_colab_fallback_path():
    """Google Gemma fails, cascades to Colab Gemma and succeeds with fallback metadata."""
    with patch.object(client, "USE_GEMMA_GOOGLE", True), \
         patch.object(client, "USE_COLAB_GEMMA", True), \
         patch.object(client, "_ask_gemma", side_effect=RuntimeError("Google quota exceeded")), \
         patch.object(client, "_ask_colab_gemma", return_value={
             "answer": "Answer from Colab",
             "model": "gemma-colab-gpu",
             "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
             "fallback": False,
         }):
        res = ask_gpt("Explain firewall")
        assert res["model"] == "gemma-colab-gpu"
        assert res["fallback"] is True
        assert "Google quota exceeded" in res["fallback_reason"]


def test_ask_gpt_both_fail_to_mock():
    """Both Google and Colab fail, cascading to safety mock response."""
    with patch.object(client, "USE_GEMMA_GOOGLE", True), \
         patch.object(client, "USE_COLAB_GEMMA", True), \
         patch.object(client, "_ask_gemma", side_effect=RuntimeError("Google down")), \
         patch.object(client, "_ask_colab_gemma", side_effect=RuntimeError("Colab tunnel dead")):
        res = ask_gpt("Explain firewall")
        assert res["model"] == "mock"
        assert res["fallback"] is True
        assert "Google down" in res["fallback_reason"]
        assert "Colab tunnel dead" in res["fallback_reason"]
        assert "[MOCK RESPONSE]" in res["answer"]
