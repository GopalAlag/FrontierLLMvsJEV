import json

from ivr_intent.data import load_seeds, make_splits, parse_call, read_jsonl, split_seeds, write_jsonl
from ivr_intent.intents import AGENT, INTENTS, NAMES
from ivr_intent.metrics import Prediction, best_threshold, summarize
from ivr_intent.models._base import clean_label
from ivr_intent.router import expected, route
from ivr_intent.workflows import _STATIC, Account, _a, extract_slots, service


def test_every_workflow_has_a_handler():
    have = set(_STATIC) | set(_a(Account()))
    missing = {i.workflow for i in INTENTS if i.workflow != AGENT} - have
    assert not missing, missing


def test_seed_dataset_covers_every_intent_and_matches_catalog():
    seeds = load_seeds()
    assert set(seeds.intent) == set(NAMES)
    assert seeds.groupby("intent").size().min() >= 4


def test_seed_split_is_disjoint_and_covers_all_intents():
    p = split_seeds(load_seeds())
    sets = {k: set(zip(v.intent, v.utterance)) for k, v in p.items()}
    assert not (sets["train"] & sets["eval"]) and not (sets["train"] & sets["calib"]) and not (sets["calib"] & sets["eval"])
    for k, v in p.items():
        assert set(v.intent) == set(NAMES), k


def test_eval_calls_are_unseen_phrasings_and_xml_parses(tmp_path):
    train, calib, ev = make_splits(1, 200, 50, 80)
    assert not (set(ev.seed_utterance) & set(train.seed_utterance))
    ci = parse_call(ev.xml.iloc[0])
    assert ci.text and ci.nbest
    p = tmp_path / "e.jsonl"
    write_jsonl(ev, p)
    rec = json.loads(p.read_text(encoding="utf-8").splitlines()[0])
    assert rec["expected"]["classified_intent"] == ev.intent.iloc[0] and rec["inputs"]["lob"] == "brands"
    assert read_jsonl(p).xml.tolist() == ev.xml.tolist()


def test_label_canonicalisation():
    assert clean_label("balance_question") == "BalanceQuestion"
    assert clean_label(" ReportLostCard ") == "ReportLostCard"
    assert clean_label("nonsense") == "nonsense"


def test_routing_rules():
    xml = make_splits(1, 10, 5, 5)[2].xml.iloc[0]
    assert route("BalanceValueInquiry", 0.9, 0.5, xml).action == "workflow"
    assert route("BalanceValueInquiry", 0.2, 0.5, xml).reason == "low_confidence_escalation"
    assert route("RequestARepresentative", 0.2, 0.9, xml).action == "agent"
    assert route("x", 1.0, 0.1, xml).reason == "invalid_label"
    assert route("BalanceQuestion", 1.0, 0.1, xml, error="boom").reason == "classifier_error"
    assert expected("RequestARepresentative") == ("agent", AGENT)
    assert service("CardActivation", xml).status in ("collect_slots", "completed")
    assert extract_slots("pay $120 on card 1234") == {"amount": 120.0, "last4": "1234"}


def test_shared_workflow_counts_as_handled_but_not_exact():
    xml = make_splits(1, 10, 5, 5)[2].xml.iloc[0]
    y = ["BalanceQuestion", "BalanceQuestion", "FraudulentActivity"]
    preds = [Prediction("BalanceValueInquiry", 0.9, 0.1, cost_usd=0.001), Prediction("ReportLostCard", 0.9, 0.1, cost_usd=0.001),
             Prediction("__error__", 0.0, 0.1, error="x")]
    m = summarize(y, preds, [xml] * 3, 0.5)
    assert abs(m["accuracy"] - 0.0) < 1e-9
    assert abs(m["handled_correctly"] - 1 / 3) < 1e-5        # synonym intent shares wf_balance
    assert abs(m["misroute_rate"] - 1 / 3) < 1e-5            # ReportLostCard is the wrong workflow
    assert m["errors"] == 1 and abs(m["total_cost_usd"] - 0.002) < 1e-9
    assert 0.0 <= best_threshold(y, preds, [xml] * 3) <= 0.99


def test_stratified_eval_gives_every_intent_the_same_number_of_calls():
    from collections import Counter
    train, calib, ev = make_splits(3, 100, 50, 114 * 2, stratified_eval=True)
    c = Counter(ev.intent)
    assert set(c) == set(NAMES) and set(c.values()) == {2}
    assert not (set(ev.seed_utterance) & set(train.seed_utterance))
    assert len(Counter(make_splits(3, 100, 50, 120, stratified_eval=True)[2].intent)) == len(NAMES)
