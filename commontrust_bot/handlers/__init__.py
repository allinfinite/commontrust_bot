from aiogram import Router

from commontrust_bot.handlers.admin import router as admin_router
from commontrust_bot.handlers.basic import router as basic_router
from commontrust_bot.handlers.credit import router as credit_router
from commontrust_bot.handlers.deal import router as deal_router
from commontrust_bot.handlers.reputation import router as reputation_router

router = Router()

router.include_router(basic_router)
router.include_router(deal_router)
router.include_router(credit_router)
router.include_router(reputation_router)
router.include_router(admin_router)
