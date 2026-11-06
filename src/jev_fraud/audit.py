"""Audit trail: every external API call is recorded (request, response, result, usage, cost).

Raw, full-fidelity records go to audit.jsonl as they happen; results.md is rendered from them.
API keys / auth headers are never part of a record (only request bodies and parsed responses).
"""
from __future__ import annotations

import json
import threading
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


class AuditLog:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.context: dict = {}
        self.entries: list[dict] = []
        self._fh = None
        self._seq = 0
        self.trace = False

    def open(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = path.open("w", encoding="utf-8")

    def record(self, **entry) -> None:
        with self._lock:
            self._seq += 1
            e = {"seq": self._seq, "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                 **self.context, **entry}
            self.entries.append(e)
            if self.trace:
                print(trace_line(e), flush=True)
            if self._fh:
                self._fh.write(json.dumps(e, default=str) + "\n")
                self._fh.flush()

    def close(self) -> None:
        if self._fh:
            self._fh.close()


def trace_line(e: dict) -> str:
    sc = e.get("source", {})
    head = (f"[{e['seq']:>5}] it{e.get('iteration')} {e.get('split', ''):<11} {e['system']:<22} "
            f"{sc.get('project_source')} -> {sc.get('library_api')}")
    if e.get("error"):
        return f"{head} | true={e.get('y_true')} ERROR {e['error'][:100]}"
    u = e.get("usage", {})
    return (f"{head} | true={e.get('y_true')} p={e['result_prob']:.3f} "
            f"{e['latency_s'] * 1000:.0f}ms tok={u.get('input_tokens')}/{u.get('output_tokens')} "
            f"cache_r={u.get('cache_read_input_tokens', 0)} ${e['cost_usd']:.6f} req={e.get('request_id')}")


AUDIT = AuditLog()

_ROOT = Path(__file__).resolve().parents[2]


def _rel(p: str | None) -> str:
    if not p:
        return "?"
    try:
        return str(Path(p).resolve().relative_to(_ROOT)).replace("\\", "/")
    except ValueError:
        parts = Path(p).parts
        return "/".join(parts[parts.index("site-packages") + 1:]) if "site-packages" in parts else p


def callsite(api_func) -> dict:
    """Call right before an API invocation. Records the project line that is about to call
    `api_func` and the exact library file/line where that function is defined."""
    import inspect

    f = inspect.currentframe().f_back
    try:
        lib_file = inspect.getsourcefile(api_func)
        lib_line = inspect.getsourcelines(api_func)[1]
    except (TypeError, OSError):
        lib_file, lib_line = None, 0
    return {
        "project_source": f"{_rel(f.f_code.co_filename)}:{f.f_lineno}",
        "project_function": f.f_code.co_qualname,
        "library_api": f"{api_func.__module__}.{api_func.__qualname__}",
        "library_source": f"{_rel(lib_file)}:{lib_line}",
    }


def _one_line(s: str) -> str:
    return s.replace("\n", " | ")


def write_markdown(path: Path, config: dict, rows: list[dict], summary_md: str, exec_md: str = "") -> None:
    L: list[str] = []
    L += ["# Results and audit trail", "",
          f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}", "",
          exec_md, "",
          "## Run configuration", "", "```json", json.dumps(config, indent=2), "```", "",
          "## Metrics per iteration", ""]
    cols = ["iteration", "system", "n", "errors", "threshold", "precision", "recall", "f1", "pr_auc",
            "latency_p50_s", "latency_p95_s", "input_tokens", "output_tokens", "cache_read_tokens",
            "eval_wall_s", "total_wall_s", "total_cost_usd", "cost_per_1k_usd"]
    L += ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        L.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
    L += ["", "## Mean across iterations", "", summary_md, "",
          "## Source code map", "",
          "Which code produced each set of API calls (project files are the code in this repo; "
          "library files are where the HTTP request is actually built and sent).", "",
          "| System | Project source (called at) | Library API invoked | Library source |",
          "|---|---|---|---|"]
    seen = {}
    for e in AUDIT.entries:
        sc = e.get("source", {})
        seen.setdefault(e["system"].rsplit("_v", 1)[0], sc)
    for sysname, sc in seen.items():
        L.append(f"| {sysname} | **`{sc.get('project_source')}`** | `{sc.get('library_api')}` | `{sc.get('library_source')}` |")
    L += ["", "Also executed (no external API): `src/jev_fraud/baseline.py` (classic GBM), "
          "`src/jev_fraud/data.py` / `synthetic.py` (data), `src/jev_fraud/metrics.py` (scoring), "
          "`src/jev_fraud/run_experiment.py` (orchestration).", "",
          "## Audit trail", "",
          f"{len(AUDIT.entries)} external API calls. Each entry shows the request sent, the raw response "
          "received, and the result used for scoring. Full-fidelity records: `audit.jsonl`.", ""]

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for e in AUDIT.entries:
        groups[(e.get("iteration"), e.get("system"), e.get("split"))].append(e)

    for (it, system, split), es in groups.items():
        errs = sum(1 for e in es if e.get("error"))
        cost = sum(e.get("cost_usd", 0) for e in es)
        L += [f"### Iteration {it} | {system} | {split}", "",
              f"{len(es)} calls, {errs} errors, ${cost:.4f} total", "",
              "| # | Source code invoked | True label | Input transaction | P(fraud) | Verdict | Reason / detail | Tokens in/out (cache read) | Latency | Cost |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for e in es:
            truth = "FRAUD" if e.get("y_true") == 1 else "legit"
            text = _one_line(e.get("input_text", "")).replace("|", "/")
            sc = e.get("source", {})
            src = f"**`{sc.get('project_source')}`** -> `{sc.get('library_api')}`"
            if e.get("error"):
                L.append(f"| {e['seq']} | {src} | {truth} | {text} | - | ERROR | {e['error'][:120]} | - | - | - |")
                continue
            thr = e.get("threshold")
            pred = ""
            if thr is not None:
                pred = "FRAUD" if e["result_prob"] >= thr else "legit"
                pred += " (correct)" if pred == ("FRAUD" if e["y_true"] == 1 else "legit") else " (WRONG)"
            resp = e["response"]
            po = resp.get("parsed_output")
            detail = (f"{po['label']}: {po['reason']}" if po else
                      "; ".join(f"{k}={v.get('noul', v.get('choice'))}" for k, v in resp["answers"].items()))
            u = e["usage"]
            L.append(f"| {e['seq']} | {src} | {truth} | {text} | {e['result_prob']:.3f} | {pred or 'n/a (calibration)'} | "
                     f"{detail.replace('|', '/')} | {u['input_tokens']}/{u['output_tokens']}"
                     f" ({u.get('cache_read_input_tokens', 0)}) | {e['latency_s'] * 1000:.0f}ms | ${e['cost_usd']:.6f} |")
        L.append("")
        if split == "eval":
            L += [f"<details><summary>Raw request / response for every {system} eval call (iteration {it})</summary>", ""]
            for e in es:
                L += [f"**Call #{e['seq']}** `{e['ts']}` provider={e['provider']} model={e['model']} "
                      f"request_id={e.get('request_id')} true_label={e.get('y_true')}", "",
                      f"> **Source code invoked:** `{e.get('source', {}).get('project_source')}` "
                      f"(`{e.get('source', {}).get('project_function')}`) calls "
                      f"`{e.get('source', {}).get('library_api')}` defined at "
                      f"`{e.get('source', {}).get('library_source')}`", "",
                      "Request:", "```json", json.dumps(e["request"], indent=2, default=str), "```"]
                if e.get("error"):
                    L += ["Error:", "```", e["error"], "```", ""]
                else:
                    L += ["Response:", "```json", json.dumps(e["response"], indent=2, default=str), "```",
                          f"Result used for scoring: fraud_probability = {e['result_prob']:.4f}, "
                          f"usage = {json.dumps(e['usage'])}", ""]
            L += ["</details>", ""]
        else:
            L += ["Raw request/response for calibration calls are in `audit.jsonl`.", ""]
    path.write_text(chr(10).join(L), encoding="utf-8")
