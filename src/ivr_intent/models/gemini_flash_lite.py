"""Google Gemini 3.1 Flash-Lite IVR intent router (google-genai, structured JSON, implicit/explicit caching)."""
from __future__ import annotations

import ssl

import truststore
from google import genai
from google.genai import types

from jev_fraud.audit import callsite

from ..prompts import PROMPTS, prompt_ref
from ._base import IntentVerdict, Raw, Router, clean_label


class GeminiFlashLiteRouter(Router):
    provider = "google"
    model = "gemini-3.1-flash-lite"
    PRICING = (0.25, 1.50)            # $/MTok (input, output), ai.google.dev pricing 2026-10-16; thinking bills as output

    def __init__(self, variant: str = "v1", workers: int = 8, system_prompt: str | None = None, cache_mode: str = "implicit"):
        self.variant, self.workers, self.cache_mode = variant, workers, cache_mode
        super().__init__()
        self.in_price, self.out_price = self.PRICING
        # OS trust store so TLS-inspecting antivirus roots are honoured; verification stays on.
        ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.client = genai.Client(http_options=types.HttpOptions(
            client_args={"verify": ctx}, async_client_args={"verify": ctx},
            retry_options=types.HttpRetryOptions(attempts=5, initial_delay=2.0, max_delay=30.0, http_status_codes=[429, 503])))
        text = self._tag(system_prompt or PROMPTS[variant])
        self.system_ref = prompt_ref(text) if system_prompt else text
        cached_name, self.cache_name = None, None
        if cache_mode == "explicit":   # explicit context cache holding the system prompt (one-off creation + storage cost)
            try:
                cached = self.client.caches.create(model=self.model, config=types.CreateCachedContentConfig(
                    system_instruction=text, ttl="3600s"))
                cached_name = self.cache_name = cached.name
                n = getattr(cached.usage_metadata, "total_token_count", 0) or 0
                self.setup_cost_usd = n * self.in_price / 1e6    # creation = one full read of the prompt; hourly storage not included
            except Exception as e:
                self.cache_mode = "explicit_failed"
                self.name = f"{self.model}_{self.cache_mode}_{self.variant}"
                print(f"  [gemini] explicit cache not created ({type(e).__name__}: {str(e)[:120]}); falling back to implicit")
        cfg = dict(response_mime_type="application/json", response_schema=IntentVerdict, max_output_tokens=1000,
                   thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL))
        cfg["cached_content" if cached_name else "system_instruction"] = cached_name or text
        self.config = types.GenerateContentConfig(**cfg)

    def close(self) -> None:
        if self.cache_name:
            try:
                self.client.caches.delete(name=self.cache_name)
            except Exception as e:
                print(f"  [gemini] could not delete cache {self.cache_name}: {type(e).__name__}")
            self.cache_name = None

    def _invoke(self, xml: str) -> Raw:
        request = {"model": self.model, "system_instruction": self.system_ref, "cache_mode": self.cache_mode, "contents": xml,
                   "response_schema": "IntentVerdict(intent, confidence, reason)", "max_output_tokens": 1000,
                   "thinking_level": "MINIMAL"}
        source = callsite(genai.models.Models.generate_content)
        r = self.client.models.generate_content(model=self.model, contents=xml, config=self.config)
        v, u = r.parsed, r.usage_metadata
        cached = u.cached_content_token_count or 0
        fresh = (u.prompt_token_count or 0) - cached
        out = (getattr(u, "response_token_count", None) or getattr(u, "candidates_token_count", 0) or 0) + (u.thoughts_token_count or 0)
        cost = (fresh * self.in_price + cached * self.in_price * 0.1 + out * self.out_price) / 1e6
        return Raw(intent=clean_label(v.intent), confidence=v.confidence, request=request, source=source,
                   response={"response_id": r.response_id, "model_version": r.model_version, "parsed_output": v.model_dump()},
                   input_tokens=fresh, output_tokens=out, cache_read_tokens=cached, cost_usd=cost, request_id=r.response_id,
                   extra_usage={"thinking_tokens": u.thoughts_token_count or 0})
