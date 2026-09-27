from __future__ import annotations

from decimal import Decimal
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.bot.keyboards.style import styled
from app.bot.filters import AdminFilter
from app.bot.keyboards import (
    format_product_button,
    get_admin_back_keyboard,
    get_admin_menu_keyboard,
    get_balance_topup_approved_keyboard,
    get_balance_topup_review_keyboard,
    get_block_menu_keyboard,
    get_order_review_keyboard,
    get_pending_orders_keyboard,
)
from app.bot.states import AdminStates
from app.constants import BalanceTopUpStatus, OrderStatus, PaymentStatus
from app.database.models import Order, Payment, User
from app.database.repositories import (
    BalanceTopUpRepository,
    PaymentRepository,
    ProductRepository,
    SupportTicketRepository,
    UserRepository,
)
from app.i18n import labels_for, t
from app.services.notification_service import notification_service
from app.services.order_service import OrderService
from app.services.topup_service import TopUpService
from app.services.user_service import UserService
from app.utils.logger import get_logger
from app.bot.utils import safe_answer, safe_edit_text
from app.config import settings

logger = get_logger(__name__)

router = Router(name="admin")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


def _user_mention(user: User | None) -> str:
    if user is None:
        return "—"
    name = escape((user.first_name or "").strip() or f"ID {user.telegram_id}")
    if user.username:
        return (
            f'<a href="https://t.me/{escape(user.username)}">{name}</a>'
        )
    return f'<a href="tg://user?id={user.telegram_id}">{name}</a>'


def _review_keyboard(order_id: int | None = None):
    from aiogram.types import (
        InlineKeyboardButton,
        InlineKeyboardMarkup,
    )

    if order_id is None:
        return None
    return styled(InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("adm.review_button"),
                    callback_data=f"review:send:{order_id}",
                )
            ]
        ]
    ))

ORDER_ICONS: dict[str, str] = {
    OrderStatus.PENDING: "⏳",
    OrderStatus.PAID: "💳",
    OrderStatus.PROCESSING: "⚙️",
    OrderStatus.COMPLETED: "✅",
    OrderStatus.FAILED: "❌",
    OrderStatus.CANCELLED: "🚫",
}

ORDER_STATUS_KEYS: dict[str, str] = {
    OrderStatus.PENDING: "status.pending",
    OrderStatus.PAID: "status.paid",
    OrderStatus.PROCESSING: "status.processing",
    OrderStatus.COMPLETED: "status.completed",
    OrderStatus.FAILED: "status.failed",
    OrderStatus.CANCELLED: "status.cancelled",
}


def _status_label(status: str) -> str:
    key = ORDER_STATUS_KEYS.get(status)
    return t(key) if key else status


def _parse_parts(data: str) -> list[str]:
    return (data or "").split(":")


def _order_detail(order: Order) -> str:
    product_name = (
        format_product_button(order.product)
        if order.product
        else str(order.product_id)
    )
    user = order.user
    user_label = "—"
    if user is not None:
        user_label = f"@{user.username}" if user.username else str(user.telegram_id)
    status_label = _status_label(order.status)
    text = t(
        "adm.detail",
        id=order.id,
        product=product_name,
        uid=order.free_fire_uid,
        amount=order.amount,
        currency=order.currency,
        user=user_label,
        status=status_label,
    )
    if getattr(order, "zone", None):
        text += "\n" + t("adm.zone_line", zone=order.zone)
    return text


@router.message(Command("admin"))
@router.message(F.text.in_(labels_for("btn.admin")))
async def admin_menu(message: Message) -> None:
    await message.answer(
        t("adm.menu"),
        reply_markup=get_admin_menu_keyboard(),
    )


@router.callback_query(F.data == "admin:menu")
async def admin_menu_callback(call: CallbackQuery) -> None:
    await safe_edit_text(call.message,
        t("adm.menu"),
        reply_markup=get_admin_menu_keyboard(),
    )
    await safe_answer(call)


@router.callback_query(F.data == "admin:stats")
async def admin_stats(call: CallbackQuery, session=None) -> None:
    users_count = await session.scalar(select(func.count(User.id)))
    orders_count = await session.scalar(select(func.count(Order.id)))
    completed = await session.scalar(
        select(func.count(Order.id)).where(Order.status == OrderStatus.COMPLETED)
    )
    pending = await session.scalar(
        select(func.count(Order.id)).where(Order.status == OrderStatus.PENDING)
    )
    pending_topups = await BalanceTopUpRepository(session).count_pending()
    paid_payments = await session.scalar(
        select(func.count(Payment.id)).where(Payment.status == PaymentStatus.PAID)
    )
    open_tickets = await SupportTicketRepository(session).count_open()

    revenue = await session.scalar(
        select(func.coalesce(func.sum(Order.amount), 0)).where(
            Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.COMPLETED])
        )
    )

    text = t(
        "adm.stats",
        users=users_count or 0,
        orders=orders_count or 0,
        completed=completed or 0,
        pending=pending or 0,
        topups=pending_topups or 0,
        payments=paid_payments or 0,
        revenue=revenue or 0,
        tickets=open_tickets or 0,
    )
    await safe_edit_text(call.message, text, reply_markup=get_admin_back_keyboard())
    await safe_answer(call)


@router.callback_query(F.data == "admin:pending")
async def admin_pending(call: CallbackQuery, session=None) -> None:
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.product), selectinload(Order.user))
        .where(Order.status == OrderStatus.PENDING)
        .order_by(Order.id.desc())
        .limit(10)
    )
    orders = list(result.scalars().all())

    if not orders:
        await safe_edit_text(call.message, 
            t("adm.pending_empty"),
            reply_markup=get_admin_back_keyboard(),
        )
        await safe_answer(call)
        return

    lines = [t("adm.pending_title") + "\n"]
    for order in orders:
        lines.append(_order_detail(order) + "\n")

    await safe_edit_text(call.message, 
        "\n".join(lines),
        reply_markup=get_pending_orders_keyboard([o.id for o in orders]),
    )
    await safe_answer(call)


@router.callback_query(F.data.startswith("admin:bal:accept:"))
async def admin_balance_topup_accept(call: CallbackQuery, session=None) -> None:
    parts = _parse_parts(call.data or "")
    if len(parts) != 4:
        await safe_answer(call, t("adm.invalid"), show_alert=True)
        return
    try:
        request_id = int(parts[3])
    except ValueError:
        await safe_answer(call, t("adm.invalid"), show_alert=True)
        return

    repo = BalanceTopUpRepository(session)
    request = await repo.get_by_id(request_id)
    if request is None:
        await safe_answer(call, t("adm.request_not_found"), show_alert=True)
        return
    if request.status != BalanceTopUpStatus.PENDING:
        await safe_answer(
            call,
            t("adm.request_already", status=request.status),
            show_alert=True,
        )
        return

    user_service = UserService(session)
    try:
        user = await user_service.add_balance(
            user_id=request.user_id,
            amount=Decimal(request.amount),
            description=f"Balance top-up #{request.id} via {request.method}",
            reference_id=request.reference_id or f"bal:{request.id}",
        )
    except ValueError as exc:
        await safe_answer(call, str(exc), show_alert=True)
        return
    except Exception:
        logger.exception("Balance top-up approve failed request_id=%s", request_id)
        await safe_answer(call, t("adm.error"), show_alert=True)
        return

    await repo.mark_approved(request_id)
    request = await repo.get_by_id(request_id)

    method_label = "🏙 Dushanbe City" if request.method == "ds" else "💳 Alif"
    if request.phone:
        detail = t(
            "adm.bal_detail_phone",
            id=request.id,
            amount=request.amount,
            currency=request.currency,
            method=method_label,
            phone=request.phone,
            balance=user.balance,
        )
    else:
        detail = t(
            "adm.bal_detail",
            id=request.id,
            amount=request.amount,
            currency=request.currency,
            method=method_label,
            balance=user.balance,
        )
    await safe_edit_text(
        call.message,
        f"{t('adm.bal_accepted_title')}\n\n{detail}",
        reply_markup=get_balance_topup_approved_keyboard(request.id),
    )

    if request.user is not None:
        await notification_service.safe_send(
            request.user.telegram_id,
            t(
                "adm.user_topup_accepted",
                id=request.id,
                amount=request.amount,
                currency=request.currency,
                balance=user.balance,
            ),
        )

    if settings.otzif_channel_id:
        await notification_service.safe_send(
            settings.otzif_channel_id,
            t(
                "adm.user_topup_accepted_oz",
                id=request.id,
                amount=request.amount,
                currency=request.currency,
                balance=user.balance,
                mention=_user_mention(user),
            ),
        )

    logger.info(
        "Admin accepted balance topup request_id=%s by=%s",
        request_id,
        call.from_user.id,
    )
    await safe_answer(call, t("adm.accepted"))


@router.callback_query(F.data.startswith("admin:bal:reject:"))
async def admin_balance_topup_reject(call: CallbackQuery, session=None) -> None:
    parts = _parse_parts(call.data or "")
    if len(parts) != 4:
        await safe_answer(call, t("adm.invalid"), show_alert=True)
        return
    try:
        request_id = int(parts[3])
    except ValueError:
        await safe_answer(call, t("adm.invalid"), show_alert=True)
        return

    repo = BalanceTopUpRepository(session)
    request = await repo.get_by_id(request_id)
    if request is None:
        await safe_answer(call, t("adm.request_not_found"), show_alert=True)
        return
    if request.status != BalanceTopUpStatus.PENDING:
        await safe_answer(
            call,
            t("adm.request_already", status=request.status),
            show_alert=True,
        )
        return

    await repo.mark_rejected(request_id, reason="Rejected by admin")
    request = await repo.get_by_id(request_id)

    method_label = "🏙 Dushanbe City" if request.method == "ds" else "💳 Alif"
    await safe_edit_text(
        call.message,
        f"{t('adm.bal_rejected_title')}\n\n"
        + t(
            "adm.bal_rejected_detail",
            id=request.id,
            amount=request.amount,
            currency=request.currency,
            method=method_label,
        ),
        reply_markup=get_admin_back_keyboard(),
    )

    if request.user is not None:
        await notification_service.safe_send(
            request.user.telegram_id,
            t(
                "adm.user_topup_rejected",
                id=request.id,
                amount=request.amount,
                currency=request.currency,
            ),
        )

    logger.info(
        "Admin rejected balance topup request_id=%s by=%s",
        request_id,
        call.from_user.id,
    )
    await safe_answer(call, t("adm.rejected"))


@router.callback_query(F.data.startswith("admin:bal:refund:"))
async def admin_balance_topup_refund(call: CallbackQuery, session=None) -> None:
    parts = _parse_parts(call.data or "")
    if len(parts) != 4:
        await safe_answer(call, t("adm.invalid"), show_alert=True)
        return
    try:
        request_id = int(parts[3])
    except ValueError:
        await safe_answer(call, t("adm.invalid"), show_alert=True)
        return

    repo = BalanceTopUpRepository(session)
    request = await repo.get_by_id(request_id)
    if request is None:
        await safe_answer(call, t("adm.request_not_found"), show_alert=True)
        return
    if request.status != BalanceTopUpStatus.APPROVED:
        await safe_answer(
            call,
            t("adm.refund_only_approved", status=request.status),
            show_alert=True,
        )
        return

    user_service = UserService(session)
    try:
        user = await user_service.remove_balance(
            user_id=request.user_id,
            amount=Decimal(request.amount),
            description=f"Balance refund for top-up #{request.id}",
            reference_id=request.reference_id or f"bal:refund:{request.id}",
        )
    except ValueError as exc:
        await safe_answer(call, str(exc), show_alert=True)
        return
    except Exception:
        logger.exception("Balance refund failed request_id=%s", request_id)
        await safe_answer(call, t("adm.error"), show_alert=True)
        return

    await repo.mark_refunded(request_id, reason="Refunded by admin")
    request = await repo.get_by_id(request_id)

    method_label = "🏙 Dushanbe City" if request.method == "ds" else "💳 Alif"
    await safe_edit_text(
        call.message,
        f"{t('adm.refund_title')}\n\n"
        + t(
            "adm.refund_detail",
            id=request.id,
            amount=request.amount,
            currency=request.currency,
            method=method_label,
            balance=user.balance,
        ),
        reply_markup=get_admin_back_keyboard(),
    )

    if request.user is not None:
        await notification_service.safe_send(
            request.user.telegram_id,
            t(
                "adm.user_refund",
                id=request.id,
                amount=request.amount,
                currency=request.currency,
                balance=user.balance,
            ),
        )

    logger.info(
        "Admin refunded balance topup request_id=%s by=%s",
        request_id,
        call.from_user.id,
    )
    await safe_answer(call, t("adm.refunded"))


@router.callback_query(F.data.startswith("admin:order:accept:"))
async def admin_order_accept(call: CallbackQuery, session=None) -> None:
    parts = _parse_parts(call.data or "")
    if len(parts) != 4:
        await safe_answer(call, t("adm.invalid"), show_alert=True)
        return
    try:
        order_id = int(parts[3])
    except ValueError:
        await safe_answer(call, t("adm.invalid"), show_alert=True)
        return

    order_service = OrderService(session)
    order = await order_service.get_order(order_id)
    if order is None:
        logger.warning(
            "Order not found on accept order_id=%s callback=%s",
            order_id,
            call.data,
        )
        await safe_answer(call, t("adm.order_not_found"), show_alert=True)
        return
    if order.status != OrderStatus.PENDING:
        await safe_answer(call, 
            t("adm.order_already", status=_status_label(order.status)),
            show_alert=True,
        )
        return

    order = await order_service.mark_paid(order_id)
    if order is None:
        await safe_answer(call, t("adm.error"), show_alert=True)
        return

    detail = ""
    try:
        topup_service = TopUpService(session)
        order = await topup_service.process_order(order_id)
        detail = t("adm.status_line", status=_status_label(order.status))
    except Exception:
        logger.exception("Top-up failed on admin accept order_id=%s", order_id)
        detail = t("adm.topup_in_progress")

    receipt_note = t("adm.receipt_card")
    await safe_edit_text(call.message, 
        f"{t('adm.order_accepted_title')}\n\n{_order_detail(order)}\n\n{detail}\n{receipt_note}",
        reply_markup=get_admin_back_keyboard(),
    )

    user = order.user
    product_name = format_product_button(order.product) if order.product else ""
    if user is not None:
        await notification_service.safe_send(
            user.telegram_id,
            t(
                "adm.user_order_accepted",
                id=order.id,
                product=product_name,
                uid=order.free_fire_uid,
                status=_status_label(order.status),
            ),
            reply_markup=_review_keyboard(order.id),
        )

    if settings.otzif_channel_id:
        await notification_service.safe_send(
            settings.otzif_channel_id,
            t(
                "adm.channel_order_accepted",
                id=order.id,
                product=product_name,
                uid=order.free_fire_uid,
                status=_status_label(order.status),
                mention=_user_mention(user),
            ),
        )

    logger.info("Admin accepted order_id=%s by=%s", order_id, call.from_user.id)
    await safe_answer(call, t("adm.accepted"))


@router.callback_query(F.data.startswith("admin:order:reject:"))
async def admin_order_reject(call: CallbackQuery, session=None) -> None:
    parts = _parse_parts(call.data or "")
    if len(parts) != 4:
        await safe_answer(call, t("adm.invalid"), show_alert=True)
        return
    try:
        order_id = int(parts[3])
    except ValueError:
        await safe_answer(call, t("adm.invalid"), show_alert=True)
        return

    order_service = OrderService(session)
    order = await order_service.get_order(order_id)
    if order is None:
        logger.warning(
            "Order not found on reject order_id=%s callback=%s",
            order_id,
            call.data,
        )
        await safe_answer(call, t("adm.order_not_found"), show_alert=True)
        return
    if order.status != OrderStatus.PENDING:
        await safe_answer(call, 
            t("adm.order_already", status=_status_label(order.status)),
            show_alert=True,
        )
        return

    was_deducted = await order_service.was_balance_deducted(order.id)
    order = await order_service.transition(order_id, OrderStatus.CANCELLED)
    if order is None:
        await safe_answer(call, t("adm.error"), show_alert=True)
        return

    if was_deducted and order.user_id:
        user_service = UserService(session)
        try:
            await user_service.add_balance(
                user_id=order.user_id,
                amount=Decimal(order.amount),
                description=f"Refund rejected order #{order.id}",
                reference_id=f"refund:order:{order.id}",
            )
        except Exception:
            logger.exception("Refund failed order_id=%s", order.id)

    refund_note = t("adm.refund_done") if was_deducted else t("adm.refund_not_done")
    await safe_edit_text(call.message, 
        f"{t('adm.order_rejected_title')}\n\n{_order_detail(order)}\n\n"
        f"{refund_note}",
        reply_markup=get_admin_back_keyboard(),
    )

    user = order.user
    if user is not None:
        product_name = (
            format_product_button(order.product) if order.product else ""
        )
        detail = (
            "\n" + t("adm.refund_done") if was_deducted else ""
        )
        await notification_service.safe_send(
            user.telegram_id,
            t(
                "adm.user_order_rejected",
                id=order.id,
                product=product_name,
                uid=order.free_fire_uid,
                detail=detail,
            ),
        )

    logger.info("Admin rejected order_id=%s by=%s", order_id, call.from_user.id)
    await safe_answer(call, t("adm.rejected"))


@router.callback_query(F.data == "admin:orders")
async def admin_orders(call: CallbackQuery, session=None) -> None:
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.product))
        .order_by(Order.id.desc())
        .limit(15)
    )
    recent = list(result.scalars().all())

    lines = [t("adm.orders_title") + "\n"]
    for order in recent:
        icon = ORDER_ICONS.get(order.status, "ℹ️")
        status_label = _status_label(order.status)
        product_name = (
            format_product_button(order.product)
            if order.product
            else str(order.product_id)
        )
        lines.append(
            f"{icon} №{order.id} · {product_name}\n"
            f"   UID {order.free_fire_uid} · {order.amount} {order.currency} · {status_label}"
        )
    if not recent:
        lines.append(t("adm.orders_empty"))

    await safe_edit_text(call.message, 
        "\n".join(lines),
        reply_markup=get_admin_back_keyboard(),
    )
    await safe_answer(call)


@router.callback_query(F.data == "admin:users")
async def admin_users(call: CallbackQuery, session=None) -> None:
    users = await UserRepository(session).list_users(limit=15)
    total = await UserRepository(session).count_users()

    lines = [t("adm.users_title", count=total) + "\n"]
    for user in users:
        name = user.username or str(user.telegram_id)
        lines.append(
            f"• {name} · id:{user.id} · tg:{user.telegram_id} · "
            f"{user.balance} TJS{t('adm.user_admin_mark') if user.is_admin else ''}"
        )

    await safe_edit_text(call.message, 
        "\n".join(lines),
        reply_markup=get_admin_back_keyboard(),
    )
    await safe_answer(call)


@router.callback_query(F.data == "admin:products")
async def admin_products(call: CallbackQuery, session=None) -> None:
    products = await ProductRepository(session).list_all(limit=30)
    lines = [t("adm.products_title") + "\n"]
    for product in products:
        status = "✅" if product.is_active else "⏸"
        lines.append(f"{status} {format_product_button(product)}")

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    buttons = []
    for product in products:
        action = "deactivate" if product.is_active else "activate"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=format_product_button(product)
                    + (" ⏸" if product.is_active else " ▶️"),
                    callback_data=f"admin:product:{action}:{product.id}",
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text=t("btn.back"), callback_data="admin:menu")])

    await safe_edit_text(call.message, 
        "\n".join(lines),
        reply_markup=styled(InlineKeyboardMarkup(inline_keyboard=buttons)),
    )
    await safe_answer(call)


@router.callback_query(F.data.startswith("admin:product:"))
async def admin_product_action(call: CallbackQuery, session=None) -> None:
    parts = _parse_parts(call.data or "")
    # admin:product:activate:{id}
    if len(parts) != 4:
        await safe_answer(call, t("adm.invalid"), show_alert=True)
        return

    action = parts[2]
    try:
        product_id = int(parts[3])
    except ValueError:
        await safe_answer(call, t("adm.invalid"), show_alert=True)
        return

    if action not in {"activate", "deactivate"}:
        await safe_answer(call, t("adm.invalid"), show_alert=True)
        return

    repo = ProductRepository(session)
    product = await repo.set_active(product_id, is_active=(action == "activate"))
    if product is None:
        await safe_answer(call, t("adm.product_not_found"), show_alert=True)
        return

    logger.info(
        "Admin product %s product_id=%s", action, product_id
    )
    await admin_products(call, session=session)


@router.callback_query(F.data == "admin:payments")
async def admin_payments(call: CallbackQuery, session=None) -> None:
    result = await session.execute(
        select(Payment).order_by(Payment.id.desc()).limit(15)
    )
    payments = list(result.scalars().all())

    lines = [t("adm.payments_title") + "\n"]
    for payment in payments:
        icon = "✅" if payment.status == PaymentStatus.PAID else (
            "⏳" if payment.status == PaymentStatus.PENDING else "❌"
        )
        lines.append(
            f"{icon} #{payment.id} · order:{payment.order_id} · "
            f"{payment.amount} {payment.currency} · {payment.provider} · {payment.status}"
        )
    if not payments:
        lines.append(t("adm.payments_empty"))

    await safe_edit_text(call.message, 
        "\n".join(lines),
        reply_markup=get_admin_back_keyboard(),
    )
    await safe_answer(call)


@router.callback_query(F.data == "admin:support")
async def admin_support(call: CallbackQuery, session=None) -> None:
    tickets = await SupportTicketRepository(session).list_all(limit=15)
    lines = [t("adm.support_title") + "\n"]
    for ticket in tickets:
        user_label = (
            ticket.user.username or ticket.user.telegram_id
            if ticket.user
            else ticket.user_id
        )
        lines.append(
            f"#{ticket.id} [{ticket.status}] · {user_label}\n"
            f"📌 {ticket.subject}\n"
            f"✉️ {ticket.message[:200]}"
        )
    if not tickets:
        lines.append(t("adm.support_empty"))

    await safe_edit_text(call.message, 
        "\n".join(lines),
        reply_markup=get_admin_back_keyboard(),
    )
    await safe_answer(call)


@router.callback_query(F.data == "admin:block_menu")
async def admin_block_menu(call: CallbackQuery) -> None:
    await safe_edit_text(
        call.message,
        t("adm.block_menu"),
        reply_markup=get_block_menu_keyboard(),
    )
    await safe_answer(call)


@router.callback_query(F.data == "admin:block_ask")
async def admin_block_ask(call: CallbackQuery, state) -> None:
    await state.set_state(AdminStates.waiting_block_id)
    await safe_edit_text(
        call.message,
        t("adm.block_ask"),
        reply_markup=get_block_menu_keyboard(),
    )
    await safe_answer(call)


@router.callback_query(F.data == "admin:unblock_ask")
async def admin_unblock_ask(call: CallbackQuery, state) -> None:
    await state.set_state(AdminStates.waiting_unblock_id)
    await safe_edit_text(
        call.message,
        t("adm.unblock_ask"),
        reply_markup=get_block_menu_keyboard(),
    )
    await safe_answer(call)


async def _set_user_active(
    session, telegram_id: int, is_active: bool
) -> User | None:
    repo = UserRepository(session)
    user = await repo.get_by_telegram_id(telegram_id)
    if user is None:
        return None
    return await repo.set_active(user.id, is_active)


@router.message(AdminStates.waiting_block_id)
async def admin_block_process(message: Message, state, session) -> None:
    text = (message.text or "").strip().lstrip("@")
    if not text.isdigit():
        await message.answer(t("adm.need_tg_id"))
        return

    telegram_id = int(text)
    if settings.is_admin_id(telegram_id):
        await message.answer(t("adm.cannot_block_admin"))
        await state.clear()
        return

    user = await _set_user_active(session, telegram_id, is_active=False)
    await state.clear()
    if user is None:
        await message.answer(t("adm.id_not_found"))
        return

    logger.info("Admin blocked user_id=%s tg=%s", user.id, telegram_id)
    await message.answer(
        t("adm.blocked", id=telegram_id, name=user.first_name or user.username or "—"),
        reply_markup=get_admin_back_keyboard(),
    )


@router.message(AdminStates.waiting_unblock_id)
async def admin_unblock_process(message: Message, state, session) -> None:
    text = (message.text or "").strip().lstrip("@")
    if not text.isdigit():
        await message.answer(t("adm.need_tg_id"))
        return

    telegram_id = int(text)
    user = await _set_user_active(session, telegram_id, is_active=True)
    await state.clear()
    if user is None:
        await message.answer(t("adm.id_not_found"))
        return

    logger.info("Admin unblocked user_id=%s tg=%s", user.id, telegram_id)
    await message.answer(
        t("adm.unblocked", id=telegram_id, name=user.first_name or user.username or "—"),
        reply_markup=get_admin_back_keyboard(),
    )


@router.callback_query(F.data == "admin:add_bal_ask")
async def admin_add_balance_ask(call: CallbackQuery, state) -> None:
    await state.set_state(AdminStates.waiting_add_balance_id)
    await safe_edit_text(
        call.message,
        t("adm.add_bal_ask"),
        reply_markup=get_block_menu_keyboard(),
    )
    await safe_answer(call)


@router.message(AdminStates.waiting_add_balance_id)
async def admin_add_balance_id(message: Message, state) -> None:
    text = (message.text or "").strip().lstrip("@")
    if not text.isdigit():
        await message.answer(t("adm.need_tg_id"))
        return

    await state.update_data(add_bal_tg_id=int(text))
    await state.set_state(AdminStates.waiting_add_balance_amount)
    await message.answer(t("adm.add_bal_amount"))


@router.message(AdminStates.waiting_add_balance_amount)
async def admin_add_balance_amount(message: Message, state, session) -> None:
    from decimal import Decimal, InvalidOperation

    raw = (message.text or "").strip().replace(",", ".")
    try:
        amount = Decimal(raw)
    except InvalidOperation:
        await message.answer(t("adm.amount_invalid"))
        return
    if amount <= 0:
        await message.answer(t("adm.amount_positive"))
        return

    data = await state.get_data()
    telegram_id = int(data.get("add_bal_tg_id", 0))
    await state.clear()

    user_service = UserService(session)
    user = await user_service.get_profile(telegram_id)
    if user is None:
        await message.answer(t("adm.id_not_found"))
        return

    try:
        user = await user_service.add_balance(
            user_id=user.id,
            amount=amount,
            description=f"Admin manual add by {message.from_user.id}",
            reference_id=f"admin:add:{message.from_user.id}:{user.id}:{amount}",
        )
    except Exception:
        logger.exception("Admin add balance failed tg=%s", telegram_id)
        await message.answer(t("adm.add_bal_error"))
        return

    logger.info(
        "Admin added balance tg=%s amount=%s by=%s",
        telegram_id,
        amount,
        message.from_user.id,
    )
    await message.answer(
        t(
            "adm.add_bal_done",
            id=telegram_id,
            name=user.first_name or user.username or "—",
            amount=amount,
            balance=user.balance,
        ),
        reply_markup=get_admin_back_keyboard(),
    )
