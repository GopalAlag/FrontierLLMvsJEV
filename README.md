# JEV fraud classification: classic ML vs JEV vs Claude

Compares three ways to classify credit card transactions as fraud, on accuracy, latency and cost,
over several iterations (each iteration = fresh data draw + a new prompt variant).

| System | Module | Notes |
|---|---|---|
| Classic GBM | `baseline.py` | scikit-learn HistGradientBoosting, same features |
| JEV (Typesafe System One) | `jev_module.py` | `langchain-typesafe` `TypeSafeClassifier`, Noul question -> P(fraud); cost = input tokens x $0.042/MTok, output free |
| Claude LLM | `llm_module.py` | Haiku 5.5 and Sonnet 5.5, structured output (label, probability, reason), cached system prompt, cost from `usage` incl. cache read/write |

Data: [NeerajCodz/creditCardFraudDetection](https://huggingface.co/datasets/NeerajCodz/creditCardFraudDetection)
(`train/us.csv`, 1.3M rows, 0.58% fraud) saved to `data/raw/us.csv`. Eval sets are fraud-enriched
(20%) so metrics are measurable at a few hundred rows; thresholds are tuned on a separate
calibration slice. Names, card numbers and street addresses are never sent to any model.

## Run

```
copy .env.example .env      # fill TYPESAFE_API_KEY and ANTHROPIC_API_KEY
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python -m jev_fraud.run_experiment --iterations 3 --n-eval 300
.venv\Scripts\python -m pytest
```

Systems whose key is missing are skipped. Results land in `results/` (`iterations.csv`,
`summary_by_system.csv`).

## Iterations

1. v1 prompts (JEV: bare Noul question; Claude: minimal system prompt)
2. v2 prompts (fraud-domain guidance added)
3. v3 (JEV adds criteria + a risk Choice question; Claude keeps v2)

## Caveats

- JEV pricing/speed numbers are vendor claims; this project measures them from the real `usage` field and wall-clock latency.
- Baseline latency is amortised batch inference, so it is not comparable to per-request API latency.
- `langchain-typesafe` is an alpha (0.0.1a3); JEV is in early access.

---

# IVR intent detection, routing and servicing (`src/ivr_intent/`)

Same cost/latency/quality comparison as the fraud project, for a credit-card IVR: speech-to-text XML in -> intent -> workflow
(or live agent when confidence is low) -> mock servicing. Scope = the 114 intent categories seen in the sample brands-LOB screenshots.

| System | Module |
|---|---|
| Classic ML (TF-IDF + LR) | `models/tfidf_baseline.py` |
| JEV (Typesafe System One, one `Choice` question) | `models/jev.py` |
| Claude Haiku 5.5 / Sonnet 5.5 | `models/claude_haiku.py`, `models/claude_sonnet.py` (shared `_anthropic.py`) |
| GPT-6 Luna | `models/openai_gpt6_luna.py` |
| Gemini 3.1 Flash-Lite | `models/gemini_flash_lite.py` |

Data (all JSONL, same record shape as the sample file): `data/ivr_seed_dataset.jsonl` = utterances transcribed from the screenshots
(`label_basis` paired = intent and utterance read from the same screenshot row; inferred = my best match) plus authored variations, per-intent split into train/calibration/eval seeds; each run writes
`results_ivr/data/iter*_{train,calib,eval}.jsonl` with ASR-noisy N-best XML (`inputs.asr_xml`).

```
.venv\Scripts\python -m ivr_intent.run_experiment --dry-run                       # plan + cost upper bound, no API calls
.venv\Scripts\python -m ivr_intent.run_experiment --skip jev,claude_haiku,claude_sonnet,openai_luna,gemini_flash_lite   # offline only
.venv\Scripts\python -m ivr_intent.run_experiment --iterations 3 --n-eval 400 --fewshot --trace --max-cost 2
```

Caveats: screenshot labels are mostly *inferred* (only a few rows show `utterance -> Classified Intent`); CRS = Credit Retail Services (retail store-brand cards);
JEV/Gemini/GPT prices are list prices at time of writing.

## Prompt caching modes (`--cache-mode implicit|explicit|both`, default `both`)

| Provider | implicit | explicit |
|---|---|---|
| Claude | top-level automatic `cache_control` | block-level breakpoint at the end of the system prompt |
| GPT-6 Luna | automatic prefix caching | `prompt_cache_breakpoint` on the system block, `prompt_cache_options.mode=explicit` |
| Gemini | automatic (best effort) | `caches.create` (setup cost counted; hourly storage not included; cache deleted after the run) |
| JEV | no cache controls exposed by `langchain-typesafe`; usage reports no cached tokens | same |

Each router instance appends a unique cache-namespace tag to its system prompt so implicit/explicit runs start cold and cannot read each other's cache.
Observed on a 2-call check: Claude implicit (automatic marker lands on the varying user message) wrote the whole request every call and never read it;
Claude/GPT explicit read the cached system prompt on call 2; Gemini explicit cut per-call cost ~78% vs implicit, which had no hits.
