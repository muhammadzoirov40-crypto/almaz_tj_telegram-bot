from __future__ import annotations

from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import func, select

from app.bot.keyboards import get_main_menu_keyboard
from app.bot.keyboards.main import (
    ORDERS_TEXT,
    PROFILE_TEXT,
    PROMO_TEXT,
)
from app.constants import OrderStatus, TransactionType
from app.database.models import Order, Transaction, User
from app.services.user_service import UserService
from app.bot.utils import safe_answer, safe_edit_text

router = Router(name="menu")


async def _load_stats(user_id: int, session) -> dict:
    topup_stmt = (
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(Transaction.user_id == user_id)
        .where(Transaction.type == TransactionType.TOPUP)
    )
    refund_stmt = (
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(Transaction.user_id == user_id)
        .where(Transaction.type == TransactionType.REFUND)
    )
    orders_total_stmt = (
        select(func.count(Order.id)).where(Order.user_id == user_id)
    )
    orders_done_stmt = (
        select(func.count(Order.id))
        .where(Order.user_id == user_id)
        .where(Order.status == OrderStatus.COMPLETED)
    )
    orders_work_stmt = (
        select(func.count(Order.id))
        .where(Order.user_id == user_id)
        .where(
            Order.status.in_(
                [
                    OrderStatus.PENDING,
                    OrderStatus.PAID,
                    OrderStatus.PROCESSING,
                ]
            )
        )
    )

    topup = (await session.execute(topup_stmt)).scalar() or Decimal("0")
    refunded = (await session.execute(refund_stmt)).scalar() or Decimal("0")
    total = (await session.execute(orders_total_stmt)).scalar() or 0
    done = (await session.execute(orders_done_stmt)).scalar() or 0
    in_work = (await session.execute(orders_work_stmt)).scalar() or 0

    return {
        "topup": Decimal(topup),
        "refunded": Decimal(refunded),
        "orders_total": int(total),
        "orders_done": int(done),
        "orders_in_work": int(in_work),
    }


def _profile_text(user: User, stats: dict | None = None) -> str:
    stats = stats or {}
    topup = stats.get("topup", Decimal("0"))
    refunded = stats.get("refunded", Decimal("0"))
    paid_total = topup - refunded

    lines = [
        "👤 <b>Профил</b>",
        "",
        f"🆔 ID: <code>{user.telegram_id}</code>",
        f"📛 Username: "
        + (f"@{user.username}" if user.username else "—"),
        "",
        "💰 <b>Молия</b>",
        f"Баланс: <b>{user.balance} TJS</b>",
        f"Ҳамагӣ пур карда шуд: {paid_total:.2f} TJS",
        "",
        "📦 <b>Фармоишҳо</b>",
        f"Ҳамагӣ: {stats.get('orders_total', 0)}",
        f"Иҷро шуд: {stats.get('orders_done', 0)}",
        f"Дар коркард: {stats.get('orders_in_work', 0)}",
        "",
        f"📅 Бо мо аз {user.created_at:%d.%m.%Y}",
        "",
        "DANAT.TJ ⚡ — Арзонтарин алмаз дар Тоҷикистон",
    ]
    return "\n".join(lines)


def _profile_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=ORDERS_TEXT, callback_data="menu:orders"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад", callback_data="back:menu"
                )
            ],
        ]
    )


async def _show_profile(message: Message, session, db_user=None) -> None:
    user_service = UserService(session)
    user = await user_service.get_profile(message.from_user.id)
    if user is None:
        await message.answer("❌ Шумо ҳанӯз сабт наштаед. /start кунед.")
        return
    stats = await _load_stats(user.id, session)
    await message.answer(
        _profile_text(user, stats),
        reply_markup=_profile_keyboard(
            is_admin=db_user.is_admin if db_user else False
        ),
    )


@router.message(F.text == PROFILE_TEXT)
async def on_profile(message: Message, session=None, db_user=None) -> None:
    await _show_profile(message, session, db_user)


@router.callback_query(F.data == "menu:profile")
async def on_profile_callback(
    call: CallbackQuery,
    state: FSMContext,
    session=None,
    db_user=None,
) -> None:
    await state.clear()
    user_service = UserService(session)
    user = await user_service.get_profile(call.from_user.id)
    if user is None:
        await safe_answer(call, "Шумо ҳанӯз сабт наштаед.", show_alert=True)
        return
    stats = await _load_stats(user.id, session)
    await safe_edit_text(call.message, 
        _profile_text(user, stats),
        reply_markup=_profile_keyboard(
            is_admin=db_user.is_admin if db_user else False
        ),
    )
    await safe_answer(call)


@router.message(F.text == PROMO_TEXT)
async def on_promo(message: Message) -> None:
    await message.answer(
        "🎁 <b>Пешниҳодҳо</b>\n\n"
        "🏆 <b>Ҷоизаи моҳина:</b> ҳар моҳ номаи он корбар, ки дар мудда"
        "ти 1 моҳ аз ҳама зиёд донат кардааст, ғолиб эълон мешавад ва "
        "<b>туҳфа</b> мегирад!\n\n"
        "📢 Канал: <a href=\"https://t.me/_ff_almaz_tj_\">@_ff_almaz_tj_</a>"
    )


@router.callback_query(F.data == "menu:promo")
async def on_promo_callback(
    call: CallbackQuery,
    state: FSMContext,
    db_user=None,
) -> None:
    await state.clear()
    await safe_edit_text(call.message, 
        "🎁 <b>Пешниҳодҳо</b>\n\n"
        "🏆 <b>Ҷоизаи моҳина:</b> ҳар моҳ номаи он корбар, ки дар мудда"
        "ти 1 моҳ аз ҳама зиёд донат кардааст, ғолиб эълон мешавад ва "
        "<b>туҳфа</b> мегирад!\n\n"
        "📢 Канал: <a href=\"https://t.me/_ff_almaz_tj_\">@_ff_almaz_tj_</a>",
        reply_markup=get_main_menu_keyboard(
            is_admin=db_user.is_admin if db_user else False
        ),
    )
    await safe_answer(call)


BUYERS_MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


async def _top_buyers(session, limit: int = 10) -> list[dict]:
    stmt = (
        select(
            User.telegram_id,
            User.username,
            User.first_name,
            func.coalesce(func.sum(Order.amount), 0).label("spent"),
            func.count(Order.id).label("orders"),
        )
        .select_from(User)
        .join(Order, Order.user_id == User.id)
        .where(Order.status == OrderStatus.COMPLETED)
        .group_by(User.id, User.telegram_id, User.username, User.first_name)
        .order_by(func.sum(Order.amount).desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [
        {
            "telegram_id": row.telegram_id,
            "username": row.username,
            "first_name": row.first_name,
            "spent": Decimal(row.spent),
            "orders": int(row.orders),
        }
        for row in rows
    ]


def _buyers_text(buyers: list[dict]) -> str:
    if not buyers:
        return "🏆 <b>Харидорҳо</b>"

    lines = ["🏆 <b>Харидорҳо — Top ҳама</b>\n"]
    for index, buyer in enumerate(buyers, start=1):
        medal = BUYERS_MEDALS.get(index, f"{index}.")
        name = (
            f"@{buyer['username']}"
            if buyer["username"]
            else (buyer["first_name"] or "—")
        )
        lines.append(
            f"{medal} {name} — {buyer['spent']:.2f} TJS "
            f"({buyer['orders']} фармоиш)"
        )
    return "\n".join(lines)


@router.callback_query(F.data == "menu:buyers")
async def on_buyers_callback(
    call: CallbackQuery,
    state: FSMContext,
    session=None,
    db_user=None,
) -> None:
    await state.clear()
    if session is None:
        await safe_answer(call, "Хатогӣ.", show_alert=True)
        return
    buyers = await _top_buyers(session)
    await safe_edit_text(
        call.message,
        _buyers_text(buyers),
        reply_markup=get_main_menu_keyboard(
            is_admin=db_user.is_admin if db_user else False
        ),
    )
    await safe_answer(call)
