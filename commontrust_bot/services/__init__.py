from typing import TYPE_CHECKING

# Avoid importing service modules at package import time; they pull in runtime
# dependencies (aiogram/settings) and can make tooling/tests harder.
if TYPE_CHECKING:  # pragma: no cover
    from commontrust_bot.services.deal import DealService as DealService
    from commontrust_bot.services.mutual_credit import MutualCreditService as MutualCreditService
    from commontrust_bot.services.reputation import ReputationService as ReputationService

__all__ = ["ReputationService", "MutualCreditService", "DealService"]
