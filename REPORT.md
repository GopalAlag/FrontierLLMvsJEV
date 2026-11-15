# Credit card fraud classification: classic ML vs JEV vs four LLMs

Detailed summary of the final experiment (`results_cached/`): real transaction data, a shared long few-shot prompt, prompt caching on every LLM. Raw evidence for every number below is in `results_cached/audit.jsonl` (one record per API call) and `results_cached/results.md` (per-call tables with the source file and line that made each call).

---

## 1. Scenario

A card issuer scores each incoming credit card transaction as **fraud** or **legitimate** in real time. Fraud is rare (about 0.58% of transactions in this dataset), the cost of a missed fraud and of a false alarm are both real, and the scoring step has to be cheap and fast because it runs on every transaction.

The system receives only what is known at authorisation time: amount, merchant name and category, local time, the cardholder's age, gender, job and home city, and the distance between the cardholder's home and the merchant. Names, card numbers and street addresses are never sent to any model.

## 2. Objective

Compare three ways of building that classifier on **accuracy, latency, cost and operational effort**:

| Approach | Needs labelled history? | Models tested |
|---|---|---|
| Classic supervised ML | Yes (100,000 labelled rows) | Gradient boosting (scikit-learn) |
| JEV, a "System One" decision model (Typesafe) | No (zero-shot) | `jev-latest` |
| General LLMs with a structured-output prompt | No (prompt plus a few examples) | Claude Haiku 5.5, Claude Sonnet 5.5, OpenAI GPT-6 Luna, Google Gemini 3.1 Flash-Lite |

Questions answered: which is most accurate, which is fastest, which is cheapest per transaction, what does caching do to LLM cost, and where does each system fail.

## 3. Test plan

**Dataset.** 1,296,675 simulated card transactions from the public Hugging Face dataset NeerajCodz/creditCardFraudDetection (`train/us.csv`), 0.5789% fraud. It appears to be the widely mirrored Kaggle simulated-transactions dataset: realistic, but generated rather than from a real bank.

**Three iterations.** Each iteration (seeds 43, 44, 45) draws a fresh, non-overlapping sample:

| Split | Rows | Fraud share | Used for |
|---|---|---|---|
| Training | 100,000 | about 7.4% (all remaining fraud, oversampled) | Classic GBM training; source of the few-shot examples |
| Calibration | 50 | 14 to 24% (7 to 12 fraud) | Choosing each system's decision threshold (best F1) |
| Evaluation | 250 | 20% (48 to 53 fraud) | All reported metrics |

The evaluation sets are **fraud-enriched to 20%** so precision and recall can be measured on a few hundred rows. Precision here is therefore much higher than it would be at the real 0.58% fraud rate. Compare systems with each other, not with production precision.

**Same inputs for everyone.** Within an iteration every system scores the identical 50 calibration and 250 evaluation transactions. Thresholds are tuned on the calibration rows only, never on the evaluation rows.

**Shared LLM prompt.** All four LLMs use the same system prompt (about 14,000 characters): fraud-analyst instructions, domain guidance, and 42 labelled examples (14 fraud, 28 legitimate) drawn only from that iteration's training split, never from calibration or evaluation rows. It is long on purpose, so that every provider's prompt cache engages. JEV cannot take a system prompt; it gets the same domain guidance inside its question text.

**Caching, applied to every LLM.**
- Claude: explicit `cache_control` on the system prompt, plus one warm-up call.
- OpenAI: automatic prefix caching with a stable `prompt_cache_key`, plus one warm-up call.
- Gemini: an explicit context cache holding the system prompt (created successfully, no fallback needed).
- JEV: no caching exists.

**Metrics.** Precision, recall, F1, PR-AUC and ROC-AUC (per iteration, then averaged); median and 95th-percentile latency per call; wall-clock time; input, cached-input and output tokens; and cost per call, per 1,000 transactions and per caught fraud. Costs use list prices (below) applied to the token counts each API reported.

**Audit trail.** Every API call records its request, the raw response, the result used for scoring, token usage, latency, cost, request ID, and the project file and line plus library function that made the call.

## 4. Systems under test: inputs, outputs, price

| System | Provider and model ID | What it receives | What it returns | List price (per 1M tokens, in / cached in / out) |
|---|---|---|---|---|
| Classic GBM | scikit-learn `HistGradientBoostingClassifier` | 9 numeric and categorical features (amount, hour, weekday, age, distance, city population, category, gender, state) | P(fraud) | local compute, $0 |
| JEV | Typesafe `jev-latest` via `langchain-typesafe` | Transaction as text, plus two typed questions: `is_fraud` (Noul, a probability that a statement is true) and `risk` (Choice: low, medium, high) | P(fraud) as `noul`, plus risk class, probabilities and confidence | $0.042 in, output free (vendor price) |
| Claude Haiku 5.5 | Anthropic `claude-haiku-5-5` | Cached system prompt (about 6,350 tokens) plus the transaction text | Structured `FraudVerdict`: label, fraud_probability, one-sentence reason | $0.10 / $0.01 / $0.50 |
| Claude Sonnet 5.5 | Anthropic `claude-sonnet-5-5` | Same as Haiku | Same as Haiku | $2.00 / $0.20 / $10.00 |
| GPT-6 Luna | OpenAI `gpt-6-luna` (Responses API) | Cached system prompt (about 4,130 tokens) plus the transaction text | Same `FraudVerdict` structure | $0.10 / $0.01 / $0.50 |
| Gemini 3.1 Flash-Lite | Google `gemini-3.1-flash-lite` | Context-cached system prompt (about 4,570 tokens) plus the transaction text | Same `FraudVerdict` structure | $0.25 / about 10% of input / $1.50 |

Token counts differ across providers because each uses its own tokenizer on the same text.

## 5. How many calls were made

| System | Calibration calls | Evaluation calls | Total | Errors |
|---|---|---|---|---|
| JEV | 150 | 750 | 900 | 0 |
| Claude Haiku 5.5 | 150 | 750 | 900 | 0 |
| Claude Sonnet 5.5 | 150 | 750 | 900 | 0 |
| GPT-6 Luna | 150 | 750 | 900 | 0 |
| Gemini 3.1 Flash-Lite | 150 | 750 | 900 | 0 |
| **Total API calls** | **750** | **3,750** | **4,500** | **0** |

(Classic GBM makes no API calls: 3 models trained, one per iteration.)

Across the whole project, three experiments plus small smoke tests made about 14,100 billable API calls and cost roughly **$6.2**: synthetic data (3,600 calls, $1.70), real data with short prompts (6,000 calls, $2.07), and this final run (4,500 calls, $2.41).

## 6. Results

### 6.1 Accuracy (mean of 3 iterations, 250 evaluation rows each)

| System | Precision | Recall | F1 | F1 range over iterations | PR-AUC | ROC-AUC |
|---|---|---|---|---|---|---|
| **Classic GBM** | 0.891 | **1.000** | **0.941** | 0.909 to 0.991 | 0.999 | 1.000 |
| GPT-6 Luna | 0.955 | 0.734 | 0.830 | 0.771 to 0.889 | 0.883 | 0.942 |
| Claude Sonnet 5.5 | 0.939 | 0.730 | 0.820 | 0.778 to 0.901 | 0.868 | 0.935 |
| Claude Haiku 5.5 | 0.945 | 0.689 | 0.796 | 0.764 to 0.844 | 0.831 | 0.921 |
| Gemini 3.1 Flash-Lite | 0.799 | 0.760 | 0.775 | 0.727 to 0.809 | 0.770 | 0.904 |
| JEV | 0.784 | 0.611 | 0.685 | 0.637 to 0.721 | 0.783 | 0.908 |

### 6.2 Per iteration: F1 and confusion counts (TP / FP / FN / TN on 250 rows)

| System | Iteration 1 (53 fraud) | Iteration 2 (50 fraud) | Iteration 3 (48 fraud) |
|---|---|---|---|
| Classic GBM | F1 0.991, 53 / 1 / 0 / 196 | F1 0.909, 50 / 10 / 0 / 190 | F1 0.923, 48 / 8 / 0 / 194 |
| JEV | F1 0.637, 29 / 9 / 24 / 188 | F1 0.721, 31 / 5 / 19 / 195 | F1 0.696, 32 / 12 / 16 / 190 |
| Claude Haiku 5.5 | F1 0.764, 34 / 2 / 19 / 195 | F1 0.844, 38 / 2 / 12 / 198 | F1 0.781, 32 / 2 / 16 / 200 |
| Claude Sonnet 5.5 | F1 0.778, 35 / 2 / 18 / 195 | F1 0.901, 41 / 0 / 9 / 200 | F1 0.782, 34 / 5 / 14 / 197 |
| GPT-6 Luna | F1 0.830, 39 / 2 / 14 / 195 | F1 0.889, 40 / 0 / 10 / 200 | F1 0.771, 32 / 3 / 16 / 199 |
| Gemini 3.1 Flash-Lite | F1 0.789, 43 / 13 / 10 / 184 | F1 0.809, 36 / 3 / 14 / 197 | F1 0.727, 36 / 15 / 12 / 187 |

Thresholds picked on the 50 calibration rows varied a lot (for example Gemini 0.6 to 0.9, Haiku 0.15 to 0.40). That is a source of the iteration-to-iteration spread. Classic GBM confusion counts are derived from its reported precision and recall.

### 6.3 Latency and time

| System | Median per call | 95th percentile | Mean | Wall time, 750 eval calls (8 parallel workers) | Throughput |
|---|---|---|---|---|---|
| Classic GBM | under 1 ms (batch) | under 1 ms | n/a | 0.07 s (all 3 iterations) | about 14,000 per s |
| JEV | **0.13 s** | 0.17 to 0.20 s | 0.14 s | 13 s | about 58 per s |
| Gemini 3.1 Flash-Lite | 0.84 s | 1.1 to 1.2 s | 0.88 s | 82 s | about 9 per s |
| Claude Haiku 5.5 | 0.99 s | 1.5 s | 1.10 s | 108 s | about 7 per s |
| Claude Sonnet 5.5 | 1.31 s | 1.7 s | 1.34 s | 131 s | about 6 per s |
| GPT-6 Luna | 2.06 s | 6.8 to 7.3 s | 2.77 s | 289 s | about 2.7 per s |

Classic GBM latency is amortised batch time and is not comparable to a network request. GPT-6 Luna has the worst tail: some calls took 7 s or more, and it also uses hidden reasoning tokens (about 58 per call).

### 6.4 Tokens per call (averages)

| System | Fresh input | Cached input | Output | Notes |
|---|---|---|---|---|
| JEV | 522 | 0 | 56 | questions included in the input |
| Claude Haiku 5.5 | 119 | 6,349 | 71 | cache write of 19,110 tokens in total, one per iteration per model |
| Claude Sonnet 5.5 | 119 | 6,349 | 67 | same |
| GPT-6 Luna | 93 | 4,133 | 107 | includes about 58 reasoning tokens |
| Gemini 3.1 Flash-Lite | 85 | 4,574 | 49 | no thinking tokens (set to minimal) |

About 98% of all LLM input tokens were served from cache.

### 6.5 Cost

| System | Total spend (900 calls) | Cost per 1,000 transactions | Per 1 million | Per caught fraud |
|---|---|---|---|---|
| Classic GBM | $0 | $0 | $0 | $0 |
| JEV | $0.020 | $0.022 | $22 | $0.0002 |
| GPT-6 Luna | $0.094 | $0.103 | $103 | $0.0007 |
| Claude Haiku 5.5 | $0.102 | $0.111 | $111 | $0.0008 |
| Gemini 3.1 Flash-Lite | $0.188 | $0.208 | $208 | $0.0014 |
| Claude Sonnet 5.5 | $2.007 | $2.18 | $2,181 | $0.0149 |
| **Run total** | **$2.411** | | | |

Per-1,000 and per-fraud figures use evaluation calls only; the totals also include calibration calls and one-time cache writes. Sonnet 5.5 is 83 percent of the run's cost.

### 6.6 What the short-prompt run looked like (same project, before few-shot and caching)

| System | F1 before | F1 now | Cost per 1,000 before | now |
|---|---|---|---|---|
| Classic GBM | 0.950 | 0.941 | n/a | n/a |
| GPT-6 Luna | 0.648 | 0.830 | $0.096 | $0.103 |
| Claude Sonnet 5.5 | 0.714 | 0.820 | $1.38 | $2.18 |
| Claude Haiku 5.5 | 0.682 | 0.796 | $0.072 | $0.111 |
| Gemini 3.1 Flash-Lite | 0.668 | 0.775 | $0.154 | $0.208 |
| JEV | 0.597 | 0.685 | $0.018 | $0.022 |

The two runs used different evaluation rows (300 versus 250 per iteration), so the improvement is not a strictly paired comparison.

## 7. Worked example: one transaction through every system

Input (evaluation row, true label **fraud**):

```
Amount: $13.28
Merchant: Bernier, Streich and Jewess (category: grocery_net)
Time: Mon 01:00
Cardholder: F, age 72, job 'Development worker, international aid', lives in Rochester, KY (city population 443)
Distance between cardholder home and merchant: 22.8 km
```

| System | P(fraud) | Verdict at its threshold | Output (abridged) | Latency |
|---|---|---|---|---|
| JEV | 0.30 | missed | `is_fraud` noul 0.30, `risk` medium (0.64) | 0.13 s |
| Claude Haiku 5.5 | 0.06 | missed | "legit: small $13.28 grocery_net purchase well below the large-amount threshold" | 1.04 s |
| Claude Sonnet 5.5 | 0.08 | missed | "legit: small grocery_net amount at a short distance; only the late-night hour is mildly suspicious" | 1.25 s |
| GPT-6 Luna | 0.06 | missed | "legit: small grocery purchase with a late-night timestamp but no strong signal" | 2.29 s |
| Gemini 3.1 Flash-Lite | 0.03 | missed | "legit: very small amount, typical for an ordinary grocery purchase" | 1.59 s |

All five API systems missed this one. It is a low-amount fraud that breaks the "large amounts are suspicious" rule in the prompt, which is exactly the kind of subtle pattern a model trained on 100,000 labelled rows can learn and a prompt cannot fully describe.

## 8. Findings

1. **Best accuracy: the classic GBM** (F1 0.941, recall 1.000, near-zero latency, zero API cost). It missed no fraud in any iteration, at the price of more false alarms (1, 10 and 8 per 200 or so legitimate rows).
2. **Best API model for accuracy: GPT-6 Luna** (F1 0.830), with Claude Sonnet 5.5 effectively tied (0.820). The gap between them is within noise.
3. **Best value among LLMs: Claude Haiku 5.5 or GPT-6 Luna.** Both cost about $0.10 per 1,000 transactions. Sonnet 5.5 costs about 20 times that for a 0.01 F1 difference from GPT-6 Luna, so on this task it is not worth the price. GPT-6 Luna is the slowest, with a long latency tail, so Haiku 5.5 is the safer choice when response time matters.
4. **JEV is the cheapest and fastest by a wide margin** (about $0.02 per 1,000, 0.13 s) but the least accurate (F1 0.685, lowest recall of the zero-shot systems at 0.611). It suits a cheap first-pass filter or a router, not a final decision.
5. **Gemini 3.1 Flash-Lite had the most false alarms** among the LLMs (3 to 15 per iteration versus 0 to 5 for Claude and GPT-6 Luna) and double the cost of Haiku or GPT-6 Luna per transaction.
6. **Few-shot examples plus caching gave the biggest improvement** over the short-prompt run: +0.09 to +0.18 F1 across the LLMs, at 1.1 to 1.6 times the per-transaction cost. Caching held that extra cost down: 98% of input tokens were billed at the cached rate.
7. **Labelled history still wins.** If you have it, train the GBM. If you do not, a Claude or GPT-6 Luna prompt with a few labelled examples is a reasonable start, and the GBM can replace it later.

## 9. Limitations

- **Small samples.** Each iteration has only 48 to 53 fraud cases, so F1 differences under about 0.05 between the LLMs are within noise. The spread across iterations (up to 0.12 F1) is larger than most gaps between them.
- **Enriched evaluation sets.** 20% fraud versus 0.58% in the data. Precision in production would be much lower for every system.
- **Noisy thresholds.** Chosen on 50 calibration rows (about 10 fraud), they vary widely between iterations. A larger calibration set would stabilise the comparison.
- **Unequal starting points.** The GBM trained on 100,000 labelled rows; the LLMs saw 42 examples. That is the realistic comparison for a team with and without labels, but it is not a like-for-like test of model quality.
- **Simulated data.** The dataset is generated, so absolute numbers may not transfer to a real portfolio.
- **Prices.** JEV's price is a vendor claim; the OpenAI and Google prices come from their official pricing pages as of 2026-10-16. Costs are computed from reported token counts, not from invoices; check provider consoles for actual billing.
- **Gemini retries.** Retries on 429 and 503 errors are not separately logged. No call ended in an error.

## 10. Files

| File | Contents |
|---|---|
| `results_cached/results.md` | Summary tables, then per-call input, output, source line and raw request or response |
| `results_cached/audit.jsonl` | Full-fidelity record of all 4,500 API calls |
| `results_cached/iterations.csv` | Per-iteration metrics for every system |
| `results_cached/system_prompts/` | The exact few-shot prompts (one per iteration) |
| `results_real/` | Earlier real-data run with short prompts (6,000 calls, $2.07) |
| `results/` | Earlier synthetic-data run (3,600 calls, $1.70) |
| `src/jev_fraud/` | Code: `baseline.py`, `jev_module.py`, `llm_module.py`, `openai_module.py`, `gemini_module.py`, `prompts.py`, `run_experiment.py`, `audit.py`, `analysis.py` |
| `watch.py` | Live terminal view of a running experiment |
