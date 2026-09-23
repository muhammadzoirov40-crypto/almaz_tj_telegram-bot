from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class TopUpStates(StatesGroup):
    choosing_game = State()
    choosing_product = State()
    waiting_uid = State()
    confirming_account = State()
    confirming_order = State()
    waiting_receipt = State()


class BalanceTopUpStates(StatesGroup):
    waiting_amount = State()
    waiting_phone = State()
    confirming = State()
    waiting_receipt = State()


class SupportStates(StatesGroup):
    waiting_subject = State()
    waiting_message = State()


class AdminStates(StatesGroup):
    edit_product_price = State()
    search_order = State()
    waiting_block_id = State()
    waiting_unblock_id = State()
    waiting_add_balance_id = State()
    waiting_add_balance_amount = State()
