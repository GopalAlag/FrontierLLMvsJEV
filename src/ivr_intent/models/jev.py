"""JEV (Typesafe System One) IVR intent router: one Choice question over the intent catalog.

JEV returns a probability for every intent in a single call; the router uses the probability of the
selected intent as its confidence, which makes it directly comparable with the LLMs' verbalised confidence.
"""
from __future__ import annotations

from langchain_typesafe import Choice, TypeSafeClassifier

from jev_fraud.audit import callsite

from ..intents import INTENTS
from ._base import Raw, Router

# Published list price: $0.042 / MTok input, output free (typesafe.ai launch post, vendor claim).
JEV_INPUT_USD_PER_MTOK = 0.042
JEV_OUTPUT_USD_PER_MTOK = 0.0

_Q = ("The input is the XML speech-to-text result of a caller's utterance to a credit card customer-service IVR "
      "(N-best hypotheses with ASR confidences). Which intent does the caller want?")
_V2 = (" ASR is noisy: words may be dropped or replaced by homophones (car/card, do/due, a count/account); use all hypotheses and "
       "the meaning. Callers often say only a few words; prefer the specific intent when the words support it, otherwise the generic one.")


def question(variant: str) -> dict:
    if variant == "v1":
        crit = {i.name: i.description for i in INTENTS}
        return {"intent": Choice(instructions=_Q, criteria=crit)}
    crit = {i.name: (i.description + (f" {i.hint}" if i.hint else "")) for i in INTENTS}
    return {"intent": Choice(instructions=_Q + _V2, criteria=crit)}


class JevRouter(Router):
    provider = "typesafe"

    def __init__(self, variant: str = "v1", model: str = "jev-latest", workers: int = 8):
        self.variant, self.workers = variant, workers
        self.model = model
        super().__init__()
        self.name = f"jev_{variant}"
        self.clf = TypeSafeClassifier(model=model)
        self.questions = question("v1" if variant == "v1" else "v2")

    def _invoke(self, xml: str) -> Raw:
        request = {"model": self.clf.model, "state": xml,
                   "questions": {k: q.model_dump(mode="json", exclude_none=True) for k, q in self.questions.items()}}
        source = callsite(TypeSafeClassifier.invoke)
        r = self.clf.invoke({"state": xml, "questions": self.questions})
        a = r.answers["intent"]
        it, ot = r.usage.input_tokens or 0, r.usage.output_tokens or 0
        cost = it * JEV_INPUT_USD_PER_MTOK / 1e6 + ot * JEV_OUTPUT_USD_PER_MTOK / 1e6
        return Raw(intent=a.choice, confidence=a.probabilities.get(a.choice, 0.0), request=request, source=source,
                   response=r.model_dump(mode="json"), input_tokens=it, output_tokens=ot, cost_usd=cost,
                   request_id=r.request_id, extra_usage={"jev_confidence": a.confidence})
