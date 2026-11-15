# IVR intent comparison: complete run summary

Run `2026-10-21T23:22:59+00:00` to `2026-10-21T23:34:39+00:00`, runtime 700.1 s, status **completed**. Measured API spend **$1.6684** of a $2.80 hard cap (user limit $3). 2780 API calls in total.

## 1. Run design

- Iterations: **2** (iteration 1 = v1 prompts, iteration 2 = v2 prompts; JEV: Choice question v1 -> v2). Base seed 42, iteration seed = base + iteration.
- Per iteration and per system: **50 calibration calls** (threshold selection only) + **228 eval calls** (scored) = 278 calls; **556 calls per API system** in total, 456 of them scored.
- Systems: TF-IDF baseline (no API) + 5 API systems, run cheapest-first: gpt-6-luna, claude-haiku-5-5, jev, gemini-flash-lite, claude-sonnet-5-5. Cache mode: explicit (JEV exposes no cache controls).
- Intent catalog: **114 intents** -> 106 workflows (some near-synonym intents share a workflow). Train seeds are never used in eval (per-intent seed split).
- Apples to apples: every system received the identical calibration and eval calls each iteration (same XML, same expected intent), the same catalog, workflow map, threshold rule and scoring.

| iteration | seed | calibration calls | eval calls | intents appearing in eval | calibration set hash | eval set hash |
|---|---|---|---|---|---|---|
| 1 | 43 | 50 | 228 | 114 | 268fc8996e1e | 10d210ecab88 |
| 2 | 44 | 50 | 228 | 114 | 81c5d2a209d3 | 441e90a01a83 |

## 2. Calls, tokens and cost per system and iteration

| system                            |   iteration |   calibration_calls |   eval_calls |   errors |   input_tokens |   cache_read_tokens |   cache_write_tokens |   output_tokens |   cost_usd |   eval_latency_p50_s |   eval_latency_p95_s |
|:----------------------------------|------------:|--------------------:|-------------:|---------:|---------------:|--------------------:|---------------------:|----------------:|-----------:|---------------------:|---------------------:|
| gpt-6-luna_explicit_v1            |           1 |                  50 |          228 |        0 |         824092 |              775046 |                 2798 |           30739 |    0.02774 |                2.25  |                5.705 |
| claude-haiku-5-5_explicit_v1      |           1 |                  50 |          228 |        0 |        1630559 |             1562280 |                 5640 |           20327 |    0.03276 |                1.037 |                1.633 |
| jev_v1                            |           1 |                  50 |          228 |        0 |        1069328 |                   0 |                    0 |          404283 |    0.04491 |                0.184 |                0.238 |
| gemini-3.1-flash-lite_explicit_v1 |           1 |                  50 |          228 |        0 |         698179 |              653022 |                    0 |           12112 |    0.04578 |                0.952 |                1.319 |
| claude-sonnet-5-5_explicit_v1     |           1 |                  50 |          228 |        0 |        1630281 |             1562003 |                 5639 |           18862 |    0.6404  |                1.363 |                2.176 |
| gpt-6-luna_explicit_v2            |           2 |                  50 |          228 |        0 |         981595 |              931274 |                 3362 |           32122 |    0.03007 |                2.409 |                8.533 |
| claude-haiku-5-5_explicit_v2      |           2 |                  50 |          228 |        0 |        1911734 |             1842327 |                 6651 |           22038 |    0.03655 |                1.073 |                1.566 |
| jev_v2                            |           2 |                  50 |          228 |        0 |        1182355 |                   0 |                    0 |          404319 |    0.04966 |                0.183 |                0.237 |
| gemini-3.1-flash-lite_explicit_v2 |           2 |                  50 |          228 |        0 |         859840 |              814540 |                    0 |           12609 |    0.0506  |                0.952 |                1.386 |
| claude-sonnet-5-5_explicit_v2     |           2 |                  50 |          228 |        0 |        1912012 |             1842604 |                 6652 |           19790 |    0.70856 |                1.418 |                2.359 |

Totals per system:

| system                         |   calibration_calls |   eval_calls |   errors |   input_tokens |   cache_read_tokens |   cache_write_tokens |   output_tokens |   cost_usd |
|:-------------------------------|--------------------:|-------------:|---------:|---------------:|--------------------:|---------------------:|----------------:|-----------:|
| gpt-6-luna_explicit            |                 100 |          456 |        0 |        1805687 |             1706320 |                 6160 |           62861 |    0.05781 |
| claude-haiku-5-5_explicit      |                 100 |          456 |        0 |        3542293 |             3404607 |                12291 |           42365 |    0.06931 |
| jev                            |                 100 |          456 |        0 |        2251683 |                   0 |                    0 |          808602 |    0.09457 |
| gemini-3.1-flash-lite_explicit |                 100 |          456 |        0 |        1558019 |             1467562 |                    0 |           24721 |    0.09638 |
| claude-sonnet-5-5_explicit     |                 100 |          456 |        0 |        3542293 |             3404607 |                12291 |           38652 |    1.34896 |

## 3. System-level metrics (mean of the 2 iterations)

Headline table: calls per system, intents tested and the main metrics. `api_calls_total` = calibration + eval calls actually sent to the provider (TF-IDF is local, 0 API calls but scored on the same calibration and eval inputs). `calls_per_intent` = scored eval calls / intents tested.

| system                         |   api_calls_total |   calibration_calls |   eval_calls_scored |   iterations |   intents_tested |   calls_per_intent |   workflows_covered |   accuracy |   macro_f1 |   handled_correctly |   automation_rate |   misroute_rate |   latency_p50_s |   latency_p95_s |   cost_per_1k_usd |   total_cost_usd |
|:-------------------------------|------------------:|--------------------:|--------------------:|-------------:|-----------------:|-------------------:|--------------------:|-----------:|-----------:|--------------------:|------------------:|----------------:|----------------:|----------------:|------------------:|-----------------:|
| classic_tfidf_lr               |                 0 |                 100 |                 456 |            2 |              114 |                  4 |                 106 |      0.281 |      0.261 |               0.046 |             0.055 |           0.018 |           0     |           0     |             0     |            0     |
| gpt-6-luna_explicit            |               556 |                 100 |                 456 |            2 |              114 |                  4 |                 106 |      0.675 |      0.707 |               0.329 |             0.386 |           0.066 |           2.329 |           7.119 |             0.102 |            0.047 |
| claude-haiku-5-5_explicit      |               556 |                 100 |                 456 |            2 |              114 |                  4 |                 106 |      0.614 |      0.636 |               0.542 |             0.682 |           0.149 |           1.055 |           1.6   |             0.122 |            0.056 |
| jev                            |               556 |                 100 |                 456 |            2 |              114 |                  4 |                 106 |      0.649 |      0.672 |               0.463 |             0.55  |           0.096 |           0.184 |           0.237 |             0.17  |            0.078 |
| gemini-3.1-flash-lite_explicit |               556 |                 100 |                 456 |            2 |              114 |                  4 |                 106 |      0.636 |      0.65  |               0.557 |             0.781 |           0.232 |           0.952 |           1.353 |             0.176 |            0.08  |
| claude-sonnet-5-5_explicit     |               556 |                 100 |                 456 |            2 |              114 |                  4 |                 106 |      0.686 |      0.716 |               0.485 |             0.625 |           0.149 |           1.39  |           2.267 |             2.37  |            1.081 |

| family                         |   accuracy |   macro_f1 |   handled_correctly |   automation_rate |   auto_precision |   misroute_rate |   errors |
|:-------------------------------|-----------:|-----------:|--------------------:|------------------:|-----------------:|----------------:|---------:|
| gemini-3.1-flash-lite_explicit |      0.636 |      0.65  |               0.557 |             0.781 |            0.702 |           0.232 |        0 |
| claude-haiku-5-5_explicit      |      0.614 |      0.636 |               0.542 |             0.682 |            0.789 |           0.149 |        0 |
| claude-sonnet-5-5_explicit     |      0.686 |      0.716 |               0.485 |             0.625 |            0.792 |           0.149 |        0 |
| jev                            |      0.649 |      0.672 |               0.463 |             0.55  |            0.833 |           0.096 |        0 |
| gpt-6-luna_explicit            |      0.675 |      0.707 |               0.329 |             0.386 |            0.829 |           0.066 |        0 |
| classic_tfidf_lr               |      0.281 |      0.261 |               0.046 |             0.055 |            0.607 |           0.018 |        0 |

| family                         |   latency_p50_s |   latency_p95_s |   throughput_per_s |   cost_per_1k_usd |   cost_per_correct_call_usd |   total_cost_usd |   cached_input_share |
|:-------------------------------|----------------:|----------------:|-------------------:|------------------:|----------------------------:|-----------------:|---------------------:|
| gemini-3.1-flash-lite_explicit |         0.952   |         1.35265 |              5.935 |           0.1761  |                     0.00032 |          0.0803  |              0.94195 |
| claude-haiku-5-5_explicit      |         1.05493 |         1.59969 |              4.935 |           0.12201 |                     0.00022 |          0.05564 |              0.96462 |
| claude-sonnet-5-5_explicit     |         1.3902  |         2.26706 |              3.66  |           2.36998 |                     0.00509 |          1.08071 |              0.96462 |
| jev                            |         0.18365 |         0.23738 |             31.49  |           0.17009 |                     0.00037 |          0.07756 |              0       |
| gpt-6-luna_explicit            |         2.32947 |         7.11901 |              1.925 |           0.10222 |                     0.00032 |          0.04661 |              0.95163 |
| classic_tfidf_lr               |         6e-05   |         6e-05   |          22172.9   |           0       |                     0       |          0       |            nan       |

Per iteration:

|   iteration | system                            |   threshold |   accuracy |   macro_f1 |   handled_correctly |   automation_rate |   misroute_rate |   latency_p50_s |   cost_per_1k_usd |   errors |
|------------:|:----------------------------------|------------:|-----------:|-----------:|--------------------:|------------------:|----------------:|----------------:|------------------:|---------:|
|           1 | classic_tfidf_lr                  |        0.51 |      0.281 |      0.247 |               0.075 |             0.092 |           0.026 |           0     |             0     |        0 |
|           1 | gpt-6-luna_explicit_v1            |        0.96 |      0.702 |      0.73  |               0.276 |             0.325 |           0.057 |           2.25  |             0.098 |        0 |
|           1 | claude-haiku-5-5_explicit_v1      |        0.72 |      0.64  |      0.657 |               0.522 |             0.601 |           0.088 |           1.037 |             0.116 |        0 |
|           1 | jev_v1                            |        0.96 |      0.662 |      0.679 |               0.43  |             0.474 |           0.053 |           0.184 |             0.162 |        0 |
|           1 | gemini-3.1-flash-lite_explicit_v1 |        0.57 |      0.658 |      0.662 |               0.57  |             0.798 |           0.237 |           0.952 |             0.167 |        0 |
|           1 | claude-sonnet-5-5_explicit_v1     |        0.81 |      0.719 |      0.75  |               0.377 |             0.417 |           0.048 |           1.363 |             2.255 |        0 |
|           2 | classic_tfidf_lr                  |        0.81 |      0.281 |      0.274 |               0.018 |             0.018 |           0.009 |           0     |             0     |        0 |
|           2 | gpt-6-luna_explicit_v2            |        0.9  |      0.649 |      0.683 |               0.382 |             0.447 |           0.075 |           2.409 |             0.106 |        0 |
|           2 | claude-haiku-5-5_explicit_v2      |        0.48 |      0.588 |      0.615 |               0.561 |             0.763 |           0.211 |           1.073 |             0.129 |        0 |
|           2 | jev_v2                            |        0.78 |      0.636 |      0.665 |               0.496 |             0.627 |           0.14  |           0.183 |             0.179 |        0 |
|           2 | gemini-3.1-flash-lite_explicit_v2 |        0.72 |      0.614 |      0.638 |               0.544 |             0.763 |           0.228 |           0.952 |             0.185 |        0 |
|           2 | claude-sonnet-5-5_explicit_v2     |        0.51 |      0.654 |      0.681 |               0.592 |             0.833 |           0.25  |           1.418 |             2.485 |        0 |

## 4. Which intents ran, and was it uniform?

- Intents with at least one eval call: **114 of 114** (per iteration: 114, 114). Calls per covered intent over both iterations: min 4, median 4, max 4, total 456.
- Uniformity check: for **114 of 114** covered intents every system (including TF-IDF) was scored on exactly the same number of calls: YES, all systems ran the same calls.
- Not sampled in either eval set (0): none.
- Sampling was stratified: every intent got exactly the same number of eval calls.

Calls-per-intent distribution (eval calls over both iterations -> number of intents):

| calls for the intent | 4 |
|---|---|
| intents | 114 |

## 5. Per-intent results (exact-intent accuracy, eval calls)

Columns: calls per iteration and total (same for every system), then exact-intent accuracy per system (share of that intent's calls where the predicted intent equals the expected one). `mean5` = mean of the five API systems. Intents never sampled are omitted.

| intent                               | workflow              |   calls it1 |   calls it2 |   calls total | classic_tfidf_lr   | gpt-6-luna   | claude-haiku-5-5   | jev   | gemini-flash-lite   | claude-sonnet-5-5   | mean5   |
|:-------------------------------------|:----------------------|------------:|------------:|--------------:|:-------------------|:-------------|:-------------------|:------|:--------------------|:--------------------|:--------|
| BalanceQuestion                      | wf_balance            |           2 |           2 |             4 | 50%                | 100%         | 100%               | 75%   | 100%                | 100%                | 95%     |
| BalanceValueInquiry                  | wf_balance            |           2 |           2 |             4 | 0%                 | 75%          | 50%                | 75%   | 75%                 | 75%                 | 70%     |
| ReviewMultipleTransactions           | wf_transactions       |           2 |           2 |             4 | 50%                | 100%         | 100%               | 100%  | 100%                | 100%                | 100%    |
| TransactionQuestion                  | wf_transactions       |           2 |           2 |             4 | 0%                 | 75%          | 100%               | 100%  | 100%                | 75%                 | 90%     |
| ReviewCredits                        | wf_credits            |           2 |           2 |             4 | 25%                | 50%          | 75%                | 75%   | 75%                 | 75%                 | 70%     |
| PaymentVerification                  | wf_payment_verify     |           2 |           2 |             4 | 0%                 | 100%         | 75%                | 75%   | 50%                 | 100%                | 80%     |
| PaymentMethodOptionsInquiry          | wf_payment_options    |           2 |           2 |             4 | 0%                 | 100%         | 50%                | 25%   | 75%                 | 100%                | 70%     |
| OnlinePaymentMethodInquiry           | wf_payment_options    |           2 |           2 |             4 | 0%                 | 75%          | 75%                | 75%   | 100%                | 75%                 | 80%     |
| PhonePaymentFeeInquiry               | wf_phone_pay_fee      |           2 |           2 |             4 | 50%                | 75%          | 75%                | 75%   | 75%                 | 75%                 | 75%     |
| PaymentAddressInquiry                | wf_payment_address    |           2 |           2 |             4 | 25%                | 100%         | 100%               | 75%   | 100%                | 100%                | 95%     |
| PayoffInquiry                        | wf_payoff             |           2 |           2 |             4 | 50%                | 50%          | 75%                | 75%   | 75%                 | 75%                 | 70%     |
| PaymentDueDateModification           | wf_due_date_change    |           2 |           2 |             4 | 75%                | 75%          | 50%                | 75%   | 75%                 | 75%                 | 70%     |
| BillingQuestion                      | wf_billing            |           2 |           2 |             4 | 0%                 | 75%          | 100%               | 100%  | 100%                | 50%                 | 85%     |
| BillDiscrepancy                      | wf_bill_dispute       |           2 |           2 |             4 | 25%                | 25%          | 25%                | 25%   | 25%                 | 75%                 | 35%     |
| StatementCopy                        | wf_statement          |           2 |           2 |             4 | 75%                | 75%          | 75%                | 75%   | 50%                 | 75%                 | 70%     |
| StatementInquiry                     | wf_statement          |           2 |           2 |             4 | 50%                | 75%          | 0%                 | 50%   | 50%                 | 100%                | 55%     |
| YearEndStatementInquiry              | wf_year_end           |           2 |           2 |             4 | 25%                | 50%          | 50%                | 50%   | 50%                 | 50%                 | 50%     |
| FraudulentActivity                   | wf_fraud              |           2 |           2 |             4 | 0%                 | 75%          | 75%                | 75%   | 75%                 | 75%                 | 75%     |
| ReportLostCard                       | wf_lost_card          |           2 |           2 |             4 | 25%                | 50%          | 50%                | 50%   | 50%                 | 50%                 | 50%     |
| CardLockUnlock                       | wf_card_lock          |           2 |           2 |             4 | 25%                | 75%          | 100%               | 100%  | 100%                | 100%                | 95%     |
| CardActivation                       | wf_activate           |           2 |           2 |             4 | 50%                | 100%         | 50%                | 75%   | 50%                 | 100%                | 75%     |
| CardFacePhotoIssue                   | wf_card_photo         |           2 |           2 |             4 | 0%                 | 75%          | 75%                | 75%   | 75%                 | 75%                 | 75%     |
| AuthorizedUserManagement             | wf_auth_user          |           2 |           2 |             4 | 75%                | 75%          | 75%                | 75%   | 75%                 | 75%                 | 75%     |
| AdditionalCardManagement             | wf_additional_card    |           2 |           2 |             4 | 50%                | 50%          | 50%                | 75%   | 75%                 | 50%                 | 60%     |
| DigitalWalletSupport                 | wf_wallet             |           2 |           2 |             4 | 50%                | 100%         | 100%               | 100%  | 100%                | 100%                | 100%    |
| OnlineAccess                         | wf_online_access      |           2 |           2 |             4 | 0%                 | 100%         | 50%                | 75%   | 100%                | 75%                 | 80%     |
| OnlineRegistrationSetup              | wf_online_reg         |           2 |           2 |             4 | 25%                | 50%          | 50%                | 50%   | 75%                 | 50%                 | 55%     |
| AccountCardLinkingforUnifiedView     | wf_card_linking       |           2 |           2 |             4 | 0%                 | 50%          | 0%                 | 25%   | 50%                 | 50%                 | 35%     |
| GeneralRewardsInformationInquiry     | wf_rewards_info       |           2 |           2 |             4 | 0%                 | 50%          | 25%                | 0%    | 25%                 | 25%                 | 25%     |
| GeneralRewardsFAQ                    | wf_rewards_info       |           2 |           2 |             4 | 25%                | 100%         | 100%               | 100%  | 100%                | 100%                | 100%    |
| AmbiguousRewardsRequest              | wf_rewards_clarify    |           2 |           2 |             4 | 0%                 | 100%         | 100%               | 100%  | 100%                | 100%                | 100%    |
| RewardsProgramEnrollment             | wf_rewards_enroll     |           2 |           2 |             4 | 50%                | 50%          | 75%                | 75%   | 75%                 | 75%                 | 70%     |
| RewardsRedemptionRequest             | wf_rewards_redeem     |           2 |           2 |             4 | 75%                | 75%          | 75%                | 100%  | 50%                 | 50%                 | 70%     |
| ExternalRewardsProgramLinkingInquiry | wf_rewards_link       |           2 |           2 |             4 | 0%                 | 50%          | 50%                | 50%   | 50%                 | 50%                 | 50%     |
| NightsInquiry                    | wf_nights        |           2 |           2 |             4 | 50%                | 50%          | 50%                | 50%   | 50%                 | 50%                 | 50%     |
| InitiateANewBalanceTransfer          | wf_bt_start           |           2 |           2 |             4 | 0%                 | 75%          | 50%                | 75%   | 50%                 | 50%                 | 60%     |
| StatusOfBalanceTransfer              | wf_bt_status          |           2 |           2 |             4 | 25%                | 75%          | 75%                | 75%   | 75%                 | 75%                 | 75%     |
| BalanceTransferGeneralInquiry        | wf_bt_info            |           2 |           2 |             4 | 25%                | 75%          | 75%                | 50%   | 75%                 | 75%                 | 70%     |
| InterestInquiry                      | wf_interest           |           2 |           2 |             4 | 0%                 | 100%         | 100%               | 100%  | 100%                | 100%                | 100%    |
| FeeInquiryManagement                 | wf_fees               |           2 |           2 |             4 | 25%                | 75%          | 75%                | 100%  | 100%                | 100%                | 90%     |
| CashAdvanceInquiry                   | wf_cash_advance       |           2 |           2 |             4 | 100%               | 100%         | 100%               | 100%  | 100%                | 100%                | 100%    |
| CreditScoreReportInquiry             | wf_credit_report      |           2 |           2 |             4 | 0%                 | 50%          | 25%                | 25%   | 50%                 | 50%                 | 40%     |
| CRSRequests                          | wf_crs                |           2 |           2 |             4 | 0%                 | 75%          | 75%                | 75%   | 75%                 | 75%                 | 75%     |
| CreditQuestion                       | wf_credit_q           |           2 |           2 |             4 | 25%                | 100%         | 100%               | 75%   | 100%                | 100%                | 95%     |
| AccountStatusInquiry                 | wf_account_status     |           2 |           2 |             4 | 75%                | 100%         | 75%                | 75%   | 75%                 | 100%                | 85%     |
| AccountProblemInquiry                | wf_account_problem    |           2 |           2 |             4 | 75%                | 50%          | 50%                | 50%   | 25%                 | 50%                 | 45%     |
| AccountQuestion                      | wf_account_q          |           2 |           2 |             4 | 0%                 | 25%          | 25%                | 25%   | 75%                 | 25%                 | 35%     |
| AccountNumberInquiry                 | wf_account_number     |           2 |           2 |             4 | 25%                | 50%          | 50%                | 50%   | 50%                 | 50%                 | 50%     |
| SecuredCardInquiry                   | wf_secured_card       |           2 |           2 |             4 | 25%                | 100%         | 75%                | 75%   | 50%                 | 100%                | 80%     |
| ProductChangeUpgradeDowngrade        | wf_product_change     |           2 |           2 |             4 | 0%                 | 25%          | 0%                 | 25%   | 0%                  | 25%                 | 15%     |
| CardAccountClosure                   | wf_closure            |           2 |           2 |             4 | 0%                 | 100%         | 75%                | 75%   | 100%                | 100%                | 90%     |
| LargePurchaseNotification            | wf_large_purchase     |           2 |           2 |             4 | 0%                 | 75%          | 75%                | 75%   | 75%                 | 75%                 | 75%     |
| AuthorizationInquiryRequest          | wf_authorization      |           2 |           2 |             4 | 50%                | 75%          | 75%                | 50%   | 75%                 | 75%                 | 70%     |
| ConciergeTravelAssistance            | wf_concierge          |           2 |           2 |             4 | 0%                 | 50%          | 50%                | 50%   | 25%                 | 50%                 | 45%     |
| DebitCardInquiryManagement           | wf_debit_transfer     |           2 |           2 |             4 | 75%                | 50%          | 50%                | 25%   | 25%                 | 50%                 | 40%     |
| MortgageInquiryManagement            | wf_mortgage_transfer  |           2 |           2 |             4 | 0%                 | 50%          | 75%                | 50%   | 50%                 | 75%                 | 60%     |
| BankAccountInformationManagement     | wf_bank_account       |           2 |           2 |             4 | 25%                | 25%          | 25%                | 25%   | 25%                 | 50%                 | 30%     |
| ContactFollowUp                      | wf_followup           |           2 |           2 |             4 | 0%                 | 50%          | 50%                | 50%   | 50%                 | 50%                 | 50%     |
| ShopProgramInquiry               | wf_shop          |           2 |           2 |             4 | 75%                | 75%          | 75%                | 75%   | 75%                 | 75%                 | 75%     |
| DeceasedAccountHolderNotification    | wf_deceased           |           2 |           2 |             4 | 25%                | 75%          | 50%                | 75%   | 75%                 | 75%                 | 70%     |
| CancelBalanceTransfer                | wf_bt_cancel          |           2 |           2 |             4 | 50%                | 50%          | 50%                | 50%   | 50%                 | 50%                 | 50%     |
| CancelAutoPay                        | wf_autopay            |           2 |           2 |             4 | 0%                 | 100%         | 100%               | 100%  | 100%                | 100%                | 100%    |
| AutoPayManagement                    | wf_autopay            |           2 |           2 |             4 | 0%                 | 50%          | 25%                | 25%   | 25%                 | 25%                 | 30%     |
| ChangeCardOrAccountNumber            | wf_change_card_number |           2 |           2 |             4 | 25%                | 75%          | 75%                | 75%   | 50%                 | 75%                 | 70%     |
| ChangeNumber                         | wf_change_number      |           2 |           2 |             4 | 0%                 | 0%           | 25%                | 0%    | 0%                  | 50%                 | 15%     |
| AddressPersonalInfoChange            | wf_update_address     |           2 |           2 |             4 | 50%                | 100%         | 75%                | 75%   | 100%                | 75%                 | 85%     |
| AddressVerificationInquiry           | wf_address_verify     |           2 |           2 |             4 | 0%                 | 75%          | 25%                | 100%  | 50%                 | 75%                 | 65%     |
| PhoneNumberUpdate                    | wf_update_phone       |           2 |           2 |             4 | 25%                | 25%          | 25%                | 25%   | 25%                 | 25%                 | 25%     |
| EmailAddressUpdate                   | wf_update_email       |           2 |           2 |             4 | 75%                | 100%         | 100%               | 100%  | 100%                | 100%                | 100%    |
| NameChangeRequest                    | wf_update_name        |           2 |           2 |             4 | 50%                | 25%          | 25%                | 50%   | 25%                 | 50%                 | 35%     |
| IncomeInformationUpdate              | wf_update_income      |           2 |           2 |             4 | 50%                | 75%          | 75%                | 75%   | 75%                 | 75%                 | 75%     |
| AccountUpdate                        | wf_account_update     |           2 |           2 |             4 | 25%                | 75%          | 75%                | 50%   | 50%                 | 75%                 | 65%     |
| PasswordResetManagement              | wf_password           |           2 |           2 |             4 | 50%                | 75%          | 50%                | 50%   | 75%                 | 75%                 | 65%     |
| PinManagement                        | wf_pin                |           2 |           2 |             4 | 75%                | 75%          | 75%                | 75%   | 75%                 | 75%                 | 75%     |
| DisputeATransaction                  | wf_dispute            |           2 |           2 |             4 | 0%                 | 50%          | 75%                | 50%   | 50%                 | 50%                 | 55%     |
| CheckStatusofExistingDispute         | wf_dispute_status     |           2 |           2 |             4 | 50%                | 50%          | 50%                | 50%   | 50%                 | 50%                 | 50%     |
| CancelRecurringCharges               | wf_recurring_charge   |           2 |           2 |             4 | 0%                 | 50%          | 25%                | 50%   | 25%                 | 50%                 | 40%     |
| CancelStopPayment                    | wf_cancel_payment     |           2 |           2 |             4 | 0%                 | 50%          | 50%                | 50%   | 50%                 | 50%                 | 50%     |
| ReportStolenCard                     | wf_lost_card          |           2 |           2 |             4 | 25%                | 50%          | 50%                | 50%   | 50%                 | 50%                 | 50%     |
| CardIsNotWorking                     | wf_card_not_working   |           2 |           2 |             4 | 25%                | 75%          | 75%                | 75%   | 75%                 | 75%                 | 75%     |
| TransactionDeclined                  | wf_declined           |           2 |           2 |             4 | 50%                | 50%          | 50%                | 50%   | 50%                 | 50%                 | 50%     |
| CardExpirationRenewal                | wf_card_renewal       |           2 |           2 |             4 | 25%                | 0%           | 0%                 | 0%    | 0%                  | 0%                  | 0%      |
| DamagedCardReplacement               | wf_replace_card       |           2 |           2 |             4 | 0%                 | 25%          | 25%                | 25%   | 25%                 | 50%                 | 30%     |
| CardNotReceivedInquiry               | wf_card_delivery      |           2 |           2 |             4 | 0%                 | 75%          | 75%                | 100%  | 75%                 | 100%                | 85%     |
| InitiateNewCardApplication           | wf_application        |           2 |           2 |             4 | 0%                 | 75%          | 50%                | 75%   | 75%                 | 75%                 | 70%     |
| LoanInquiryManagement                | wf_loan_transfer      |           2 |           2 |             4 | 0%                 | 50%          | 50%                | 25%   | 25%                 | 25%                 | 35%     |
| GeneralCheckInquiry                  | wf_check_inquiry      |           2 |           2 |             4 | 50%                | 75%          | 75%                | 100%  | 75%                 | 75%                 | 80%     |
| MultiAccountCardManagement           | wf_multi_account      |           2 |           2 |             4 | 0%                 | 25%          | 25%                | 75%   | 50%                 | 50%                 | 45%     |
| AccountDebtConsolidation             | wf_debt_consolidation |           2 |           2 |             4 | 25%                | 75%          | 75%                | 75%   | 50%                 | 50%                 | 65%     |
| MembershipManagement                 | wf_membership         |           2 |           2 |             4 | 100%               | 100%         | 100%               | 100%  | 100%                | 100%                | 100%    |
| VirtualAccountCardManagement         | wf_virtual_card       |           2 |           2 |             4 | 25%                | 75%          | 50%                | 75%   | 75%                 | 75%                 | 70%     |
| GiftCardInquiryManagement            | wf_gift_card          |           2 |           2 |             4 | 50%                | 50%          | 25%                | 50%   | 50%                 | 50%                 | 45%     |
| RebateInquiryAndManagement           | wf_rebate             |           2 |           2 |             4 | 0%                 | 50%          | 25%                | 25%   | 25%                 | 50%                 | 35%     |
| RewardsCertificateRegeneration       | wf_rewards_cert       |           2 |           2 |             4 | 25%                | 75%          | 50%                | 75%   | 75%                 | 75%                 | 70%     |
| RewardsBalanceInquiry                | wf_rewards_balance    |           2 |           2 |             4 | 0%                 | 100%         | 25%                | 100%  | 75%                 | 75%                 | 75%     |
| PromotionInquiry                     | wf_promo              |           2 |           2 |             4 | 0%                 | 75%          | 75%                | 100%  | 75%                 | 75%                 | 80%     |
| MinimumPaymentCalculation            | wf_min_payment        |           2 |           2 |             4 | 25%                | 50%          | 50%                | 50%   | 50%                 | 50%                 | 50%     |
| OverpaymentDuplicatePaymentInquiry   | wf_overpayment        |           2 |           2 |             4 | 0%                 | 100%         | 75%                | 100%  | 100%                | 100%                | 95%     |
| PaymentAssistanceFinancialHardship   | wf_hardship           |           2 |           2 |             4 | 25%                | 100%         | 100%               | 100%  | 100%                | 100%                | 100%    |
| DocumentRequestInquiry               | wf_document_request   |           2 |           2 |             4 | 0%                 | 75%          | 75%                | 75%   | 75%                 | 75%                 | 75%     |
| DisasterReliefInquiry                | wf_disaster_relief    |           2 |           2 |             4 | 0%                 | 75%          | 75%                | 75%   | 75%                 | 75%                 | 75%     |
| BranchATMLocationANDIssueInquiry     | wf_branch             |           2 |           2 |             4 | 25%                | 50%          | 50%                | 25%   | 25%                 | 25%                 | 35%     |
| OnlineTransactionInquiry             | wf_online_txn         |           2 |           2 |             4 | 50%                | 75%          | 50%                | 75%   | 25%                 | 75%                 | 60%     |
| BalanceAndMakePayment                | wf_balance_pay        |           2 |           2 |             4 | 50%                | 75%          | 50%                | 100%  | 100%                | 75%                 | 80%     |
| OtherLanguageRequest                 | wf_other_language     |           2 |           2 |             4 | 25%                | 50%          | 50%                | 50%   | 50%                 | 50%                 | 50%     |
| IVRNavigationRestart                 | wf_menu_restart       |           2 |           2 |             4 | 100%               | 50%          | 50%                | 100%  | 50%                 | 50%                 | 60%     |
| ConversationHoldOn                   | wf_hold               |           2 |           2 |             4 | 50%                | 75%          | 75%                | 50%   | 75%                 | 75%                 | 70%     |
| PaperlessManagement                  | wf_paperless          |           2 |           2 |             4 | 75%                | 75%          | 75%                | 75%   | 75%                 | 75%                 | 75%     |
| UnclassifiableOther                  | wf_out_of_scope       |           2 |           2 |             4 | 0%                 | 75%          | 75%                | 75%   | 75%                 | 100%                | 80%     |
| RequestARepresentative               | live_agent_queue      |           2 |           2 |             4 | 75%                | 100%         | 100%               | 100%  | 100%                | 100%                | 100%    |
| RepeatVerbiage                       | wf_repeat             |           2 |           2 |             4 | 50%                | 50%          | 50%                | 25%   | 25%                 | 25%                 | 35%     |
| EnglishLanguageRequest               | wf_english            |           2 |           2 |             4 | 75%                | 100%         | 75%                | 50%   | 50%                 | 75%                 | 70%     |
| AcknowledgementOfGratitude           | wf_end_call           |           2 |           2 |             4 | 0%                 | 50%          | 100%               | 50%   | 25%                 | 50%                 | 55%     |
| InteractionComplete                  | wf_end_call           |           2 |           2 |             4 | 0%                 | 25%          | 50%                | 25%   | 50%                 | 50%                 | 40%     |

## 6. Per-intent handled-correctly (right workflow / agent transfer at the tuned threshold)

| intent                               |   calls total | classic_tfidf_lr   | gpt-6-luna   | claude-haiku-5-5   | jev   | gemini-flash-lite   | claude-sonnet-5-5   |
|:-------------------------------------|--------------:|:-------------------|:-------------|:-------------------|:------|:--------------------|:--------------------|
| BalanceQuestion                      |             4 | 0%                 | 50%          | 75%                | 50%   | 100%                | 75%                 |
| BalanceValueInquiry                  |             4 | 0%                 | 50%          | 75%                | 50%   | 75%                 | 25%                 |
| ReviewMultipleTransactions           |             4 | 0%                 | 50%          | 100%               | 75%   | 75%                 | 100%                |
| TransactionQuestion                  |             4 | 0%                 | 25%          | 75%                | 50%   | 75%                 | 50%                 |
| ReviewCredits                        |             4 | 0%                 | 25%          | 25%                | 50%   | 25%                 | 25%                 |
| PaymentVerification                  |             4 | 0%                 | 0%           | 50%                | 0%    | 50%                 | 50%                 |
| PaymentMethodOptionsInquiry          |             4 | 0%                 | 25%          | 75%                | 0%    | 75%                 | 25%                 |
| OnlinePaymentMethodInquiry           |             4 | 0%                 | 25%          | 75%                | 75%   | 75%                 | 75%                 |
| PhonePaymentFeeInquiry               |             4 | 25%                | 75%          | 75%                | 75%   | 75%                 | 75%                 |
| PaymentAddressInquiry                |             4 | 0%                 | 50%          | 100%               | 50%   | 100%                | 75%                 |
| PayoffInquiry                        |             4 | 0%                 | 50%          | 50%                | 75%   | 75%                 | 50%                 |
| PaymentDueDateModification           |             4 | 0%                 | 75%          | 50%                | 75%   | 75%                 | 75%                 |
| BillingQuestion                      |             4 | 0%                 | 0%           | 50%                | 25%   | 75%                 | 0%                  |
| BillDiscrepancy                      |             4 | 0%                 | 25%          | 25%                | 25%   | 25%                 | 25%                 |
| StatementCopy                        |             4 | 25%                | 50%          | 75%                | 50%   | 75%                 | 50%                 |
| StatementInquiry                     |             4 | 0%                 | 0%           | 25%                | 25%   | 25%                 | 50%                 |
| YearEndStatementInquiry              |             4 | 0%                 | 50%          | 50%                | 50%   | 50%                 | 50%                 |
| FraudulentActivity                   |             4 | 0%                 | 50%          | 75%                | 75%   | 75%                 | 75%                 |
| ReportLostCard                       |             4 | 0%                 | 25%          | 50%                | 25%   | 50%                 | 50%                 |
| CardLockUnlock                       |             4 | 0%                 | 75%          | 75%                | 75%   | 100%                | 75%                 |
| CardActivation                       |             4 | 25%                | 25%          | 25%                | 50%   | 50%                 | 50%                 |
| CardFacePhotoIssue                   |             4 | 0%                 | 75%          | 75%                | 75%   | 75%                 | 75%                 |
| AuthorizedUserManagement             |             4 | 25%                | 75%          | 75%                | 75%   | 75%                 | 75%                 |
| AdditionalCardManagement             |             4 | 0%                 | 25%          | 50%                | 50%   | 75%                 | 50%                 |
| DigitalWalletSupport                 |             4 | 0%                 | 50%          | 100%               | 100%  | 100%                | 100%                |
| OnlineAccess                         |             4 | 0%                 | 50%          | 50%                | 50%   | 75%                 | 50%                 |
| OnlineRegistrationSetup              |             4 | 0%                 | 25%          | 50%                | 25%   | 50%                 | 50%                 |
| AccountCardLinkingforUnifiedView     |             4 | 0%                 | 0%           | 0%                 | 0%    | 50%                 | 25%                 |
| GeneralRewardsInformationInquiry     |             4 | 0%                 | 0%           | 0%                 | 0%    | 0%                  | 0%                  |
| GeneralRewardsFAQ                    |             4 | 0%                 | 50%          | 100%               | 75%   | 100%                | 75%                 |
| AmbiguousRewardsRequest              |             4 | 0%                 | 0%           | 50%                | 0%    | 75%                 | 50%                 |
| RewardsProgramEnrollment             |             4 | 25%                | 25%          | 75%                | 50%   | 75%                 | 50%                 |
| RewardsRedemptionRequest             |             4 | 0%                 | 25%          | 25%                | 50%   | 25%                 | 25%                 |
| ExternalRewardsProgramLinkingInquiry |             4 | 0%                 | 50%          | 50%                | 50%   | 50%                 | 50%                 |
| NightsInquiry                    |             4 | 0%                 | 50%          | 50%                | 50%   | 50%                 | 50%                 |
| InitiateANewBalanceTransfer          |             4 | 0%                 | 50%          | 50%                | 50%   | 25%                 | 50%                 |
| StatusOfBalanceTransfer              |             4 | 0%                 | 25%          | 50%                | 50%   | 75%                 | 75%                 |
| BalanceTransferGeneralInquiry        |             4 | 0%                 | 0%           | 50%                | 25%   | 50%                 | 25%                 |
| InterestInquiry                      |             4 | 0%                 | 50%          | 100%               | 100%  | 100%                | 75%                 |
| FeeInquiryManagement                 |             4 | 25%                | 75%          | 75%                | 75%   | 75%                 | 75%                 |
| CashAdvanceInquiry                   |             4 | 25%                | 75%          | 100%               | 100%  | 100%                | 100%                |
| CreditScoreReportInquiry             |             4 | 0%                 | 0%           | 25%                | 25%   | 25%                 | 25%                 |
| CRSRequests                          |             4 | 0%                 | 50%          | 75%                | 75%   | 75%                 | 50%                 |
| CreditQuestion                       |             4 | 0%                 | 50%          | 100%               | 50%   | 75%                 | 75%                 |
| AccountStatusInquiry                 |             4 | 25%                | 0%           | 50%                | 25%   | 75%                 | 50%                 |
| AccountProblemInquiry                |             4 | 0%                 | 25%          | 50%                | 50%   | 25%                 | 25%                 |
| AccountQuestion                      |             4 | 0%                 | 0%           | 0%                 | 0%    | 25%                 | 0%                  |
| AccountNumberInquiry                 |             4 | 0%                 | 50%          | 50%                | 50%   | 50%                 | 50%                 |
| SecuredCardInquiry                   |             4 | 0%                 | 100%         | 75%                | 50%   | 50%                 | 100%                |
| ProductChangeUpgradeDowngrade        |             4 | 0%                 | 0%           | 0%                 | 25%   | 0%                  | 0%                  |
| CardAccountClosure                   |             4 | 0%                 | 75%          | 75%                | 75%   | 100%                | 75%                 |
| LargePurchaseNotification            |             4 | 0%                 | 50%          | 75%                | 50%   | 75%                 | 50%                 |
| AuthorizationInquiryRequest          |             4 | 0%                 | 25%          | 50%                | 50%   | 50%                 | 50%                 |
| ConciergeTravelAssistance            |             4 | 0%                 | 0%           | 50%                | 0%    | 0%                  | 50%                 |
| DebitCardInquiryManagement           |             4 | 25%                | 25%          | 50%                | 0%    | 25%                 | 50%                 |
| MortgageInquiryManagement            |             4 | 0%                 | 25%          | 50%                | 50%   | 50%                 | 50%                 |
| BankAccountInformationManagement     |             4 | 0%                 | 25%          | 25%                | 25%   | 25%                 | 25%                 |
| ContactFollowUp                      |             4 | 0%                 | 25%          | 25%                | 25%   | 25%                 | 25%                 |
| ShopProgramInquiry               |             4 | 0%                 | 50%          | 50%                | 50%   | 75%                 | 50%                 |
| DeceasedAccountHolderNotification    |             4 | 0%                 | 25%          | 25%                | 50%   | 50%                 | 50%                 |
| CancelBalanceTransfer                |             4 | 0%                 | 50%          | 50%                | 50%   | 50%                 | 50%                 |
| CancelAutoPay                        |             4 | 0%                 | 75%          | 100%               | 100%  | 100%                | 100%                |
| AutoPayManagement                    |             4 | 0%                 | 0%           | 25%                | 25%   | 25%                 | 25%                 |
| ChangeCardOrAccountNumber            |             4 | 0%                 | 25%          | 75%                | 50%   | 50%                 | 50%                 |
| ChangeNumber                         |             4 | 0%                 | 0%           | 25%                | 0%    | 0%                  | 25%                 |
| AddressPersonalInfoChange            |             4 | 25%                | 50%          | 50%                | 50%   | 75%                 | 50%                 |
| AddressVerificationInquiry           |             4 | 0%                 | 25%          | 25%                | 0%    | 50%                 | 50%                 |
| PhoneNumberUpdate                    |             4 | 25%                | 25%          | 25%                | 25%   | 25%                 | 25%                 |
| EmailAddressUpdate                   |             4 | 0%                 | 75%          | 100%               | 100%  | 100%                | 100%                |
| NameChangeRequest                    |             4 | 25%                | 25%          | 25%                | 50%   | 25%                 | 25%                 |
| IncomeInformationUpdate              |             4 | 0%                 | 50%          | 75%                | 75%   | 75%                 | 75%                 |
| AccountUpdate                        |             4 | 0%                 | 0%           | 50%                | 25%   | 25%                 | 25%                 |
| PasswordResetManagement              |             4 | 0%                 | 0%           | 50%                | 0%    | 50%                 | 25%                 |
| PinManagement                        |             4 | 0%                 | 50%          | 75%                | 75%   | 75%                 | 50%                 |
| DisputeATransaction                  |             4 | 0%                 | 25%          | 50%                | 50%   | 50%                 | 50%                 |
| CheckStatusofExistingDispute         |             4 | 0%                 | 50%          | 50%                | 50%   | 50%                 | 50%                 |
| CancelRecurringCharges               |             4 | 0%                 | 0%           | 25%                | 0%    | 25%                 | 25%                 |
| CancelStopPayment                    |             4 | 0%                 | 25%          | 50%                | 25%   | 50%                 | 25%                 |
| ReportStolenCard                     |             4 | 0%                 | 25%          | 50%                | 50%   | 50%                 | 25%                 |
| CardIsNotWorking                     |             4 | 25%                | 25%          | 75%                | 50%   | 75%                 | 75%                 |
| TransactionDeclined                  |             4 | 0%                 | 50%          | 50%                | 50%   | 50%                 | 50%                 |
| CardExpirationRenewal                |             4 | 0%                 | 0%           | 0%                 | 0%    | 0%                  | 0%                  |
| DamagedCardReplacement               |             4 | 0%                 | 0%           | 25%                | 0%    | 0%                  | 0%                  |
| CardNotReceivedInquiry               |             4 | 0%                 | 0%           | 75%                | 50%   | 50%                 | 75%                 |
| InitiateNewCardApplication           |             4 | 0%                 | 25%          | 50%                | 75%   | 50%                 | 50%                 |
| LoanInquiryManagement                |             4 | 0%                 | 0%           | 50%                | 25%   | 25%                 | 0%                  |
| GeneralCheckInquiry                  |             4 | 0%                 | 50%          | 50%                | 50%   | 50%                 | 50%                 |
| MultiAccountCardManagement           |             4 | 0%                 | 0%           | 25%                | 25%   | 50%                 | 0%                  |
| AccountDebtConsolidation             |             4 | 0%                 | 25%          | 75%                | 25%   | 50%                 | 25%                 |
| MembershipManagement                 |             4 | 25%                | 25%          | 75%                | 25%   | 100%                | 75%                 |
| VirtualAccountCardManagement         |             4 | 0%                 | 25%          | 50%                | 50%   | 50%                 | 50%                 |
| GiftCardInquiryManagement            |             4 | 0%                 | 0%           | 25%                | 25%   | 25%                 | 0%                  |
| RebateInquiryAndManagement           |             4 | 0%                 | 0%           | 0%                 | 25%   | 0%                  | 25%                 |
| RewardsCertificateRegeneration       |             4 | 0%                 | 25%          | 25%                | 25%   | 50%                 | 75%                 |
| RewardsBalanceInquiry                |             4 | 0%                 | 0%           | 25%                | 75%   | 75%                 | 50%                 |
| PromotionInquiry                     |             4 | 0%                 | 25%          | 50%                | 75%   | 50%                 | 50%                 |
| MinimumPaymentCalculation            |             4 | 0%                 | 25%          | 50%                | 25%   | 50%                 | 50%                 |
| OverpaymentDuplicatePaymentInquiry   |             4 | 0%                 | 25%          | 75%                | 75%   | 100%                | 50%                 |
| PaymentAssistanceFinancialHardship   |             4 | 0%                 | 25%          | 100%               | 100%  | 100%                | 75%                 |
| DocumentRequestInquiry               |             4 | 0%                 | 25%          | 75%                | 75%   | 75%                 | 25%                 |
| DisasterReliefInquiry                |             4 | 0%                 | 75%          | 75%                | 50%   | 75%                 | 75%                 |
| BranchATMLocationANDIssueInquiry     |             4 | 0%                 | 50%          | 25%                | 25%   | 25%                 | 25%                 |
| OnlineTransactionInquiry             |             4 | 0%                 | 50%          | 25%                | 50%   | 25%                 | 50%                 |
| BalanceAndMakePayment                |             4 | 0%                 | 50%          | 50%                | 75%   | 75%                 | 50%                 |
| OtherLanguageRequest                 |             4 | 0%                 | 25%          | 25%                | 50%   | 50%                 | 25%                 |
| IVRNavigationRestart                 |             4 | 25%                | 25%          | 50%                | 50%   | 50%                 | 50%                 |
| ConversationHoldOn                   |             4 | 0%                 | 25%          | 75%                | 50%   | 50%                 | 25%                 |
| PaperlessManagement                  |             4 | 0%                 | 50%          | 75%                | 75%   | 75%                 | 75%                 |
| UnclassifiableOther                  |             4 | 0%                 | 50%          | 50%                | 75%   | 75%                 | 75%                 |
| RequestARepresentative               |             4 | 100%               | 100%         | 100%               | 100%  | 100%                | 100%                |
| RepeatVerbiage                       |             4 | 25%                | 0%           | 50%                | 25%   | 25%                 | 25%                 |
| EnglishLanguageRequest               |             4 | 25%                | 50%          | 75%                | 50%   | 50%                 | 75%                 |
| AcknowledgementOfGratitude           |             4 | 0%                 | 25%          | 100%               | 50%   | 25%                 | 25%                 |
| InteractionComplete                  |             4 | 0%                 | 50%          | 50%                | 25%   | 50%                 | 50%                 |

## 7. Hardest and easiest intents (intents with at least 3 calls)

Hardest 12 by mean exact accuracy of the 5 API systems:

| intent                           |   eval_calls_total |   exact_acc__mean_5_api_systems |   exact_acc__classic_tfidf_lr |
|:---------------------------------|-------------------:|--------------------------------:|------------------------------:|
| CardExpirationRenewal            |                  4 |                            0    |                          0.25 |
| ProductChangeUpgradeDowngrade    |                  4 |                            0.15 |                          0    |
| ChangeNumber                     |                  4 |                            0.15 |                          0    |
| GeneralRewardsInformationInquiry |                  4 |                            0.25 |                          0    |
| PhoneNumberUpdate                |                  4 |                            0.25 |                          0.25 |
| DamagedCardReplacement           |                  4 |                            0.3  |                          0    |
| BankAccountInformationManagement |                  4 |                            0.3  |                          0.25 |
| AutoPayManagement                |                  4 |                            0.3  |                          0    |
| BranchATMLocationANDIssueInquiry |                  4 |                            0.35 |                          0.25 |
| NameChangeRequest                |                  4 |                            0.35 |                          0.5  |
| LoanInquiryManagement            |                  4 |                            0.35 |                          0    |
| RebateInquiryAndManagement       |                  4 |                            0.35 |                          0    |

Easiest 8:

| intent                             |   eval_calls_total |   exact_acc__mean_5_api_systems |   exact_acc__classic_tfidf_lr |
|:-----------------------------------|-------------------:|--------------------------------:|------------------------------:|
| InterestInquiry                    |                  4 |                               1 |                          0    |
| AmbiguousRewardsRequest            |                  4 |                               1 |                          0    |
| ReviewMultipleTransactions         |                  4 |                               1 |                          0.5  |
| DigitalWalletSupport               |                  4 |                               1 |                          0.5  |
| MembershipManagement               |                  4 |                               1 |                          1    |
| EmailAddressUpdate                 |                  4 |                               1 |                          0.75 |
| RequestARepresentative             |                  4 |                               1 |                          0.75 |
| PaymentAssistanceFinancialHardship |                  4 |                               1 |                          0.25 |

## 8. Most common confusions per system (expected -> predicted, both iterations)

| family                         | y_true                           | pred                                 |   count |
|:-------------------------------|:---------------------------------|:-------------------------------------|--------:|
| classic_tfidf_lr               | CreditScoreReportInquiry         | CRSRequests                          |       3 |
| classic_tfidf_lr               | DocumentRequestInquiry           | CreditScoreReportInquiry             |       3 |
| classic_tfidf_lr               | PaymentMethodOptionsInquiry      | OnlinePaymentMethodInquiry           |       3 |
| classic_tfidf_lr               | UnclassifiableOther              | IVRNavigationRestart                 |       3 |
| classic_tfidf_lr               | AccountCardLinkingforUnifiedView | ExternalRewardsProgramLinkingInquiry |       2 |
| classic_tfidf_lr               | AccountDebtConsolidation         | AccountCardLinkingforUnifiedView     |       2 |
| claude-haiku-5-5_explicit      | CardExpirationRenewal            | UnclassifiableOther                  |       4 |
| claude-haiku-5-5_explicit      | DamagedCardReplacement           | UnclassifiableOther                  |       3 |
| claude-haiku-5-5_explicit      | GiftCardInquiryManagement        | UnclassifiableOther                  |       3 |
| claude-haiku-5-5_explicit      | PhoneNumberUpdate                | UnclassifiableOther                  |       3 |
| claude-haiku-5-5_explicit      | RewardsBalanceInquiry            | GeneralRewardsInformationInquiry     |       3 |
| claude-haiku-5-5_explicit      | AccountNumberInquiry             | AccountQuestion                      |       2 |
| claude-sonnet-5-5_explicit     | CardExpirationRenewal            | UnclassifiableOther                  |       3 |
| claude-sonnet-5-5_explicit     | PhoneNumberUpdate                | UnclassifiableOther                  |       3 |
| claude-sonnet-5-5_explicit     | RepeatVerbiage                   | UnclassifiableOther                  |       3 |
| claude-sonnet-5-5_explicit     | AccountNumberInquiry             | AccountQuestion                      |       2 |
| claude-sonnet-5-5_explicit     | AccountProblemInquiry            | AccountQuestion                      |       2 |
| claude-sonnet-5-5_explicit     | AccountQuestion                  | UnclassifiableOther                  |       2 |
| gemini-3.1-flash-lite_explicit | AccountProblemInquiry            | AccountQuestion                      |       3 |
| gemini-3.1-flash-lite_explicit | CardExpirationRenewal            | UnclassifiableOther                  |       3 |
| gemini-3.1-flash-lite_explicit | ChangeNumber                     | AccountUpdate                        |       3 |
| gemini-3.1-flash-lite_explicit | DamagedCardReplacement           | UnclassifiableOther                  |       3 |
| gemini-3.1-flash-lite_explicit | PhoneNumberUpdate                | UnclassifiableOther                  |       3 |
| gemini-3.1-flash-lite_explicit | RepeatVerbiage                   | UnclassifiableOther                  |       3 |
| gpt-6-luna_explicit            | CardExpirationRenewal            | UnclassifiableOther                  |       3 |
| gpt-6-luna_explicit            | DamagedCardReplacement           | UnclassifiableOther                  |       3 |
| gpt-6-luna_explicit            | PhoneNumberUpdate                | UnclassifiableOther                  |       3 |
| gpt-6-luna_explicit            | AccountNumberInquiry             | AccountQuestion                      |       2 |
| gpt-6-luna_explicit            | AccountQuestion                  | UnclassifiableOther                  |       2 |
| gpt-6-luna_explicit            | BankAccountInformationManagement | UnclassifiableOther                  |       2 |
| jev                            | CardExpirationRenewal            | UnclassifiableOther                  |       3 |
| jev                            | DamagedCardReplacement           | UnclassifiableOther                  |       3 |
| jev                            | PhoneNumberUpdate                | UnclassifiableOther                  |       3 |
| jev                            | AccountCardLinkingforUnifiedView | UnclassifiableOther                  |       2 |
| jev                            | AccountQuestion                  | UnclassifiableOther                  |       2 |
| jev                            | AcknowledgementOfGratitude       | CRSRequests                          |       2 |

## 9. Files

- `summary_by_intent.csv` (every column above for all 114 intents), `summary_by_system_iteration.csv`, `calls_per_intent_uniformity.csv`
- `results.md` (the run's own report), `run.log`, `events.jsonl`, `run_manifest.json`, `audit.jsonl`, `iterations.csv`, `data/*.jsonl`
