from commontrust_bot.pocketbase_client import pb_client
from commontrust_bot.services.reputation import reputation_service


class InsufficientCreditError(Exception):
    pass


class MutualCreditService:
    def __init__(self, pb=None, reputation=None):
        # Allow injection for tests; default to global singletons.
        self.pb = pb or pb_client
        self.reputation = reputation or reputation_service

    async def get_or_create_mc_group(
        self, group_id: str, currency_name: str = "Credit", currency_symbol: str = "Cr"
    ) -> dict:
        mc_group = await self.pb.mc_group_get(group_id)
        if mc_group:
            return mc_group
        return await self.pb.mc_group_create(group_id, currency_name, currency_symbol)

    async def get_or_create_account(
        self, mc_group_id: str, member_id: str, member_record_id: str | None = None
    ) -> dict:
        account = await self.pb.mc_account_get(mc_group_id, member_id)
        if account:
            return account

        member_id_to_use = member_record_id or member_id
        rep = await self.reputation.get_reputation(member_id_to_use)
        credit_limit = self.reputation.compute_credit_limit(
            rep.get("verified_deals", 0) if rep else 0
        )

        return await self.pb.mc_account_create(mc_group_id, member_id, credit_limit)

    async def get_account_balance(self, mc_group_id: str, member_id: str) -> dict:
        account = await self.get_or_create_account(mc_group_id, member_id)
        mc_group = None
        try:
            mc_group = await self.pb.get_record("mc_groups", mc_group_id)
        except Exception:
            mc_group = None
        
        return {
            "balance": account.get("balance", 0),
            "credit_limit": account.get("credit_limit", 0),
            "available": account.get("balance", 0) + account.get("credit_limit", 0),
            "account_id": account.get("id"),
            "currency": mc_group.get("currency_name", "Credit") if mc_group else "Credit",
            "symbol": mc_group.get("currency_symbol", "Cr") if mc_group else "Cr",
        }

    async def create_payment(
        self,
        mc_group_id: str,
        payer_member_id: str,
        payee_member_id: str,
        amount: int,
        description: str | None = None,
    ) -> dict:
        if amount <= 0:
            raise ValueError("Amount must be positive")

        if payer_member_id == payee_member_id:
            raise ValueError("Cannot pay yourself")

        payer_account = await self.get_or_create_account(mc_group_id, payer_member_id)
        payee_account = await self.get_or_create_account(mc_group_id, payee_member_id)

        payer_balance = payer_account.get("balance", 0)
        payer_credit_limit = payer_account.get("credit_limit", 0)
        payer_available = payer_balance + payer_credit_limit

        if payer_available < amount:
            raise InsufficientCreditError(
                f"Insufficient credit. Available: {payer_available}, Required: {amount}"
            )

        new_payer_balance = payer_balance - amount
        new_payee_balance = payee_account.get("balance", 0) + amount

        transaction = await self.pb.mc_transaction_create(
            mc_group_id=mc_group_id,
            payer_id=payer_member_id,
            payee_id=payee_member_id,
            amount=amount,
            description=description,
        )

        transaction_id = transaction.get("id")

        payer_entry = await self.pb.mc_entry_create(
            transaction_id=transaction_id,
            account_id=payer_account.get("id"),
            amount=-amount,
            balance_after=new_payer_balance,
        )

        payee_entry = await self.pb.mc_entry_create(
            transaction_id=transaction_id,
            account_id=payee_account.get("id"),
            amount=amount,
            balance_after=new_payee_balance,
        )

        await self.pb.mc_account_update(payer_account.get("id"), new_payer_balance)
        await self.pb.mc_account_update(payee_account.get("id"), new_payee_balance)

        return {
            "transaction": transaction,
            "payer_entry": payer_entry,
            "payee_entry": payee_entry,
            "new_payer_balance": new_payer_balance,
            "new_payee_balance": new_payee_balance,
        }

    async def verify_zero_sum(self, mc_group_id: str) -> dict:
        result = await self.pb.list_records("mc_accounts", filter=f'mc_group_id="{mc_group_id}"', per_page=500)
        accounts = result.get("items", [])

        total_balance = sum(acc.get("balance", 0) for acc in accounts)
        
        return {
            "is_zero_sum": total_balance == 0,
            "total_balance": total_balance,
            "account_count": len(accounts),
        }

    async def get_transaction_history(
        self, mc_group_id: str, member_id: str, limit: int = 20
    ) -> list[dict]:
        filter_str = f'mc_group_id="{mc_group_id}" && (payer_id="{member_id}" || payee_id="{member_id}")'
        result = await self.pb.list_records(
            "mc_transactions", filter=filter_str, per_page=limit, sort="-created"
        )
        return result.get("items", [])

    async def update_credit_limit(self, mc_group_id: str, member_id: str, new_limit: int) -> dict:
        account = await self.get_or_create_account(mc_group_id, member_id)
        return await self.pb.mc_account_update(account.get("id"), account.get("balance", 0), new_limit)

    async def recalculate_credit_limit(self, mc_group_id: str, member_id: str) -> dict:
        rep = await self.reputation.get_reputation(member_id)
        new_limit = self.reputation.compute_credit_limit(
            rep.get("verified_deals", 0) if rep else 0
        )
        return await self.update_credit_limit(mc_group_id, member_id, new_limit)


mutual_credit_service = MutualCreditService()
