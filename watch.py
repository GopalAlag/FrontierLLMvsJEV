"""Live terminal view of a running experiment: one line per API call plus a running cost footer.

Usage:  .venv\\Scripts\\python watch.py [results_dir] [--quiet]
  --quiet  print only a status line every 10 s instead of every call
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
from jev_fraud.audit import trace_line  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
quiet = "--quiet" in sys.argv
path = Path(args[0] if args else "results_real") / "audit.jsonl"
while not path.exists():
    print(f"waiting for {path} ...", flush=True)
    time.sleep(2)

calls = errors = 0
cost = 0.0
by_sys: dict[str, float] = {}
last_status = 0.0
with path.open(encoding="utf-8") as f:
    while True:
        line = f.readline()
        if not line or not line.endswith("\n"):
            if quiet and time.time() - last_status > 10:
                print(f"calls={calls} errors={errors} cost=${cost:.4f} " +
                      " ".join(f"{k}=${v:.3f}" for k, v in by_sys.items()), flush=True)
                last_status = time.time()
            time.sleep(0.3)
            if line:
                f.seek(f.tell() - len(line.encode()))
            continue
        e = json.loads(line)
        calls += 1
        errors += bool(e.get("error"))
        cost += e.get("cost_usd", 0.0)
        fam = e["system"].rsplit("_v", 1)[0]
        by_sys[fam] = by_sys.get(fam, 0.0) + e.get("cost_usd", 0.0)
        if not quiet:
            print(trace_line(e)[:260], flush=True)
            if calls % 50 == 0:
                print(f"--- {calls} calls | {errors} errors | ${cost:.4f} | " +
                      " ".join(f"{k}=${v:.3f}" for k, v in by_sys.items()), flush=True)
