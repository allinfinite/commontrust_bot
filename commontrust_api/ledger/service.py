from __future__ import annotations

from commontrust_api.reputation.service import ReputationService


class InsufficientCreditError(Exception):
    pass


class MutualCreditService:
    def __init__(self, pb: object, reputation: ReputationService):
        self.pb = pb
        self.reputation = reputation

    async def get_or_create_mc_group(
        self, group_record_id: str, currency_name: str = "Credit", currency_symbol: str = "Cr"
    ) -> dict:
        mc_group = await self.pb.mc_group_get(group_record_id)
        if mc_group:
            should_update = (
                mc_group.get("currency_name") != currency_name
                or mc_group.get("currency_symbol") != currency_symbol
            )
            if should_update:
                return await self.pb.mc_group_update_currency(
                    mc_group.get("id"), currency_name, currency_symbol
                )
            return mc_group
        return await self.pb.mc_group_create(group_record_id, currency_name, currency_symbol)

    async def get_or_create_account(self, mc_group_id: str, member_record_id: str) -> dict:
        account = await self.pb.mc_account_get(mc_group_id, member_record_id)
        if account:
            return account

        rep = await self.reputation.get_reputation(member_record_id)
        credit_limit = self.reputation.compute_credit_limit(int(rep["verified_deals"]))
        return await self.pb.mc_account_create(mc_group_id, member_record_id, credit_limit)

    async def refresh_credit_limit(self, mc_group_id: str, member_record_id: str) -> dict:
        account = await self.get_or_create_account(mc_group_id, member_record_id)
        rep = await self.reputation.get_reputation(member_record_id)
        new_limit = self.reputation.compute_credit_limit(int(rep["verified_deals"]))
        if int(account.get("credit_limit", 0)) != new_limit:
            return await self.pb.mc_account_update(account.get("id"), int(account.get("balance", 0)), new_limit)
        return account

    async def get_account_balance(self, mc_group_id: str, member_record_id: str) -> dict:
        account = await self.refresh_credit_limit(mc_group_id, member_record_id)
        mc_group = await self.pb.get_record("mc_groups", mc_group_id)
        bal = int(account.get("balance", 0))
        limit = int(account.get("credit_limit", 0))
        return {
            "balance": bal,
            "credit_limit": limit,
            "available": bal + limit,
            "currency": mc_group.get("currency_name", "Credit"),
            "symbol": mc_group.get("currency_symbol", "Cr"),
        }

    async def create_payment(
        self,
        mc_group_id: str,
        payer_member_record_id: str,
        payee_member_record_id: str,
        amount: int,
        description: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if payer_member_record_id == payee_member_record_id:
            raise ValueError("Cannot pay yourself")

        if idempotency_key:
            existing = await self.pb.mc_transaction_get_by_idempotency(mc_group_id, idempotency_key)
            if existing:
                payer_account = await self.pb.mc_account_get(mc_group_id, payer_member_record_id)
                payee_account = await self.pb.mc_account_get(mc_group_id, payee_member_record_id)
                return {
                    "transaction": existing,
                    "new_payer_balance": int(payer_account.get("balance", 0)) if payer_account else 0,
                    "new_payee_balance": int(payee_account.get("balance", 0)) if payee_account else 0,
                    "already_applied": True,
                }

        payer_account = await self.refresh_credit_limit(mc_group_id, payer_member_record_id)
        payee_account = await self.refresh_credit_limit(mc_group_id, payee_member_record_id)

        payer_balance = int(payer_account.get("balance", 0))
        payer_credit_limit = int(payer_account.get("credit_limit", 0))
        payer_available = payer_balance + payer_credit_limit
        if payer_available < amount:
            raise InsufficientCreditError(
                f"Insufficient credit. Available: {payer_available}, Required: {amount}"
            )

        new_payer_balance = payer_balance - amount
        new_payee_balance = int(payee_account.get("balance", 0)) + amount

        transaction = await self.pb.mc_transaction_create(
            mc_group_id=mc_group_id,
            payer_id=payer_member_record_id,
            payee_id=payee_member_record_id,
            amount=amount,
            description=description,
            idempotency_key=idempotency_key,
        )

        transaction_id = transaction.get("id")
        await self.pb.mc_entry_create(
            transaction_id=transaction_id,
            account_id=payer_account.get("id"),
            amount=-amount,
            balance_after=new_payer_balance,
        )
        await self.pb.mc_entry_create(
            transaction_id=transaction_id,
            account_id=payee_account.get("id"),
            amount=amount,
            balance_after=new_payee_balance,
        )

        await self.pb.mc_account_update(payer_account.get("id"), new_payer_balance)
        await self.pb.mc_account_update(payee_account.get("id"), new_payee_balance)

        return {
            "transaction": transaction,
            "new_payer_balance": new_payer_balance,
            "new_payee_balance": new_payee_balance,
            "already_applied": False,
        }

    async def verify_zero_sum(self, mc_group_id: str) -> dict:
        result = await self.pb.list_records(
            "mc_accounts", filter=f'mc_group_id="{mc_group_id}"', per_page=500
        )
        accounts = result.get("items", [])
        total_balance = sum(int(acc.get("balance", 0)) for acc in accounts)
        return {
            "is_zero_sum": total_balance == 0,
            "total_balance": total_balance,
            "account_count": len(accounts),
        }

    async def get_transaction_history(
        self, mc_group_id: str, member_record_id: str, limit: int = 20
    ) -> list[dict]:
        filter_str = (
            f'mc_group_id="{mc_group_id}" && (payer_id="{member_record_id}" || payee_id="{member_record_id}")'
        )
        result = await self.pb.list_records(
            "mc_transactions", filter=filter_str, per_page=limit, sort="-created"
        )
        return result.get("items", [])

    async def update_credit_limit(self, mc_group_id: str, member_record_id: str, new_limit: int) -> dict:
        account = await self.get_or_create_account(mc_group_id, member_record_id)
        return await self.pb.mc_account_update(account.get("id"), int(account.get("balance", 0)), new_limit)
