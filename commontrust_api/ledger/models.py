from __future__ import annotations

from pydantic import BaseModel, Field


class EnableLedgerIn(BaseModel):
    currency_name: str = Field(default="Credit", min_length=1, max_length=32)
    currency_symbol: str = Field(default="Cr", min_length=1, max_length=8)
    group_title: str | None = Field(default=None, max_length=128)


class BalanceOut(BaseModel):
    balance: int
    credit_limit: int
    available: int
    currency: str
    symbol: str


class PaymentIn(BaseModel):
    payer_telegram_user_id: int = Field(..., ge=1)
    payee_telegram_user_id: int = Field(..., ge=1)
    amount: int = Field(..., ge=1)
    description: str | None = Field(default=None, max_length=256)
    idempotency_key: str | None = Field(default=None, max_length=128)


class PaymentOut(BaseModel):
    transaction_id: str
    new_payer_balance: int
    new_payee_balance: int
    symbol: str
    already_applied: bool = False


class SetAccountIn(BaseModel):
    credit_limit: int = Field(..., ge=0)


class ZeroSumOut(BaseModel):
    is_zero_sum: bool
    total_balance: int
    account_count: int

