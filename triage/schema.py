from enum import Enum

from pydantic import BaseModel, Field


class Language(str, Enum):
    sv = "sv"
    fi = "fi"
    no = "no"
    da = "da"
    nl = "nl"
    en = "en"
    other = "other"


class Category(str, Enum):
    shipping_status = "shipping_status"
    return_exchange = "return_exchange"
    damaged_wrong_item = "damaged_wrong_item"
    order_change = "order_change"
    product_question = "product_question"
    payment_billing = "payment_billing"
    other = "other"


class Email(BaseModel):
    """An incoming customer email. `market` is the storefront it was sent to."""

    market: str
    subject: str
    body: str


class Triage(BaseModel):
    language: Language = Field(description="Language the customer wrote in.")
    category: Category = Field(description="What the customer needs resolved first.")
    escalate: bool = Field(description="True when a person has to decide, per the escalation rules.")
    escalate_reason: str = Field(description="Which escalation rule applies, in a few words. Empty when escalate is false.")
    summary: str = Field(description="One sentence in English for the person handling the inbox.")
    draft_reply: str = Field(description="Reply to the customer, in the customer's language.")
