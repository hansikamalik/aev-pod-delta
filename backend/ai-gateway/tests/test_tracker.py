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
    