"""Intent catalog (names taken from the sample brands-LOB credit card IVR data) and the workflow each intent routes to.

Near-synonymous intents share a workflow (e.g. BalanceQuestion and BalanceValueInquiry -> wf_balance), so the
experiment reports both intent accuracy (exact label) and routing accuracy (right workflow).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Intent:
    name: str
    workflow: str          # servicing workflow id, or AGENT for a live-agent transfer
    description: str
    hint: str = ""         # disambiguation guidance used by the v2/v3 prompts


AGENT = "live_agent_queue"

# (name, workflow, description, optional hint)
_ROWS = [
    ("BalanceQuestion", "wf_balance", "Vague question or discussion about the card balance, without asking for the amount.",
     "No specific ask ('question about my balance'). If they ask for the amount ('what is my balance') it is BalanceValueInquiry."),
    ("BalanceValueInquiry", "wf_balance", "Caller asks for the actual balance amount owed."),
    ("ReviewMultipleTransactions", "wf_transactions", "Caller wants to review several recent purchases or transactions."),
    ("TransactionQuestion", "wf_transactions", "Question about one specific charge or transaction (unrecognised, duplicate, e-commerce).",
     "One charge = TransactionQuestion; a list of recent activity = ReviewMultipleTransactions; charges the caller denies making = FraudulentActivity."),
    ("ReviewCredits", "wf_credits", "Caller asks about credits, refunds or statement credits posted to the account."),
    ("PaymentVerification", "wf_payment_verify", "Caller wants to confirm a payment was received or posted."),
    ("PaymentMethodOptionsInquiry", "wf_payment_options", "Caller asks what ways they can pay (check, debit, phone, mail)."),
    ("OnlinePaymentMethodInquiry", "wf_payment_options", "Caller asks how to pay online or about online bill pay."),
    ("PhonePaymentFeeInquiry", "wf_phone_pay_fee", "Caller asks whether there is a fee for paying by phone or with an agent."),
    ("PaymentAddressInquiry", "wf_payment_address", "Caller asks where to mail a payment."),
    ("PayoffInquiry", "wf_payoff", "Caller asks for a payoff amount or payoff statement."),
    ("PaymentDueDateModification", "wf_due_date_change", "Caller wants to change or adjust the payment due date (including autopay date)."),
    ("BillingQuestion", "wf_billing", "General question about the bill or billing."),
    ("BillDiscrepancy", "wf_bill_dispute", "Caller says the bill or billing is wrong (billing error or issue).",
     "BillingQuestion is a neutral question; BillDiscrepancy asserts an error."),
    ("StatementCopy", "wf_statement", "Caller wants a copy of a statement sent or downloaded (a specific month)."),
    ("StatementInquiry", "wf_statement", "Question about the content of a statement."),
    ("YearEndStatementInquiry", "wf_year_end", "Caller wants annual, year-end or tax-year statements or summaries."),
    ("FraudulentActivity", "wf_fraud", "Caller reports fraud, scams, unauthorised use or a hacked account."),
    ("ReportLostCard", "wf_lost_card", "Caller lost the card or it is missing/stolen."),
    ("CardLockUnlock", "wf_card_lock", "Caller wants to lock, block, freeze or unlock the card."),
    ("CardActivation", "wf_activate", "Caller wants to activate a new card or account."),
    ("CardFacePhotoIssue", "wf_card_photo", "Caller has an issue with the photo/image on the card face."),
    ("AuthorizedUserManagement", "wf_auth_user", "Caller wants to add, change or remove an authorized user or card holder."),
    ("AdditionalCardManagement", "wf_additional_card", "Caller wants a second or additional card.",
     "Adding a person to the account = AuthorizedUserManagement; an extra card = AdditionalCardManagement."),
    ("DigitalWalletSupport", "wf_wallet", "Caller wants help adding the card to Apple Pay, Google Pay or another wallet."),
    ("OnlineAccess", "wf_online_access", "Caller cannot log in, needs a password reset or has locked online access."),
    ("OnlineRegistrationSetup", "wf_online_reg", "Caller wants to register or set up online or mobile account access."),
    ("AccountCardLinkingforUnifiedView", "wf_card_linking", "Caller wants to link cards or accounts to see them together (e.g. in an app or profile)."),
    ("GeneralRewardsInformationInquiry", "wf_rewards_info", "Caller asks for information about their rewards, miles or cash back earned."),
    ("GeneralRewardsFAQ", "wf_rewards_info", "General rewards policy questions (expiry, bonus rules, combining, rebates)."),
    ("AmbiguousRewardsRequest", "wf_rewards_clarify", "Only mentions rewards/points/miles with no clear request; needs clarification.",
     "Very short or vague rewards mentions ('rewards', 'question about points') are Ambiguous; a clear ask is one of the other rewards intents."),
    ("RewardsProgramEnrollment", "wf_rewards_enroll", "Caller wants to enrol in or sign up for a rewards program."),
    ("RewardsRedemptionRequest", "wf_rewards_redeem", "Caller wants to redeem or spend points / cash back."),
    ("ExternalRewardsProgramLinkingInquiry", "wf_rewards_link", "Caller wants to link the card to an airline, hotel or other external rewards program."),
    ("CitiNightsInquiry", "wf_citi_nights", "Caller asks about the Citi Nights program."),
    ("InitiateANewBalanceTransfer", "wf_bt_start", "Caller wants to start a new balance transfer."),
    ("StatusOfBalanceTransfer", "wf_bt_status", "Caller asks about the status of an existing balance transfer."),
    ("BalanceTransferGeneralInquiry", "wf_bt_info", "General questions about balance transfers, fees, or debt consolidation."),
    ("InterestInquiry", "wf_interest", "Caller asks about APR, interest charged or promotional rates."),
    ("FeeInquiryManagement", "wf_fees", "Caller asks about fees (annual, late) or wants one waived or removed."),
    ("CashAdvanceInquiry", "wf_cash_advance", "Caller asks about cash advances, limit, fee or APR."),
    ("CreditScoreReportInquiry", "wf_credit_report", "Caller asks about their credit score or credit report."),
    ("CRSRequests", "wf_crs", "Credit Retail Services (CRS): help with a retail store-brand card or its program (Home Depot credit, Bean Bucks, store card questions)."),
    ("CreditQuestion", "wf_credit_q", "Question about available credit or the credit line."),
    ("AccountStatusInquiry", "wf_account_status", "Caller asks whether the account is open, closed or active."),
    ("AccountProblemInquiry", "wf_account_problem", "Caller reports a problem, issue or discrepancy with the account."),
    ("AccountQuestion", "wf_account_q", "Generic question about the account or account changes, no specifics."),
    ("AccountNumberInquiry", "wf_account_number", "Caller asks for or wants to change the account or card number."),
    ("SecuredCardInquiry", "wf_secured_card", "Questions about a secured card, deposit, upgrade or its delivery."),
    ("ProductChangeUpgradeDowngrade", "wf_product_change", "Caller wants to upgrade, downgrade or change the card/account type."),
    ("CardAccountClosure", "wf_closure", "Caller wants to close the account or card (including closure after a death)."),
    ("LargePurchaseNotification", "wf_large_purchase", "Caller wants to notify the bank of an upcoming large purchase."),
    ("AuthorizationInquiryRequest", "wf_authorization", "Caller asks to approve/authorize a purchase or payment, or why one was declined."),
    ("ConciergeTravelAssistance", "wf_concierge", "Caller wants concierge or travel booking help (flights, hotels)."),
    ("DebitCardInquiryManagement", "wf_debit_transfer", "Caller asks about a debit card (not this credit card); transfer to debit servicing."),
    ("MortgageInquiryManagement", "wf_mortgage_transfer", "Caller asks about a mortgage; transfer to mortgage servicing."),
    ("BankAccountInformationManagement", "wf_bank_account", "Caller wants to update the bank account used for payments."),
    ("ContactFollowUp", "wf_followup", "Caller is returning a call or following up on an email, letter or message from the bank."),
    # ---- intents seen in the second set of screenshots (paired intent + utterance rows) ----
    ("CitiShopProgramInquiry", "wf_citi_shop", "Caller asks about the Citi Shop program (auto-enrollment, problems, benefits)."),
    ("DeceasedAccountHolderNotification", "wf_deceased", "Caller reports that the account holder died or asks to close the account because of a death.",
     "Closing for a death = DeceasedAccountHolderNotification; any other closure = CardAccountClosure."),
    ("CancelBalanceTransfer", "wf_bt_cancel", "Caller wants to cancel, stop or undo a balance transfer."),
    ("CancelAutoPay", "wf_autopay", "Caller wants to cancel or stop automatic payments (auto pay).",
     "Stopping autopay = CancelAutoPay; changing its amount or date, or enrolling = AutoPayManagement."),
    ("AutoPayManagement", "wf_autopay", "Caller wants to enrol in, change the amount or date of, or otherwise manage automatic payments."),
    ("ChangeCardOrAccountNumber", "wf_change_card_number", "Caller wants a new or different card or account number."),
    ("ChangeNumber", "wf_change_number", "Caller wants to 'change my number' without saying which number (card, account or phone)."),
    ("AddressPersonalInfoChange", "wf_update_address", "Caller wants to change a home, mailing or billing address."),
    ("AddressVerificationInquiry", "wf_address_verify", "Caller wants to verify or check the address on file."),
    ("PhoneNumberUpdate", "wf_update_phone", "Caller wants to change the phone number on file."),
    ("EmailAddressUpdate", "wf_update_email", "Caller wants to change the email address on file."),
    ("NameChangeRequest", "wf_update_name", "Caller wants to change the name on the account or card (first, middle, last, legal)."),
    ("IncomeInformationUpdate", "wf_update_income", "Caller wants to update income or employment details."),
    ("AccountUpdate", "wf_account_update", "Generic request to update or change the account or card, without saying what."),
    ("PasswordResetManagement", "wf_password", "Caller forgot, wants to reset or change an online password.",
     "Password problems = PasswordResetManagement; cannot reach the app/site for other reasons = OnlineAccess; PIN = PinManagement."),
    ("PinManagement", "wf_pin", "Caller forgot, wants to change or set a card PIN."),
    ("DisputeATransaction", "wf_dispute", "Caller wants to dispute or cancel a charge or transaction.",
     "Contesting a known charge = DisputeATransaction; asking what a charge is = TransactionQuestion; denying all knowledge/unauthorised use = FraudulentActivity."),
    ("CheckStatusofExistingDispute", "wf_dispute_status", "Caller asks for the status of an existing dispute."),
    ("CancelRecurringCharges", "wf_recurring_charge", "Caller wants a recurring charge or subscription cancelled."),
    ("CancelStopPayment", "wf_cancel_payment", "Caller wants to cancel or stop a payment they made or scheduled."),
    ("ReportStolenCard", "wf_lost_card", "Caller says the card was stolen.",
     "Stolen = ReportStolenCard; lost/missing = ReportLostCard (same workflow)."),
    ("CardIsNotWorking", "wf_card_not_working", "Caller says the card is not working (chip/swipe failure)."),
    ("TransactionDeclined", "wf_declined", "Caller says a purchase or the card was declined or denied."),
    ("CardExpirationRenewal", "wf_card_renewal", "Caller asks about card expiry or needs a renewal card."),
    ("DamagedCardReplacement", "wf_replace_card", "Caller needs a replacement for a damaged, unreadable or worn card."),
    ("CardNotReceivedInquiry", "wf_card_delivery", "Caller has not received a new or replacement card."),
    ("InitiateNewCardApplication", "wf_application", "Caller wants to apply for a new credit card."),
    ("LoanInquiryManagement", "wf_loan_transfer", "Caller asks about a loan (student, auto, personal); not this credit card."),
    ("GeneralCheckInquiry", "wf_check_inquiry", "Caller asks about checks (reordering, a specific check)."),
    ("MultiAccountCardManagement", "wf_multi_account", "Caller has several cards/accounts and wants to switch to or manage another one."),
    ("AccountDebtConsolidation", "wf_debt_consolidation", "Caller wants to merge or combine accounts or consolidate debt."),
    ("MembershipManagement", "wf_membership", "Caller wants to manage a membership."),
    ("VirtualAccountCardManagement", "wf_virtual_card", "Caller asks about or has a problem with a virtual card or virtual account number."),
    ("GiftCardInquiryManagement", "wf_gift_card", "Caller asks about a gift card (balance, order not received)."),
    ("RebateInquiryAndManagement", "wf_rebate", "Caller asks about tracking or a missing rebate."),
    ("RewardsCertificateRegeneration", "wf_rewards_cert", "Caller needs a lost, stolen or expired rewards certificate reissued."),
    ("RewardsBalanceInquiry", "wf_rewards_balance", "Caller asks how many points, miles, dollars or cash back they have.",
     "A concrete ask for a rewards balance = RewardsBalanceInquiry; general rewards information = GeneralRewardsInformationInquiry; a vague mention = AmbiguousRewardsRequest."),
    ("PromotionInquiry", "wf_promo", "Caller asks about promotions or promotional rate eligibility."),
    ("MinimumPaymentCalculation", "wf_min_payment", "Caller asks how the minimum payment is calculated or affected by a payment."),
    ("OverpaymentDuplicatePaymentInquiry", "wf_overpayment", "Caller made a duplicate or extra payment and asks about it."),
    ("PaymentAssistanceFinancialHardship", "wf_hardship", "Caller asks for a payment plan or help because of financial hardship."),
    ("DocumentRequestInquiry", "wf_document_request", "Caller wants a letter or document (credit verification, account letter)."),
    ("DisasterReliefInquiry", "wf_disaster_relief", "Caller asks how a disaster or government shutdown affects the account."),
    ("BranchATMLocationANDIssueInquiry", "wf_branch", "Caller asks for a branch/ATM location, hours, or has an ATM issue."),
    ("OnlineTransactionInquiry", "wf_online_txn", "Caller asks about an online or e-commerce purchase or charge."),
    ("BalanceAndMakePayment", "wf_balance_pay", "Caller wants their balance and to make a payment in the same request."),
    ("OtherLanguageRequest", "wf_other_language", "Caller asks for a language other than English."),
    ("IVRNavigationRestart", "wf_menu_restart", "Caller wants to go back to the main menu or start over."),
    ("ConversationHoldOn", "wf_hold", "Caller asks the IVR to wait or hold on."),
    ("PaperlessManagement", "wf_paperless", "Caller wants to go paperless or get paper statements sent (e-statement settings)."),
    ("UnclassifiableOther", "wf_out_of_scope", "Utterance that is fragmentary, unintelligible or does not fit any intent."),
    ("RequestARepresentative", AGENT, "Caller asks for a live agent or representative."),
    ("RepeatVerbiage", "wf_repeat", "Caller asks the IVR to repeat or restart the prompt."),
    ("EnglishLanguageRequest", "wf_english", "Caller asks to switch to English."),
    ("AcknowledgementOfGratitude", "wf_end_call", "Caller says thank you.",
     "Thank-you and goodbye both end the call."),
    ("InteractionComplete", "wf_end_call", "Caller signals they are finished (goodbye, that is all)."),
]

INTENTS: list[Intent] = [Intent(*r) for r in _ROWS]
NAMES = [i.name for i in INTENTS]
BY_NAME = {i.name: i for i in INTENTS}
CANON = {n.lower(): n for n in NAMES}     # case-insensitive label canonicalisation


def catalog_text(with_hints: bool = False) -> str:
    lines = []
    for i in INTENTS:
        s = f"- {i.name}: {i.description}"
        if with_hints and i.hint:
            s += f" ({i.hint})"
        lines.append(s)
    return "\n".join(lines)
