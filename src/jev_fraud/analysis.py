"""Turn per-iteration metric rows into the comparison tables and a 'which is best' verdict.

Every sentence in the verdict is computed from the measured rows, nothing is hardcoded.
"""
from __future__ import annotations

import pandas as pd

LLM_PRICE_NOTE = "classic GBM has no API cost (local compute only)"


def family_table(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["family"] = df["system"].str.replace(r"_v\d+$", "", regex=True)
    g = df.groupby("family")
    t = pd.DataFrame({
        "iterations": g.size(),
        "precision": g.precision.mean(), "recall": g.recall.mean(), "f1": g.f1.mean(),
        "f1_min": g.f1.min(), "f1_max": g.f1.max(),
        "pr_auc": g.pr_auc.mean(), "roc_auc": g.roc_auc.mean(),
        "latency_p50_s": g.latency_p50_s.mean(), "latency_p95_s": g.latency_p95_s.mean(),
        "eval_wall_s": g.eval_wall_s.sum(), "total_wall_s": g.total_wall_s.sum(),
        "throughput_per_s": g.throughput_per_s.mean(),
        "cost_per_1k_usd": g.cost_per_1k_usd.mean(), "total_cost_usd": g.total_cost_usd.sum(),
        "errors": g.errors.sum(), "tp": g.tp.sum(),
        "cached_input_share": g.cache_read_tokens.sum() / g.input_tokens.sum().replace(0, float("nan")),
    })
    t["cost_per_caught_fraud_usd"] = (g.total_cost_usd.sum() / g.tp.sum().replace(0, float("nan")))
    t["cost_per_1m_txn_usd"] = t.cost_per_1k_usd * 1000
    return t.sort_values("f1", ascending=False)


def _fmt(t: pd.DataFrame) -> str:
    cols = {
        "precision": "{:.3f}", "recall": "{:.3f}", "f1": "{:.3f}", "pr_auc": "{:.3f}",
        "latency_p50_s": "{:.3f}", "latency_p95_s": "{:.3f}", "eval_wall_s": "{:.1f}",
        "total_wall_s": "{:.1f}", "throughput_per_s": "{:.1f}", "cost_per_1k_usd": "{:.4f}",
        "cost_per_1m_txn_usd": "{:,.0f}", "total_cost_usd": "{:.4f}",
        "cost_per_caught_fraud_usd": "{:.5f}",
    }
    out = t.reset_index()
    for c, f in cols.items():
        out[c] = out[c].map(lambda v, f=f: "-" if pd.isna(v) else f.format(v))
    return out.to_markdown(index=False)


def executive_summary(rows: list[dict], total_runtime_s: float, n_eval: int, data: str) -> str:
    t = family_table(rows)
    api = t[t.total_cost_usd > 0]
    best_q = t.f1.idxmax()
    fastest = t.latency_p50_s.idxmin()
    L = ["## Summary: performance, latency, time and cost", ""]
    L += [f"Data: **{data}**, {n_eval} eval transactions per iteration (fraud-enriched), "
          f"{int(t.iterations.max())} iterations. Whole experiment took **{total_runtime_s:.0f} s** wall clock.", ""]

    L += ["### Performance (mean over iterations)", "",
          t[["precision", "recall", "f1", "f1_min", "f1_max", "pr_auc", "roc_auc", "errors"]]
          .round(3).reset_index().to_markdown(index=False), "",
          "### Latency and time taken", "",
          t[["latency_p50_s", "latency_p95_s", "throughput_per_s", "eval_wall_s", "total_wall_s"]]
          .round(3).reset_index().to_markdown(index=False), "",
          "`latency_*` is seconds per transaction (API round trip; classic GBM is amortised batch time, "
          "so it is not a like-for-like request latency). `eval_wall_s` is wall time scoring the eval "
          "sets with 8 parallel workers; `total_wall_s` adds calibration scoring and, for classic GBM, "
          "training.", "",
          "### Cost", "",
          t[["cost_per_1k_usd", "cost_per_1m_txn_usd", "cost_per_caught_fraud_usd", "total_cost_usd",
             "cached_input_share"]]
          .round(5).reset_index().to_markdown(index=False), "",
          f"`cost_per_1m_txn_usd` extrapolates the measured per-call cost to one million transactions; "
          f"{LLM_PRICE_NOTE}. `cost_per_caught_fraud_usd` = API spend / true positives on the eval sets.", ""]

    L += ["### Which model is best?", ""]
    L.append(f"- **Best accuracy (F1):** `{best_q}` with mean F1 {t.f1[best_q]:.3f} "
             f"(range {t.f1_min[best_q]:.3f} to {t.f1_max[best_q]:.3f}), "
             f"precision {t.precision[best_q]:.3f}, recall {t.recall[best_q]:.3f}.")
    L.append(f"- **Fastest per transaction:** `{fastest}` at {t.latency_p50_s[fastest] * 1000:.1f} ms median.")
    if len(api):
        cheapest = api.cost_per_1k_usd.idxmin()
        best_api = api.f1.idxmax()
        L.append(f"- **Cheapest API option:** `{cheapest}` at ${api.cost_per_1k_usd[cheapest]:.4f} per 1,000 "
                 f"transactions (about ${api.cost_per_1m_txn_usd[cheapest]:,.0f} per million).")
        L.append(f"- **Most accurate API option:** `{best_api}` (F1 {api.f1[best_api]:.3f}, "
                 f"${api.cost_per_1k_usd[best_api]:.4f} per 1,000).")
        eff = (api.f1 / api.cost_per_1k_usd).idxmax()
        L.append(f"- **Best F1 per dollar among API options:** `{eff}` "
                 f"({api.f1[eff] / api.cost_per_1k_usd[eff]:,.1f} F1 points per $ per 1k transactions).")
        pairs = []
        for a in api.index:
            for b in api.index:
                if a < b:
                    pairs.append(f"`{a}` vs `{b}`: {api.cost_per_1k_usd[a] / api.cost_per_1k_usd[b]:.1f}x cost, "
                                 f"{api.latency_p50_s[a] / api.latency_p50_s[b]:.1f}x latency, "
                                 f"F1 {api.f1[a]:.3f} vs {api.f1[b]:.3f}")
        L += ["", "Head-to-head among API systems (ratios are first / second):", ""] + [f"- {p}" for p in pairs]

    verdict = [f"**Overall:** `{best_q}` gives the best accuracy on this data"]
    if best_q == fastest:
        verdict.append("and is also the fastest")
    if best_q not in api.index:
        verdict.append("with no per-call API spend")
    L += ["", ", ".join(verdict) + ".", ""]
    if len(api):
        ba = api.f1.idxmax()
        gap = t.f1[best_q] - api.f1[ba]
        L.append(f"Among API-based systems the F1 leader is `{ba}`, "
                 f"{'ahead of' if gap < 0 else 'behind'} `{best_q}` by {abs(gap):.3f} F1.")
        L.append("")
    L += ["**How to read this fairly**", "",
          "- The classic GBM is trained on labelled history; JEV and Claude run with no training data "
          "(zero-shot, prompt only). If you have no labels yet, the zero-shot systems are the only option.",
          "- Eval sets are fraud-enriched, so precision here is higher than it would be at the real 0.5 to 3% "
          "fraud rate. Compare systems with each other, not with production precision.",
          "- Differences of a few F1 points on a few hundred rows are within noise; the F1 range column "
          "shows the iteration-to-iteration spread.",
          "- JEV cost uses the vendor list price of $0.042/MTok input and free output; Claude cost uses "
          "measured `usage` tokens at list prices with cache read/write adjustments.", ""]
    L += ["### Full comparison table", "", _fmt(t), ""]
    return "\n".join(L)
