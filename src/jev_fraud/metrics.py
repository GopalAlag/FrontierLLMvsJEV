from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.metrics import (
    average_precision_score, f1_score, precision_score, recall_score, roc_auc_score,
)


@dataclass
class Prediction:
    prob: float
    latency_s: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0
    error: str | None = None


@dataclass
class Result:
    name: str
    preds: list[Prediction] = field(default_factory=list)


def best_f1_threshold(y, p) -> float:
    """Pick a threshold on a *calibration* set; never on the eval set."""
    grid = np.unique(np.round(np.concatenate([p, np.linspace(0.05, 0.95, 19)]), 4))
    return float(max(grid, key=lambda t: f1_score(y, p >= t, zero_division=0)))


def summarize(y, preds: list[Prediction], threshold: float = 0.5) -> dict:
    ok = [(yi, pr) for yi, pr in zip(y, preds) if pr.error is None]
    n_err = len(preds) - len(ok)
    yy = np.array([a for a, _ in ok])
    pp = np.array([b.prob for _, b in ok])
    lat = np.array([b.latency_s for b in preds])
    cost = sum(b.cost_usd for b in preds)
    out = {
        "n": len(preds),
        "errors": n_err,
        "threshold": round(threshold, 4),
        "tp": int(((pp >= threshold) & (yy == 1)).sum()),
        "precision": precision_score(yy, pp >= threshold, zero_division=0),
        "recall": recall_score(yy, pp >= threshold, zero_division=0),
        "f1": f1_score(yy, pp >= threshold, zero_division=0),
        "roc_auc": roc_auc_score(yy, pp) if len(set(yy)) > 1 else float("nan"),
        "pr_auc": average_precision_score(yy, pp) if len(set(yy)) > 1 else float("nan"),
        "latency_p50_s": float(np.percentile(lat, 50)),
        "latency_p95_s": float(np.percentile(lat, 95)),
        "input_tokens": sum(b.input_tokens + b.cache_read_tokens + b.cache_write_tokens for b in preds),
        "output_tokens": sum(b.output_tokens for b in preds),
        "cache_read_tokens": sum(b.cache_read_tokens for b in preds),
        "total_cost_usd": cost,
        "cost_per_1k_usd": cost / len(preds) * 1000,
    }
    return {k: (round(v, 6) if isinstance(v, float) else v) for k, v in out.items()}
