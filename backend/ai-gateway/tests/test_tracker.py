import pytest

from app.token_tracker import TokenTracker
from app.cost_tracker import CostTracker


def test_token_tracker_without_usage():
    result = TokenTracker.extract_usage(object())

    assert result == {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }


def test_token_tracker_with_usage():
    class MockUsage:
        prompt_token_count = 100
        candidates_token_count = 50
        total_token_count = 150

    class MockResponse:
        usage_metadata = MockUsage()

    result = TokenTracker.extract_usage(MockResponse())

    assert result == {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150,
    }


def test_cost_tracker_known_model():
    result = CostTracker.calculate_cost(
        model="gemma-4-26b-a4b-it",
        prompt_tokens=1000,
        completion_tokens=500,
    )

    assert result["model"] == "gemma-4-26b-a4b-it"
    assert result["input_cost"] == 0.0
    assert result["output_cost"] == 0.0
    assert result["estimated_cost"] == 0.0


def test_cost_tracker_unknown_model():
    result = CostTracker.calculate_cost(
        model="unknown-model",
        prompt_tokens=1000,
        completion_tokens=500,
    )

    assert result["estimated_cost"] == 0.0


def test_cost_tracker_zero_tokens():
    result = CostTracker.calculate_cost(
        model="gemma-4-26b-a4b-it",
        prompt_tokens=0,
        completion_tokens=0,
    )

    assert result["input_cost"] == 0.0
    assert result["output_cost"] == 0.0
    assert result["estimated_cost"] == 0.0


def test_cost_tracker_negative_prompt_tokens_rejected():
    with pytest.raises(ValueError, match="prompt_tokens"):
        CostTracker.calculate_cost(
            model="gemma-4-26b-a4b-it",
            prompt_tokens=-1,
            completion_tokens=100,
        )


def test_cost_tracker_negative_completion_tokens_rejected():
    with pytest.raises(ValueError, match="completion_tokens"):
        CostTracker.calculate_cost(
            model="gemma-4-26b-a4b-it",
            prompt_tokens=100,
            completion_tokens=-1,
        )


def test_cost_tracker_invalid_token_type_rejected():
    with pytest.raises(TypeError, match="prompt_tokens"):
        CostTracker.calculate_cost(
            model="gemma-4-26b-a4b-it",
            prompt_tokens=100.5,
            completion_tokens=100,
        )


def test_cost_tracker_empty_model_rejected():
    with pytest.raises(ValueError, match="model"):
        CostTracker.calculate_cost(
            model="",
            prompt_tokens=100,
            completion_tokens=100,
        )


def test_cost_tracker_negative_budget_cap_rejected():
    with pytest.raises(ValueError, match="budget_cap"):
        CostTracker.calculate_cost(
            model="gemma-4-26b-a4b-it",
            prompt_tokens=100,
            completion_tokens=100,
            budget_cap=-1,
        )


def test_cost_tracker_budget_cap_not_exceeded():
    original_pricing = CostTracker.MODEL_PRICING[
        "gemma-4-26b-a4b-it"
    ].copy()

    try:
        CostTracker.MODEL_PRICING["gemma-4-26b-a4b-it"] = {
            "input": 1.0,
            "output": 2.0,
        }

        result = CostTracker.calculate_cost(
            model="gemma-4-26b-a4b-it",
            prompt_tokens=1000,
            completion_tokens=500,
            budget_cap=3.0,
        )

        assert result["estimated_cost"] == 2.0
        assert result["budget_cap"] == 3.0
        assert result["budget_exceeded"] is False

    finally:
        CostTracker.MODEL_PRICING[
            "gemma-4-26b-a4b-it"
        ] = original_pricing


def test_cost_tracker_budget_cap_exact_limit():
    original_pricing = CostTracker.MODEL_PRICING[
        "gemma-4-26b-a4b-it"
    ].copy()

    try:
        CostTracker.MODEL_PRICING["gemma-4-26b-a4b-it"] = {
            "input": 1.0,
            "output": 2.0,
        }

        result = CostTracker.calculate_cost(
            model="gemma-4-26b-a4b-it",
            prompt_tokens=1000,
            completion_tokens=500,
            budget_cap=2.0,
        )

        assert result["estimated_cost"] == 2.0
        assert result["budget_exceeded"] is False

    finally:
        CostTracker.MODEL_PRICING[
            "gemma-4-26b-a4b-it"
        ] = original_pricing


def test_cost_tracker_budget_cap_exceeded():
    original_pricing = CostTracker.MODEL_PRICING[
        "gemma-4-26b-a4b-it"
    ].copy()

    try:
        CostTracker.MODEL_PRICING["gemma-4-26b-a4b-it"] = {
            "input": 1.0,
            "output": 2.0,
        }

        result = CostTracker.calculate_cost(
            model="gemma-4-26b-a4b-it",
            prompt_tokens=2000,
            completion_tokens=1000,
            budget_cap=3.0,
        )

        assert result["estimated_cost"] == 4.0
        assert result["budget_cap"] == 3.0
        assert result["budget_exceeded"] is True

    finally:
        CostTracker.MODEL_PRICING[
            "gemma-4-26b-a4b-it"
        ] = original_pricing


def test_cost_tracker_unknown_model_with_budget_cap():
    result = CostTracker.calculate_cost(
        model="unknown-model",
        prompt_tokens=1000,
        completion_tokens=500,
        budget_cap=0.0,
    )

    assert result["estimated_cost"] == 0.0
    assert result["budget_cap"] == 0.0
    assert result["budget_exceeded"] is False


def test_cost_tracker_boolean_tokens_rejected():
    with pytest.raises(TypeError, match="prompt_tokens"):
        CostTracker.calculate_cost(
            model="gemma-4-26b-a4b-it",
            prompt_tokens=True,
            completion_tokens=100,
        )
