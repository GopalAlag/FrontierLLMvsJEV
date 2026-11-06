"""Google Gemini classifier (google-genai, structured JSON output). Separate module by design."""
from __future__ import annotations

import ssl
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import truststore
from google import genai
from google.genai import types

from .audit import AUDIT, callsite
from .data import to_text
from .llm_module import PROMPTS, FraudVerdict
from .metrics import Prediction

# $/MTok (input, output) from ai.google.dev/gemini-api/docs/pricing, 2026-10-16. Thinking tokens bill as output.
PRICING = {
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini-2.5-flash-lite": (0.10, 0.40),
}


class GeminiClassifier:
    def __init__(self, model: str = "gemini-3.1-flash-lite", variant: str = "v1", workers: int = 8,
                 system_prompt: str | None = None):
        from .prompts import prompt_ref
        self.model, self.variant, self.workers = model, variant, workers
        self.name = f"{model}_{variant}"
        self.in_price, self.out_price = PRICING[model]
        # Use the OS trust store: TLS-inspecting antivirus (e.g. Norton Web Shield) installs its root
        # there, and google-genai otherwise verifies against certifi only. Verification stays on.
        ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.client = genai.Client(  # reads GEMINI_API_KEY / GOOGLE_API_KEY
            http_options=types.HttpOptions(
                client_args={"verify": ctx}, async_client_args={"verify": ctx},
                retry_options=types.HttpRetryOptions(
                    attempts=5, initial_delay=2.0, max_delay=30.0, http_status_codes=[429, 503]),
            )
        )
        text = system_prompt or PROMPTS[variant]
        self.system_ref = prompt_ref(text) if system_prompt else text
        self.cache_mode = "implicit"
        cached_name = None
        if system_prompt:  # explicit context cache holding the long shared system prompt
            try:
                cached = self.client.caches.create(
                    model=model,
                    config=types.CreateCachedContentConfig(system_instruction=text, ttl="3600s"),
                )
                cached_name, self.cache_mode = cached.name, "explicit"
            except Exception as e:  # below the model's minimum cacheable size, or unsupported: fall back
                print(f"  [gemini] explicit cache not created ({type(e).__name__}: {str(e)[:120]}); using implicit")
        cfg = dict(
            response_mime_type="application/json",
            response_schema=FraudVerdict,
            max_output_tokens=1000,
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL),
        )
        if cached_name:
            cfg["cached_content"] = cached_name
        else:
            cfg["system_instruction"] = text
        self.config = types.GenerateContentConfig(**cfg)

    def _one(self, text: str, y_true: int) -> Prediction:
        user = f"Transaction:\n{text}"
        request = {"model": self.model, "system_instruction": self.system_ref, "cache_mode": self.cache_mode, "contents": user,
                   "response_schema": "FraudVerdict(label, fraud_probability, reason)",
                   "max_output_tokens": 1000, "thinking_level": "MINIMAL"}
        base = dict(provider="google", system=self.name, model=self.model, request=request,
                    input_text=text, y_true=y_true)
        base["source"] = callsite(genai.models.Models.generate_content)
        t0 = time.perf_counter()
        try:
            r = self.client.models.generate_content(model=self.model, contents=user, config=self.config)
            v = r.parsed
            p = min(1.0, max(0.0, float(v.fraud_probability)))
        except Exception as e:
            dt = time.perf_counter() - t0
            AUDIT.record(**base, latency_s=dt, error=f"{type(e).__name__}: {e}", cost_usd=0.0)
            return Prediction(prob=0.0, latency_s=dt, error=f"{type(e).__name__}: {e}")
        dt = time.perf_counter() - t0
        u = r.usage_metadata
        cached = u.cached_content_token_count or 0
        fresh = (u.prompt_token_count or 0) - cached
        out = (getattr(u, "response_token_count", None) or getattr(u, "candidates_token_count", 0) or 0) \
            + (u.thoughts_token_count or 0)
        cost = (fresh * self.in_price + cached * self.in_price * 0.1 + out * self.out_price) / 1e6
        AUDIT.record(
            **base, latency_s=dt, request_id=r.response_id,
            response={"response_id": r.response_id, "model_version": r.model_version,
                      "text": r.text, "parsed_output": v.model_dump()},
            result_prob=p, cost_usd=cost,
            usage={"input_tokens": fresh, "output_tokens": out, "cache_read_input_tokens": cached,
                   "thinking_tokens": u.thoughts_token_count or 0},
        )
        return Prediction(prob=p, latency_s=dt, input_tokens=fresh, output_tokens=out,
                          cache_read_tokens=cached, cost_usd=cost)

    def predict(self, df: pd.DataFrame) -> list[Prediction]:
        texts = [to_text(r) for r in df.itertuples(index=False)]
        ys = df["is_fraud"].tolist()
        with ThreadPoolExecutor(self.workers) as ex:
            return list(ex.map(self._one, texts, ys))
