"""Anthropic Messages API router (structured output, cached system prompt). Subclassed once per Claude model."""
from __future__ import annotations

import anthropic

from jev_fraud.audit import callsite

from ..prompts import PROMPTS, prompt_ref
from ._base import IntentVerdict, Raw, Router, clean_label


class AnthropicRouter(Router):
    provider = "anthropic"
    warm_cache = True
    PRICING: tuple[float, float]       # $/MTok (input, output); cache reads 0.1x, 5-min cache writes 1.25x
    THINKING: dict

    def __init__(self, variant: str = "v1", workers: int = 8, system_prompt: str | None = None, cache_mode: str = "explicit"):
        self.variant, self.workers, self.cache_mode = variant, workers, cache_mode
        super().__init__()
        self.in_price, self.out_price = self.PRICING
        self.client = anthropic.Anthropic()
        text = self._tag(system_prompt or PROMPTS[variant])
        self.system_ref = prompt_ref(text) if system_prompt else text
        if cache_mode == "explicit":    # our own breakpoint at the end of the system prompt
            self.system, self.extra = [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}], {}
        else:                           # implicit: top-level automatic marker on the last cacheable block of the request
            self.system, self.extra = text, {"extra_body": {"cache_control": {"type": "ephemeral"}}}

    def _invoke(self, xml: str) -> Raw:
        request = {"model": self.model, "max_tokens": 300, "thinking": self.THINKING, "system": self.system_ref,
                   "cache_mode": self.cache_mode,
                   "cache_control": "block-level on system" if self.cache_mode == "explicit" else "top-level (automatic)", "messages": [{"role": "user", "content": xml}],
                   "output_format": "IntentVerdict(intent, confidence, reason)"}
        source = callsite(anthropic.resources.messages.Messages.parse)
        r = self.client.messages.parse(model=self.model, max_tokens=300, system=self.system, thinking=self.THINKING,
                                       messages=[{"role": "user", "content": xml}], output_format=IntentVerdict, **self.extra)
        v, u = r.parsed_output, r.usage
        cr = getattr(u, "cache_read_input_tokens", 0) or 0
        cw = getattr(u, "cache_creation_input_tokens", 0) or 0
        cost = (u.input_tokens * self.in_price + cr * self.in_price * 0.1 + cw * self.in_price * 1.25
                + u.output_tokens * self.out_price) / 1e6
        return Raw(intent=clean_label(v.intent), confidence=v.confidence, request=request, source=source,
                   response={"id": r.id, "model": r.model, "stop_reason": r.stop_reason, "parsed_output": v.model_dump()},
                   input_tokens=u.input_tokens, output_tokens=u.output_tokens, cache_read_tokens=cr, cache_write_tokens=cw,
                   cost_usd=cost, request_id=getattr(r, "_request_id", None))
