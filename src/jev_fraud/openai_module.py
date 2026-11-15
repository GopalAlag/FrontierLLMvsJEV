"""OpenAI classifier (Responses API, structured output). Separate module by design."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import openai
import pandas as pd

from .audit import AUDIT, callsite
from .data import to_text
from .llm_module import PROMPTS, FraudVerdict
from .metrics import Prediction

# $/MTok (input, cached input, output) from developers.openai.com/api/docs/pricing, 2026-10-16.
PRICING = {
    "gpt-6-luna": (0.10, 0.01, 0.50),
    "gpt-5.6-luna": (0.20, 0.02, 1.20),
    "gpt-5-nano": (0.05, 0.005, 0.40),
}


class OpenAIClassifier:
    def __init__(self, model: str = "gpt-6-luna", variant: str = "v1", workers: int = 8,
                 system_prompt: str | None = None):
        from .prompts import prompt_hash, prompt_ref
        self.model, self.variant, self.workers = model, variant, workers
        self.name = f"{model}_{variant}"
        self.in_price, self.cached_price, self.out_price = PRICING[model]
        self.client = openai.OpenAI()
        self.system_text = system_prompt or PROMPTS[variant]
        self.system_ref = prompt_ref(self.system_text) if system_prompt else self.system_text
        # Automatic prefix caching (>=1024 token prefix); a stable cache key improves routing to the same cache.
        self.cache_key = f"jev-fraud-{prompt_hash(self.system_text)}"

    def _one(self, text: str, y_true: int) -> Prediction:
        user = f"Transaction:\n{text}"
        request = {"model": self.model, "instructions": self.system_ref, "prompt_cache_key": self.cache_key, "input": user,
                   "max_output_tokens": 1000, "text_format": "FraudVerdict(label, fraud_probability, reason)"}
        base = dict(provider="openai", system=self.name, model=self.model, request=request,
                    input_text=text, y_true=y_true)
        base["source"] = callsite(type(self.client.responses).parse)
        t0 = time.perf_counter()
        try:
            r = self.client.responses.parse(
                model=self.model, instructions=self.system_text, input=user, prompt_cache_key=self.cache_key,
                max_output_tokens=1000, text_format=FraudVerdict,
            )
            v = r.output_parsed
            p = min(1.0, max(0.0, float(v.fraud_probability)))
        except Exception as e:
            dt = time.perf_counter() - t0
            AUDIT.record(**base, latency_s=dt, error=f"{type(e).__name__}: {e}", cost_usd=0.0)
            return Prediction(prob=0.0, latency_s=dt, error=f"{type(e).__name__}: {e}")
        dt = time.perf_counter() - t0
        u = r.usage
        cached = getattr(u.input_tokens_details, "cached_tokens", 0) or 0
        fresh = u.input_tokens - cached
        cost = (fresh * self.in_price + cached * self.cached_price + u.output_tokens * self.out_price) / 1e6
        AUDIT.record(
            **base, latency_s=dt, request_id=getattr(r, "_request_id", None) or r.id,
            response={"id": r.id, "model": r.model, "status": r.status,
                      "output_text": r.output_text, "parsed_output": v.model_dump()},
            result_prob=p, cost_usd=cost,
            usage={"input_tokens": fresh, "output_tokens": u.output_tokens, "cache_read_input_tokens": cached,
                   "reasoning_tokens": getattr(u.output_tokens_details, "reasoning_tokens", 0)},
        )
        return Prediction(prob=p, latency_s=dt, input_tokens=fresh, output_tokens=u.output_tokens,
                          cache_read_tokens=cached, cost_usd=cost)

    def predict(self, df: pd.DataFrame) -> list[Prediction]:
        texts = [to_text(r) for r in df.itertuples(index=False)]
        ys = df["is_fraud"].tolist()
        first = [self._one(texts[0], ys[0])]  # warm the prefix cache before going parallel
        with ThreadPoolExecutor(self.workers) as ex:
            return first + list(ex.map(self._one, texts[1:], ys[1:]))
