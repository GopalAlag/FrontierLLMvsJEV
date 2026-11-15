"""JEV (Typesafe System One) classifier. Separate module from the LLM path by design."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from langchain_typesafe import Choice, Noul, TypeSafeClassifier

from .audit import AUDIT, callsite
from .data import to_text
from .metrics import Prediction

# Published list price: $0.042 / MTok input, output free (typesafe.ai launch post, vendor claim).
JEV_INPUT_USD_PER_MTOK = 0.042
JEV_OUTPUT_USD_PER_MTOK = 0.0

# Prompt variants = the "iterations" for JEV. v1 is a bare question; v2 adds domain cues.
QUESTIONS = {
    "v1": {
        "is_fraud": Noul(instructions="Is this credit card transaction fraudulent?"),
    },
    "v2": {
        "is_fraud": Noul(
            instructions=(
                "Is this credit card transaction fraudulent? Fraud is rare (well under 1% of "
                "real traffic). Strong signals: online/shopping_net/misc_net/grocery_pos "
                "categories with large amounts, late-night hours (22:00-03:00), and unusually "
                "high amounts for the category. Normal small everyday purchases are legitimate."
            ),
        ),
    },
    "v3": {
        "is_fraud": Noul(
            instructions=(
                "Is this credit card transaction fraudulent? Fraud is rare in real traffic. "
                "Strong signals: online (shopping_net, misc_net) or point-of-sale grocery/gas "
                "purchases with large amounts, late-night hours (22:00-03:00), and amounts far "
                "above what is typical for the category."
            ),
            criteria={
                "true": "Amount is unusually high for the category and/or occurs late at night.",
                "false": "Ordinary-sized purchase at a normal hour for its category.",
            },
        ),
        "risk": Choice(
            instructions="Overall fraud risk level of this transaction?",
            criteria={"low": "Typical purchase", "medium": "Some unusual traits", "high": "Several strong fraud signals"},
        ),
    },
}


class JevClassifier:
    def __init__(self, variant: str = "v1", model: str = "jev-latest", workers: int = 8):
        self.variant = variant
        self.name = f"jev_{variant}"
        self.workers = workers
        self.clf = TypeSafeClassifier(model=model)
        self.questions = QUESTIONS[variant]

    def _one(self, text: str, y_true: int) -> Prediction:
        request = {
            "model": self.clf.model,
            "state": text,
            "questions": {k: q.model_dump(mode="json", exclude_none=True) for k, q in self.questions.items()},
        }
        base = dict(provider="typesafe", system=self.name, model=self.clf.model, request=request, input_text=text, y_true=y_true)
        base["source"] = callsite(TypeSafeClassifier.invoke)
        t0 = time.perf_counter()
        try:
            r = self.clf.invoke({"state": text, "questions": self.questions})
        except Exception as e:  # network/API errors are recorded, not fatal to the run
            dt = time.perf_counter() - t0
            AUDIT.record(**base, latency_s=dt, error=f"{type(e).__name__}: {e}", cost_usd=0.0)
            return Prediction(prob=0.0, latency_s=dt, error=f"{type(e).__name__}: {e}")
        dt = time.perf_counter() - t0
        it, ot = r.usage.input_tokens or 0, r.usage.output_tokens or 0
        cost = it * JEV_INPUT_USD_PER_MTOK / 1e6 + ot * JEV_OUTPUT_USD_PER_MTOK / 1e6
        prob = r.answers["is_fraud"].noul
        AUDIT.record(**base, latency_s=dt, response=r.model_dump(mode="json"), request_id=r.request_id,
                     result_prob=prob, usage={"input_tokens": it, "output_tokens": ot}, cost_usd=cost)
        return Prediction(prob=prob, latency_s=dt, input_tokens=it, output_tokens=ot, cost_usd=cost)

    def predict(self, df: pd.DataFrame) -> list[Prediction]:
        texts = [to_text(r) for r in df.itertuples(index=False)]
        ys = df["is_fraud"].tolist()
        with ThreadPoolExecutor(self.workers) as ex:
            return list(ex.map(self._one, texts, ys))
