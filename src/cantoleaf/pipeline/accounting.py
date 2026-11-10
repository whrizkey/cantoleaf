import tomllib
from pathlib import Path

from cantoleaf.errors import BudgetExceededError


class UsageTracker:
    """
    Tracks character and token usage across TTS and LLM calls,
    loads rates from pricing.toml, and enforces CANTOLEAF_MAX_COST_USD.
    """

    def __init__(
        self,
        max_cost_usd: float = 5.0,
        pricing_path: Path | None = None,
        max_budget_usd: float | None = None,
    ) -> None:
        self.max_cost_usd = max_budget_usd if max_budget_usd is not None else max_cost_usd
        self.pricing_path = pricing_path or Path(__file__).parents[2] / "pricing.toml"
        self.rates = self._load_rates()
        self.cumulative_cost_usd = 0.0

    @property
    def total_cost_usd(self) -> float:
        return self.cumulative_cost_usd

    @property
    def max_budget_usd(self) -> float:
        return self.max_cost_usd

    def _load_rates(self) -> dict[str, float]:
        if not self.pricing_path.exists():
            return {"fake": 0.0, "edge": 0.0, "elevenlabs": 0.030, "openai_compat": 0.015}
        try:
            with open(self.pricing_path, "rb") as f:
                data = tomllib.load(f)
            tts_rates = data.get("tts", {})
            return {
                "fake": float(tts_rates.get("fake", 0.0)),
                "edge": float(tts_rates.get("edge", 0.0)),
                "elevenlabs": float(tts_rates.get("elevenlabs_standard", 0.030)),
                "openai_compat": float(tts_rates.get("openai_tts", 0.015)),
            }
        except Exception:
            return {"fake": 0.0, "edge": 0.0, "elevenlabs": 0.030, "openai_compat": 0.015}

    def record_tts_usage(self, provider_name: str, char_count: int) -> float:
        rate_per_1k = self.rates.get(provider_name.lower(), 0.0)
        cost = (char_count / 1000.0) * rate_per_1k
        if self.cumulative_cost_usd + cost > self.max_cost_usd:
            raise BudgetExceededError(
                f"Spending limit reached: ${self.cumulative_cost_usd + cost:.4f} > limit of ${self.max_cost_usd:.2f} USD."
            )
        self.cumulative_cost_usd += cost
        return cost
