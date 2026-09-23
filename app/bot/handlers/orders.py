from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.utils import safe_answer, safe_edit_text
from app.bot.keyboards import (
    format_product_button,
    get_main_menu_keyboard,
    get_orders_keyboard,
)
from app.bot.keyboards.main import ORDERS_TEXT
from app.constants import OrderStatus
from app.database.models import Order, User
from app.services.order_service import OrderService

router = Router(name="orders")

STATUS_ICONS: dict[str, str] = {
    OrderStatus.PENDING: "⏳",
    OrderStatus.PAID: "💳",
    OrderStatus.PROCESSING: "⚙️",
    OrderStatus.COMPLETED: "✅",
    OrderStatus.FAILED: "❌",
    OrderStatus.CANCELLED: "🚫",
}

STATUS_LABELS: dict[str, str] = {
    OrderStatus.PENDING: "Дар интизори қабул",
    OrderStatus.PAID: "Пардохт шуд",
    OrderStatus.PROCESSING: "Дар кор",
    OrderStatus.COMPLETED: "Тайёр",
    OrderStatus.FAILED: "Ноком",
    OrderStatus.CANCELLED: "Бекор",
}


def format_orders(orders: list[Order]) -> str:
    if not orders:
        return "📦 Шумо ҳанӯз фармоишҳо надоред."

    lines = ["📦 <b>Фармоишҳои ман</b> — ALMAZ TJ ⚡\n"]
    for order in orders:
        icon = STATUS_ICONS.get(order.status, "ℹ️")
        status_label = STATUS_LABELS.get(order.status, order.status)
        product_name = (
            format_product_button(order.product)
            if order.product
            else str(order.product_id)
        )
        lines.append(
            f"{icon} №{order.id} · {product_name}\n"
            f"   UID: <code>{order.free_fire_uid}</code> · "
            f"{order.created_at:%Y-%m-%d %H:%M} · {status_label}"
        )
    return "\n".join(lines)


async def _send_orders(message: Message, session, db_user: User | None) -> None:
    if db_user is None:
        await message.answer("❌ Шумо ҳанӯз сабт наштаед. /start кунед.")
        return

    order_service = OrderService(session)
    orders = await order_service.list_user_orders(db_user.id, limit=10)
    await message.answer(
        format_orders(orders),
        reply_markup=get_orders_keyboard(),
    )


@router.message(Command("orders"))
@router.message(F.text == ORDERS_TEXT)
async def on_orders_message(
    message: Message,
    session=None,
    db_user: User | None = None,
) -> None:
    await _send_orders(message, session, db_user)


@router.callback_query(F.data == "menu:orders")
async def on_orders_callback(
    call: CallbackQuery,
    state: FSMContext,
    session=None,
    db_user: User | None = None,
) -> None:
    await state.clear()
    if db_user is None:
        await safe_answer(call, "Шумо ҳанӯз сабт наштаед.", show_alert=True)
        return

    order_service = OrderService(session)
    orders = await order_service.list_user_orders(db_user.id, limit=10)
    await safe_edit_text(call.message, 
        format_orders(orders),
        reply_markup=get_orders_keyboard(),
    )
    await safe_answer(call)


@router.callback_query(F.data == "orders:refresh")
async def on_orders_refresh(
    call: CallbackQuery,
    session=None,
    db_user: User | None = None,
) -> None:
    if db_user is None:
        await safe_answer(call, "Шумо ҳанӯз сабт наштаед.", show_alert=True)
        return

    order_service = OrderService(session)
    orders = await order_service.list_user_orders(db_user.id, limit=10)
    text = format_orders(orders)
    try:
        await safe_edit_text(call.message, text, reply_markup=get_orders_keyboard())
    except Exception:
        await call.message.answer(text, reply_markup=get_orders_keyboard())
    await safe_answer(call, "Навсозӣ шуд")


@router.callback_query(F.data == "back:menu")
async def on_back_menu(
    call: CallbackQuery,
    state: FSMContext,
    db_user: User | None = None,
) -> None:
    await state.clear()
    is_admin = db_user.is_admin if db_user else False
    await safe_answer(call)
    try:
        await safe_edit_text(
            call.message,
            "🏠 <b>Менюи ALMAZ TJ</b>",
            reply_markup=get_main_menu_keyboard(is_admin=is_admin),
        )
    except Exception:
        await call.message.answer(
            "🏠 <b>Менюи ALMAZ TJ</b>",
            reply_markup=get_main_menu_keyboard(is_admin=is_admin),
        )
