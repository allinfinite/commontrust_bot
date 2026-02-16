from aiogram import Router

from commontrust_credit_bot.handlers.admin import router as admin_router
from commontrust_credit_bot.handlers.basic import router as basic_router
from commontrust_credit_bot.handlers.credit import router as credit_router

router = Router()
router.include_router(basic_router)
router.include_router(credit_router)
router.include_router(admin_router)

