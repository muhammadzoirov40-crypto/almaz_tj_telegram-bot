from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ChatMemberUpdated, Message

from app.bot.utils import safe_answer, safe_edit_text
from app.bot.keyboards import (
    format_product_button,
    get_main_menu_keyboard,
    get_orders_keyboard,
)
from app.config import settings
from app.constants import OrderStatus
from app.database.models import Order, User
from app.i18n import labels_for, t
from app.services import review_channel
from app.services.order_service import OrderService
from app.utils.logger import get_logger

router = Router(name="orders")
logger = get_logger(__name__)

STATUS_ICONS: dict[str, str] = {
    OrderStatus.PENDING: "⏳",
    OrderStatus.PAID: "💳",
    OrderStatus.PROCESSING: "⚙️",
    OrderStatus.COMPLETED: "✅",
    OrderStatus.FAILED: "❌",
    OrderStatus.CANCELLED: "🚫",
}

STATUS_LABEL_KEYS: dict[str, str] = {
    OrderStatus.PENDING: "status.pending",
    OrderStatus.PAID: "status.paid",
    OrderStatus.PROCESSING: "status.processing",
    OrderStatus.COMPLETED: "status.completed",
    OrderStatus.FAILED: "status.failed",
    OrderStatus.CANCELLED: "status.cancelled",
}


def format_orders(orders: list[Order]) -> str:
    if not orders:
        return t("orders.empty")

    lines = [t("orders.title")]
    for order in orders:
        icon = STATUS_ICONS.get(order.status, "ℹ️")
        label_key = STATUS_LABEL_KEYS.get(order.status)
        status_label = t(label_key) if label_key else order.status
        product_name = (
            format_product_button(order.product)
            if order.product
            else str(order.product_id)
        )
        lines.append(
            f"{icon} №{order.id} · {product_name}\n"
            f"   {t('orders.uid')}: <code>{order.free_fire_uid}</code> · "
            f"{order.created_at:%Y-%m-%d %H:%M} · {status_label}"
        )
    return "\n".join(lines)


async def _send_orders(message: Message, session, db_user: User | None) -> None:
    if db_user is None:
        await message.answer(t("start.not_registered"))
        return

    order_service = OrderService(session)
    orders = await order_service.list_user_orders(db_user.id, limit=10)
    await message.answer(
        format_orders(orders),
        reply_markup=get_orders_keyboard(),
    )


@router.message(Command("orders"))
@router.message(F.text.in_(labels_for("btn.orders")))
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
        await safe_answer(call, t("alert.not_registered"), show_alert=True)
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
        await safe_answer(call, t("alert.not_registered"), show_alert=True)
        return

    order_service = OrderService(session)
    orders = await order_service.list_user_orders(db_user.id, limit=10)
    text = format_orders(orders)
    try:
        await safe_edit_text(call.message, text, reply_markup=get_orders_keyboard())
    except Exception:
        await call.message.answer(text, reply_markup=get_orders_keyboard())
    await safe_answer(call, t("orders.refreshed"))


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
            t("menu.title"),
            reply_markup=get_main_menu_keyboard(is_admin=is_admin),
        )
    except Exception:
        await call.message.answer(
            t("menu.title"),
            reply_markup=get_main_menu_keyboard(is_admin=is_admin),
        )


@router.callback_query(F.data.startswith("review:send:"))
async def on_review_send(call: CallbackQuery) -> None:
    channel: int | str | None = review_channel.get_channel_id()
    if channel is None and settings.otzif_channel_id:
        channel = settings.otzif_channel_id
    if channel is None and settings.otzif_channel_username:
        channel = settings.otzif_channel_username

    if channel is None:
        await safe_answer(
            call,
            t("review.no_channel"),
            show_alert=True,
        )
        return

    try:
        await call.message.copy_to(channel)
    except Exception:
        logger.exception(
            "Review forward failed chat_id=%s channel=%s",
            call.message.chat.id,
            channel,
        )
        await safe_answer(
            call,
            t("review.failed"),
            show_alert=True,
        )
        return

    await safe_answer(
        call, t("review.sent"), show_alert=True
    )
    logger.info(
        "Review forwarded user_id=%s order_msg_id=%s channel=%s",
        call.from_user.id if call.from_user else 0,
        call.message.message_id,
        channel,
    )


@router.message(F.forward_origin)
async def on_forwarded_chat(message: Message) -> None:
    origin = message.forward_origin
    chat = getattr(origin, "chat", None)
    if chat is None:
        return
    if not message.from_user or not settings.is_admin_id(message.from_user.id):
        return
    logger.info(
        "Forwarded chat id=%s type=%s title=%s username=%s",
        chat.id,
        chat.type,
        chat.title,
        chat.username,
    )
    await message.answer(
        t(
            "chan.info",
            id=chat.id,
            title=chat.title or "—",
            username=f"@{chat.username}" if chat.username else t("chan.none"),
        )
    )


@router.my_chat_member()
async def on_bot_chat_member(update: ChatMemberUpdated) -> None:
    chat = update.chat
    new_member = update.new_chat_member
    status = new_member.status if new_member else ""

    if status not in ("administrator", "member"):
        return
    if chat.type not in ("channel", "supergroup", "group"):
        return

    review_channel.set_channel_id(chat.id)
    logger.info(
        "Bot added to chat id=%s type=%s title=%s status=%s",
        chat.id,
        chat.type,
        chat.title,
        status,
    )

    for admin_id in settings.admin_ids:
        try:
            await update.bot.send_message(
                admin_id,
                t(
                    "chan.linked",
                    id=chat.id,
                    title=chat.title or "—",
                    username=(
                        f"@{chat.username}" if chat.username else t("chan.none")
                    ),
                ),
            )
        except Exception:
            logger.exception(
                "Cannot notify admin %s about channel", admin_id
            )
