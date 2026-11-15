"""OpenAI GPT-6 Luna IVR intent router (Responses API, structured output, automatic prefix caching)."""
from __future__ import annotations

import openai

from jev_fraud.audit import callsite

from ..prompts import PROMPTS, prompt_hash, prompt_ref
from ._base import IntentVerdict, Raw, Router, clean_label


class OpenAILunaRouter(Router):
    provider = "openai"
    model = "gpt-6-luna"
    warm_cache = True
    PRICING = (0.10, 0.01, 0.50)      # $/MTok (input, cached input, output), developers.openai.com pricing 2026-10-16

    def __init__(self, variant: str = "v1", workers: int = 8, system_prompt: str | None = None, cache_mode: str = "implicit"):
        self.variant, self.workers, self.cache_mode = variant, workers, cache_mode
        super().__init__()
        self.in_price, self.cached_price, self.out_price = self.PRICING
        self.client = openai.OpenAI()
        self.system_text = self._tag(system_prompt or PROMPTS[variant])
        self.system_ref = prompt_ref(self.system_text) if system_prompt else self.system_text
        self.cache_key = f"jev-ivr-{prompt_hash(self.system_text)}"

    def _invoke(self, xml: str) -> Raw:
        if self.cache_mode == "explicit":
            # explicit: the system prompt is an input block that ends in a cache breakpoint; the implicit breakpoint is disabled
            wire = dict(input=[{"role": "developer", "content": [{"type": "input_text", "text": self.system_text,
                                                                  "prompt_cache_breakpoint": {"mode": "explicit"}}]},
                               {"role": "user", "content": xml}],
                        prompt_cache_options={"mode": "explicit"})
            shown = dict(input=[{"role": "developer", "content": self.system_ref + " [prompt_cache_breakpoint: explicit]"},
                                {"role": "user", "content": xml}], prompt_cache_options={"mode": "explicit"})
        else:   # implicit: automatic prefix caching; a stable key improves routing to the same cache
            wire = dict(instructions=self.system_text, input=xml)
            shown = dict(instructions=self.system_ref, input=xml, prompt_cache_options={"mode": "implicit (default)"})
        request = {"model": self.model, "prompt_cache_key": self.cache_key, "max_output_tokens": 1000,
                   "text_format": "IntentVerdict(intent, confidence, reason)", "cache_mode": self.cache_mode, **shown}
        source = callsite(type(self.client.responses).parse)
        r = self.client.responses.parse(model=self.model, prompt_cache_key=self.cache_key, max_output_tokens=1000,
                                        text_format=IntentVerdict, **wire)
        v, u = r.output_parsed, r.usage
        cached = getattr(u.input_tokens_details, "cached_tokens", 0) or 0
        written = getattr(u.input_tokens_details, "cache_write_tokens", 0) or 0
        fresh = u.input_tokens - cached
        cost = (fresh * self.in_price + cached * self.cached_price + u.output_tokens * self.out_price) / 1e6
        return Raw(intent=clean_label(v.intent), confidence=v.confidence, request=request, source=source,
                   response={"id": r.id, "model": r.model, "status": r.status, "parsed_output": v.model_dump()},
                   input_tokens=fresh, output_tokens=u.output_tokens, cache_read_tokens=cached, cache_write_tokens=written,
                   cost_usd=cost, request_id=getattr(r, "_request_id", None) or r.id,
                   extra_usage={"reasoning_tokens": getattr(u.output_tokens_details, "reasoning_tokens", 0)})
