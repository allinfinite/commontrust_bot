import pytest

from commontrust_api.ledger.service import InsufficientCreditError, MutualCreditService
from commontrust_api.reputation.service import ReputationService


@pytest.mark.asyncio
async def test_create_payment_happy_path(fake_pb) -> None:
    rep = ReputationService(pb=fake_pb)
    mc = MutualCreditService(pb=fake_pb, reputation=rep)

    group = await fake_pb.create_record("mc_groups", {"group_id": "g1", "currency_symbol": "Cr"})
    payer = await fake_pb.create_record("members", {"telegram_id": 1})
    payee = await fake_pb.create_record("members", {"telegram_id": 2})

    result = await mc.create_payment(
        mc_group_id=group["id"],
        payer_member_record_id=payer["id"],
        payee_member_record_id=payee["id"],
        amount=50,
        description="hello",
    )

    assert result["new_payer_balance"] == -50
    assert result["new_payee_balance"] == 50

    payer_account = await fake_pb.mc_account_get(group["id"], payer["id"])
    payee_account = await fake_pb.mc_account_get(group["id"], payee["id"])
    assert payer_account is not None and payer_account["balance"] == -50
    assert payee_account is not None and payee_account["balance"] == 50


@pytest.mark.asyncio
async def test_create_payment_insufficient_credit(fake_pb) -> None:
    rep = ReputationService(pb=fake_pb)
    mc = MutualCreditService(pb=fake_pb, reputation=rep)

    group = await fake_pb.create_record("mc_groups", {"group_id": "g1"})
    payer = await fake_pb.create_record("members", {"telegram_id": 1})
    payee = await fake_pb.create_record("members", {"telegram_id": 2})

    with pytest.raises(InsufficientCreditError):
        await mc.create_payment(
            group["id"], payer["id"], payee["id"], amount=10_000  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_update_credit_limit(fake_pb) -> None:
    rep = ReputationService(pb=fake_pb)
    mc = MutualCreditService(pb=fake_pb, reputation=rep)

    group = await fake_pb.create_record("mc_groups", {"group_id": "g1"})
    member = await fake_pb.create_record("members", {"telegram_id": 1})

    updated = await mc.update_credit_limit(group["id"], member["id"], new_limit=7)  # type: ignore[arg-type]
    assert updated["credit_limit"] == 7
