"""IVR intent detection + routing + servicing: classic TF-IDF vs JEV vs Claude / GPT / Gemini, over N iterations.

Apples to apples: for each iteration every system gets the identical calibration and eval calls (same XML, same labels),
the same intent catalog, the same workflow mapping, the same threshold-selection method and the same scoring. Iteration i draws
fresh data (seed base+i) and uses prompt variant v1 -> v2 (JEV: its Choice question v1 -> v2).

Cost control: a pre-flight check refuses to start if the expected spend exceeds --hard-cap, and a global guard refuses further
API calls once measured spend reaches it.

Everything is logged under <out>/: run.log (console + every API call), events.jsonl (timeline), run_manifest.json (config, versions,
data hashes, spend plan and totals), audit.jsonl (raw request/response per call), iterations.csv/json, results.md, data/*.jsonl.

  python -m ivr_intent.run_experiment --dry-run
  python -m ivr_intent.run_experiment --iterations 2 --n-calib 50 --n-eval 250 --cache-mode explicit --hard-cap 2.8
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from jev_fraud.audit import AUDIT

from .data import make_splits, write_jsonl
from .metrics import best_threshold, confusions, summarize
from .models._base import BUDGET
from .report import write_report

ROOT = Path(__file__).resolve().parents[2]

LLM_KEYS = {"jev": "TYPESAFE_API_KEY", "claude_haiku": "ANTHROPIC_API_KEY", "claude_sonnet": "ANTHROPIC_API_KEY",
            "openai_luna": "OPENAI_API_KEY", "gemini_flash_lite": "GEMINI_API_KEY"}
# Measured mean cost per call (calibration + eval) with explicit caching over the first 3,000-call run (USD), and one-off cache setup per router instance.
# Used only for the pre-flight budget plan; actual cost always comes from the usage fields.
PER_CALL = {"jev": 0.00017, "claude_haiku": 0.000125, "openai_luna": 0.000105, "gemini_flash_lite": 0.000175, "claude_sonnet": 0.00243}
SETUP = {"jev": 0.0, "claude_haiku": 0.0008, "openai_luna": 0.0004, "gemini_flash_lite": 0.0007, "claude_sonnet": 0.016}
PLAN_MARGIN = 1.15      # v2 prompt is longer than v1, output length varies


class Tee:
    """Mirror stdout to the run log."""
    def __init__(self, path: Path):
        self.out, self.err, self.fh = sys.stdout, sys.stderr, path.open("w", encoding="utf-8", buffering=1)

    def write(self, s):
        self.out.write(s)
        self.fh.write(s)

    def flush(self):
        self.out.flush()
        self.fh.flush()

    def close(self):
        sys.stdout, sys.stderr = self.out, self.err
        self.fh.close()


def make_system(key: str, it: int, sys_prompt: str | None, workers: int, cache_mode: str | None = None):
    v = "v3" if sys_prompt else f"v{min(it, 2)}"
    if key == "jev":
        from .models.jev import JevRouter
        return JevRouter(variant=f"v{min(it, 2)}", workers=workers)
    if key == "claude_haiku":
        from .models.claude_haiku import ClaudeHaikuRouter
        return ClaudeHaikuRouter(variant=v, workers=workers, system_prompt=sys_prompt, cache_mode=cache_mode or "explicit")
    if key == "claude_sonnet":
        from .models.claude_sonnet import ClaudeSonnetRouter
        return ClaudeSonnetRouter(variant=v, workers=workers, system_prompt=sys_prompt, cache_mode=cache_mode or "explicit")
    if key == "openai_luna":
        from .models.openai_gpt6_luna import OpenAILunaRouter
        return OpenAILunaRouter(variant=v, workers=workers, system_prompt=sys_prompt, cache_mode=cache_mode or "implicit")
    if key == "gemini_flash_lite":
        from .models.gemini_flash_lite import GeminiFlashLiteRouter
        return GeminiFlashLiteRouter(variant=v, workers=workers, system_prompt=sys_prompt, cache_mode=cache_mode or "implicit")
    raise KeyError(key)


def _sha(items) -> str:
    return hashlib.sha256("\n".join(items).encode()).hexdigest()[:12]


def _versions() -> dict:
    out = {"python": platform.python_version(), "platform": platform.platform()}
    for p in ("anthropic", "openai", "google-genai", "langchain-typesafe", "scikit-learn", "pandas", "numpy"):
        try:
            out[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            out[p] = None
    return out


def main() -> None:
    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=2)
    ap.add_argument("--n-eval", type=int, default=250)
    ap.add_argument("--n-calib", type=int, default=50)
    ap.add_argument("--n-train", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--stratified", action="store_true", help="eval set gets exactly n_eval // 114 calls per intent (uniform), not random counts")
    ap.add_argument("--fewshot", action="store_true", help="long shared system prompt with labelled train examples (all providers cache)")
    ap.add_argument("--cache-mode", choices=["implicit", "explicit", "both"], default="explicit",
                    help="prompt-cache mode for Claude/GPT/Gemini (JEV exposes no cache controls); 'both' runs each model twice")
    ap.add_argument("--no-trace", action="store_true", help="do not log one line per API call")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--skip", default="", help="comma list of: tfidf," + ",".join(LLM_KEYS))
    ap.add_argument("--hard-cap", type=float, default=2.8, help="never spend more than this many USD in this run")
    ap.add_argument("--agent-cost", type=float, default=5.0, help="assumed $ per live-agent handled call (illustrative)")
    ap.add_argument("--misroute-cost", type=float, default=10.0, help="assumed $ rework cost per misrouted call (illustrative)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and expected cost; make no API calls")
    ap.add_argument("--out", default=str(ROOT / "results_ivr"))
    args = ap.parse_args()
    skip = set(filter(None, args.skip.split(",")))

    keys = [k for k, env in LLM_KEYS.items() if k not in skip and (os.getenv(env) or (env == "GEMINI_API_KEY" and os.getenv("GOOGLE_API_KEY")))]
    keys.sort(key=lambda k: PER_CALL[k])                      # cheapest first, so the priciest system is last
    missing = [k for k in LLM_KEYS if k not in skip and k not in keys]

    modes_of = lambda k: [None] if k == "jev" else (["implicit", "explicit"] if args.cache_mode == "both" else [args.cache_mode])
    calls_per_it = args.n_calib + args.n_eval
    plan = {}
    for k in keys:
        runs = len(modes_of(k))
        plan[k] = round(runs * (args.iterations * calls_per_it * PER_CALL[k] * PLAN_MARGIN + args.iterations * SETUP[k]), 4)
    expected_total = round(sum(plan.values()), 4)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tee = Tee(out / "run.log")
    sys.stdout = sys.stderr = tee      # warnings and tracebacks go to the run log too
    events = (out / "events.jsonl").open("w", encoding="utf-8", buffering=1)
    t_run = time.perf_counter()

    def event(kind: str, **kw) -> None:
        events.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                                 "elapsed_s": round(time.perf_counter() - t_run, 2), "event": kind,
                                 "spent_usd": round(BUDGET.spent, 6), **kw}, default=str) + "\n")

    print(f"# IVR intent experiment | started {datetime.now(timezone.utc).isoformat(timespec='seconds')} | out={out}")
    print(f"systems: tfidf={'tfidf' not in skip} | LLM/JEV (cheapest first): {keys or 'none'}" + (f" | no key for: {missing}" if missing else ""))
    print(f"design: {args.iterations} iterations x ({args.n_calib} calibration + {args.n_eval} eval) = {args.iterations * calls_per_it} calls per system; "
          f"cache-mode={args.cache_mode}; workers={args.workers}")
    print("expected spend (measured per-call costs x margin): " + ", ".join(f"{k}=${v:.3f}" for k, v in plan.items()) +
          f" | total ${expected_total:.3f} vs hard cap ${args.hard_cap:.2f}")
    manifest = {"started": datetime.now(timezone.utc).isoformat(timespec="seconds"), "args": vars(args), "versions": _versions(),
                "systems": keys, "expected_spend_by_system_usd": plan, "expected_total_usd": expected_total,
                "hard_cap_usd": args.hard_cap, "plan_margin": PLAN_MARGIN, "per_call_assumption_usd": PER_CALL, "setup_assumption_usd": SETUP,
                "iterations": []}
    event("run_start", args=vars(args), expected_total_usd=expected_total)

    def finish(status: str) -> None:
        manifest.update(status=status, finished=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        runtime_s=round(time.perf_counter() - t_run, 1), measured_spend_usd=round(BUDGET.spent, 6),
                        api_calls=len(AUDIT.entries))
        (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
        event("run_end", status=status)
        events.close()
        print(f"\n# {status} | runtime {manifest['runtime_s']}s | API calls {manifest['api_calls']} | measured spend ${BUDGET.spent:.4f} "
              f"(hard cap ${args.hard_cap:.2f})")
        tee.close()

    if args.dry_run:
        finish("dry-run")
        return
    if expected_total > args.hard_cap:
        print(f"ABORT: expected spend ${expected_total:.3f} exceeds hard cap ${args.hard_cap:.2f}. Reduce --n-eval/--n-calib/--iterations or skip a system.")
        event("preflight_abort", expected_total_usd=expected_total)
        finish("aborted-preflight")
        return

    from .models.tfidf_baseline import TfidfBaseline
    AUDIT.open(out / "audit.jsonl")
    AUDIT.trace = not args.no_trace
    BUDGET.cap = args.hard_cap
    rows, confs = [], []

    for it in range(1, args.iterations + 1):
        seed = args.seed + it
        train, calib, ev = make_splits(seed, args.n_train, args.n_calib, args.n_eval, stratified_eval=args.stratified)
        for name, df in (("train", train), ("calib", calib), ("eval", ev)):
            write_jsonl(df, out / "data" / f"iter{it}_{name}.jsonl")
        y_c, y_e = calib.intent.tolist(), ev.intent.tolist()
        x_c, x_e = calib.xml.tolist(), ev.xml.tolist()
        info = {"iteration": it, "seed": seed, "n_train": len(train), "n_calib": len(calib), "n_eval": len(ev),
                "eval_intents": int(ev.intent.nunique()), "calib_sha": _sha(x_c), "eval_sha": _sha(x_e),
                "eval_intent_counts": ev.intent.value_counts().to_dict()}
        manifest["iterations"].append(info)
        print(f"\n=== iteration {it} (seed {seed}) eval n={len(ev)} over {info['eval_intents']} intents | calib sha {info['calib_sha']} "
              f"eval sha {info['eval_sha']} (identical input for every system) ===")
        event("iteration_start", **{k: v for k, v in info.items() if k != "eval_intent_counts"})

        sys_prompt = None
        if args.fewshot:
            from .prompts import build_fewshot_prompt, prompt_hash
            sys_prompt = build_fewshot_prompt(train, seed)
            pdir = out / "system_prompts"
            pdir.mkdir(exist_ok=True)
            (pdir / f"{prompt_hash(sys_prompt)}.txt").write_text(sys_prompt, encoding="utf-8")
            print(f"  few-shot system prompt: {len(sys_prompt):,} chars (~{len(sys_prompt) // 4:,} tokens)")

        systems = [] if "tfidf" in skip else [TfidfBaseline(seed).fit(train)]
        for k in keys:
            for cm in modes_of(k):
                try:
                    s = make_system(k, it, sys_prompt, args.workers, cm)
                except Exception as e:
                    print(f"  {k} ({cm}) could not be created: {type(e).__name__}: {e}")
                    event("system_setup_error", system=k, cache_mode=cm, error=f"{type(e).__name__}: {e}")
                    continue
                BUDGET.add(getattr(s, "setup_cost_usd", 0.0))
                systems.append(s)

        for s in systems:
            print(f"\n--- {s.name} | cache_mode={getattr(s, 'cache_mode', None)} | setup ${getattr(s, 'setup_cost_usd', 0.0):.5f} "
                  f"| spend so far ${BUDGET.spent:.4f} ---")
            AUDIT.context = {"iteration": it, "split": "calibration"}
            t_sys = time.perf_counter()
            event("system_start", system=s.name, iteration=it)
            cal = s.predict(calib)
            event("calibration_done", system=s.name, iteration=it, errors=sum(p.error is not None for p in cal),
                  cost_usd=round(sum(p.cost_usd for p in cal), 6))
            if all(p.error for p in cal):
                print(f"  {s.name:32s} SKIPPED: all {len(cal)} calibration calls failed: {cal[0].error[:160]}")
                event("system_skipped", system=s.name, iteration=it, error=cal[0].error[:200])
                if hasattr(s, "close"):
                    s.close()
                continue
            thr = best_threshold(y_c, cal, x_c)
            print(f"  calibration done: threshold={thr} (chosen on calibration only)")
            AUDIT.context = {"iteration": it, "split": "eval", "threshold": thr}
            t_ev = time.perf_counter()
            preds = s.predict(ev)
            t_end = time.perf_counter()
            setup = getattr(s, "setup_cost_usd", 0.0)
            m = summarize(y_e, preds, x_e, thr, agent_cost=args.agent_cost, misroute_cost=args.misroute_cost, extra_cost=setup)
            if hasattr(s, "close"):
                s.close()
            m.update(iteration=it, system=s.name, cache_setup_cost_usd=round(setup, 6), eval_wall_s=round(t_end - t_ev, 2),
                     total_wall_s=round(t_end - t_sys + getattr(s, "train_seconds", 0.0), 2),
                     throughput_per_s=round(len(ev) / max(t_end - t_ev, 1e-9), 2), calib_sha=info["calib_sha"], eval_sha=info["eval_sha"])
            if err := next((p.error for p in preds if p.error), None):
                m["first_error"] = err
            rows.append(m)
            confs += [dict(iteration=it, system=s.name, true=a, predicted=b, count=c) for a, b, c in confusions(y_e, preds, 10)]
            print(f"  {s.name:32s} acc={m['accuracy']:.3f} macroF1={m['macro_f1']:.3f} handled={m['handled_correctly']:.3f} "
                  f"auto={m['automation_rate']:.3f} misroute={m['misroute_rate']:.3f} p50={m['latency_p50_s']*1000:.0f}ms "
                  f"cost/1k=${m['cost_per_1k_usd']:.4f} err={m['errors']}  (spend so far ${BUDGET.spent:.4f})")
            print("  ALL METRICS: " + json.dumps(m, default=str))
            event("system_done", system=s.name, iteration=it, metrics=m)
            if BUDGET.exceeded():
                print(f"  !! hard cap ${args.hard_cap:.2f} reached; later calls are refused")
                event("budget_stop", system=s.name)

    AUDIT.close()
    res = pd.DataFrame(rows)
    res.to_csv(out / "iterations.csv", index=False)
    (out / "iterations.json").write_text(json.dumps(rows, indent=2))
    write_report(out, vars(args), rows, confs, time.perf_counter() - t_run, AUDIT.entries)
    print(f"\nwrote {out}: run.log, events.jsonl, run_manifest.json, audit.jsonl, iterations.csv/json, summary_by_system.csv, results.md, data/")
    finish("completed")


if __name__ == "__main__":
    import traceback
    try:
        main()
    except BaseException:
        traceback.print_exc()          # lands in run.log via the tee when it is active
        raise
