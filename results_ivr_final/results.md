# IVR conversational AI: intent detection, routing and servicing

Generated 2026-10-21T23:14:39+00:00. Whole experiment 768 s wall clock, 3000 external API calls, $1.7945 measured spend.

## Scenario

A credit card customer calls the IVR. Speech-to-text returns an XML N-best result. The system must (1) detect the intent from a taxonomy of 114 credit-card servicing intents (the intent categories in the sample brands-LOB data), (2) route to the servicing workflow when confident, otherwise to a live agent (threshold tuned on a calibration slice), and (3) run the workflow against a mock account. Eval utterances are phrasings never seen by the TF-IDF model or the few-shot prompt.

## Headline

- Best end-to-end handling: **claude-haiku-5-5_explicit** (51.6% handled correctly, misroute 9.6%, automation 59.8%).
- Highest exact-intent accuracy: **gpt-6-luna_explicit** (65.2%); best macro-F1: **gpt-6-luna_explicit** (0.599).
- Fastest median latency: **classic_tfidf_lr** (0 ms).
- Cheapest API system: **gpt-6-luna_explicit** ($0.1030 per 1,000 calls, $103 per million).
  - claude-haiku-5-5_explicit: $0.00024 per correctly handled call; illustrative total ops cost $2,970.12 per 1,000 calls (model spend + $5.0/agent call + $10.0/misroute).
  - jev: $0.00036 per correctly handled call; illustrative total ops cost $3,090.17 per 1,000 calls (model spend + $5.0/agent call + $10.0/misroute).
  - gemini-3.1-flash-lite_explicit: $0.00038 per correctly handled call; illustrative total ops cost $3,210.18 per 1,000 calls (model spend + $5.0/agent call + $10.0/misroute).
  - gpt-6-luna_explicit: $0.00026 per correctly handled call; illustrative total ops cost $3,530.10 per 1,000 calls (model spend + $5.0/agent call + $10.0/misroute).
  - claude-sonnet-5-5_explicit: $0.00681 per correctly handled call; illustrative total ops cost $3,562.37 per 1,000 calls (model spend + $5.0/agent call + $10.0/misroute).

## Quality (mean over iterations)

| family                         |   accuracy |   macro_f1 |   handled_correctly |   automation_rate |   auto_precision |   misroute_rate |   unnecessary_escalation_rate |   invalid_labels |   errors |
|:-------------------------------|-----------:|-----------:|--------------------:|------------------:|-----------------:|----------------:|------------------------------:|-----------------:|---------:|
| claude-haiku-5-5_explicit      |      0.608 |      0.562 |               0.516 |             0.598 |            0.842 |           0.096 |                         0.388 |                0 |        0 |
| jev                            |      0.636 |      0.571 |               0.476 |             0.55  |            0.847 |           0.084 |                         0.44  |                0 |        0 |
| gemini-3.1-flash-lite_explicit |      0.62  |      0.555 |               0.472 |             0.558 |            0.835 |           0.1   |                         0.426 |                0 |        0 |
| gpt-6-luna_explicit            |      0.652 |      0.599 |               0.402 |             0.486 |            0.803 |           0.096 |                         0.502 |                0 |        0 |
| claude-sonnet-5-5_explicit     |      0.644 |      0.583 |               0.348 |             0.384 |            0.877 |           0.048 |                         0.604 |                0 |        0 |
| classic_tfidf_lr               |      0.304 |      0.245 |               0.104 |             0.138 |            0.649 |           0.048 |                         0.842 |                0 |        0 |

`accuracy` = exact intent label. `handled_correctly` = right workflow (or right agent transfer), counting near-synonym intents that share a workflow as correct. `misroute_rate` = automatic action on the wrong workflow. `automation_rate` = share sent to a workflow without a human.

## Latency and time

| family                         |   latency_p50_s |   latency_p95_s |   throughput_per_s |   eval_wall_s |   total_wall_s |
|:-------------------------------|----------------:|----------------:|-------------------:|--------------:|---------------:|
| claude-haiku-5-5_explicit      |           1.185 |           1.748 |              4.615 |        108.48 |         136.04 |
| jev                            |           0.188 |           0.275 |             29.82  |         16.77 |          20.67 |
| gemini-3.1-flash-lite_explicit |           0.953 |           1.416 |              5.87  |         85.16 |         103.98 |
| gpt-6-luna_explicit            |           2.671 |           5.891 |              1.86  |        269.21 |         331.25 |
| claude-sonnet-5-5_explicit     |           1.426 |           2.132 |              3.87  |        129.3  |         160.98 |
| classic_tfidf_lr               |           0     |           0     |          31043.8   |          0.02 |           4.41 |

TF-IDF latency is amortised batch time, not a per-request round trip.

## Cost

| family                         |   cost_per_1k_usd |   cost_per_1m_calls_usd |   cost_per_correct_call_usd |   total_cost_usd |   ops_cost_per_1k_usd |   cached_input_share |   cache_write_tokens |   cache_setup_cost_usd |
|:-------------------------------|------------------:|------------------------:|----------------------------:|-----------------:|----------------------:|---------------------:|---------------------:|-----------------------:|
| claude-haiku-5-5_explicit      |           0.12187 |                 121.873 |                     0.00024 |          0.06094 |               2970.12 |              0.96464 |                    0 |                0       |
| jev                            |           0.17009 |                 170.094 |                     0.00036 |          0.08505 |               3090.17 |              0       |                    0 |                0       |
| gemini-3.1-flash-lite_explicit |           0.17586 |                 175.863 |                     0.00038 |          0.08793 |               3210.18 |              0.94196 |                    0 |                0.00132 |
| gpt-6-luna_explicit            |           0.10302 |                 103.02  |                     0.00026 |          0.05151 |               3530.1  |              0.95156 |                    0 |                0       |
| claude-sonnet-5-5_explicit     |           2.3701  |                2370.1   |                     0.00681 |          1.18505 |               3562.37 |              0.96464 |                    0 |                0       |
| classic_tfidf_lr               |           0       |                   0     |                     0       |          0       |               4790    |            nan       |                    0 |                0       |

Caching: rows are suffixed `_implicit` / `_explicit` for Claude, GPT and Gemini. Claude explicit = block-level breakpoint on the system prompt, implicit = top-level automatic marker. GPT implicit = automatic prefix caching, explicit = `prompt_cache_breakpoint` with the implicit breakpoint disabled. Gemini implicit = automatic, explicit = `caches.create` (creation cost shown as `cache_setup_cost_usd`; hourly storage not included). JEV exposes no cache controls and reports no cached tokens, so it has a single row.

## Per iteration

| iteration | system | n | errors | threshold | accuracy | macro_f1 | handled_correctly | automation_rate | misroute_rate | latency_p50_s | latency_p95_s | input_tokens | output_tokens | cache_read_tokens | eval_wall_s | total_cost_usd | cost_per_1k_usd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | classic_tfidf_lr | 250 | 0 | 0.54 | 0.3 | 0.24529 | 0.056 | 0.056 | 0.02 | 3.4e-05 | 3.4e-05 | 0 | 0 | 0 | 0.01 | 0.0 | 0.0 |
| 1 | claude-haiku-5-5_explicit_v1 | 250 | 0 | 0.72 | 0.604 | 0.542742 | 0.504 | 0.552 | 0.068 | 1.23767 | 1.847955 | 1465892 | 18252 | 1409500 | 56.33 | 0.02886 | 0.115441 |
| 1 | gpt-6-luna_explicit_v1 | 250 | 0 | 0.87 | 0.656 | 0.582875 | 0.44 | 0.532 | 0.108 | 2.681132 | 5.052985 | 738726 | 25921 | 699500 | 128.97 | 0.023878 | 0.095512 |
| 1 | jev_v1 | 250 | 0 | 0.93 | 0.636 | 0.558345 | 0.488 | 0.56 | 0.084 | 0.186688 | 0.277787 | 961767 | 363592 | 0 | 8.39 | 0.040394 | 0.161577 |
| 1 | gemini-3.1-flash-lite_explicit_v1 | 250 | 0 | 0.9 | 0.616 | 0.545222 | 0.4 | 0.424 | 0.044 | 0.949521 | 1.39088 | 628742 | 10961 | 588000 | 42.27 | 0.041915 | 0.16766 |
| 1 | claude-sonnet-5-5_explicit_v1 | 250 | 0 | 0.87 | 0.644 | 0.565123 | 0.344 | 0.36 | 0.032 | 1.400251 | 2.104985 | 1466142 | 16863 | 1409750 | 64.02 | 0.563364 | 2.253456 |
| 2 | classic_tfidf_lr | 250 | 0 | 0.27 | 0.308 | 0.244716 | 0.152 | 0.22 | 0.076 | 2.9e-05 | 2.9e-05 | 0 | 0 | 0 | 0.01 | 0.0 | 0.0 |
| 2 | claude-haiku-5-5_explicit_v2 | 250 | 0 | 0.57 | 0.612 | 0.581303 | 0.528 | 0.644 | 0.124 | 1.133138 | 1.649037 | 1719237 | 19645 | 1663000 | 52.15 | 0.032076 | 0.128305 |
| 2 | gpt-6-luna_explicit_v2 | 250 | 0 | 0.9 | 0.648 | 0.614163 | 0.364 | 0.44 | 0.084 | 2.660998 | 6.728475 | 878615 | 30651 | 839500 | 140.24 | 0.027632 | 0.110528 |
| 2 | jev_v2 | 250 | 0 | 0.9 | 0.636 | 0.584164 | 0.464 | 0.54 | 0.084 | 0.188774 | 0.272074 | 1063154 | 363568 | 0 | 8.38 | 0.044652 | 0.17861 |
| 2 | gemini-3.1-flash-lite_explicit_v2 | 250 | 0 | 0.81 | 0.624 | 0.564949 | 0.544 | 0.692 | 0.156 | 0.957312 | 1.440292 | 773381 | 11205 | 732750 | 42.89 | 0.046017 | 0.184067 |
| 2 | claude-sonnet-5-5_explicit_v2 | 250 | 0 | 0.81 | 0.644 | 0.60042 | 0.352 | 0.408 | 0.064 | 1.452622 | 2.158115 | 1718987 | 17666 | 1662750 | 65.28 | 0.621684 | 2.486736 |

## Most common intent confusions (summed over iterations, top 5 per system)

| family                         | true                             | predicted                        |   count |
|:-------------------------------|:---------------------------------|:---------------------------------|--------:|
| classic_tfidf_lr               | StatementCopy                    | StatementInquiry                 |       6 |
| classic_tfidf_lr               | CardIsNotWorking                 | DamagedCardReplacement           |       4 |
| classic_tfidf_lr               | AccountNumberInquiry             | AccountProblemInquiry            |       3 |
| classic_tfidf_lr               | ChangeNumber                     | ChangeCardOrAccountNumber        |       3 |
| classic_tfidf_lr               | FraudulentActivity               | AccountStatusInquiry             |       3 |
| claude-haiku-5-5_explicit      | CardAccountClosure               | UnclassifiableOther              |       3 |
| claude-haiku-5-5_explicit      | OnlineAccess                     | AccountCardLinkingforUnifiedView |       3 |
| claude-haiku-5-5_explicit      | AccountNumberInquiry             | AccountQuestion                  |       2 |
| claude-haiku-5-5_explicit      | AccountProblemInquiry            | AccountQuestion                  |       2 |
| claude-haiku-5-5_explicit      | AccountUpdate                    | AccountQuestion                  |       2 |
| claude-sonnet-5-5_explicit     | CardAccountClosure               | UnclassifiableOther              |       3 |
| claude-sonnet-5-5_explicit     | AccountNumberInquiry             | AccountQuestion                  |       2 |
| claude-sonnet-5-5_explicit     | AccountNumberInquiry             | ChangeCardOrAccountNumber        |       2 |
| claude-sonnet-5-5_explicit     | AccountProblemInquiry            | AccountQuestion                  |       2 |
| claude-sonnet-5-5_explicit     | AccountUpdate                    | AccountQuestion                  |       2 |
| gemini-3.1-flash-lite_explicit | ChangeNumber                     | AccountUpdate                    |       3 |
| gemini-3.1-flash-lite_explicit | OnlineAccess                     | AccountCardLinkingforUnifiedView |       3 |
| gemini-3.1-flash-lite_explicit | AccountNumberInquiry             | AccountQuestion                  |       2 |
| gemini-3.1-flash-lite_explicit | AccountProblemInquiry            | AccountQuestion                  |       2 |
| gemini-3.1-flash-lite_explicit | AccountUpdate                    | AccountQuestion                  |       2 |
| gpt-6-luna_explicit            | AcknowledgementOfGratitude       | UnclassifiableOther              |       4 |
| gpt-6-luna_explicit            | CardAccountClosure               | UnclassifiableOther              |       3 |
| gpt-6-luna_explicit            | CardIsNotWorking                 | UnclassifiableOther              |       3 |
| gpt-6-luna_explicit            | OnlineAccess                     | AccountCardLinkingforUnifiedView |       3 |
| gpt-6-luna_explicit            | AccountCardLinkingforUnifiedView | DigitalWalletSupport             |       2 |
| jev                            | ChangeNumber                     | PhoneNumberUpdate                |       4 |
| jev                            | CardAccountClosure               | UnclassifiableOther              |       3 |
| jev                            | CardIsNotWorking                 | UnclassifiableOther              |       3 |
| jev                            | OnlineAccess                     | AccountCardLinkingforUnifiedView |       3 |
| jev                            | AccountNumberInquiry             | ChangeCardOrAccountNumber        |       2 |

## Run configuration

```json
{
  "iterations": 2,
  "n_eval": 250,
  "n_calib": 50,
  "n_train": 2000,
  "seed": 42,
  "fewshot": false,
  "cache_mode": "explicit",
  "no_trace": false,
  "workers": 6,
  "skip": "",
  "hard_cap": 2.8,
  "agent_cost": 5.0,
  "misroute_cost": 10.0,
  "dry_run": false,
  "out": "results_ivr_final"
}
```

Raw per-call request/response/usage/cost records: `audit.jsonl`. Test data for every split: `data/iter*_{train,calib,eval}.jsonl`.
