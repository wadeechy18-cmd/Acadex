"""Rough cost estimates for usage tracking (Section 18 of the brief). Not
billing-accurate -- Anthropic's own usage/cost reporting is the source of
truth for actual spend -- but enough for a teacher/school to see roughly
what a request cost without leaving the app.
"""

# (input $ / 1M tokens, output $ / 1M tokens)
_PRICING_PER_MILLION_USD: dict[str, tuple[float, float]] = {
    "claude-opus-5": (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
}

_DEFAULT_PRICING = _PRICING_PER_MILLION_USD["claude-opus-5"]


def estimate_cost_cents(model: str, input_tokens: int, output_tokens: int) -> int:
    input_price, output_price = _PRICING_PER_MILLION_USD.get(model, _DEFAULT_PRICING)
    dollars = (input_tokens / 1_000_000) * input_price + (output_tokens / 1_000_000) * output_price
    return round(dollars * 100)
