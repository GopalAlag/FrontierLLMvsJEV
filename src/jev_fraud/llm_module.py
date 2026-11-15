"""Claude LLM classifier. Separate module from the JEV path by design."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import anthropic
import pandas as pd
from pydantic import BaseModel, Field

from .audit import AUDIT, callsite
from .data import to_text
from .metrics import Prediction

# $/MTok (input, output) from the Anthropic price list. Cache reads 0.1x, 5-min cache writes 1.25x.
PRICING = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
}
# Haiku 5.5 may disable thinking at effort <= high; Sonnet 5.5 rejects "disabled".
THINKING = {
    "claude-haiku-5-5": {"type": "disabled"},
    "claude-sonnet-5-5": {"type": "between_tools"},
}


class FraudVerdict(BaseModel):
    label: str = Field(description="'fraud' or 'legit'")
    fraud_probability: float = Field(description="Calibrated probability in [0,1] that the transaction is fraud")
    reason: str = Field(description="One short sentence")


_BASE = (
    "You are a credit card fraud analyst. For each transaction, return a label ('fraud' or "
    "'legit'), a calibrated fraud probability between 0 and 1, and a one-sentence reason. "
    "Output only the structured verdict."
)

_GUIDE = """
Domain guidance (apply to every transaction):
- Real-world fraud is rare (well under 1% of traffic). Default to low probabilities (<0.05)
  for ordinary purchases; reserve probabilities above 0.5 for transactions with several
  strong signals.
- Strong signals: online categories (shopping_net, misc_net) and point-of-sale grocery/gas
  with large amounts; late-night hours (22:00-03:00); amounts far above typical for the
  category (e.g. shopping_net over $500, grocery_pos over $300, gas_transport over $100);
  very large home-to-merchant distance for in-person categories.
- Weak/neutral signals: gender, age, job, state, city population. Do not infer fraud from
  demographics alone.
- Typical legitimate patterns: small recurring purchases (food_dining, entertainment,
  health_fitness, kids_pets, home, personal_care) during daytime/evening hours.
- Calibrate: if unsure, output a probability near 0.1-0.3 rather than 0 or 1.
"""

PROMPTS = {
    "v1": _BASE,
    "v2": _BASE + _GUIDE,
}


class ClaudeClassifier:
    def __init__(self, model: str = "claude-haiku-5-5", variant: str = "v1", workers: int = 8,
                 system_prompt: str | None = None):
        from .prompts import prompt_ref
        self.model, self.variant, self.workers = model, variant, workers
        self.name = f"{model}_{variant}"
        self.in_price, self.out_price = PRICING[model]
        self.client = anthropic.Anthropic()
        text = system_prompt or PROMPTS[variant]
        self.system_ref = prompt_ref(text) if system_prompt else text
        # Shared, frozen system prompt marked cacheable. Prefixes below the model's minimum
        # cacheable length silently skip caching; cache_read_tokens in the results shows if it hit.
        self.system = [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]

    def _one(self, text: str, y_true: int) -> Prediction:
        request = {
            "model": self.model, "max_tokens": 300, "thinking": THINKING[self.model],
            "system": self.system_ref, "system_cache_control": "ephemeral",
            "messages": [{"role": "user", "content": f"Transaction:\n{text}"}],
            "output_format": "FraudVerdict(label, fraud_probability, reason)",
        }
        base = dict(provider="anthropic", system=self.name, model=self.model, request=request, input_text=text, y_true=y_true)
        base["source"] = callsite(anthropic.resources.messages.Messages.parse)
        t0 = time.perf_counter()
        try:
            r = self.client.messages.parse(
                model=self.model,
                max_tokens=300,
                system=self.system,
                thinking=THINKING[self.model],
                messages=[{"role": "user", "content": f"Transaction:\n{text}"}],
                output_format=FraudVerdict,
            )
            v = r.parsed_output
            p = min(1.0, max(0.0, float(v.fraud_probability)))
        except Exception as e:
            dt = time.perf_counter() - t0
            AUDIT.record(**base, latency_s=dt, error=f"{type(e).__name__}: {e}", cost_usd=0.0)
            return Prediction(prob=0.0, latency_s=dt, error=f"{type(e).__name__}: {e}")
        dt = time.perf_counter() - t0
        u = r.usage
        cr = getattr(u, "cache_read_input_tokens", 0) or 0
        cw = getattr(u, "cache_creation_input_tokens", 0) or 0
        cost = (
            u.input_tokens * self.in_price
            + cr * self.in_price * 0.1
            + cw * self.in_price * 1.25
            + u.output_tokens * self.out_price
        ) / 1e6
        AUDIT.record(
            **base, latency_s=dt, request_id=getattr(r, "_request_id", None),
            response={"id": r.id, "model": r.model, "stop_reason": r.stop_reason,
                      "content": [b.model_dump(mode="json") for b in r.content],
                      "parsed_output": v.model_dump()},
            result_prob=p, cost_usd=cost,
            usage={"input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                   "cache_read_input_tokens": cr, "cache_creation_input_tokens": cw},
        )
        return Prediction(
            prob=p, latency_s=dt, input_tokens=u.input_tokens, output_tokens=u.output_tokens,
            cache_read_tokens=cr, cache_write_tokens=cw, cost_usd=cost,
        )

    def predict(self, df: pd.DataFrame) -> list[Prediction]:
        texts = [to_text(r) for r in df.itertuples(index=False)]
        # Warm the cache with one call so parallel workers read instead of each writing.
        ys = df["is_fraud"].tolist()
        first = [self._one(texts[0], ys[0])]
        with ThreadPoolExecutor(self.workers) as ex:
            return first + list(ex.map(self._one, texts[1:], ys[1:]))
