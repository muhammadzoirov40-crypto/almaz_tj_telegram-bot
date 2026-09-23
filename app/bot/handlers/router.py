from __future__ import annotations

from aiogram import Router

from app.bot.handlers import admin, balance, menu, orders, start, support, topup

router = Router(name="handlers")

# Order matters: topup/balance before menu so text buttons are not swallowed.
router.include_router(start.router)
router.include_router(topup.router)
router.include_router(balance.router)
router.include_router(orders.router)
router.include_router(support.router)
router.include_router(admin.router)
router.include_router(menu.router)

__all__ = ["router"]
