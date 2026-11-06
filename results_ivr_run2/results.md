# IVR conversational AI: intent detection, routing and servicing

Generated 2026-10-21T23:34:39+00:00. Whole experiment 700 s wall clock, 2780 external API calls, $1.6670 measured spend.

## Scenario

A credit card customer calls the IVR. Speech-to-text returns an XML N-best result. The system must (1) detect the intent from a taxonomy of 114 credit-card servicing intents (the intent categories in the sample brands-LOB data), (2) route to the servicing workflow when confident, otherwise to a live agent (threshold tuned on a calibration slice), and (3) run the workflow against a mock account. Eval utterances are phrasings never seen by the TF-IDF model or the few-shot prompt.

## Headline

- Best end-to-end handling: **gemini-3.1-flash-lite_explicit** (55.7% handled correctly, misroute 23.2%, automation 78.1%).
- Highest exact-intent accuracy: **claude-sonnet-5-5_explicit** (68.6%); best macro-F1: **claude-sonnet-5-5_explicit** (0.716).
- Fastest median latency: **classic_tfidf_lr** (0 ms).
- Cheapest API system: **gpt-6-luna_explicit** ($0.1022 per 1,000 calls, $102 per million).
  - gemini-3.1-flash-lite_explicit: $0.00032 per correctly handled call; illustrative total ops cost $3,421.23 per 1,000 calls (model spend + $5.0/agent call + $10.0/misroute).
  - claude-haiku-5-5_explicit: $0.00022 per correctly handled call; illustrative total ops cost $3,081.26 per 1,000 calls (model spend + $5.0/agent call + $10.0/misroute).
  - claude-sonnet-5-5_explicit: $0.00509 per correctly handled call; illustrative total ops cost $3,368.60 per 1,000 calls (model spend + $5.0/agent call + $10.0/misroute).
  - jev: $0.00037 per correctly handled call; illustrative total ops cost $3,212.89 per 1,000 calls (model spend + $5.0/agent call + $10.0/misroute).
  - gpt-6-luna_explicit: $0.00032 per correctly handled call; illustrative total ops cost $3,728.17 per 1,000 calls (model spend + $5.0/agent call + $10.0/misroute).

## Quality (mean over iterations)

| family                         |   accuracy |   macro_f1 |   handled_correctly |   automation_rate |   auto_precision |   misroute_rate |   unnecessary_escalation_rate |   invalid_labels |   errors |
|:-------------------------------|-----------:|-----------:|--------------------:|------------------:|-----------------:|----------------:|------------------------------:|-----------------:|---------:|
| gemini-3.1-flash-lite_explicit |      0.636 |      0.65  |               0.557 |             0.781 |            0.702 |           0.232 |                         0.211 |                0 |        0 |
| claude-haiku-5-5_explicit      |      0.614 |      0.636 |               0.542 |             0.682 |            0.789 |           0.149 |                         0.309 |                0 |        0 |
| claude-sonnet-5-5_explicit     |      0.686 |      0.716 |               0.485 |             0.625 |            0.792 |           0.149 |                         0.366 |                0 |        0 |
| jev                            |      0.649 |      0.672 |               0.463 |             0.55  |            0.833 |           0.096 |                         0.441 |                0 |        0 |
| gpt-6-luna_explicit            |      0.675 |      0.707 |               0.329 |             0.386 |            0.829 |           0.066 |                         0.605 |                0 |        0 |
| classic_tfidf_lr               |      0.281 |      0.261 |               0.046 |             0.055 |            0.607 |           0.018 |                         0.928 |                0 |        0 |

`accuracy` = exact intent label. `handled_correctly` = right workflow (or right agent transfer), counting near-synonym intents that share a workflow as correct. `misroute_rate` = automatic action on the wrong workflow. `automation_rate` = share sent to a workflow without a human.

## Latency and time

| family                         |   latency_p50_s |   latency_p95_s |   throughput_per_s |   eval_wall_s |   total_wall_s |
|:-------------------------------|----------------:|----------------:|-------------------:|--------------:|---------------:|
| gemini-3.1-flash-lite_explicit |           0.952 |           1.353 |              5.935 |         76.86 |          95.52 |
| claude-haiku-5-5_explicit      |           1.055 |           1.6   |              4.935 |         92.41 |         117.25 |
| claude-sonnet-5-5_explicit     |           1.39  |           2.267 |              3.66  |        125.01 |         155.92 |
| jev                            |           0.184 |           0.237 |             31.49  |         14.48 |          18.48 |
| gpt-6-luna_explicit            |           2.329 |           7.119 |              1.925 |        241.16 |         298.91 |
| classic_tfidf_lr               |           0     |           0     |          22172.9   |          0.03 |           4.52 |

TF-IDF latency is amortised batch time, not a per-request round trip.

## Cost

| family                         |   cost_per_1k_usd |   cost_per_1m_calls_usd |   cost_per_correct_call_usd |   total_cost_usd |   ops_cost_per_1k_usd |   cached_input_share |   cache_write_tokens |   cache_setup_cost_usd |
|:-------------------------------|------------------:|------------------------:|----------------------------:|-----------------:|----------------------:|---------------------:|---------------------:|-----------------------:|
| gemini-3.1-flash-lite_explicit |           0.1761  |                 176.104 |                     0.00032 |          0.0803  |               3421.23 |              0.94195 |                    0 |                0.00132 |
| claude-haiku-5-5_explicit      |           0.12201 |                 122.007 |                     0.00022 |          0.05564 |               3081.26 |              0.96462 |                    0 |                0       |
| claude-sonnet-5-5_explicit     |           2.36998 |                2369.98  |                     0.00509 |          1.08071 |               3368.6  |              0.96462 |                    0 |                0       |
| jev                            |           0.17009 |                 170.09  |                     0.00037 |          0.07756 |               3212.89 |              0       |                    0 |                0       |
| gpt-6-luna_explicit            |           0.10222 |                 102.216 |                     0.00032 |          0.04661 |               3728.17 |              0.95163 |                    0 |                0       |
| classic_tfidf_lr               |           0       |                   0     |                     0       |          0       |               4901.32 |            nan       |                    0 |                0       |

Caching: rows are suffixed `_implicit` / `_explicit` for Claude, GPT and Gemini. Claude explicit = block-level breakpoint on the system prompt, implicit = top-level automatic marker. GPT implicit = automatic prefix caching, explicit = `prompt_cache_breakpoint` with the implicit breakpoint disabled. Gemini implicit = automatic, explicit = `caches.create` (creation cost shown as `cache_setup_cost_usd`; hourly storage not included). JEV exposes no cache controls and reports no cached tokens, so it has a single row.

## Per iteration

| iteration | system | n | errors | threshold | accuracy | macro_f1 | handled_correctly | automation_rate | misroute_rate | latency_p50_s | latency_p95_s | input_tokens | output_tokens | cache_read_tokens | eval_wall_s | total_cost_usd | cost_per_1k_usd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | classic_tfidf_lr | 228 | 0 | 0.51 | 0.280702 | 0.2467 | 0.074561 | 0.092105 | 0.026316 | 3e-05 | 3e-05 | 0 | 0 | 0 | 0.01 | 0.0 | 0.0 |
| 1 | gpt-6-luna_explicit_v1 | 228 | 0 | 0.96 | 0.701754 | 0.730395 | 0.276316 | 0.324561 | 0.057018 | 2.249747 | 5.704624 | 673639 | 24922 | 637944 | 105.05 | 0.02241 | 0.098289 |
| 1 | claude-haiku-5-5_explicit_v1 | 228 | 0 | 0.72 | 0.640351 | 0.657289 | 0.52193 | 0.600877 | 0.087719 | 1.036673 | 1.633234 | 1337372 | 16661 | 1285920 | 47.26 | 0.026335 | 0.115504 |
| 1 | jev_v1 | 228 | 0 | 0.96 | 0.662281 | 0.679218 | 0.429825 | 0.473684 | 0.052632 | 0.184185 | 0.237521 | 877063 | 331558 | 0 | 7.19 | 0.036837 | 0.161564 |
| 1 | gemini-3.1-flash-lite_explicit_v1 | 228 | 0 | 0.57 | 0.657895 | 0.661626 | 0.570175 | 0.798246 | 0.236842 | 0.952196 | 1.318901 | 572672 | 9955 | 535572 | 38.13 | 0.038184 | 0.167474 |
| 1 | claude-sonnet-5-5_explicit_v1 | 228 | 0 | 0.81 | 0.719298 | 0.750046 | 0.377193 | 0.416667 | 0.048246 | 1.362502 | 2.175503 | 1337144 | 15413 | 1285692 | 59.26 | 0.514172 | 2.255142 |
| 2 | classic_tfidf_lr | 228 | 0 | 0.81 | 0.280702 | 0.274408 | 0.017544 | 0.017544 | 0.008772 | 8.4e-05 | 8.4e-05 | 0 | 0 | 0 | 0.02 | 0.0 | 0.0 |
| 2 | gpt-6-luna_explicit_v2 | 228 | 0 | 0.9 | 0.649123 | 0.68313 | 0.381579 | 0.447368 | 0.074561 | 2.409189 | 8.533403 | 802231 | 25932 | 766536 | 136.11 | 0.024201 | 0.106144 |
| 2 | claude-haiku-5-5_explicit_v2 | 228 | 0 | 0.48 | 0.587719 | 0.614615 | 0.561404 | 0.763158 | 0.210526 | 1.073186 | 1.566152 | 1567771 | 18003 | 1516428 | 45.15 | 0.0293 | 0.128509 |
| 2 | jev_v2 | 228 | 0 | 0.78 | 0.635965 | 0.664714 | 0.495614 | 0.627193 | 0.140351 | 0.183124 | 0.237242 | 969637 | 331581 | 0 | 7.29 | 0.040725 | 0.178617 |
| 2 | gemini-3.1-flash-lite_explicit_v2 | 228 | 0 | 0.72 | 0.614035 | 0.637847 | 0.54386 | 0.763158 | 0.22807 | 0.951794 | 1.386408 | 705121 | 10277 | 668040 | 38.73 | 0.042119 | 0.184734 |
| 2 | claude-sonnet-5-5_explicit_v2 | 228 | 0 | 0.51 | 0.653509 | 0.681405 | 0.592105 | 0.833333 | 0.25 | 1.417895 | 2.358607 | 1567999 | 16052 | 1516656 | 65.75 | 0.566537 | 2.484812 |

## Most common intent confusions (summed over iterations, top 5 per system)

| family                         | true                             | predicted                        |   count |
|:-------------------------------|:---------------------------------|:---------------------------------|--------:|
| classic_tfidf_lr               | AccountDebtConsolidation         | AccountCardLinkingforUnifiedView |       2 |
| classic_tfidf_lr               | AccountNumberInquiry             | PaymentMethodOptionsInquiry      |       2 |
| classic_tfidf_lr               | AutoPayManagement                | PaymentDueDateModification       |       2 |
| classic_tfidf_lr               | BranchATMLocationANDIssueInquiry | PaymentMethodOptionsInquiry      |       2 |
| classic_tfidf_lr               | CancelAutoPay                    | AutoPayManagement                |       2 |
| claude-haiku-5-5_explicit      | CardExpirationRenewal            | UnclassifiableOther              |       4 |
| claude-haiku-5-5_explicit      | DamagedCardReplacement           | UnclassifiableOther              |       3 |
| claude-haiku-5-5_explicit      | PhoneNumberUpdate                | UnclassifiableOther              |       3 |
| claude-haiku-5-5_explicit      | AccountNumberInquiry             | AccountQuestion                  |       2 |
| claude-haiku-5-5_explicit      | CancelBalanceTransfer            | BalanceTransferGeneralInquiry    |       2 |
| claude-sonnet-5-5_explicit     | CardExpirationRenewal            | UnclassifiableOther              |       3 |
| claude-sonnet-5-5_explicit     | PhoneNumberUpdate                | UnclassifiableOther              |       3 |
| claude-sonnet-5-5_explicit     | AccountNumberInquiry             | AccountQuestion                  |       2 |
| claude-sonnet-5-5_explicit     | CancelBalanceTransfer            | BalanceTransferGeneralInquiry    |       2 |
| claude-sonnet-5-5_explicit     | POCNightsInquiry                | UnclassifiableOther              |       2 |
| gemini-3.1-flash-lite_explicit | DamagedCardReplacement           | UnclassifiableOther              |       3 |
| gemini-3.1-flash-lite_explicit | PhoneNumberUpdate                | UnclassifiableOther              |       3 |
| gemini-3.1-flash-lite_explicit | AccountNumberInquiry             | AccountQuestion                  |       2 |
| gemini-3.1-flash-lite_explicit | AccountProblemInquiry            | AccountQuestion                  |       2 |
| gemini-3.1-flash-lite_explicit | BillDiscrepancy                  | BalanceValueInquiry              |       2 |
| gpt-6-luna_explicit            | DamagedCardReplacement           | UnclassifiableOther              |       3 |
| gpt-6-luna_explicit            | PhoneNumberUpdate                | UnclassifiableOther              |       3 |
| gpt-6-luna_explicit            | AccountNumberInquiry             | AccountQuestion                  |       2 |
| gpt-6-luna_explicit            | BankAccountInformationManagement | UnclassifiableOther              |       2 |
| gpt-6-luna_explicit            | CancelBalanceTransfer            | BalanceTransferGeneralInquiry    |       2 |
| jev                            | CardExpirationRenewal            | UnclassifiableOther              |       3 |
| jev                            | DamagedCardReplacement           | UnclassifiableOther              |       3 |
| jev                            | PhoneNumberUpdate                | UnclassifiableOther              |       3 |
| jev                            | AcknowledgementOfGratitude       | CRSRequests                      |       2 |
| jev                            | CancelBalanceTransfer            | InitiateANewBalanceTransfer      |       2 |

## Run configuration

```json
{
  "iterations": 2,
  "n_eval": 228,
  "n_calib": 50,
  "n_train": 2000,
  "seed": 42,
  "stratified": true,
  "fewshot": false,
  "cache_mode": "explicit",
  "no_trace": false,
  "workers": 6,
  "skip": "",
  "hard_cap": 2.8,
  "agent_cost": 5.0,
  "misroute_cost": 10.0,
  "dry_run": false,
  "out": "results_ivr_run2"
}
```

Raw per-call request/response/usage/cost records: `audit.jsonl`. Test data for every split: `data/iter*_{train,calib,eval}.jsonl`.
