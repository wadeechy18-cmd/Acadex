from app.ai.pricing import estimate_cost_cents


def test_estimate_cost_cents_known_model():
    # claude-opus-5: $5.00 / $25.00 per 1M tokens
    cents = estimate_cost_cents("claude-opus-5", input_tokens=1_000_000, output_tokens=1_000_000)
    assert cents == 3000  # $5 + $25 = $30 = 3000 cents


def test_estimate_cost_cents_zero_tokens():
    assert estimate_cost_cents("claude-opus-5", 0, 0) == 0


def test_estimate_cost_cents_unknown_model_falls_back_to_opus_pricing():
    cents_unknown = estimate_cost_cents("some-future-model", 1_000_000, 1_000_000)
    cents_opus = estimate_cost_cents("claude-opus-5", 1_000_000, 1_000_000)
    assert cents_unknown == cents_opus
