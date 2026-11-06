"""Shared plumbing for all routers: timing, error capture, audit record, parallel predict.

Each LLM lives in its own module and only implements `_invoke` (the provider call + cost maths).
"""
from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import pandas as pd
from pydantic import BaseModel, Field

from jev_fraud.audit import AUDIT

from ..intents import CANON, NAMES
from ..metrics import Prediction


class IntentVerdict(BaseModel):
    intent: str = Field(description="Exactly one of: " + ", ".join(NAMES))
    confidence: float = Field(description="Calibrated probability in [0,1] that this is the caller's true intent")
    reason: str = Field(description="One short sentence")


@dataclass
class Raw:
    """What a provider call returned, normalised."""
    intent: str
    confidence: float
    request: dict
    response: dict
    source: dict
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0
    request_id: str | None = None
    extra_usage: dict = field(default_factory=dict)


def clean_label(s: str) -> str:
    """Map a model's label to the canonical CamelCase intent name; unknown labels stay as-is (scored invalid)."""
    key = (s or "").strip().strip("\"'`").replace(" ", "").replace("_", "").replace("-", "").lower()
    return CANON.get(key, (s or "").strip())


class Budget:
    """Global spend guard: once measured spend reaches `cap`, every further API call is refused."""
    def __init__(self) -> None:
        self.cap: float | None = None
        self.spent = 0.0
        self._lock = threading.Lock()

    def add(self, usd: float) -> None:
        with self._lock:
            self.spent += usd

    def exceeded(self) -> bool:
        return self.cap is not None and self.spent >= self.cap


BUDGET = Budget()


class Router:
    provider = "?"
    model = "?"
    workers = 8
    warm_cache = False       # send the first call alone so parallel workers read the prompt cache
    cache_mode: str | None = None   # "implicit" | "explicit" | None (provider exposes no cache controls)
    setup_cost_usd = 0.0     # one-off cost of creating an explicit cache, added to the system's total cost

    def __init__(self) -> None:
        self.name = f"{self.model}_{self.cache_mode}_{self.variant}" if self.cache_mode else f"{self.model}_{self.variant}"

    def _tag(self, text: str) -> str:
        """Give every router instance its own prompt-cache namespace so implicit/explicit runs (and iterations) start cold
        and never read a cache another system wrote."""
        return text + f"\n\n[cache namespace {self.cache_mode} {uuid.uuid4().hex[:8]}; ignore this line]"

    def close(self) -> None:
        """Release provider-side resources (e.g. delete an explicit cache)."""

    def _invoke(self, xml: str) -> Raw:   # pragma: no cover - provider specific
        raise NotImplementedError

    def _one(self, xml: str, truth: str) -> Prediction:
        t0 = time.perf_counter()
        base = dict(provider=self.provider, system=self.name, model=self.model, input_text=xml, y_true=truth)
        if BUDGET.exceeded():
            err = f"BudgetExceeded: spend ${BUDGET.spent:.4f} reached cap ${BUDGET.cap}"
            AUDIT.record(**base, request={}, latency_s=0.0, error=err, cost_usd=0.0)
            return Prediction(intent="__error__", latency_s=0.0, error=err)
        try:
            r = self._invoke(xml)
        except Exception as e:     # network/API errors are recorded, not fatal to the run
            dt = time.perf_counter() - t0
            err = f"{type(e).__name__}: {e}"
            AUDIT.record(**base, request={}, latency_s=dt, error=err, cost_usd=0.0)
            return Prediction(intent="__error__", latency_s=dt, error=err)
        dt = time.perf_counter() - t0
        BUDGET.add(r.cost_usd)
        conf = min(1.0, max(0.0, float(r.confidence)))
        AUDIT.record(**base, request=r.request, response=r.response, source=r.source, latency_s=dt, request_id=r.request_id,
                     result_prob=conf, result_intent=r.intent, cost_usd=r.cost_usd,
                     usage={"input_tokens": r.input_tokens, "output_tokens": r.output_tokens,
                            "cache_read_input_tokens": r.cache_read_tokens,
                            "cache_creation_input_tokens": r.cache_write_tokens, **r.extra_usage})
        return Prediction(intent=r.intent, confidence=conf, latency_s=dt, input_tokens=r.input_tokens,
                          output_tokens=r.output_tokens, cache_read_tokens=r.cache_read_tokens,
                          cache_write_tokens=r.cache_write_tokens, cost_usd=r.cost_usd)

    def predict(self, df: pd.DataFrame) -> list[Prediction]:
        xmls, ys = df["xml"].tolist(), df["intent"].tolist()
        first = [self._one(xmls[0], ys[0])] if self.warm_cache else []
        start = len(first)
        with ThreadPoolExecutor(self.workers) as ex:
            return first + list(ex.map(self._one, xmls[start:], ys[start:]))
