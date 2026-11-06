"""Render results.md / summary_by_system.csv from the measured rows. Every verdict sentence is computed, none hardcoded."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from .intents import NAMES
from pathlib import Path

import pandas as pd


def family_table(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["family"] = df["system"].str.replace(r"_v\d+$", "", regex=True)
    g = df.groupby("family")
    t = pd.DataFrame({
        "iterations": g.size(),
        "accuracy": g.accuracy.mean(), "macro_f1": g.macro_f1.mean(), "handled_correctly": g.handled_correctly.mean(),
        "automation_rate": g.automation_rate.mean(), "auto_precision": g.auto_precision.mean(),
        "misroute_rate": g.misroute_rate.mean(), "unnecessary_escalation_rate": g.unnecessary_escalation_rate.mean(),
        "invalid_labels": g.invalid_labels.sum(), "errors": g.errors.sum(),
        "latency_p50_s": g.latency_p50_s.mean(), "latency_p95_s": g.latency_p95_s.mean(),
        "throughput_per_s": g.throughput_per_s.mean(), "eval_wall_s": g.eval_wall_s.sum(), "total_wall_s": g.total_wall_s.sum(),
        "cost_per_1k_usd": g.cost_per_1k_usd.mean(), "total_cost_usd": g.total_cost_usd.sum(),
        "cost_per_correct_call_usd": g.cost_per_correct_call_usd.mean(), "ops_cost_per_1k_usd": g.ops_cost_per_1k_usd.mean(),
        "cached_input_share": g.cache_read_tokens.sum() / g.input_tokens.sum().replace(0, float("nan")),
        "cache_write_tokens": g.cache_write_tokens.sum(), "cache_setup_cost_usd": g.cache_setup_cost_usd.sum(),
    })
    t["cost_per_1m_calls_usd"] = t.cost_per_1k_usd * 1000
    return t.sort_values("handled_correctly", ascending=False)


def write_report(out: Path, config: dict, rows: list[dict], confs: list[dict], runtime_s: float, entries: list[dict]) -> None:
    if not rows:
        (out / "results.md").write_text("# IVR intent results\n\nNo system completed.\n", encoding="utf-8")
        return
    t = family_table(rows)
    t.round(5).to_csv(out / "summary_by_system.csv")
    api = t[t.total_cost_usd > 0]
    best, fastest = t.handled_correctly.idxmax(), t.latency_p50_s.idxmin()
    L = ["# IVR conversational AI: intent detection, routing and servicing", "",
         f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}. Whole experiment {runtime_s:.0f} s wall clock, "
         f"{len(entries)} external API calls, ${sum(e.get('cost_usd', 0) for e in entries):.4f} measured spend.", "",
         "## Scenario", "",
         f"A credit card customer calls the IVR. Speech-to-text returns an XML N-best result. The system must (1) detect the intent from a "
         f"taxonomy of {len(NAMES)} credit-card servicing intents (the intent categories in the sample brands-LOB data), (2) route to the servicing workflow when confident, otherwise to a live agent "
         "(threshold tuned on a calibration slice), and (3) run the workflow against a mock account. Eval utterances are phrasings never "
         "seen by the TF-IDF model or the few-shot prompt.", "",
         "## Headline", "",
         f"- Best end-to-end handling: **{best}** ({t.handled_correctly[best]:.1%} handled correctly, misroute {t.misroute_rate[best]:.1%}, "
         f"automation {t.automation_rate[best]:.1%}).",
         f"- Highest exact-intent accuracy: **{t.accuracy.idxmax()}** ({t.accuracy.max():.1%}); best macro-F1: **{t.macro_f1.idxmax()}** ({t.macro_f1.max():.3f}).",
         f"- Fastest median latency: **{fastest}** ({t.latency_p50_s[fastest] * 1000:.0f} ms)."]
    if len(api):
        cheap = api.cost_per_1k_usd.idxmin()
        L.append(f"- Cheapest API system: **{cheap}** (${api.cost_per_1k_usd[cheap]:.4f} per 1,000 calls, "
                 f"${api.cost_per_1m_calls_usd[cheap]:,.0f} per million).")
        for f in api.index:
            L.append(f"  - {f}: ${t.cost_per_correct_call_usd[f]:.5f} per correctly handled call; illustrative total ops cost "
                     f"${t.ops_cost_per_1k_usd[f]:,.2f} per 1,000 calls (model spend + ${config['agent_cost']}/agent call + ${config['misroute_cost']}/misroute).")
    L += ["", "## Quality (mean over iterations)", "",
          t[["accuracy", "macro_f1", "handled_correctly", "automation_rate", "auto_precision", "misroute_rate",
             "unnecessary_escalation_rate", "invalid_labels", "errors"]].round(3).reset_index().to_markdown(index=False), "",
          "`accuracy` = exact intent label. `handled_correctly` = right workflow (or right agent transfer), counting near-synonym intents that "
          "share a workflow as correct. `misroute_rate` = automatic action on the wrong workflow. `automation_rate` = share sent to a "
          "workflow without a human.", "",
          "## Latency and time", "",
          t[["latency_p50_s", "latency_p95_s", "throughput_per_s", "eval_wall_s", "total_wall_s"]].round(3).reset_index().to_markdown(index=False), "",
          "TF-IDF latency is amortised batch time, not a per-request round trip.", "",
          "## Cost", "",
          t[["cost_per_1k_usd", "cost_per_1m_calls_usd", "cost_per_correct_call_usd", "total_cost_usd", "ops_cost_per_1k_usd", "cached_input_share", "cache_write_tokens", "cache_setup_cost_usd"]]
          .round(5).reset_index().to_markdown(index=False), "",
          "Caching: rows are suffixed `_implicit` / `_explicit` for Claude, GPT and Gemini. Claude explicit = block-level breakpoint on the system prompt, "
          "implicit = top-level automatic marker. GPT implicit = automatic prefix caching, explicit = `prompt_cache_breakpoint` with the implicit "
          "breakpoint disabled. Gemini implicit = automatic, explicit = `caches.create` (creation cost shown as `cache_setup_cost_usd`; hourly "
          "storage not included). JEV exposes no cache controls and reports no cached tokens, so it has a single row.", "",
          "## Per iteration", ""]
    cols = ["iteration", "system", "n", "errors", "threshold", "accuracy", "macro_f1", "handled_correctly", "automation_rate", "misroute_rate",
            "latency_p50_s", "latency_p95_s", "input_tokens", "output_tokens", "cache_read_tokens", "eval_wall_s", "total_cost_usd", "cost_per_1k_usd"]
    L += ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    L += ["| " + " | ".join(str(r.get(c, "")) for c in cols) + " |" for r in rows]
    if confs:
        cdf = pd.DataFrame(confs)
        cdf["family"] = cdf.system.str.replace(r"_v\d+$", "", regex=True)
        top = cdf.groupby(["family", "true", "predicted"], as_index=False)["count"].sum().sort_values(["family", "count"], ascending=[True, False])
        L += ["", "## Most common intent confusions (summed over iterations, top 5 per system)", "",
              top.groupby("family").head(5).to_markdown(index=False), ""]
    L += ["## Run configuration", "", "```json", json.dumps(config, indent=2), "```", "",
          "Raw per-call request/response/usage/cost records: `audit.jsonl`. Test data for every split: `data/iter*_{train,calib,eval}.jsonl`.", ""]
    (out / "results.md").write_text("\n".join(L), encoding="utf-8")
