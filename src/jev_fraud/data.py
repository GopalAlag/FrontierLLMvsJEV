"""Load the fraud CSV, engineer shared features, and render transactions as text."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RAW_CSV = Path(__file__).resolve().parents[2] / "data" / "raw" / "us.csv"

NUMERIC = ["amt", "hour", "weekday", "age", "dist_km", "city_pop"]
CATEGORICAL = ["category", "gender", "state"]

_USECOLS = [
    "trans_date_trans_time", "merchant", "category", "amt", "gender", "city", "state",
    "lat", "long", "city_pop", "job", "dob", "merch_lat", "merch_long", "is_fraud",
]


def _haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def load_frame(path: Path = RAW_CSV, nrows: int | None = None) -> pd.DataFrame:
    df = pd.read_csv(path, usecols=_USECOLS, nrows=nrows)
    ts = pd.to_datetime(df["trans_date_trans_time"])
    df["hour"] = ts.dt.hour
    df["weekday"] = ts.dt.dayofweek
    df["age"] = (ts - pd.to_datetime(df["dob"])).dt.days // 365
    df["dist_km"] = _haversine_km(df["lat"], df["long"], df["merch_lat"], df["merch_long"]).round(1)
    df["merchant"] = df["merchant"].str.removeprefix("fraud_")
    return df


def make_splits(df: pd.DataFrame, seed: int, n_train: int, n_eval: int, eval_fraud_rate: float):
    """Train set keeps the natural rate with fraud oversampled; eval set is fraud-enriched so
    precision/recall are measurable at small sizes. Disjoint by row."""
    rng = np.random.default_rng(seed)
    fraud_idx = df.index[df["is_fraud"] == 1].to_numpy()
    legit_idx = df.index[df["is_fraud"] == 0].to_numpy()
    n_eval_fraud = int(round(n_eval * eval_fraud_rate))
    ev_f = rng.choice(fraud_idx, n_eval_fraud, replace=False)
    ev_l = rng.choice(legit_idx, n_eval - n_eval_fraud, replace=False)
    eval_idx = np.concatenate([ev_f, ev_l])
    rng.shuffle(eval_idx)
    rest_f = np.setdiff1d(fraud_idx, ev_f)
    rest_l = np.setdiff1d(legit_idx, ev_l)
    tr_f = rng.choice(rest_f, min(len(rest_f), n_train // 4), replace=False)
    tr_l = rng.choice(rest_l, n_train - len(tr_f), replace=False)
    train_idx = np.concatenate([tr_f, tr_l])
    rng.shuffle(train_idx)
    return df.loc[train_idx].reset_index(drop=True), df.loc[eval_idx].reset_index(drop=True)


DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def to_text(row: pd.Series) -> str:
    """Identical information the classical model sees, plus merchant name/job/city. No PII
    (name, card number, street) is rendered."""
    return (
        f"Amount: ${row.amt:,.2f}\n"
        f"Merchant: {row.merchant} (category: {row.category})\n"
        f"Time: {DAYS[int(row.weekday)]} {int(row.hour):02d}:00\n"
        f"Cardholder: {row.gender}, age {int(row.age)}, job '{row.job}', "
        f"lives in {row.city}, {row.state} (city population {int(row.city_pop):,})\n"
        f"Distance between cardholder home and merchant: {row.dist_km:,.1f} km"
    )
