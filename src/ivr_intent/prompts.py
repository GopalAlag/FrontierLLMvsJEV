"""System prompts for the generative-LLM routers (JEV builds its own Choice question instead)."""
from __future__ import annotations

import hashlib

import pandas as pd

from .data import parse_call
from .intents import INTENTS, catalog_text

_BASE = (
    "You are the intent router of a credit card customer-service IVR. The user message is the XML "
    "speech-to-text result for the caller's utterance (N-best hypotheses with ASR confidences). "
    "Pick exactly one intent name (spelled exactly as listed) from the list below, give a calibrated confidence in [0,1] that it is the "
    "caller's true intent, and a one-sentence reason. Output only the structured verdict.\n\n"
    "Intents:\n" + catalog_text()
)

_GUIDE = (
    "\n\nGuidance:\n"
    "- Speech recognition is noisy: words may be dropped, replaced by homophones (e.g. 'car' for 'card', 'do' for 'due', "
    "'a count' for 'account') or padded with fillers. Use all N-best hypotheses and the sentence meaning, not exact words.\n"
    "- Rank 1 is not always the best hypothesis; a lower-ranked one may be cleaner.\n"
    "- Callers often phrase requests indirectly ('I keep forgetting' -> setup_autopay). Infer the underlying need.\n"
    "- Disambiguation:\n" + "\n".join(f"  * {i.name}: {i.hint}" for i in INTENTS if i.hint) +
    "\n- Many callers say only a few words (e.g. 'account help', 'balance transfer status'); choose the closest intent, "
    "preferring the more specific one when the words support it and the generic one (AccountQuestion, BalanceQuestion, "
    "AmbiguousRewardsRequest) when they do not.\n"
    "- Confidence must reflect real uncertainty: use 0.9+ only when the intent is unambiguous; use 0.4-0.7 when two "
    "intents are plausible."
)

PROMPTS = {"v1": _BASE, "v2": _BASE + _GUIDE}


def build_fewshot_prompt(train: pd.DataFrame, seed: int, per_intent: int = 4) -> str:
    """v3: guidance + labelled training calls (train split only) so every provider's prompt cache engages."""
    parts = [PROMPTS["v2"], "\n\nLabelled examples (rank-1 ASR text -> intent):\n"]
    ex = pd.concat([g.sample(min(per_intent, len(g)), random_state=seed) for _, g in train.groupby("intent")])
    ex = ex.sample(frac=1, random_state=seed)
    for r in ex.itertuples(index=False):
        parts.append(f'"{parse_call(r.xml).text}" -> {r.intent}')
    parts.append("\nNow route the next call the user sends, using the intents, guidance and examples above.")
    return "\n".join(parts)


def prompt_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def prompt_ref(text: str) -> str:
    h = prompt_hash(text)
    return f"[system prompt sha256:{h}, {len(text)} chars (~{len(text) // 4} tokens); full text in system_prompts/{h}.txt]"
