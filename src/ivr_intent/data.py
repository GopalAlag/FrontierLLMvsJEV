"""IVR test data in JSONL (same record shape as the sample main_intent_full_genai_brands_full.jsonl).

Seed file: data/ivr_seed_dataset.jsonl = utterances transcribed from the sample screenshots plus authored extras
(metadata.label_basis: explicit | inferred | authored). Synthetic calls are generated from the seeds, then
written as JSONL; the ASR-style XML the models receive is carried in inputs.asr_xml.

Seeds are split per intent into train / calibration / eval seeds (~55/15/30%), so eval and calibration
utterances are phrasings the baseline and few-shot prompts never saw. Variation = filler words, ASR noise,
N-best hypotheses. No real customer data is involved.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = ROOT / "data" / "ivr_seed_dataset.jsonl"

_PRE = ["", "", "", "hi ", "yeah ", "um ", "uh yes ", "okay so ", "hello ", "i need to ask about this ", "yes "]
_SUF = ["", "", "", " please", " thanks", " uh", " i guess", " on my card", " on my card", " for my card", " on my card"]
_CONFUSE = {"balance": "ballance", "payment": "payments", "due": "do", "card": "car", "rewards": "rewords", "statement": "state meant",
            "activate": "active eight", "address": "a dress", "bill": "build", "charge": "charged", "credit": "created", "fee": "fee's",
            "mail": "male", "agent": "a gent", "points": "point", "travel": "trouble", "interest": "interests", "pay": "pate",
            "transfer": "transfers", "account": "a count", "lost": "lust", "limit": "lint", "close": "clothes", "block": "black"}
_FILLERS = ["uh", "um"]


def load_seeds(path: Path = SEED_PATH) -> pd.DataFrame:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            rows.append(dict(intent=d["expected"]["classified_intent"], utterance=d["inputs"]["customer_utterance"],
                             source=d["metadata"].get("source", ""), label_basis=d["metadata"].get("label_basis", "")))
    return pd.DataFrame(rows).drop_duplicates(["intent", "utterance"], ignore_index=True)


def split_seeds(seeds: pd.DataFrame, split_seed: int = 7) -> dict[str, pd.DataFrame]:
    """Per-intent seed split. Fixed split_seed => a seed never leaks between train/calib/eval across iterations."""
    rng = np.random.default_rng(split_seed)
    parts = defaultdict(list)
    for _, g in seeds.groupby("intent"):
        g = g.iloc[rng.permutation(len(g))]
        n = len(g)
        n_ev = min(max(2, round(0.30 * n)), n - 2)    # at least 2 eval phrasings per intent, and >= 1 calibration + 1 train seed
        n_ca = max(1, min(round(0.15 * n), n - n_ev - 1))
        parts["eval"].append(g.iloc[:n_ev])
        parts["calib"].append(g.iloc[n_ev:n_ev + n_ca])
        parts["train"].append(g.iloc[n_ev + n_ca:])
    return {k: pd.concat(v, ignore_index=True) for k, v in parts.items()}


def _asr_text(s: str) -> str:
    return "".join(c for c in s.lower() if c.isalnum() or c in " '$").strip()


def _noisy(text: str, rng: np.random.Generator, level: float) -> tuple[str, int]:
    out, edits = [], 0
    for w in text.split():
        r = rng.random()
        if w in _CONFUSE and r < 0.5 * level:
            out.append(_CONFUSE[w]); edits += 1
        elif r < 0.5 * level + 0.12 * level:
            edits += 1                      # dropped word
        else:
            out.append(w)
        if rng.random() < 0.12 * level:
            out.append(_FILLERS[rng.integers(2)]); edits += 1
    return (" ".join(out) or text), edits


def build_xml(call_id: str, hyps: list[tuple[str, float]], attempt: int = 1) -> str:
    lines = [f'<call id="{call_id}" channel="ivr" lang="en-US" lob="brands" ani="XXXXXX{call_id[-4:]}">',
             f'  <context prompt="main_menu: How can I help you with your credit card today?" authenticated="true" attempt="{attempt}"/>',
             f'  <asr engine="generic-stt" nbest="{len(hyps)}">']
    for r, (txt, conf) in enumerate(hyps, 1):
        lines.append(f'    <hypothesis rank="{r}" confidence="{conf:.2f}">{escape(txt)}</hypothesis>')
    lines += ["  </asr>", "</call>"]
    return "\n".join(lines)


@dataclass
class CallInfo:
    call_id: str
    text: str            # rank-1 hypothesis
    asr_conf: float
    nbest: list[str]


def parse_call(xml: str) -> CallInfo:
    root = ET.fromstring(xml)
    hyps = sorted(root.iter("hypothesis"), key=lambda h: int(h.get("rank", "99")))
    texts = [(h.text or "").strip() for h in hyps]
    return CallInfo(root.get("id", ""), texts[0] if texts else "", float(hyps[0].get("confidence", 0)) if hyps else 0.0, texts)


def generate(seed_df: pd.DataFrame, n: int, seed: int, id_base: int = 0, noise: bool = True, stratified: bool = False) -> pd.DataFrame:
    """n synthetic calls drawn from seed utterances.

    stratified=False: each call picks an intent uniformly at random (counts per intent vary).
    stratified=True: every intent gets exactly n // K calls (the n % K remainder goes to randomly chosen intents), in shuffled order.
    """
    rng = np.random.default_rng(seed)
    by_intent = {k: g.reset_index(drop=True) for k, g in seed_df.groupby("intent")}
    names = sorted(by_intent)
    if stratified:
        plan = [k for k in names for _ in range(n // len(names))]
        plan += [names[i] for i in rng.choice(len(names), n % len(names), replace=False)]
        plan = [plan[i] for i in rng.permutation(len(plan))]
    rows = []
    for j in range(n):
        intent = plan[j] if stratified else names[rng.integers(len(names))]
        g = by_intent[intent]
        s = g.iloc[rng.integers(len(g))]
        clean = _PRE[rng.integers(len(_PRE))] + _asr_text(s.utterance) + _SUF[rng.integers(len(_SUF))]
        level = float(rng.choice([0.0, 0.5, 1.0, 1.6], p=[0.30, 0.35, 0.25, 0.10])) if noise else 0.0
        h1, e1 = _noisy(clean, rng, level)
        alts = [_noisy(clean, rng, level + 0.8) for _ in range(2)]
        c1 = float(np.clip(0.96 - 0.10 * e1 + rng.normal(0, 0.03), 0.30, 0.99))
        alt_h = sorted(((a, float(np.clip(c1 - 0.12 - 0.10 * (r + e), 0.05, 0.9))) for r, (a, e) in enumerate(alts)), key=lambda x: -x[1])
        hyps = [(h1, c1)] + alt_h
        if rng.random() < 0.08 and e1 > 0:    # mis-ordered N-best: clean text only appears as rank 2
            hyps[0], hyps[1] = (clean, hyps[1][1]), hyps[0]
        cid = f"{id_base + j:08d}"
        rows.append(dict(call_id=cid, intent=intent, seed_utterance=s.utterance, seed_source=s.source,
                         label_basis=s.label_basis, xml=build_xml(cid, hyps)))
    return pd.DataFrame(rows)


def make_splits(seed: int, n_train: int, n_calib: int, n_eval: int, seeds: pd.DataFrame | None = None, stratified_eval: bool = False):
    parts = split_seeds(load_seeds() if seeds is None else seeds)
    train = generate(parts["train"], n_train, seed, 0)
    calib = generate(parts["calib"], n_calib, seed + 10_000, 10_000_000)
    ev = generate(parts["eval"], n_eval, seed + 20_000, 20_000_000, stratified=stratified_eval)
    return train, calib, ev


def write_jsonl(df: pd.DataFrame, path: Path) -> None:
    """Persist a split in the sample-file record shape (+ inputs.asr_xml = what the models actually receive)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for i, r in enumerate(df.itertuples(index=False), 1):
            f.write(json.dumps({
                "inputs": {"chat_history": "", "customer_utterance": parse_call(r.xml).text, "lob": "brands", "asr_xml": r.xml},
                "expected": {"classified_intent": r.intent, "model_response": ""},
                "metadata": {"conv_status": "ongoing", "conversation_no": i, "call_id": r.call_id,
                             "seed_utterance": r.seed_utterance, "seed_source": r.seed_source, "label_basis": r.label_basis}},
                ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> pd.DataFrame:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        md = d.get("metadata", {})
        rows.append(dict(call_id=md.get("call_id", ""), intent=d["expected"]["classified_intent"],
                         seed_utterance=md.get("seed_utterance", ""), seed_source=md.get("seed_source", ""),
                         label_basis=md.get("label_basis", ""), xml=d["inputs"]["asr_xml"]))
    return pd.DataFrame(rows)
