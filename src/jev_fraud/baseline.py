"""Classical ML baseline: gradient boosting on the same features the other systems see."""
from __future__ import annotations

import time

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

from .data import CATEGORICAL, NUMERIC
from .metrics import Prediction


def build_model(seed: int) -> Pipeline:
    pre = ColumnTransformer(
        [("cat", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1), CATEGORICAL)],
        remainder="passthrough",
    )
    cat_mask = [True] * len(CATEGORICAL) + [False] * len(NUMERIC)
    clf = HistGradientBoostingClassifier(
        categorical_features=cat_mask, max_iter=200, learning_rate=0.1, random_state=seed
    )
    return Pipeline([("pre", pre), ("clf", clf)])


class Baseline:
    name = "classic_gbm"

    def __init__(self, seed: int):
        self.model = build_model(seed)
        self.train_seconds = 0.0

    def fit(self, train: pd.DataFrame) -> "Baseline":
        t0 = time.perf_counter()
        self.model.fit(train[CATEGORICAL + NUMERIC], train["is_fraud"])
        self.train_seconds = time.perf_counter() - t0
        return self

    def predict(self, df: pd.DataFrame) -> list[Prediction]:
        X = df[CATEGORICAL + NUMERIC]
        t0 = time.perf_counter()
        p = self.model.predict_proba(X)[:, 1]
        per_row = (time.perf_counter() - t0) / len(df)
        return [Prediction(prob=float(x), latency_s=per_row) for x in np.asarray(p)]
