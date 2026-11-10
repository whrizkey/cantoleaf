import tomllib
from pathlib import Path

from cantoleaf.errors import BudgetExceededError


def find_pricing_path(explicit_path: Path | None = None) -> Path:
    """Finds the pricing.toml configuration file across project root, working directory, and package directories."""
    if explicit_path and explicit_path.exists():
        return explicit_path
    candidates = [
        Path.cwd() / "pricing.toml",
        Path(__file__).resolve().parents[3] / "pricing.toml",
        Path(__file__).resolve().parents[2] / "pricing.toml",
        Path.home() / ".cantoleaf" / "pricing.toml",
    ]
    for c in candidates:
        if c.is_file() and c.exists():
            return c
    return candidates[0]


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
        self.pricing_path = find_pricing_path(pricing_path)
        self.tts_rates, self.llm_rates = self._load_rates()
        self.cumulative_cost_usd = 0.0

    @property
    def total_cost_usd(self) -> float:
        return self.cumulative_cost_usd

    @property
    def max_budget_usd(self) -> float:
        return self.max_cost_usd

    def _load_rates(self) -> tuple[dict[str, float], dict[str, tuple[float, float]]]:
        tts_defaults = {"fake": 0.0, "edge": 0.0, "elevenlabs": 0.030, "openai_compat": 0.015}
        llm_defaults = {"gpt-4o-mini": (0.00015, 0.00060), "claude-3-haiku": (0.00025, 0.00125)}

        if not self.pricing_path.exists():
            return tts_defaults, llm_defaults
        try:
            with open(self.pricing_path, "rb") as f:
                data = tomllib.load(f)
            raw_tts = data.get("tts", {})
            tts_rates = {
                "fake": float(raw_tts.get("fake", 0.0)),
                "edge": float(raw_tts.get("edge", 0.0)),
                "elevenlabs": float(raw_tts.get("elevenlabs_standard", 0.030)),
                "openai_compat": float(raw_tts.get("openai_tts", 0.015)),
            }
            raw_llm = data.get("llm", {})
            llm_rates = {}
            for model_name, rates in raw_llm.items():
                if isinstance(rates, dict):
                    prompt_rate = float(rates.get("prompt_per_1k_tokens", 0.00015))
                    completion_rate = float(rates.get("completion_per_1k_tokens", 0.00060))
                    llm_rates[model_name] = (prompt_rate, completion_rate)
            return tts_rates, (llm_rates or llm_defaults)
        except Exception:
            return tts_defaults, llm_defaults

    def record_tts_usage(
        self,
        provider_name: str,
        char_count: int,
        *,
        base_url: str = "",
    ) -> float:
        norm = provider_name.lower().strip()
        # Zero cost for local instances (Kokoro-FastAPI, LocalAI on localhost)
        if any(h in base_url for h in ("localhost", "127.0.0.1", "0.0.0.0")):
            return 0.0

        rate_per_1k = self.tts_rates.get(norm, 0.0)
        cost = (char_count / 1000.0) * rate_per_1k
        if self.max_cost_usd > 0.0 and (self.cumulative_cost_usd + cost > self.max_cost_usd):
            raise BudgetExceededError(
                f"Spending limit reached: ${self.cumulative_cost_usd + cost:.4f} > limit of ${self.max_cost_usd:.2f} USD."
            )
        self.cumulative_cost_usd += cost
        return cost

    def record_llm_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        *,
        base_url: str = "",
    ) -> float:
        if any(h in base_url for h in ("localhost", "127.0.0.1", "0.0.0.0")):
            return 0.0

        rates = self.llm_rates.get(model, (0.00015, 0.00060))
        cost = (prompt_tokens / 1000.0) * rates[0] + (completion_tokens / 1000.0) * rates[1]
        if self.max_cost_usd > 0.0 and (self.cumulative_cost_usd + cost > self.max_cost_usd):
            raise BudgetExceededError(
                f"Spending limit reached: ${self.cumulative_cost_usd + cost:.4f} > limit of ${self.max_cost_usd:.2f} USD."
            )
        self.cumulative_cost_usd += cost
        return cost
