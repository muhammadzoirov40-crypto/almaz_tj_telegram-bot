from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Optional

# Free Fire numeric UID: typically 8-12 digits. We never ask for a password.
UID_PATTERN = re.compile(r"^\d{8,12}$")
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]{5,32}$")
# Tajikistan phone: +992XXXXXXXXX / 992XXXXXXXXX / 0XXXXXXXXX / local 9 digits
PHONE_PATTERN = re.compile(r"^(?:\+?992|0)?[5-9]\d{8}$")

TOPUP_MIN_AMOUNT = Decimal("1.00")
TOPUP_MAX_AMOUNT = Decimal("10000.00")


def is_valid_uid(value: str) -> bool:
    return bool(UID_PATTERN.match(value.strip()))


def normalize_uid(value: str) -> str:
    return value.strip()


def validate_uid(value: str) -> tuple[bool, Optional[str]]:
    uid = normalize_uid(value)
    if not uid:
        return False, "UID холӣ аст."
    if not uid.isdigit():
        return False, "UID бояд танҳо рақам бошад."
    if not is_valid_uid(uid):
        return False, "UID бояд аз 8 то 12 рақам бошад."
    return True, None


def is_valid_username(value: str) -> bool:
    return bool(USERNAME_PATTERN.match(value or ""))


def validate_topup_amount(value: str) -> tuple[bool, Optional[str], Optional[Decimal]]:
    raw = (value or "").strip().replace(",", ".")
    if not raw:
        return False, "Маблағ холӣ аст.", None
    try:
        amount = Decimal(raw)
    except (InvalidOperation, ValueError):
        return False, "Маблағ бояд рақам бошад.", None
    if amount != amount.to_integral_value() and amount.as_tuple().exponent < -2:
        return False, "Ҳадди аққал ду рақами касрӣ.", None
    if amount <= 0:
        return False, "Маблағ бояд аз нол зиёд бошад.", None
    if amount < TOPUP_MIN_AMOUNT:
        return False, f"Ҳадди аққал {TOPUP_MIN_AMOUNT} TJS.", None
    if amount > TOPUP_MAX_AMOUNT:
        return False, f"Ҳадди аксар {TOPUP_MAX_AMOUNT} TJS.", None
    return True, None, amount.quantize(Decimal("0.01"))


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("992") and len(digits) >= 12:
        digits = digits[3:]
    elif digits.startswith("0") and len(digits) == 10:
        digits = digits[1:]
    return f"+992{digits}" if len(digits) == 9 else value.strip()


def validate_phone(value: str) -> tuple[bool, Optional[str], Optional[str]]:
    raw = (value or "").strip()
    if not raw:
        return False, "Рақами телефон холӣ аст.", None
    cleaned = raw.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not PHONE_PATTERN.match(cleaned):
        return False, "Рақами Тоҷикистон нависед (масалан: +992901234567).", None
    return True, None, normalize_phone(cleaned)
