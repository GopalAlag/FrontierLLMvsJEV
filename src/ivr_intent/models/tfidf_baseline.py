"""Classic ML baseline: TF-IDF + logistic regression on the rank-1 ASR text. No API cost."""
from __future__ import annotations

import time

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from ..data import parse_call
from ..metrics import Prediction


class TfidfBaseline:
    name = "classic_tfidf_lr"

    def __init__(self, seed: int = 0):
        self.pipe = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True),
                                  LogisticRegression(max_iter=1000, C=10, random_state=seed))
        self.train_seconds = 0.0

    @staticmethod
    def _texts(df: pd.DataFrame) -> list[str]:
        return [" ".join(parse_call(x).nbest[:1]) for x in df["xml"]]

    def fit(self, train: pd.DataFrame) -> "TfidfBaseline":
        t0 = time.perf_counter()
        self.pipe.fit(self._texts(train), train["intent"])
        self.train_seconds = time.perf_counter() - t0
        return self

    def predict(self, df: pd.DataFrame) -> list[Prediction]:
        t0 = time.perf_counter()
        proba = self.pipe.predict_proba(self._texts(df))
        dt = (time.perf_counter() - t0) / len(df)    # amortised batch latency, not a per-request round trip
        classes = self.pipe.classes_
        return [Prediction(intent=str(classes[i]), confidence=float(row[i]), latency_s=dt)
                for row, i in zip(proba, np.argmax(proba, axis=1))]
