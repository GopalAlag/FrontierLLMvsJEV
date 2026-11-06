"""Servicing workflows behind each intent, run against a mock card account (no real backend).

Each workflow either completes (speaks an answer / performs a mock action) or asks the caller for the next
piece of information (a normal IVR dialog turn); both count as serviced. Slots (amount, last 4 digits) come from
one shared regex extractor, so every classifier is compared on intent routing alone.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .data import parse_call
from .intents import AGENT, BY_NAME


@dataclass
class Account:
    balance: float = 1254.30
    credit_limit: float = 5000.0
    min_payment: float = 35.0
    due_date: str = "November 3rd"
    payoff: float = 1269.87
    apr: float = 21.99
    last_txns: tuple = (("", 48.12), ("", 89.99), ("", 63.40))


@dataclass
class Result:
    workflow: str
    status: str            # completed | collect_slots | transferred
    say: str               # what the IVR speaks back
    slots: dict = field(default_factory=dict)


_AMT = re.compile(r"\$\s?(\d[\d,]*(?:\.\d{2})?)")
_L4 = re.compile(r"\b(\d{4})\b")


def extract_slots(text: str) -> dict:
    s = {}
    if m := _AMT.search(text):
        s["amount"] = float(m.group(1).replace(",", ""))
    if m := _L4.search(text):
        s["last4"] = m.group(1)
    return s


def _a(a: Account):
    """workflow id -> (status, say) for workflows that read account data."""
    return {
        "wf_balance": ("completed", f"Your current balance is ${a.balance:,.2f}."),
        "wf_transactions": ("completed", "Recent charges: " + "; ".join(f"{m} ${v:.2f}" for m, v in a.last_txns) + "."),
        "wf_payoff": ("completed", f"Your payoff amount through today is ${a.payoff:,.2f}."),
        "wf_credit_q": ("completed", f"You have ${a.credit_limit - a.balance:,.2f} of ${a.credit_limit:,.0f} available."),
        "wf_interest": ("completed", f"Your purchase APR is {a.apr}%."),
        "wf_min_payment": ("completed", f"Your minimum payment is ${a.min_payment:.2f}; paying part of the balance does not change the due date."),
        "wf_due_date_change": ("collect_slots", f"Your due date is {a.due_date}. Which day of the month would you prefer?"),
    }


_STATIC = {  # workflow id -> (status, say)
    "wf_credits": ("completed", "Recent credits and refunds on your account are listed in your statement; I can read the latest ones."),
    "wf_payment_verify": ("completed", "Your last payment was received and posted to your account."),
    "wf_payment_options": ("completed", "You can pay online, by phone, by mail, or set up automatic payments."),
    "wf_phone_pay_fee": ("completed", "Payments by phone with an agent may carry a fee; paying with the automated system is free."),
    "wf_payment_address": ("completed", "Mail payments to the address printed on your statement's payment coupon."),
    "wf_billing": ("collect_slots", "What would you like to know about your bill?"),
    "wf_bill_dispute": ("collect_slots", "I'm sorry about the billing error. Which charge on the bill looks wrong?"),
    "wf_statement": ("completed", "I have emailed your latest statement to the address on file."),
    "wf_year_end": ("completed", "Your year-end summary is available online and I can mail a copy."),
    "wf_fraud": ("completed", "I've flagged your account and will connect you to the fraud team."),
    "wf_lost_card": ("completed", "Your card is blocked and a replacement will arrive in 3 to 5 business days."),
    "wf_card_lock": ("completed", "Your card lock setting has been updated."),
    "wf_activate": ("collect_slots", "Please say or enter the last four digits of your new card."),
    "wf_card_photo": ("completed", "I can order a replacement card with a new photo."),
    "wf_auth_user": ("collect_slots", "Would you like to add or remove an authorized user?"),
    "wf_additional_card": ("collect_slots", "Who is the additional card for?"),
    "wf_wallet": ("completed", "I've texted you a link with steps to add your card to your digital wallet."),
    "wf_online_access": ("completed", "I've sent a password reset link to your registered contact."),
    "wf_online_reg": ("completed", "I've sent a registration link to your registered contact."),
    "wf_card_linking": ("completed", "I've sent steps to link your cards in the app."),
    "wf_rewards_info": ("completed", "You earn points on every purchase; I can read your current rewards summary."),
    "wf_rewards_clarify": ("collect_slots", "Would you like to check, redeem or enroll in rewards?"),
    "wf_rewards_enroll": ("completed", "I've enrolled your card in the rewards program."),
    "wf_rewards_redeem": ("collect_slots", "How would you like to redeem: statement credit, gift card or travel?"),
    "wf_rewards_link": ("completed", "I've sent instructions to link your external rewards program."),
    "wf_nights": ("completed", "Nights offers access to special events; I've texted the details."),
    "wf_bt_start": ("collect_slots", "What amount would you like to transfer, and from which card?"),
    "wf_bt_status": ("completed", "Your balance transfer is in process and should post in 7 to 10 days."),
    "wf_bt_info": ("completed", "Balance transfers carry a fee and a promotional rate; I can read the current offer."),
    "wf_fees": ("completed", "Your fees are listed in your agreement; I can start a fee review."),
    "wf_cash_advance": ("completed", "Your cash advance limit and fee are listed in your agreement; I can read them."),
    "wf_credit_report": ("completed", "I can explain what affects your credit score; the report is available from the bureaus."),
    "wf_crs": ("completed", "I've logged your credit reporting request."),
    "wf_account_status": ("completed", "Your account is open and in good standing."),
    "wf_account_problem": ("collect_slots", "I'm sorry about the problem. Can you tell me what is wrong with your account?"),
    "wf_account_q": ("collect_slots", "What would you like to know about your account?"),
    "wf_account_number": ("completed", "For security I can only read the last four digits of your card number."),
    "wf_secured_card": ("completed", "I can give you the status of your secured card and deposit."),
    "wf_product_change": ("collect_slots", "Which card would you like to switch to?"),
    "wf_closure": ("collect_slots", "I can help with closing the account. May I ask the reason?"),
    "wf_large_purchase": ("completed", "A large-purchase note has been added to your account."),
    "wf_authorization": ("collect_slots", "Please give me the merchant and amount of the purchase."),
    "wf_concierge": ("completed", "Connecting you to concierge travel services."),
    "wf_debit_transfer": ("completed", "Transferring you to debit card services."),
    "wf_mortgage_transfer": ("completed", "Transferring you to mortgage services."),
    "wf_bank_account": ("collect_slots", "Please provide the new bank routing and account number."),
    "wf_shop": ("completed", "Shop gives offers at partner merchants; I've texted you a link."),
    "wf_deceased": ("collect_slots", "I'm very sorry for your loss. I can start the process; are you an authorized person on the account?"),
    "wf_bt_cancel": ("completed", "I've requested cancellation of your pending balance transfer."),
    "wf_autopay": ("collect_slots", "Would you like to set up, change or cancel automatic payments?"),
    "wf_change_card_number": ("completed", "I can issue a new card number; it will arrive in 3 to 5 business days."),
    "wf_change_number": ("collect_slots", "Which number would you like to change: card number, account number or phone number?"),
    "wf_update_address": ("collect_slots", "Please say your new address."),
    "wf_address_verify": ("completed", "The address on file ends in the digits shown in your profile; I can read it back."),
    "wf_update_phone": ("collect_slots", "Please say your new phone number."),
    "wf_update_email": ("collect_slots", "Please say your new email address."),
    "wf_update_name": ("collect_slots", "A name change needs documentation; I'll text you the steps."),
    "wf_update_income": ("collect_slots", "What is your updated annual income or employer?"),
    "wf_account_update": ("collect_slots", "What would you like to update on your account?"),
    "wf_password": ("completed", "I've sent a password reset link to your registered contact."),
    "wf_pin": ("completed", "I have sent a PIN reset link to your registered phone."),
    "wf_dispute": ("collect_slots", "Which charge would you like to dispute? Say the merchant name or amount."),
    "wf_dispute_status": ("completed", "Your dispute is under review; we will update you within 10 business days."),
    "wf_recurring_charge": ("collect_slots", "Which merchant's recurring charge would you like stopped?"),
    "wf_cancel_payment": ("collect_slots", "Which payment would you like to cancel?"),
    "wf_card_not_working": ("completed", "I'm sorry your card isn't working. I can send a replacement card."),
    "wf_declined": ("collect_slots", "I'm sorry about the decline. Please tell me the merchant and amount so I can check."),
    "wf_card_renewal": ("completed", "Your card's expiry is on the card face; a renewal card is mailed automatically before it expires."),
    "wf_replace_card": ("completed", "A replacement card will arrive in 3 to 5 business days."),
    "wf_card_delivery": ("completed", "Your new card shipped and should arrive within 5 business days."),
    "wf_application": ("completed", "I can share application requirements and check your application status."),
    "wf_loan_transfer": ("completed", "Transferring you to loan servicing."),
    "wf_check_inquiry": ("completed", "I can help with checks; what would you like to know?"),
    "wf_multi_account": ("collect_slots", "Which card would you like to switch to?"),
    "wf_debt_consolidation": ("completed", "I can explain how to consolidate accounts or transfer balances."),
    "wf_membership": ("collect_slots", "What would you like to do with your membership?"),
    "wf_virtual_card": ("completed", "I can help with your virtual card number; a replacement can be issued online."),
    "wf_gift_card": ("completed", "I can give you gift card information; what would you like to know?"),
    "wf_rebate": ("completed", "I can look up your rebate status and send details."),
    "wf_rewards_cert": ("completed", "I've requested a new rewards certificate."),
    "wf_rewards_balance": ("completed", "Your rewards balance is available now; I can read it to you."),
    "wf_promo": ("completed", "You have current offers; I've texted the details."),
    "wf_overpayment": ("completed", "I see an extra payment on your account; I can start a refund of the credit balance."),
    "wf_hardship": ("collect_slots", "I'm sorry you're having difficulty. I can review payment relief options; shall I continue?"),
    "wf_document_request": ("collect_slots", "Which letter or document would you like me to send?"),
    "wf_disaster_relief": ("completed", "We offer relief options for affected customers; I can connect you to that team."),
    "wf_branch": ("completed", "I've texted you a link to find the nearest branch or ATM."),
    "wf_online_txn": ("completed", "I can look up recent online purchases; which merchant?"),
    "wf_balance_pay": ("collect_slots", "I can read your balance and take a payment. How much would you like to pay?"),
    "wf_other_language": ("completed", "Let me connect you with language support."),
    "wf_menu_restart": ("completed", "Returning to the main menu."),
    "wf_hold": ("completed", "Of course, I'll wait."),
    "wf_paperless": ("completed", "Your statement delivery preference has been updated."),
    "wf_out_of_scope": ("collect_slots", "Sorry, I didn't catch that. What would you like to do with your credit card?"),
    "wf_followup": ("completed", "Thank you for following up; I'm connecting you to the right team."),
    "wf_repeat": ("completed", "Sure, let me say that again."),
    "wf_english": ("completed", "Switching to English."),
    "wf_end_call": ("completed", "You're welcome. Goodbye."),
}


def service(intent: str, xml: str, account: Account | None = None) -> Result:
    """Run the workflow for a *confidently classified* intent."""
    wf = BY_NAME[intent].workflow
    if wf == AGENT:
        return Result(AGENT, "transferred", "Connecting you to an agent.")
    slots = extract_slots(parse_call(xml).text)
    status, say = {**_STATIC, **_a(account or Account())}[wf]
    return Result(wf, status, say, slots)
