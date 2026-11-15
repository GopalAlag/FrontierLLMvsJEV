"""Run N iterations comparing classic GBM vs JEV vs Claude on fraud-enriched eval samples.

Iteration i uses seed (base+i) -> a fresh train/calibration/eval draw, and a prompt variant
(v1 -> v2 -> v3 for JEV; v1 -> v2 for Claude), so each iteration changes both data and prompt.
Thresholds for LLM-style systems are chosen on a separate calibration slice, never on eval.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from .audit import AUDIT, write_markdown
from .baseline import Baseline
from .data import load_frame, make_splits
from .metrics import best_f1_threshold, summarize

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=3)
    ap.add_argument("--n-eval", type=int, default=300)
    ap.add_argument("--n-calib", type=int, default=100)
    ap.add_argument("--n-train", type=int, default=100_000)
    ap.add_argument("--eval-fraud-rate", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--fewshot", action="store_true",
                    help="long shared system prompt (guidance + labelled train examples) so all providers cache")
    ap.add_argument("--trace", action="store_true", help="print one line per API call as it happens")
    ap.add_argument("--data", choices=["real", "synthetic"], default="real")
    ap.add_argument("--claude-models", default="claude-haiku-5-5,claude-sonnet-5-5")
    ap.add_argument("--openai-models", default="gpt-6-luna")
    ap.add_argument("--gemini-models", default="gemini-3.1-flash-lite")
    ap.add_argument("--skip", default="", help="comma list: jev,claude,openai,gemini")
    ap.add_argument("--out", default=str(ROOT / "results"))
    args = ap.parse_args()
    skip = set(filter(None, args.skip.split(",")))

    have_jev = bool(os.getenv("TYPESAFE_API_KEY")) and "jev" not in skip
    have_claude = bool(os.getenv("ANTHROPIC_API_KEY")) and "claude" not in skip
    have_openai = bool(os.getenv("OPENAI_API_KEY")) and "openai" not in skip
    have_gemini = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")) and "gemini" not in skip
    print(f"JEV: {have_jev} | Claude: {have_claude} | OpenAI: {have_openai} | Gemini: {have_gemini}")
    if not have_openai:
        print("  (set OPENAI_API_KEY in .env to run OpenAI)")
    if not have_gemini:
        print("  (set GEMINI_API_KEY in .env to run Gemini)")
    if not have_jev:
        print("  (set TYPESAFE_API_KEY in .env to run JEV)")
    if not have_claude:
        print("  (set ANTHROPIC_API_KEY in .env to run Claude)")

    t_run = time.perf_counter()
    out = Path(args.out)
    out.mkdir(exist_ok=True)
    AUDIT.open(out / "audit.jsonl")
    AUDIT.trace = args.trace
    if args.data == "synthetic":
        from .synthetic import generate
        df = generate(n=max(60_000, args.n_train * 2), fraud_rate=0.03, seed=args.seed)
    else:
        df = load_frame()
    print(f"loaded {len(df):,} rows, fraud rate {df.is_fraud.mean():.4%}")

    rows = []
    for it in range(1, args.iterations + 1):
        seed = args.seed + it
        # calib is carved from the eval draw; the remainder is the held-out eval set
        train, pool = make_splits(df, seed, args.n_train, args.n_eval + args.n_calib, args.eval_fraud_rate)
        calib, ev = pool.iloc[: args.n_calib], pool.iloc[args.n_calib:]
        y_c, y_e = calib.is_fraud.to_numpy(), ev.is_fraud.to_numpy()
        print(f"\n=== iteration {it} (seed {seed}) eval n={len(ev)} fraud={int(y_e.sum())} ===")

        sys_prompt = None
        if args.fewshot:
            from .prompts import build_fewshot_prompt, prompt_hash
            sys_prompt = build_fewshot_prompt(train, seed)
            pdir = out / "system_prompts"
            pdir.mkdir(exist_ok=True)
            (pdir / f"{prompt_hash(sys_prompt)}.txt").write_text(sys_prompt, encoding="utf-8")
            print(f"  few-shot system prompt: {len(sys_prompt):,} chars (~{len(sys_prompt) // 4:,} tokens)")
        pv = 3 if args.fewshot else None
        systems = [Baseline(seed).fit(train)]
        if have_jev:
            from .jev_module import JevClassifier
            systems.append(JevClassifier(variant=f"v{pv or min(it, 3)}"))
        if have_claude:
            from .llm_module import ClaudeClassifier
            for m in args.claude_models.split(","):
                systems.append(ClaudeClassifier(model=m, variant=f"v{pv or min(it, 2)}", system_prompt=sys_prompt))
        if have_openai:
            from .openai_module import OpenAIClassifier
            for m in args.openai_models.split(","):
                systems.append(OpenAIClassifier(model=m, variant=f"v{pv or min(it, 2)}", system_prompt=sys_prompt))
        if have_gemini:
            from .gemini_module import GeminiClassifier
            for m in args.gemini_models.split(","):
                systems.append(GeminiClassifier(model=m, variant=f"v{pv or min(it, 2)}", system_prompt=sys_prompt))

        for s in systems:
            AUDIT.context = {"iteration": it, "split": "calibration"}
            t_sys = time.perf_counter()
            cal_preds = s.predict(calib)
            if all(p.error for p in cal_preds):
                print(f"  {s.name:32s} SKIPPED: all {len(cal_preds)} calibration calls failed: {cal_preds[0].error[:160]}")
                continue
            thr = best_f1_threshold(y_c, pd.Series([p.prob for p in cal_preds]).to_numpy())
            AUDIT.context = {"iteration": it, "split": "eval", "threshold": thr}
            t_ev = time.perf_counter()
            ev_preds = s.predict(ev)
            t_end = time.perf_counter()
            m = summarize(y_e, ev_preds, thr)
            m.update(iteration=it, system=s.name, eval_wall_s=round(t_end - t_ev, 2),
                     total_wall_s=round(t_end - t_sys + getattr(s, "train_seconds", 0.0), 2),
                     throughput_per_s=round(len(ev) / max(t_end - t_ev, 1e-9), 2))
            if hasattr(s, "train_seconds"):
                m["train_seconds"] = round(s.train_seconds, 2)
            first_err = next((p.error for p in ev_preds if p.error), None)
            if first_err:
                m["first_error"] = first_err
            rows.append(m)
            print(f"  {s.name:32s} P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f} "
                  f"PR-AUC={m['pr_auc']:.3f} p50={m['latency_p50_s']*1000:.0f}ms "
                  f"cost/1k=${m['cost_per_1k_usd']:.4f} eval_time={m['eval_wall_s']}s err={m['errors']}")

    res = pd.DataFrame(rows)
    res.to_csv(out / "iterations.csv", index=False)
    (out / "iterations.json").write_text(json.dumps(rows, indent=2))
    summary = (
        res.assign(family=res.system.str.replace(r"_v\d+$", "", regex=True))
        .groupby("family")[["precision", "recall", "f1", "pr_auc", "latency_p50_s", "cost_per_1k_usd"]]
        .mean().round(4)
    )
    summary.to_csv(out / "summary_by_system.csv")
    print("\nMean across iterations:\n", summary.to_string())
    AUDIT.close()
    from .analysis import executive_summary
    exec_md = executive_summary(rows, time.perf_counter() - t_run, args.n_eval, args.data)
    write_markdown(out / "results.md", vars(args), rows, summary.to_markdown(), exec_md)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
