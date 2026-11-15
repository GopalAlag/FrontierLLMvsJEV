"""Complete post-run summary from a finished results folder: run design, calls/tokens/cost per system, and a per-intent breakdown.

  python -m ivr_intent.summary results_ivr_final

Reads audit.jsonl (every API call), run_manifest.json, iterations.csv and data/*.jsonl. TF-IDF makes no API calls, so its
predictions are rebuilt deterministically (same seed, same train/calibration/eval files, same threshold rule).
Writes complete_summary.md, summary_by_intent.csv, summary_by_system_iteration.csv, calls_per_intent_uniformity.csv.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

from .data import read_jsonl
from .intents import BY_NAME, NAMES
from .metrics import best_threshold
from .models.tfidf_baseline import TfidfBaseline
from .router import expected, route


def _family(s: str) -> str:
    return re.sub(r"_v\d+$", "", s)


def load_calls(root: Path) -> pd.DataFrame:
    rows = []
    for line in (root / "audit.jsonl").read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        u = e.get("usage") or {}
        rows.append(dict(iteration=e.get("iteration"), split=e.get("split"), system=e["system"], provider=e["provider"],
                         y_true=e["y_true"], pred=e.get("result_intent"), conf=e.get("result_prob"), thr=e.get("threshold"),
                         xml=e["input_text"], error=e.get("error"), latency_s=e.get("latency_s", 0.0), cost=e.get("cost_usd", 0.0),
                         in_tok=u.get("input_tokens", 0), out_tok=u.get("output_tokens", 0),
                         cache_read=u.get("cache_read_input_tokens", 0), cache_write=u.get("cache_creation_input_tokens", 0)))
    return pd.DataFrame(rows)


def tfidf_calls(root: Path, iterations: list[int], base_seed: int) -> pd.DataFrame:
    out = []
    for it in iterations:
        tr, ca, ev = (read_jsonl(root / "data" / f"iter{it}_{n}.jsonl") for n in ("train", "calib", "eval"))
        m = TfidfBaseline(base_seed + it).fit(tr)
        thr = best_threshold(ca.intent.tolist(), m.predict(ca), ca.xml.tolist())
        for r, p in zip(ev.itertuples(index=False), m.predict(ev)):
            out.append(dict(iteration=it, split="eval", system=f"classic_tfidf_lr_v{it}", provider="local", y_true=r.intent, pred=p.intent,
                            conf=p.confidence, thr=thr, xml=r.xml, error=None, latency_s=p.latency_s, cost=0.0,
                            in_tok=0, out_tok=0, cache_read=0, cache_write=0))
    return pd.DataFrame(out)


def score(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["family"] = df.system.map(_family)
    df["exact"] = (df.pred == df.y_true) & df.error.isna()
    ok = []
    for r in df.itertuples(index=False):
        d = route(r.pred or "", float(r.conf or 0.0), float(r.thr or 0.0), r.xml, r.error)
        ok.append((d.action, d.workflow) == expected(r.y_true))
    df["handled"] = ok
    return df


def build(root: Path) -> None:
    man = json.loads((root / "run_manifest.json").read_text(encoding="utf-8"))
    its = sorted(i["iteration"] for i in man["iterations"])
    calls = load_calls(root)
    ev_llm = calls[calls.split == "eval"]
    ev = score(pd.concat([ev_llm, tfidf_calls(root, its, man["args"]["seed"])], ignore_index=True))
    fams = list(dict.fromkeys(ev.family))                        # run order, cheapest API system first
    order = ["classic_tfidf_lr"] + [f for f in fams if f != "classic_tfidf_lr"]
    short = {f: f.replace("-explicit", "").replace("_explicit", "").replace("gemini-3.1-flash-lite", "gemini-flash-lite") for f in order}

    # ---- per-intent table (eval calls; identical for every system by construction) ----
    n_by = ev.groupby(["y_true", "family", "iteration"]).size().unstack(["family", "iteration"], fill_value=0)
    per_intent = pd.DataFrame(index=NAMES)
    per_intent["workflow"] = [BY_NAME[n].workflow for n in NAMES]
    ref = order[1]
    for it in its:
        per_intent[f"eval_calls_iter{it}"] = [int(n_by[(ref, it)].get(n, 0)) if (ref, it) in n_by else 0 for n in NAMES]
    per_intent["eval_calls_total"] = per_intent[[f"eval_calls_iter{i}" for i in its]].sum(axis=1)
    uniform = []
    for n in NAMES:
        counts = {f: int(sum(n_by[(f, it)].get(n, 0) for it in its)) for f in order}
        uniform.append(len(set(counts.values())) == 1)
    per_intent["identical_calls_for_all_systems"] = uniform
    g_exact = ev.groupby(["y_true", "family"]).exact.mean().unstack("family")
    g_hand = ev.groupby(["y_true", "family"]).handled.mean().unstack("family")
    for f in order:
        per_intent[f"exact_acc__{short[f]}"] = g_exact[f].reindex(NAMES)
    llm = [f for f in order if f != "classic_tfidf_lr"]
    per_intent["exact_acc__mean_5_api_systems"] = per_intent[[f"exact_acc__{short[f]}" for f in llm]].mean(axis=1)
    for f in order:
        per_intent[f"handled__{short[f]}"] = g_hand[f].reindex(NAMES)
    per_intent.index.name = "intent"
    per_intent.round(3).to_csv(root / "summary_by_intent.csv")

    # ---- per system x iteration ----
    tot = calls.assign(family=calls.system.map(_family))
    sysit = []
    for (system, it), g in tot.groupby(["system", "iteration"], sort=False):
        e = g[g.split == "eval"]
        sysit.append(dict(system=system, iteration=int(it), calibration_calls=int((g.split == "calibration").sum()), eval_calls=len(e),
                          errors=int(g.error.notna().sum()), input_tokens=int(g.in_tok.sum() + g.cache_read.sum() + g.cache_write.sum()),
                          cache_read_tokens=int(g.cache_read.sum()), cache_write_tokens=int(g.cache_write.sum()), output_tokens=int(g.out_tok.sum()),
                          cost_usd=round(g.cost.sum(), 5), eval_latency_p50_s=round(e.latency_s.median(), 3),
                          eval_latency_p95_s=round(e.latency_s.quantile(0.95), 3)))
    sysit = pd.DataFrame(sysit)
    sysit.to_csv(root / "summary_by_system_iteration.csv", index=False)

    # headline table: metrics plus how many calls / which intents each system was tested on
    fam = fam_df = pd.read_csv(root / "summary_by_system.csv").set_index("family")
    tot_f = tot.groupby("family")
    head = pd.DataFrame(index=[f for f in order])
    head["api_calls_total"] = [int(len(tot_f.get_group(f))) if f in tot_f.groups else 0 for f in order]
    head["calibration_calls"] = [int((tot_f.get_group(f).split == "calibration").sum()) if f in tot_f.groups else 0 for f in order]
    head["eval_calls_scored"] = [int((ev.family == f).sum()) for f in order]
    head["iterations"] = len(its)
    head["intents_tested"] = [int(ev[ev.family == f].y_true.nunique()) for f in order]
    head["calls_per_intent"] = [round((ev.family == f).sum() / max(ev[ev.family == f].y_true.nunique(), 1), 2) for f in order]
    head["workflows_covered"] = [int(ev[ev.family == f].y_true.map(lambda n: BY_NAME[n].workflow).nunique()) for f in order]
    for c in ["accuracy", "macro_f1", "handled_correctly", "automation_rate", "misroute_rate", "latency_p50_s", "latency_p95_s", "cost_per_1k_usd", "total_cost_usd"]:
        head[c] = fam[c].reindex(order).values
    head.loc["classic_tfidf_lr", "api_calls_total"] = 0     # local model: predictions only, no API calls
    head.loc["classic_tfidf_lr", "calibration_calls"] = len(its) * man["args"]["n_calib"]   # scored on the same calibration inputs
    head.index.name = "system"
    head.round(4).to_csv(root / "summary_by_system_with_calls.csv")
    headline_md = head.round(3).reset_index().to_markdown(index=False)

    cnt = per_intent[[f"eval_calls_iter{i}" for i in its] + ["eval_calls_total", "identical_calls_for_all_systems"]]
    cnt.to_csv(root / "calls_per_intent_uniformity.csv")

    # ---- markdown ----
    it_df = pd.read_csv(root / "iterations.csv")
    fam_df = pd.read_csv(root / "summary_by_system.csv")
    a = man["args"]
    L = ["# IVR intent comparison: complete run summary", "",
         f"Run `{man['started']}` to `{man['finished']}`, runtime {man['runtime_s']} s, status **{man['status']}**. "
         f"Measured API spend **${man['measured_spend_usd']:.4f}** of a ${man['hard_cap_usd']:.2f} hard cap (user limit $3). "
         f"{man['api_calls']} API calls in total.", "",
         "## 1. Run design", "",
         f"- Iterations: **{a['iterations']}** (iteration 1 = v1 prompts, iteration 2 = v2 prompts; JEV: Choice question v1 -> v2). Base seed {a['seed']}, iteration seed = base + iteration.",
         f"- Per iteration and per system: **{a['n_calib']} calibration calls** (threshold selection only) + **{a['n_eval']} eval calls** (scored) = {a['n_calib'] + a['n_eval']} calls; "
         f"**{a['iterations'] * (a['n_calib'] + a['n_eval'])} calls per API system** in total, {a['iterations'] * a['n_eval']} of them scored.",
         f"- Systems: TF-IDF baseline (no API) + 5 API systems, run cheapest-first: {', '.join(short[f] for f in llm)}. Cache mode: {a['cache_mode']} (JEV exposes no cache controls).",
         f"- Intent catalog: **{len(NAMES)} intents** -> {len({i.workflow for i in BY_NAME.values()})} workflows (some near-synonym intents share a workflow). Train seeds are never used in eval (per-intent seed split).",
         "- Apples to apples: every system received the identical calibration and eval calls each iteration (same XML, same expected intent), the same catalog, workflow map, threshold rule and scoring.", ""]
    L += ["| iteration | seed | calibration calls | eval calls | intents appearing in eval | calibration set hash | eval set hash |", "|---|---|---|---|---|---|---|"]
    for i in man["iterations"]:
        L.append(f"| {i['iteration']} | {i['seed']} | {i['n_calib']} | {i['n_eval']} | {i['eval_intents']} | {i['calib_sha']} | {i['eval_sha']} |")
    L += ["", "## 2. Calls, tokens and cost per system and iteration", "", sysit.to_markdown(index=False), "",
          "Totals per system:", "",
          sysit.assign(system=sysit.system.map(_family)).groupby("system", sort=False).agg(
              calibration_calls=("calibration_calls", "sum"), eval_calls=("eval_calls", "sum"), errors=("errors", "sum"),
              input_tokens=("input_tokens", "sum"), cache_read_tokens=("cache_read_tokens", "sum"), cache_write_tokens=("cache_write_tokens", "sum"),
              output_tokens=("output_tokens", "sum"), cost_usd=("cost_usd", "sum")).round(5).reset_index().to_markdown(index=False), "",
          "## 3. System-level metrics (mean of the 2 iterations)", "",
          "Headline table: calls per system, intents tested and the main metrics. `api_calls_total` = calibration + eval calls actually sent to the "
          "provider (TF-IDF is local, 0 API calls but scored on the same calibration and eval inputs). `calls_per_intent` = scored eval calls / intents tested.", "",
          headline_md, "",
          fam_df[["family", "accuracy", "macro_f1", "handled_correctly", "automation_rate", "auto_precision", "misroute_rate", "errors"]].round(3).to_markdown(index=False), "",
          fam_df[["family", "latency_p50_s", "latency_p95_s", "throughput_per_s", "cost_per_1k_usd", "cost_per_correct_call_usd", "total_cost_usd", "cached_input_share"]].round(5).to_markdown(index=False), "",
          "Per iteration:", "",
          it_df[["iteration", "system", "threshold", "accuracy", "macro_f1", "handled_correctly", "automation_rate", "misroute_rate", "latency_p50_s", "cost_per_1k_usd", "errors"]].round(3).to_markdown(index=False), "",
          "## 4. Which intents ran, and was it uniform?", ""]
    covered = per_intent[per_intent.eval_calls_total > 0]
    nz = covered.eval_calls_total
    L += [f"- Intents with at least one eval call: **{len(covered)} of {len(NAMES)}** "
          f"(per iteration: {', '.join(str(int(i['eval_intents'])) for i in man['iterations'])}). Calls per covered intent over both iterations: min {int(nz.min())}, median {int(nz.median())}, max {int(nz.max())}, total {int(nz.sum())}.",
          f"- Uniformity check: for **{int(per_intent[per_intent.eval_calls_total > 0].identical_calls_for_all_systems.sum())} of {len(covered)}** covered intents every system (including TF-IDF) was scored on exactly the same number of calls: "
          f"{'YES, all systems ran the same calls' if per_intent[per_intent.eval_calls_total > 0].identical_calls_for_all_systems.all() else 'NO - see the column identical_calls_for_all_systems'}.",
          f"- Not sampled in either eval set ({int((per_intent.eval_calls_total == 0).sum())}): {', '.join(per_intent.index[per_intent.eval_calls_total == 0]) or 'none'}.",
          ("- Sampling was stratified: every intent got exactly the same number of eval calls." if nz.min() == nz.max() else
           "- Sampling picked intents at random, so calls per intent vary (min %d, max %d)." % (nz.min(), nz.max())), ""]
    hist = covered.eval_calls_total.value_counts().sort_index()
    L += ["Calls-per-intent distribution (eval calls over both iterations -> number of intents):", "",
          "| calls for the intent | " + " | ".join(str(int(k)) for k in hist.index) + " |", "|---|" + "---|" * len(hist),
          "| intents | " + " | ".join(str(int(v)) for v in hist.values) + " |", ""]

    L += ["## 5. Per-intent results (exact-intent accuracy, eval calls)", "",
          "Columns: calls per iteration and total (same for every system), then exact-intent accuracy per system (share of that intent's calls where "
          "the predicted intent equals the expected one). `mean5` = mean of the five API systems. Intents never sampled are omitted.", ""]
    cols = ["workflow"] + [f"eval_calls_iter{i}" for i in its] + ["eval_calls_total"] + [f"exact_acc__{short[f]}" for f in order] + ["exact_acc__mean_5_api_systems"]
    t = covered[cols].copy()
    t.columns = ["workflow"] + [f"calls it{i}" for i in its] + ["calls total"] + [short[f] for f in order] + ["mean5"]
    pct = lambda s: s.map(lambda v: "" if pd.isna(v) else f"{v * 100:.0f}%")
    for c in t.columns[len(its) + 2:]:
        t[c] = pct(t[c])
    L += [t.reset_index().to_markdown(index=False), ""]
    L += ["## 6. Per-intent handled-correctly (right workflow / agent transfer at the tuned threshold)", ""]
    h = covered[[f"handled__{short[f]}" for f in order]].copy()
    h.columns = [short[f] for f in order]
    h.insert(0, "calls total", covered.eval_calls_total)
    for c in h.columns[1:]:
        h[c] = pct(h[c])
    L += [h.reset_index().to_markdown(index=False), ""]

    ranked = covered.sort_values("exact_acc__mean_5_api_systems")
    big = ranked[ranked.eval_calls_total >= 3]
    L += ["## 7. Hardest and easiest intents (intents with at least 3 calls)", "",
          "Hardest 12 by mean exact accuracy of the 5 API systems:", "",
          big.head(12)[["eval_calls_total", "exact_acc__mean_5_api_systems", "exact_acc__classic_tfidf_lr"]].round(2).reset_index().to_markdown(index=False), "",
          "Easiest 8:", "",
          big.tail(8)[["eval_calls_total", "exact_acc__mean_5_api_systems", "exact_acc__classic_tfidf_lr"]].round(2).reset_index().to_markdown(index=False), ""]

    conf = ev[~ev.exact & ev.error.isna()].groupby(["family", "y_true", "pred"]).size().reset_index(name="count").sort_values(["family", "count"], ascending=[True, False])
    L += ["## 8. Most common confusions per system (expected -> predicted, both iterations)", "",
          conf.groupby("family").head(6).to_markdown(index=False), "",
          "## 9. Files", "",
          "- `summary_by_intent.csv` (every column above for all 114 intents), `summary_by_system_iteration.csv`, `calls_per_intent_uniformity.csv`",
          "- `results.md` (the run's own report), `run.log`, `events.jsonl`, `run_manifest.json`, `audit.jsonl`, `iterations.csv`, `data/*.jsonl`", ""]
    (root / "complete_summary.md").write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {root / 'complete_summary.md'}")
    print(f"  intents covered {len(covered)}/{len(NAMES)}; uniform across systems: {per_intent[per_intent.eval_calls_total > 0].identical_calls_for_all_systems.all()}")


if __name__ == "__main__":
    build(Path(sys.argv[1] if len(sys.argv) > 1 else "results_ivr_final"))
