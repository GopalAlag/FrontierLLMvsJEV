"""Long shared system prompt (guidance + labelled few-shot examples) so every provider's prompt
cache engages. Examples come only from the training split, never from calibration/eval rows."""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from .data import to_text
from .llm_module import _BASE, _GUIDE


def build_fewshot_prompt(train: pd.DataFrame, seed: int, n_fraud: int = 14, n_legit: int = 28) -> str:
    rng = np.random.default_rng(seed)
    f = train[train.is_fraud == 1]
    l = train[train.is_fraud == 0]
    ex = pd.concat([f.iloc[rng.choice(len(f), n_fraud, replace=False)],
                    l.iloc[rng.choice(len(l), n_legit, replace=False)]])
    ex = ex.iloc[rng.permutation(len(ex))]
    parts = [_BASE, _GUIDE, "\nLabelled reference examples from historical data "
             "(fraud is over-represented here; do not copy these proportions):\n"]
    for i, r in enumerate(ex.itertuples(index=False), 1):
        verdict = "fraud (probability about 0.90)" if r.is_fraud else "legit (probability about 0.03)"
        parts.append(f"### Example {i}\n{to_text(r)}\nVerdict: {verdict}\n")
    parts.append("Now classify the next transaction the user sends, using the guidance and examples above.")
    return "\n".join(parts)


def prompt_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def prompt_ref(text: str) -> str:
    h = prompt_hash(text)
    return f"[system prompt sha256:{h}, {len(text)} chars (~{len(text) // 4} tokens); full text in system_prompts/{h}.txt]"
