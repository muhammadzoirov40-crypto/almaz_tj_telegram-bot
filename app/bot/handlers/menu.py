from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import get_main_menu_keyboard
from app.bot.keyboards.main import (
    PROFILE_TEXT,
    PROMO_TEXT,
)
from app.services.user_service import UserService
from app.bot.utils import safe_answer, safe_edit_text

router = Router(name="menu")


def _profile_text(user) -> str:
    return (
        "👤 <b>Саҳифаи ман</b>\n\n"
        f"🆔 ID: <code>{user.telegram_id}</code>\n"
        f"📛 Номи корбар: @{user.username if user.username else '-'}\n"
        f"💰 Баланс: <b>{user.balance} TJS</b>\n"
        f"📅 Қайд: {user.created_at:%Y-%m-%d}\n\n"
        "DANAT.TJ ⚡ — Арзонтарин алмаз дар Тоҷикистон"
    )


async def _show_profile(message: Message, session, db_user=None) -> None:
    user_service = UserService(session)
    user = await user_service.get_profile(message.from_user.id)
    if user is None:
        await message.answer("❌ Шумо ҳанӯз сабт наштаед. /start кунед.")
        return
    await message.answer(_profile_text(user))


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
    await safe_edit_text(call.message, 
        _profile_text(user),
        reply_markup=get_main_menu_keyboard(
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
