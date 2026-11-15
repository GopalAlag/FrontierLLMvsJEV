import numpy as np
import pandas as pd

from jev_fraud.data import make_splits, to_text
from jev_fraud.metrics import Prediction, best_f1_threshold, summarize


def _df(n=2000):
    rng = np.random.default_rng(0)
    return pd.DataFrame({"is_fraud": (rng.random(n) < 0.05).astype(int), "amt": rng.random(n) * 100})


def test_splits_are_disjoint_and_enriched():
    df = _df()
    train, ev = make_splits(df, seed=1, n_train=400, n_eval=100, eval_fraud_rate=0.2)
    assert len(ev) == 100 and ev.is_fraud.sum() == 20
    assert len(train) == 400


def test_to_text_has_no_pii_fields():
    row = pd.Series(dict(amt=12.5, merchant="Acme", category="misc_net", weekday=2, hour=23,
                         gender="F", age=40, job="Nurse", city="Austin", state="TX",
                         city_pop=1000, dist_km=12.3, first="Jane", last="Doe", cc_num=1))
    t = to_text(row)
    assert "Jane" not in t and "Doe" not in t and "$12.50" in t and "23:00" in t


def test_summarize_cost_and_errors():
    y = np.array([1, 0, 1, 0])
    preds = [Prediction(0.9, cost_usd=0.001), Prediction(0.1, cost_usd=0.001),
             Prediction(0.0, error="boom"), Prediction(0.2, cost_usd=0.001)]
    m = summarize(y, preds, 0.5)
    assert m["errors"] == 1 and abs(m["total_cost_usd"] - 0.003) < 1e-9
    assert best_f1_threshold(np.array([1, 0]), np.array([0.9, 0.1])) <= 0.9
