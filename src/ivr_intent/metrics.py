"""Scoring: intent quality, routing/servicing outcomes, latency and cost."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import f1_score

from .intents import NAMES
from .router import expected, route

MISROUTE_PENALTY = 2.0     # threshold utility = correct auto-service - 2 x misroute


@dataclass
class Prediction:
    intent: str
    confidence: float = 0.0
    latency_s: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0
    error: str | None = None


def _outcomes(y, preds, xmls, thr):
    out = []
    for t, p, x in zip(y, preds, xmls):
        d = route(p.intent, p.confidence, thr, x, p.error)
        ea, ew = expected(t)
        out.append((d, (d.action, d.workflow) == (ea, ew), ea))
    return out


def best_threshold(y, preds, xmls) -> float:
    """Pick the escalation threshold on a calibration set (never the eval set)."""
    best, best_u = 0.5, -1e9
    for thr in np.round(np.linspace(0.0, 0.99, 34), 3):
        u = 0.0
        for d, ok, ea in _outcomes(y, preds, xmls, thr):
            if d.action == "workflow":
                u += 1.0 if ok else -MISROUTE_PENALTY
            elif ok:
                u += 1.0
        if u > best_u + 1e-9:
            best, best_u = float(thr), u
    return best


def summarize(y, preds: list[Prediction], xmls, thr: float, unseen=None,
              agent_cost: float = 5.0, misroute_cost: float = 10.0, extra_cost: float = 0.0) -> dict:
    n = len(preds)
    y = list(y)
    yp = [p.intent if p.error is None else "__error__" for p in preds]
    correct = np.array([a == b for a, b in zip(y, yp)])
    oc = _outcomes(y, preds, xmls, thr)
    auto = np.array([d.action == "workflow" for d, _, _ in oc])
    ok = np.array([o for _, o, _ in oc])
    # a misroute = the system acted automatically on the wrong workflow (or ran a workflow for a caller who wanted an agent)
    misroute = np.array([(d.action == "workflow" and not o) for d, o, _ in oc])
    unnecessary_esc = np.array([(d.reason == "low_confidence_escalation" and ea == "workflow") for d, _, ea in oc])
    lat = np.array([p.latency_s for p in preds])
    cost = sum(p.cost_usd for p in preds) + extra_cost     # extra_cost = one-off explicit-cache setup
    agent_calls = sum(d.action == "agent" for d, _, _ in oc)
    out = {
        "n": n, "errors": sum(p.error is not None for p in preds), "threshold": round(thr, 3),
        "accuracy": correct.mean(),
        "macro_f1": f1_score(y, yp, labels=NAMES, average="macro", zero_division=0),
        "accuracy_unseen": float(correct[np.array(unseen)].mean()) if unseen is not None and np.any(unseen) else float("nan"),
        "automation_rate": auto.mean(),
        "auto_precision": float(ok[auto].mean()) if auto.any() else float("nan"),
        "misroute_rate": misroute.mean(),
        "unnecessary_escalation_rate": unnecessary_esc.mean(),
        "handled_correctly": ok.mean(),          # right workflow, or right agent/reprompt for agent/oos callers
        "invalid_labels": sum(p.error is None and p.intent not in NAMES for p in preds),
        "latency_p50_s": float(np.percentile(lat, 50)), "latency_p95_s": float(np.percentile(lat, 95)),
        "input_tokens": sum(p.input_tokens + p.cache_read_tokens + p.cache_write_tokens for p in preds),
        "output_tokens": sum(p.output_tokens for p in preds),
        "cache_read_tokens": sum(p.cache_read_tokens for p in preds),
        "cache_write_tokens": sum(p.cache_write_tokens for p in preds),
        "total_cost_usd": cost, "cost_per_1k_usd": cost / n * 1000,
        "cost_per_correct_call_usd": cost / max(int(ok.sum()), 1),
        # Illustrative total operating cost per 1,000 calls: model spend + human-agent handling + misroute rework.
        "ops_cost_per_1k_usd": (cost + agent_calls * agent_cost + int(misroute.sum()) * misroute_cost) / n * 1000,
    }
    return {k: (round(v, 6) if isinstance(v, float) else v) for k, v in out.items()}


def confusions(y, preds, top=8) -> list[tuple[str, str, int]]:
    from collections import Counter
    c = Counter((t, p.intent) for t, p in zip(y, preds) if p.error is None and t != p.intent)
    return [(a, b, k) for (a, b), k in c.most_common(top)]
