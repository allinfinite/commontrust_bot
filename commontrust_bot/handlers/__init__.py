from aiogram import Router

from commontrust_bot.handlers.report import router as report_router
from commontrust_bot.handlers.dm import router as dm_router
from commontrust_bot.handlers.admin import router as admin_router
from commontrust_bot.handlers.basic import router as basic_router
from commontrust_bot.handlers.deal import router as deal_router
from commontrust_bot.handlers.reputation import router as reputation_router

router = Router()

router.include_router(report_router)
router.include_router(dm_router)
router.include_router(basic_router)
router.include_router(deal_router)
router.include_router(reputation_router)
router.include_router(admin_router)
