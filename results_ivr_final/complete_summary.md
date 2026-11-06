# IVR intent comparison: complete run summary

Run `2026-10-21T23:01:51+00:00` to `2026-10-21T23:14:39+00:00`, runtime 767.7 s, status **completed**. Measured API spend **$1.7958** of a $2.80 hard cap (user limit $3). 3000 API calls in total.

## 1. Run design

- Iterations: **2** (iteration 1 = v1 prompts, iteration 2 = v2 prompts; JEV: Choice question v1 -> v2). Base seed 42, iteration seed = base + iteration.
- Per iteration and per system: **50 calibration calls** (threshold selection only) + **250 eval calls** (scored) = 300 calls; **600 calls per API system** in total, 500 of them scored.
- Systems: TF-IDF baseline (no API) + 5 API systems, run cheapest-first: claude-haiku-5-5, gpt-6-luna, jev, gemini-flash-lite, claude-sonnet-5-5. Cache mode: explicit (JEV exposes no cache controls).
- Intent catalog: **114 intents** -> 106 workflows (some near-synonym intents share a workflow). Train seeds are never used in eval (per-intent seed split).
- Apples to apples: every system received the identical calibration and eval calls each iteration (same XML, same expected intent), the same catalog, workflow map, threshold rule and scoring.

| iteration | seed | calibration calls | eval calls | intents appearing in eval | calibration set hash | eval set hash |
|---|---|---|---|---|---|---|
| 1 | 43 | 50 | 250 | 98 | 22dd8c6a6df3 | bb0342449089 |
| 2 | 44 | 50 | 250 | 103 | 65289f8e227d | 258bd3442b4d |

## 2. Calls, tokens and cost per system and iteration

| system                            |   iteration |   calibration_calls |   eval_calls |   errors |   input_tokens |   cache_read_tokens |   cache_write_tokens |   output_tokens |   cost_usd |   eval_latency_p50_s |   eval_latency_p95_s |
|:----------------------------------|------------:|--------------------:|-------------:|---------:|---------------:|--------------------:|---------------------:|----------------:|-----------:|---------------------:|---------------------:|
| claude-haiku-5-5_explicit_v1      |           1 |                  50 |          250 |        0 |        1759077 |             1685762 |                 5638 |           21958 |    0.03531 |                1.238 |                1.848 |
| gpt-6-luna_explicit_v1            |           1 |                  50 |          250 |        0 |         889215 |              836602 |                 2798 |           31449 |    0.02907 |                2.681 |                5.053 |
| jev_v1                            |           1 |                  50 |          250 |        0 |        1154075 |                   0 |                    0 |          436336 |    0.04847 |                0.187 |                0.278 |
| gemini-3.1-flash-lite_explicit_v1 |           1 |                  50 |          250 |        0 |         754442 |              705600 |                    0 |           13203 |    0.04966 |                0.95  |                1.391 |
| claude-sonnet-5-5_explicit_v1     |           1 |                  50 |          250 |        0 |        1759377 |             1686061 |                 5639 |           20303 |    0.68969 |                1.4   |                2.105 |
| claude-haiku-5-5_explicit_v2      |           2 |                  50 |          250 |        0 |        2063267 |             1988948 |                 6652 |           23430 |    0.0392  |                1.133 |                1.649 |
| gpt-6-luna_explicit_v2            |           2 |                  50 |          250 |        0 |        1057830 |             1004042 |                 3358 |           36231 |    0.0332  |                2.661 |                6.728 |
| jev_v2                            |           2 |                  50 |          250 |        0 |        1275930 |                   0 |                    0 |          436281 |    0.05359 |                0.189 |                0.272 |
| gemini-3.1-flash-lite_explicit_v2 |           2 |                  50 |          250 |        0 |         928214 |              879300 |                    0 |           13473 |    0.05442 |                0.957 |                1.44  |
| claude-sonnet-5-5_explicit_v2     |           2 |                  50 |          250 |        0 |        2062967 |             1988649 |                 6651 |           21222 |    0.76191 |                1.453 |                2.158 |

Totals per system:

| system                         |   calibration_calls |   eval_calls |   errors |   input_tokens |   cache_read_tokens |   cache_write_tokens |   output_tokens |   cost_usd |
|:-------------------------------|--------------------:|-------------:|---------:|---------------:|--------------------:|---------------------:|----------------:|-----------:|
| claude-haiku-5-5_explicit      |                 100 |          500 |        0 |        3822344 |             3674710 |                12290 |           45388 |    0.07451 |
| gpt-6-luna_explicit            |                 100 |          500 |        0 |        1947045 |             1840644 |                 6156 |           67680 |    0.06227 |
| jev                            |                 100 |          500 |        0 |        2430005 |                   0 |                    0 |          872617 |    0.10206 |
| gemini-3.1-flash-lite_explicit |                 100 |          500 |        0 |        1682656 |             1584900 |                    0 |           26676 |    0.10408 |
| claude-sonnet-5-5_explicit     |                 100 |          500 |        0 |        3822344 |             3674710 |                12290 |           41525 |    1.4516  |

## 3. System-level metrics (mean of the 2 iterations)

| family                         |   accuracy |   macro_f1 |   handled_correctly |   automation_rate |   auto_precision |   misroute_rate |   errors |
|:-------------------------------|-----------:|-----------:|--------------------:|------------------:|-----------------:|----------------:|---------:|
| claude-haiku-5-5_explicit      |      0.608 |      0.562 |               0.516 |             0.598 |            0.842 |           0.096 |        0 |
| jev                            |      0.636 |      0.571 |               0.476 |             0.55  |            0.847 |           0.084 |        0 |
| gemini-3.1-flash-lite_explicit |      0.62  |      0.555 |               0.472 |             0.558 |            0.835 |           0.1   |        0 |
| gpt-6-luna_explicit            |      0.652 |      0.599 |               0.402 |             0.486 |            0.803 |           0.096 |        0 |
| claude-sonnet-5-5_explicit     |      0.644 |      0.583 |               0.348 |             0.384 |            0.877 |           0.048 |        0 |
| classic_tfidf_lr               |      0.304 |      0.245 |               0.104 |             0.138 |            0.649 |           0.048 |        0 |

| family                         |   latency_p50_s |   latency_p95_s |   throughput_per_s |   cost_per_1k_usd |   cost_per_correct_call_usd |   total_cost_usd |   cached_input_share |
|:-------------------------------|----------------:|----------------:|-------------------:|------------------:|----------------------------:|-----------------:|---------------------:|
| claude-haiku-5-5_explicit      |         1.1854  |         1.7485  |              4.615 |           0.12187 |                     0.00024 |          0.06094 |              0.96464 |
| jev                            |         0.18773 |         0.27493 |             29.82  |           0.17009 |                     0.00036 |          0.08505 |              0       |
| gemini-3.1-flash-lite_explicit |         0.95342 |         1.41559 |              5.87  |           0.17586 |                     0.00038 |          0.08793 |              0.94196 |
| gpt-6-luna_explicit            |         2.67106 |         5.89073 |              1.86  |           0.10302 |                     0.00026 |          0.05151 |              0.95156 |
| claude-sonnet-5-5_explicit     |         1.42644 |         2.13155 |              3.87  |           2.3701  |                     0.00681 |          1.18505 |              0.96464 |
| classic_tfidf_lr               |         3e-05   |         3e-05   |          31043.8   |           0       |                     0       |          0       |            nan       |

Per iteration:

|   iteration | system                            |   threshold |   accuracy |   macro_f1 |   handled_correctly |   automation_rate |   misroute_rate |   latency_p50_s |   cost_per_1k_usd |   errors |
|------------:|:----------------------------------|------------:|-----------:|-----------:|--------------------:|------------------:|----------------:|----------------:|------------------:|---------:|
|           1 | classic_tfidf_lr                  |        0.54 |      0.3   |      0.245 |               0.056 |             0.056 |           0.02  |           0     |             0     |        0 |
|           1 | claude-haiku-5-5_explicit_v1      |        0.72 |      0.604 |      0.543 |               0.504 |             0.552 |           0.068 |           1.238 |             0.115 |        0 |
|           1 | gpt-6-luna_explicit_v1            |        0.87 |      0.656 |      0.583 |               0.44  |             0.532 |           0.108 |           2.681 |             0.096 |        0 |
|           1 | jev_v1                            |        0.93 |      0.636 |      0.558 |               0.488 |             0.56  |           0.084 |           0.187 |             0.162 |        0 |
|           1 | gemini-3.1-flash-lite_explicit_v1 |        0.9  |      0.616 |      0.545 |               0.4   |             0.424 |           0.044 |           0.95  |             0.168 |        0 |
|           1 | claude-sonnet-5-5_explicit_v1     |        0.87 |      0.644 |      0.565 |               0.344 |             0.36  |           0.032 |           1.4   |             2.253 |        0 |
|           2 | classic_tfidf_lr                  |        0.27 |      0.308 |      0.245 |               0.152 |             0.22  |           0.076 |           0     |             0     |        0 |
|           2 | claude-haiku-5-5_explicit_v2      |        0.57 |      0.612 |      0.581 |               0.528 |             0.644 |           0.124 |           1.133 |             0.128 |        0 |
|           2 | gpt-6-luna_explicit_v2            |        0.9  |      0.648 |      0.614 |               0.364 |             0.44  |           0.084 |           2.661 |             0.111 |        0 |
|           2 | jev_v2                            |        0.9  |      0.636 |      0.584 |               0.464 |             0.54  |           0.084 |           0.189 |             0.179 |        0 |
|           2 | gemini-3.1-flash-lite_explicit_v2 |        0.81 |      0.624 |      0.565 |               0.544 |             0.692 |           0.156 |           0.957 |             0.184 |        0 |
|           2 | claude-sonnet-5-5_explicit_v2     |        0.81 |      0.644 |      0.6   |               0.352 |             0.408 |           0.064 |           1.453 |             2.487 |        0 |

## 4. Which intents ran, and was it uniform?

- Intents with at least one eval call: **113 of 114** (per iteration: 98, 103). Calls per covered intent over both iterations: min 1, median 4, max 10, total 500.
- Uniformity check: for **113 of 113** covered intents every system (including TF-IDF) was scored on exactly the same number of calls: YES, all systems ran the same calls.
- Not sampled in either eval set (1): AmbiguousRewardsRequest.
- Sampling is uniform over intents that have seeds, so the number of calls per intent is random, not exactly equal. A stratified run (equal calls per intent) would need about 114 x k calls per system.

Calls-per-intent distribution (eval calls over both iterations -> number of intents):

| calls for the intent | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| intents | 8 | 12 | 19 | 20 | 22 | 13 | 12 | 5 | 1 | 1 |

## 5. Per-intent results (exact-intent accuracy, eval calls)

Columns: calls per iteration and total (same for every system), then exact-intent accuracy per system (share of that intent's calls where the predicted intent equals the expected one). `mean5` = mean of the five API systems. Intents never sampled are omitted.

| intent                               | workflow              |   calls it1 |   calls it2 |   calls total | classic_tfidf_lr   | claude-haiku-5-5   | gpt-6-luna   | jev   | gemini-flash-lite   | claude-sonnet-5-5   | mean5   |
|:-------------------------------------|:----------------------|------------:|------------:|--------------:|:-------------------|:-------------------|:-------------|:------|:--------------------|:--------------------|:--------|
| BalanceQuestion                      | wf_balance            |           2 |           2 |             4 | 0%                 | 25%                | 75%          | 25%   | 75%                 | 50%                 | 50%     |
| BalanceValueInquiry                  | wf_balance            |           0 |           3 |             3 | 0%                 | 33%                | 33%          | 33%   | 33%                 | 33%                 | 33%     |
| ReviewMultipleTransactions           | wf_transactions       |           2 |           5 |             7 | 29%                | 71%                | 71%          | 71%   | 86%                 | 86%                 | 77%     |
| TransactionQuestion                  | wf_transactions       |           1 |           4 |             5 | 40%                | 40%                | 60%          | 80%   | 60%                 | 60%                 | 60%     |
| ReviewCredits                        | wf_credits            |           0 |           2 |             2 | 0%                 | 50%                | 50%          | 50%   | 50%                 | 50%                 | 50%     |
| PaymentVerification                  | wf_payment_verify     |           0 |           1 |             1 | 0%                 | 100%               | 100%         | 0%    | 100%                | 100%                | 80%     |
| PaymentMethodOptionsInquiry          | wf_payment_options    |           0 |           1 |             1 | 0%                 | 100%               | 100%         | 100%  | 100%                | 100%                | 100%    |
| OnlinePaymentMethodInquiry           | wf_payment_options    |           3 |           0 |             3 | 0%                 | 67%                | 67%          | 67%   | 67%                 | 67%                 | 67%     |
| PhonePaymentFeeInquiry               | wf_phone_pay_fee      |           0 |           4 |             4 | 25%                | 75%                | 75%          | 50%   | 75%                 | 75%                 | 70%     |
| PaymentAddressInquiry                | wf_payment_address    |           2 |           4 |             6 | 67%                | 83%                | 83%          | 83%   | 83%                 | 83%                 | 83%     |
| PayoffInquiry                        | wf_payoff             |           2 |           2 |             4 | 75%                | 75%                | 75%          | 75%   | 75%                 | 75%                 | 75%     |
| PaymentDueDateModification           | wf_due_date_change    |           4 |           1 |             5 | 60%                | 80%                | 80%          | 80%   | 80%                 | 80%                 | 80%     |
| BillingQuestion                      | wf_billing            |           1 |           1 |             2 | 50%                | 100%               | 100%         | 100%  | 100%                | 50%                 | 90%     |
| BillDiscrepancy                      | wf_bill_dispute       |           0 |           2 |             2 | 0%                 | 50%                | 100%         | 50%   | 100%                | 50%                 | 70%     |
| StatementCopy                        | wf_statement          |           4 |           4 |             8 | 12%                | 88%                | 50%          | 62%   | 88%                 | 62%                 | 70%     |
| StatementInquiry                     | wf_statement          |           3 |           2 |             5 | 60%                | 20%                | 80%          | 40%   | 60%                 | 80%                 | 56%     |
| YearEndStatementInquiry              | wf_year_end           |           1 |           0 |             1 | 100%               | 100%               | 100%         | 100%  | 100%                | 100%                | 100%    |
| FraudulentActivity                   | wf_fraud              |           5 |           1 |             6 | 0%                 | 50%                | 50%          | 50%   | 50%                 | 50%                 | 50%     |
| ReportLostCard                       | wf_lost_card          |           3 |           1 |             4 | 75%                | 50%                | 100%         | 75%   | 75%                 | 100%                | 80%     |
| CardLockUnlock                       | wf_card_lock          |           2 |           1 |             3 | 0%                 | 67%                | 100%         | 67%   | 67%                 | 67%                 | 73%     |
| CardActivation                       | wf_activate           |           2 |           2 |             4 | 50%                | 75%                | 50%          | 75%   | 50%                 | 75%                 | 65%     |
| CardFacePhotoIssue                   | wf_card_photo         |           2 |           1 |             3 | 33%                | 100%               | 100%         | 100%  | 100%                | 100%                | 100%    |
| AuthorizedUserManagement             | wf_auth_user          |           0 |           3 |             3 | 0%                 | 33%                | 67%          | 67%   | 67%                 | 67%                 | 60%     |
| AdditionalCardManagement             | wf_additional_card    |           1 |           0 |             1 | 0%                 | 0%                 | 0%           | 0%    | 0%                  | 0%                  | 0%      |
| DigitalWalletSupport                 | wf_wallet             |           2 |           4 |             6 | 83%                | 83%                | 83%          | 83%   | 83%                 | 83%                 | 83%     |
| OnlineAccess                         | wf_online_access      |           5 |           3 |             8 | 50%                | 0%                 | 12%          | 12%   | 12%                 | 12%                 | 10%     |
| OnlineRegistrationSetup              | wf_online_reg         |           1 |           2 |             3 | 67%                | 67%                | 67%          | 67%   | 67%                 | 67%                 | 67%     |
| AccountCardLinkingforUnifiedView     | wf_card_linking       |           1 |           3 |             4 | 25%                | 50%                | 25%          | 75%   | 75%                 | 75%                 | 60%     |
| GeneralRewardsInformationInquiry     | wf_rewards_info       |           0 |           3 |             3 | 0%                 | 33%                | 0%           | 0%    | 0%                  | 0%                  | 7%      |
| GeneralRewardsFAQ                    | wf_rewards_info       |           1 |           0 |             1 | 100%               | 100%               | 0%           | 0%    | 0%                  | 0%                  | 20%     |
| RewardsProgramEnrollment             | wf_rewards_enroll     |           4 |           1 |             5 | 0%                 | 80%                | 100%         | 100%  | 80%                 | 80%                 | 88%     |
| RewardsRedemptionRequest             | wf_rewards_redeem     |           3 |           2 |             5 | 0%                 | 20%                | 40%          | 60%   | 60%                 | 20%                 | 40%     |
| ExternalRewardsProgramLinkingInquiry | wf_rewards_link       |           3 |           2 |             5 | 40%                | 100%               | 80%          | 100%  | 100%                | 100%                | 96%     |
| POCNightsInquiry                    | wf_POC_nights        |           1 |           3 |             4 | 50%                | 50%                | 50%          | 50%   | 50%                 | 50%                 | 50%     |
| InitiateANewBalanceTransfer          | wf_bt_start           |           3 |           3 |             6 | 17%                | 33%                | 50%          | 83%   | 67%                 | 50%                 | 57%     |
| StatusOfBalanceTransfer              | wf_bt_status          |           5 |           1 |             6 | 17%                | 83%                | 83%          | 83%   | 83%                 | 83%                 | 83%     |
| BalanceTransferGeneralInquiry        | wf_bt_info            |           2 |           1 |             3 | 67%                | 33%                | 67%          | 67%   | 67%                 | 100%                | 67%     |
| InterestInquiry                      | wf_interest           |           1 |           1 |             2 | 0%                 | 100%               | 100%         | 100%  | 100%                | 100%                | 100%    |
| FeeInquiryManagement                 | wf_fees               |           1 |           1 |             2 | 50%                | 100%               | 100%         | 100%  | 100%                | 100%                | 100%    |
| CashAdvanceInquiry                   | wf_cash_advance       |           1 |           4 |             5 | 60%                | 80%                | 100%         | 80%   | 100%                | 80%                 | 88%     |
| CreditScoreReportInquiry             | wf_credit_report      |           1 |           2 |             3 | 0%                 | 100%               | 100%         | 33%   | 100%                | 100%                | 87%     |
| CRSRequests                          | wf_crs                |           2 |           3 |             5 | 0%                 | 80%                | 80%          | 80%   | 80%                 | 80%                 | 80%     |
| CreditQuestion                       | wf_credit_q           |           4 |           3 |             7 | 29%                | 71%                | 100%         | 100%  | 86%                 | 100%                | 91%     |
| AccountStatusInquiry                 | wf_account_status     |           2 |           2 |             4 | 25%                | 25%                | 50%          | 25%   | 25%                 | 50%                 | 35%     |
| AccountProblemInquiry                | wf_account_problem    |           3 |           2 |             5 | 60%                | 40%                | 40%          | 60%   | 40%                 | 40%                 | 44%     |
| AccountQuestion                      | wf_account_q          |           2 |           5 |             7 | 0%                 | 57%                | 43%          | 43%   | 57%                 | 57%                 | 51%     |
| AccountNumberInquiry                 | wf_account_number     |           2 |           5 |             7 | 29%                | 14%                | 14%          | 29%   | 29%                 | 14%                 | 20%     |
| SecuredCardInquiry                   | wf_secured_card       |           3 |           4 |             7 | 14%                | 57%                | 71%          | 57%   | 57%                 | 71%                 | 63%     |
| ProductChangeUpgradeDowngrade        | wf_product_change     |           3 |           2 |             5 | 20%                | 100%               | 100%         | 100%  | 100%                | 100%                | 100%    |
| CardAccountClosure                   | wf_closure            |           4 |           2 |             6 | 0%                 | 0%                 | 17%          | 17%   | 17%                 | 17%                 | 13%     |
| LargePurchaseNotification            | wf_large_purchase     |           1 |           1 |             2 | 100%               | 100%               | 100%         | 100%  | 100%                | 100%                | 100%    |
| AuthorizationInquiryRequest          | wf_authorization      |           2 |           3 |             5 | 60%                | 80%                | 80%          | 80%   | 80%                 | 80%                 | 80%     |
| ConciergeTravelAssistance            | wf_concierge          |           1 |           2 |             3 | 0%                 | 67%                | 67%          | 67%   | 33%                 | 33%                 | 53%     |
| DebitCardInquiryManagement           | wf_debit_transfer     |           2 |           3 |             5 | 60%                | 40%                | 40%          | 40%   | 40%                 | 40%                 | 40%     |
| MortgageInquiryManagement            | wf_mortgage_transfer  |           2 |           3 |             5 | 60%                | 80%                | 80%          | 80%   | 80%                 | 80%                 | 80%     |
| BankAccountInformationManagement     | wf_bank_account       |           5 |           2 |             7 | 71%                | 86%                | 86%          | 71%   | 86%                 | 86%                 | 83%     |
| ContactFollowUp                      | wf_followup           |           3 |           0 |             3 | 0%                 | 67%                | 67%          | 67%   | 67%                 | 67%                 | 67%     |
| POCShopProgramInquiry               | wf_POC_shop          |           2 |           1 |             3 | 100%               | 100%               | 100%         | 100%  | 100%                | 100%                | 100%    |
| DeceasedAccountHolderNotification    | wf_deceased           |           1 |           2 |             3 | 0%                 | 33%                | 33%          | 33%   | 33%                 | 33%                 | 33%     |
| CancelBalanceTransfer                | wf_bt_cancel          |           3 |           2 |             5 | 60%                | 100%               | 100%         | 100%  | 100%                | 100%                | 100%    |
| CancelAutoPay                        | wf_autopay            |           2 |           2 |             4 | 0%                 | 100%               | 100%         | 100%  | 75%                 | 100%                | 95%     |
| AutoPayManagement                    | wf_autopay            |           3 |           2 |             5 | 0%                 | 20%                | 40%          | 40%   | 40%                 | 40%                 | 36%     |
| ChangeCardOrAccountNumber            | wf_change_card_number |           2 |           4 |             6 | 33%                | 33%                | 33%          | 50%   | 0%                  | 33%                 | 30%     |
| ChangeNumber                         | wf_change_number      |           4 |           3 |             7 | 0%                 | 57%                | 29%          | 0%    | 14%                 | 29%                 | 26%     |
| AddressPersonalInfoChange            | wf_update_address     |           1 |           3 |             4 | 50%                | 75%                | 75%          | 75%   | 100%                | 100%                | 85%     |
| AddressVerificationInquiry           | wf_address_verify     |           3 |           3 |             6 | 50%                | 50%                | 67%          | 50%   | 67%                 | 67%                 | 60%     |
| PhoneNumberUpdate                    | wf_update_phone       |           3 |           4 |             7 | 43%                | 57%                | 86%          | 86%   | 86%                 | 71%                 | 77%     |
| EmailAddressUpdate                   | wf_update_email       |           2 |           0 |             2 | 0%                 | 100%               | 100%         | 100%  | 100%                | 100%                | 100%    |
| NameChangeRequest                    | wf_update_name        |           4 |           5 |             9 | 78%                | 78%                | 78%          | 78%   | 67%                 | 89%                 | 78%     |
| IncomeInformationUpdate              | wf_update_income      |           2 |           3 |             5 | 60%                | 60%                | 60%          | 60%   | 60%                 | 60%                 | 60%     |
| AccountUpdate                        | wf_account_update     |           2 |           4 |             6 | 0%                 | 50%                | 50%          | 50%   | 50%                 | 50%                 | 50%     |
| PasswordResetManagement              | wf_password           |           0 |           1 |             1 | 0%                 | 100%               | 100%         | 100%  | 0%                  | 100%                | 80%     |
| PinManagement                        | wf_pin                |           4 |           3 |             7 | 29%                | 43%                | 57%          | 57%   | 43%                 | 43%                 | 49%     |
| DisputeATransaction                  | wf_dispute            |           3 |           2 |             5 | 40%                | 80%                | 80%          | 80%   | 80%                 | 80%                 | 80%     |
| CheckStatusofExistingDispute         | wf_dispute_status     |           2 |           3 |             5 | 20%                | 40%                | 60%          | 60%   | 60%                 | 60%                 | 56%     |
| CancelRecurringCharges               | wf_recurring_charge   |           4 |           0 |             4 | 50%                | 25%                | 25%          | 25%   | 25%                 | 25%                 | 25%     |
| CancelStopPayment                    | wf_cancel_payment     |           3 |           3 |             6 | 17%                | 50%                | 67%          | 67%   | 50%                 | 33%                 | 53%     |
| ReportStolenCard                     | wf_lost_card          |           2 |           2 |             4 | 50%                | 75%                | 75%          | 75%   | 75%                 | 75%                 | 75%     |
| CardIsNotWorking                     | wf_card_not_working   |           6 |           2 |             8 | 25%                | 75%                | 62%          | 50%   | 50%                 | 75%                 | 62%     |
| TransactionDeclined                  | wf_declined           |           5 |           1 |             6 | 17%                | 83%                | 83%          | 83%   | 83%                 | 83%                 | 83%     |
| CardExpirationRenewal                | wf_card_renewal       |           2 |           3 |             5 | 0%                 | 60%                | 80%          | 80%   | 60%                 | 80%                 | 72%     |
| DamagedCardReplacement               | wf_replace_card       |           5 |           3 |             8 | 0%                 | 62%                | 62%          | 62%   | 62%                 | 62%                 | 62%     |
| CardNotReceivedInquiry               | wf_card_delivery      |           1 |           2 |             3 | 33%                | 67%                | 33%          | 67%   | 67%                 | 67%                 | 60%     |
| InitiateNewCardApplication           | wf_application        |           1 |           2 |             3 | 67%                | 67%                | 67%          | 33%   | 33%                 | 67%                 | 53%     |
| LoanInquiryManagement                | wf_loan_transfer      |           4 |           6 |            10 | 40%                | 70%                | 70%          | 70%   | 50%                 | 70%                 | 66%     |
| GeneralCheckInquiry                  | wf_check_inquiry      |           3 |           2 |             5 | 60%                | 80%                | 100%         | 100%  | 80%                 | 100%                | 92%     |
| MultiAccountCardManagement           | wf_multi_account      |           0 |           3 |             3 | 0%                 | 33%                | 67%          | 100%  | 67%                 | 33%                 | 60%     |
| AccountDebtConsolidation             | wf_debt_consolidation |           4 |           0 |             4 | 25%                | 100%               | 100%         | 100%  | 75%                 | 100%                | 95%     |
| MembershipManagement                 | wf_membership         |           4 |           1 |             5 | 60%                | 80%                | 80%          | 80%   | 80%                 | 80%                 | 80%     |
| VirtualAccountCardManagement         | wf_virtual_card       |           1 |           3 |             4 | 50%                | 50%                | 50%          | 50%   | 50%                 | 50%                 | 50%     |
| GiftCardInquiryManagement            | wf_gift_card          |           0 |           2 |             2 | 100%               | 50%                | 100%         | 100%  | 100%                | 100%                | 90%     |
| RebateInquiryAndManagement           | wf_rebate             |           3 |           1 |             4 | 0%                 | 50%                | 50%          | 50%   | 50%                 | 50%                 | 50%     |
| RewardsCertificateRegeneration       | wf_rewards_cert       |           1 |           2 |             3 | 33%                | 67%                | 100%         | 67%   | 67%                 | 67%                 | 73%     |
| RewardsBalanceInquiry                | wf_rewards_balance    |           3 |           1 |             4 | 50%                | 100%               | 100%         | 100%  | 100%                | 100%                | 100%    |
| PromotionInquiry                     | wf_promo              |           3 |           3 |             6 | 0%                 | 33%                | 50%          | 50%   | 50%                 | 50%                 | 47%     |
| MinimumPaymentCalculation            | wf_min_payment        |           2 |           3 |             5 | 60%                | 80%                | 80%          | 80%   | 60%                 | 60%                 | 72%     |
| OverpaymentDuplicatePaymentInquiry   | wf_overpayment        |           6 |           1 |             7 | 0%                 | 43%                | 43%          | 43%   | 29%                 | 43%                 | 40%     |
| PaymentAssistanceFinancialHardship   | wf_hardship           |           2 |           0 |             2 | 50%                | 50%                | 50%          | 50%   | 50%                 | 50%                 | 50%     |
| DocumentRequestInquiry               | wf_document_request   |           2 |           2 |             4 | 25%                | 75%                | 75%          | 75%   | 50%                 | 75%                 | 70%     |
| DisasterReliefInquiry                | wf_disaster_relief    |           0 |           1 |             1 | 0%                 | 100%               | 100%         | 100%  | 100%                | 100%                | 100%    |
| BranchATMLocationANDIssueInquiry     | wf_branch             |           0 |           1 |             1 | 0%                 | 100%               | 100%         | 100%  | 100%                | 100%                | 100%    |
| OnlineTransactionInquiry             | wf_online_txn         |           2 |           0 |             2 | 0%                 | 0%                 | 0%           | 0%    | 0%                  | 0%                  | 0%      |
| BalanceAndMakePayment                | wf_balance_pay        |           0 |           4 |             4 | 25%                | 100%               | 100%         | 100%  | 100%                | 100%                | 100%    |
| OtherLanguageRequest                 | wf_other_language     |           3 |           5 |             8 | 25%                | 75%                | 75%          | 75%   | 75%                 | 75%                 | 75%     |
| IVRNavigationRestart                 | wf_menu_restart       |           2 |           1 |             3 | 33%                | 33%                | 33%          | 33%   | 33%                 | 33%                 | 33%     |
| ConversationHoldOn                   | wf_hold               |           1 |           3 |             4 | 50%                | 75%                | 75%          | 75%   | 75%                 | 75%                 | 75%     |
| PaperlessManagement                  | wf_paperless          |           2 |           4 |             6 | 0%                 | 33%                | 33%          | 33%   | 17%                 | 33%                 | 30%     |
| UnclassifiableOther                  | wf_out_of_scope       |           2 |           1 |             3 | 0%                 | 100%               | 100%         | 100%  | 100%                | 100%                | 100%    |
| RequestARepresentative               | live_agent_queue      |           5 |           2 |             7 | 0%                 | 57%                | 57%          | 43%   | 57%                 | 57%                 | 54%     |
| RepeatVerbiage                       | wf_repeat             |           4 |           3 |             7 | 0%                 | 0%                 | 14%          | 14%   | 14%                 | 14%                 | 11%     |
| EnglishLanguageRequest               | wf_english            |           0 |           2 |             2 | 100%               | 100%               | 100%         | 100%  | 100%                | 100%                | 100%    |
| AcknowledgementOfGratitude           | wf_end_call           |           2 |           2 |             4 | 25%                | 50%                | 0%           | 25%   | 0%                  | 0%                  | 15%     |
| InteractionComplete                  | wf_end_call           |           1 |           1 |             2 | 0%                 | 50%                | 100%         | 50%   | 50%                 | 50%                 | 60%     |

## 6. Per-intent handled-correctly (right workflow / agent transfer at the tuned threshold)

| intent                               |   calls total | classic_tfidf_lr   | claude-haiku-5-5   | gpt-6-luna   | jev   | gemini-flash-lite   | claude-sonnet-5-5   |
|:-------------------------------------|--------------:|:-------------------|:-------------------|:-------------|:------|:--------------------|:--------------------|
| BalanceQuestion                      |             4 | 0%                 | 50%                | 25%          | 25%   | 50%                 | 25%                 |
| BalanceValueInquiry                  |             3 | 0%                 | 33%                | 33%          | 33%   | 33%                 | 33%                 |
| ReviewMultipleTransactions           |             7 | 0%                 | 71%                | 43%          | 57%   | 71%                 | 29%                 |
| TransactionQuestion                  |             5 | 20%                | 40%                | 20%          | 60%   | 60%                 | 40%                 |
| ReviewCredits                        |             2 | 0%                 | 50%                | 50%          | 50%   | 50%                 | 50%                 |
| PaymentVerification                  |             1 | 0%                 | 100%               | 0%           | 0%    | 100%                | 0%                  |
| PaymentMethodOptionsInquiry          |             1 | 0%                 | 100%               | 100%         | 100%  | 100%                | 100%                |
| OnlinePaymentMethodInquiry           |             3 | 0%                 | 67%                | 67%          | 0%    | 67%                 | 0%                  |
| PhonePaymentFeeInquiry               |             4 | 25%                | 50%                | 50%          | 50%   | 50%                 | 50%                 |
| PaymentAddressInquiry                |             6 | 50%                | 83%                | 67%          | 83%   | 67%                 | 67%                 |
| PayoffInquiry                        |             4 | 25%                | 75%                | 50%          | 50%   | 75%                 | 25%                 |
| PaymentDueDateModification           |             5 | 60%                | 80%                | 20%          | 40%   | 40%                 | 20%                 |
| BillingQuestion                      |             2 | 50%                | 0%                 | 0%           | 50%   | 50%                 | 0%                  |
| BillDiscrepancy                      |             2 | 0%                 | 50%                | 0%           | 50%   | 100%                | 0%                  |
| StatementCopy                        |             8 | 0%                 | 88%                | 50%          | 50%   | 75%                 | 38%                 |
| StatementInquiry                     |             5 | 40%                | 60%                | 20%          | 20%   | 80%                 | 0%                  |
| YearEndStatementInquiry              |             1 | 0%                 | 100%               | 100%         | 100%  | 100%                | 0%                  |
| FraudulentActivity                   |             6 | 0%                 | 50%                | 50%          | 50%   | 50%                 | 50%                 |
| ReportLostCard                       |             4 | 25%                | 50%                | 25%          | 50%   | 25%                 | 25%                 |
| CardLockUnlock                       |             3 | 0%                 | 67%                | 67%          | 67%   | 33%                 | 67%                 |
| CardActivation                       |             4 | 25%                | 25%                | 0%           | 25%   | 0%                  | 25%                 |
| CardFacePhotoIssue                   |             3 | 33%                | 100%               | 100%         | 100%  | 100%                | 67%                 |
| AuthorizedUserManagement             |             3 | 0%                 | 33%                | 33%          | 33%   | 33%                 | 33%                 |
| AdditionalCardManagement             |             1 | 0%                 | 0%                 | 0%           | 0%    | 0%                  | 0%                  |
| DigitalWalletSupport                 |             6 | 17%                | 67%                | 50%          | 67%   | 67%                 | 50%                 |
| OnlineAccess                         |             8 | 0%                 | 0%                 | 0%           | 12%   | 0%                  | 0%                  |
| OnlineRegistrationSetup              |             3 | 0%                 | 67%                | 33%          | 0%    | 67%                 | 33%                 |
| AccountCardLinkingforUnifiedView     |             4 | 0%                 | 25%                | 0%           | 25%   | 50%                 | 0%                  |
| GeneralRewardsInformationInquiry     |             3 | 0%                 | 33%                | 0%           | 0%    | 0%                  | 0%                  |
| GeneralRewardsFAQ                    |             1 | 0%                 | 100%               | 0%           | 0%    | 100%                | 0%                  |
| RewardsProgramEnrollment             |             5 | 0%                 | 60%                | 40%          | 60%   | 40%                 | 40%                 |
| RewardsRedemptionRequest             |             5 | 0%                 | 20%                | 20%          | 20%   | 40%                 | 20%                 |
| ExternalRewardsProgramLinkingInquiry |             5 | 40%                | 100%               | 60%          | 80%   | 100%                | 60%                 |
| POCNightsInquiry                    |             4 | 25%                | 50%                | 25%          | 25%   | 50%                 | 25%                 |
| InitiateANewBalanceTransfer          |             6 | 0%                 | 33%                | 17%          | 67%   | 50%                 | 17%                 |
| StatusOfBalanceTransfer              |             6 | 0%                 | 83%                | 83%          | 83%   | 67%                 | 67%                 |
| BalanceTransferGeneralInquiry        |             3 | 0%                 | 33%                | 0%           | 33%   | 0%                  | 0%                  |
| InterestInquiry                      |             2 | 0%                 | 100%               | 100%         | 50%   | 50%                 | 50%                 |
| FeeInquiryManagement                 |             2 | 0%                 | 50%                | 50%          | 100%  | 100%                | 50%                 |
| CashAdvanceInquiry                   |             5 | 20%                | 60%                | 20%          | 60%   | 40%                 | 0%                  |
| CreditScoreReportInquiry             |             3 | 0%                 | 0%                 | 0%           | 0%    | 33%                 | 0%                  |
| CRSRequests                          |             5 | 0%                 | 80%                | 80%          | 80%   | 80%                 | 80%                 |
| CreditQuestion                       |             7 | 0%                 | 71%                | 71%          | 86%   | 57%                 | 57%                 |
| AccountStatusInquiry                 |             4 | 0%                 | 25%                | 0%           | 0%    | 25%                 | 0%                  |
| AccountProblemInquiry                |             5 | 0%                 | 40%                | 40%          | 40%   | 40%                 | 40%                 |
| AccountQuestion                      |             7 | 0%                 | 0%                 | 0%           | 0%    | 14%                 | 0%                  |
| AccountNumberInquiry                 |             7 | 0%                 | 14%                | 0%           | 0%    | 29%                 | 0%                  |
| SecuredCardInquiry                   |             7 | 0%                 | 43%                | 57%          | 43%   | 43%                 | 29%                 |
| ProductChangeUpgradeDowngrade        |             5 | 0%                 | 80%                | 80%          | 100%  | 100%                | 60%                 |
| CardAccountClosure                   |             6 | 0%                 | 0%                 | 0%           | 17%   | 17%                 | 0%                  |
| LargePurchaseNotification            |             2 | 50%                | 100%               | 100%         | 50%   | 100%                | 100%                |
| AuthorizationInquiryRequest          |             5 | 60%                | 80%                | 80%          | 80%   | 80%                 | 60%                 |
| ConciergeTravelAssistance            |             3 | 0%                 | 33%                | 0%           | 33%   | 33%                 | 0%                  |
| DebitCardInquiryManagement           |             5 | 20%                | 40%                | 20%          | 40%   | 40%                 | 40%                 |
| MortgageInquiryManagement            |             5 | 40%                | 60%                | 40%          | 20%   | 60%                 | 20%                 |
| BankAccountInformationManagement     |             7 | 0%                 | 57%                | 43%          | 71%   | 43%                 | 43%                 |
| ContactFollowUp                      |             3 | 0%                 | 67%                | 67%          | 67%   | 67%                 | 67%                 |
| POCShopProgramInquiry               |             3 | 67%                | 100%               | 100%         | 100%  | 100%                | 100%                |
| DeceasedAccountHolderNotification    |             3 | 0%                 | 0%                 | 0%           | 33%   | 33%                 | 0%                  |
| CancelBalanceTransfer                |             5 | 0%                 | 100%               | 60%          | 100%  | 60%                 | 80%                 |
| CancelAutoPay                        |             4 | 0%                 | 100%               | 75%          | 100%  | 75%                 | 50%                 |
| AutoPayManagement                    |             5 | 0%                 | 20%                | 20%          | 20%   | 20%                 | 20%                 |
| ChangeCardOrAccountNumber            |             6 | 0%                 | 33%                | 17%          | 0%    | 0%                  | 17%                 |
| ChangeNumber                         |             7 | 0%                 | 29%                | 14%          | 0%    | 0%                  | 0%                  |
| AddressPersonalInfoChange            |             4 | 50%                | 75%                | 75%          | 75%   | 100%                | 75%                 |
| AddressVerificationInquiry           |             6 | 17%                | 33%                | 50%          | 50%   | 33%                 | 33%                 |
| PhoneNumberUpdate                    |             7 | 14%                | 57%                | 71%          | 57%   | 71%                 | 57%                 |
| EmailAddressUpdate                   |             2 | 0%                 | 100%               | 50%          | 100%  | 100%                | 50%                 |
| NameChangeRequest                    |             9 | 22%                | 67%                | 56%          | 78%   | 67%                 | 56%                 |
| IncomeInformationUpdate              |             5 | 20%                | 60%                | 60%          | 60%   | 60%                 | 60%                 |
| AccountUpdate                        |             6 | 0%                 | 33%                | 0%           | 50%   | 33%                 | 17%                 |
| PasswordResetManagement              |             1 | 0%                 | 100%               | 100%         | 0%    | 0%                  | 0%                  |
| PinManagement                        |             7 | 14%                | 43%                | 43%          | 43%   | 29%                 | 29%                 |
| DisputeATransaction                  |             5 | 0%                 | 80%                | 80%          | 80%   | 80%                 | 80%                 |
| CheckStatusofExistingDispute         |             5 | 0%                 | 40%                | 40%          | 40%   | 40%                 | 40%                 |
| CancelRecurringCharges               |             4 | 0%                 | 25%                | 25%          | 25%   | 25%                 | 25%                 |
| CancelStopPayment                    |             6 | 0%                 | 50%                | 17%          | 17%   | 17%                 | 17%                 |
| ReportStolenCard                     |             4 | 25%                | 75%                | 50%          | 75%   | 75%                 | 50%                 |
| CardIsNotWorking                     |             8 | 0%                 | 38%                | 38%          | 38%   | 38%                 | 38%                 |
| TransactionDeclined                  |             6 | 0%                 | 83%                | 67%          | 67%   | 83%                 | 67%                 |
| CardExpirationRenewal                |             5 | 0%                 | 40%                | 40%          | 60%   | 40%                 | 20%                 |
| DamagedCardReplacement               |             8 | 0%                 | 62%                | 62%          | 38%   | 62%                 | 62%                 |
| CardNotReceivedInquiry               |             3 | 0%                 | 33%                | 33%          | 33%   | 33%                 | 33%                 |
| InitiateNewCardApplication           |             3 | 0%                 | 33%                | 0%           | 33%   | 33%                 | 0%                  |
| LoanInquiryManagement                |            10 | 10%                | 40%                | 20%          | 50%   | 20%                 | 20%                 |
| GeneralCheckInquiry                  |             5 | 0%                 | 60%                | 40%          | 40%   | 40%                 | 40%                 |
| MultiAccountCardManagement           |             3 | 0%                 | 33%                | 0%           | 67%   | 33%                 | 33%                 |
| AccountDebtConsolidation             |             4 | 0%                 | 50%                | 50%          | 75%   | 0%                  | 0%                  |
| MembershipManagement                 |             5 | 0%                 | 40%                | 40%          | 60%   | 20%                 | 40%                 |
| VirtualAccountCardManagement         |             4 | 25%                | 50%                | 50%          | 50%   | 50%                 | 50%                 |
| GiftCardInquiryManagement            |             2 | 50%                | 50%                | 50%          | 50%   | 50%                 | 50%                 |
| RebateInquiryAndManagement           |             4 | 0%                 | 50%                | 25%          | 25%   | 50%                 | 25%                 |
| RewardsCertificateRegeneration       |             3 | 33%                | 67%                | 67%          | 67%   | 67%                 | 67%                 |
| RewardsBalanceInquiry                |             4 | 50%                | 100%               | 100%         | 100%  | 100%                | 50%                 |
| PromotionInquiry                     |             6 | 0%                 | 33%                | 33%          | 33%   | 33%                 | 33%                 |
| MinimumPaymentCalculation            |             5 | 0%                 | 40%                | 40%          | 60%   | 40%                 | 20%                 |
| OverpaymentDuplicatePaymentInquiry   |             7 | 0%                 | 43%                | 29%          | 43%   | 29%                 | 29%                 |
| PaymentAssistanceFinancialHardship   |             2 | 0%                 | 0%                 | 0%           | 50%   | 0%                  | 0%                  |
| DocumentRequestInquiry               |             4 | 0%                 | 75%                | 75%          | 50%   | 25%                 | 25%                 |
| DisasterReliefInquiry                |             1 | 0%                 | 100%               | 100%         | 100%  | 100%                | 100%                |
| BranchATMLocationANDIssueInquiry     |             1 | 0%                 | 100%               | 100%         | 100%  | 100%                | 100%                |
| OnlineTransactionInquiry             |             2 | 0%                 | 0%                 | 0%           | 0%    | 0%                  | 0%                  |
| BalanceAndMakePayment                |             4 | 0%                 | 75%                | 25%          | 75%   | 75%                 | 25%                 |
| OtherLanguageRequest                 |             8 | 0%                 | 62%                | 62%          | 75%   | 62%                 | 50%                 |
| IVRNavigationRestart                 |             3 | 0%                 | 33%                | 33%          | 33%   | 33%                 | 33%                 |
| ConversationHoldOn                   |             4 | 25%                | 75%                | 75%          | 75%   | 50%                 | 75%                 |
| PaperlessManagement                  |             6 | 0%                 | 33%                | 17%          | 0%    | 17%                 | 17%                 |
| UnclassifiableOther                  |             3 | 0%                 | 0%                 | 67%          | 0%    | 0%                  | 33%                 |
| RequestARepresentative               |             7 | 100%               | 100%               | 86%          | 71%   | 100%                | 86%                 |
| RepeatVerbiage                       |             7 | 0%                 | 0%                 | 14%          | 14%   | 0%                  | 0%                  |
| EnglishLanguageRequest               |             2 | 0%                 | 100%               | 50%          | 100%  | 100%                | 100%                |
| AcknowledgementOfGratitude           |             4 | 0%                 | 25%                | 0%           | 0%    | 0%                  | 0%                  |
| InteractionComplete                  |             2 | 0%                 | 50%                | 50%          | 50%   | 50%                 | 50%                 |

## 7. Hardest and easiest intents (intents with at least 3 calls)

Hardest 12 by mean exact accuracy of the 5 API systems:

| intent                           |   eval_calls_total |   exact_acc__mean_5_api_systems |   exact_acc__classic_tfidf_lr |
|:---------------------------------|-------------------:|--------------------------------:|------------------------------:|
| GeneralRewardsInformationInquiry |                  3 |                            0.07 |                          0    |
| OnlineAccess                     |                  8 |                            0.1  |                          0.5  |
| RepeatVerbiage                   |                  7 |                            0.11 |                          0    |
| CardAccountClosure               |                  6 |                            0.13 |                          0    |
| AcknowledgementOfGratitude       |                  4 |                            0.15 |                          0.25 |
| AccountNumberInquiry             |                  7 |                            0.2  |                          0.29 |
| CancelRecurringCharges           |                  4 |                            0.25 |                          0.5  |
| ChangeNumber                     |                  7 |                            0.26 |                          0    |
| ChangeCardOrAccountNumber        |                  6 |                            0.3  |                          0.33 |
| PaperlessManagement              |                  6 |                            0.3  |                          0    |
| BalanceValueInquiry              |                  3 |                            0.33 |                          0    |
| IVRNavigationRestart             |                  3 |                            0.33 |                          0.33 |

Easiest 8:

| intent                               |   eval_calls_total |   exact_acc__mean_5_api_systems |   exact_acc__classic_tfidf_lr |
|:-------------------------------------|-------------------:|--------------------------------:|------------------------------:|
| ExternalRewardsProgramLinkingInquiry |                  5 |                            0.96 |                          0.4  |
| POCShopProgramInquiry               |                  3 |                            1    |                          1    |
| ProductChangeUpgradeDowngrade        |                  5 |                            1    |                          0.2  |
| CardFacePhotoIssue                   |                  3 |                            1    |                          0.33 |
| CancelBalanceTransfer                |                  5 |                            1    |                          0.6  |
| RewardsBalanceInquiry                |                  4 |                            1    |                          0.5  |
| BalanceAndMakePayment                |                  4 |                            1    |                          0.25 |
| UnclassifiableOther                  |                  3 |                            1    |                          0    |

## 8. Most common confusions per system (expected -> predicted, both iterations)

| family                         | y_true                     | pred                              |   count |
|:-------------------------------|:---------------------------|:----------------------------------|--------:|
| classic_tfidf_lr               | StatementCopy              | StatementInquiry                  |       6 |
| classic_tfidf_lr               | CardIsNotWorking           | DamagedCardReplacement            |       4 |
| classic_tfidf_lr               | ChangeNumber               | ChangeCardOrAccountNumber         |       4 |
| classic_tfidf_lr               | RepeatVerbiage             | IVRNavigationRestart              |       4 |
| classic_tfidf_lr               | AccountNumberInquiry       | AccountProblemInquiry             |       3 |
| classic_tfidf_lr               | AccountStatusInquiry       | AccountProblemInquiry             |       3 |
| claude-haiku-5-5_explicit      | AccountNumberInquiry       | AccountQuestion                   |       3 |
| claude-haiku-5-5_explicit      | CardAccountClosure         | DeceasedAccountHolderNotification |       3 |
| claude-haiku-5-5_explicit      | CardAccountClosure         | UnclassifiableOther               |       3 |
| claude-haiku-5-5_explicit      | DamagedCardReplacement     | UnclassifiableOther               |       3 |
| claude-haiku-5-5_explicit      | OnlineAccess               | AccountCardLinkingforUnifiedView  |       3 |
| claude-haiku-5-5_explicit      | OnlineAccess               | UnclassifiableOther               |       3 |
| claude-sonnet-5-5_explicit     | AccountNumberInquiry       | AccountQuestion                   |       3 |
| claude-sonnet-5-5_explicit     | AcknowledgementOfGratitude | UnclassifiableOther               |       3 |
| claude-sonnet-5-5_explicit     | CardAccountClosure         | UnclassifiableOther               |       3 |
| claude-sonnet-5-5_explicit     | DamagedCardReplacement     | UnclassifiableOther               |       3 |
| claude-sonnet-5-5_explicit     | OnlineAccess               | UnclassifiableOther               |       3 |
| claude-sonnet-5-5_explicit     | PromotionInquiry           | UnclassifiableOther               |       3 |
| gemini-3.1-flash-lite_explicit | AccountNumberInquiry       | AccountQuestion                   |       3 |
| gemini-3.1-flash-lite_explicit | AccountUpdate              | AccountQuestion                   |       3 |
| gemini-3.1-flash-lite_explicit | AcknowledgementOfGratitude | UnclassifiableOther               |       3 |
| gemini-3.1-flash-lite_explicit | ChangeCardOrAccountNumber  | AccountNumberInquiry              |       3 |
| gemini-3.1-flash-lite_explicit | ChangeNumber               | AccountUpdate                     |       3 |
| gemini-3.1-flash-lite_explicit | OnlineAccess               | AccountCardLinkingforUnifiedView  |       3 |
| gpt-6-luna_explicit            | AcknowledgementOfGratitude | UnclassifiableOther               |       4 |
| gpt-6-luna_explicit            | AccountNumberInquiry       | AccountQuestion                   |       3 |
| gpt-6-luna_explicit            | CardAccountClosure         | UnclassifiableOther               |       3 |
| gpt-6-luna_explicit            | CardIsNotWorking           | UnclassifiableOther               |       3 |
| gpt-6-luna_explicit            | OnlineAccess               | AccountCardLinkingforUnifiedView  |       3 |
| gpt-6-luna_explicit            | OnlineAccess               | UnclassifiableOther               |       3 |
| jev                            | ChangeNumber               | PhoneNumberUpdate                 |       4 |
| jev                            | BalanceQuestion            | BalanceValueInquiry               |       3 |
| jev                            | CardAccountClosure         | UnclassifiableOther               |       3 |
| jev                            | CardIsNotWorking           | UnclassifiableOther               |       3 |
| jev                            | OnlineAccess               | AccountCardLinkingforUnifiedView  |       3 |
| jev                            | RepeatVerbiage             | IVRNavigationRestart              |       3 |

## 9. Files

- `summary_by_intent.csv` (every column above for all 114 intents), `summary_by_system_iteration.csv`, `calls_per_intent_uniformity.csv`
- `results.md` (the run's own report), `run.log`, `events.jsonl`, `run_manifest.json`, `audit.jsonl`, `iterations.csv`, `data/*.jsonl`
