from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Optional

# Free Fire numeric UID: typically 8-12 digits. We never ask for a password.
UID_PATTERN = re.compile(r"^\d{8,12}$")
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]{5,32}$")
# Tajikistan national number is 9 digits (can start with 00, 01, 90, …)
PHONE_NATIONAL_LEN = 9
PHONE_PATTERN = re.compile(r"^(?:\+?992)?\d{9}$")

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


def _phone_digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _phone_national(value: str) -> str:
    """Return 9-digit Tajik national number (without +992), or '' if not possible."""
    digits = _phone_digits(value)
    # International: 00992XXXXXXXXX
    if digits.startswith("00992") and len(digits) >= 14:
        digits = digits[5:]
    # International: 992XXXXXXXXX
    elif digits.startswith("992") and len(digits) >= 12:
        digits = digits[3:]
    # Local dialing: 0XXXXXXXXX (10 digits)
    elif digits.startswith("0") and len(digits) == 10:
        digits = digits[1:]
    if len(digits) == PHONE_NATIONAL_LEN and digits.isdigit():
        return digits
    return ""


def normalize_phone(value: str) -> str:
    national = _phone_national(value)
    if national:
        return f"+992{national}"
    return (value or "").strip()


def validate_phone(value: str) -> tuple[bool, Optional[str], Optional[str]]:
    raw = (value or "").strip()
    if not raw:
        return False, "Рақами телефон холӣ аст.", None

    cleaned = (
        raw.replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
        .replace("\t", "")
    )
    national = _phone_national(cleaned)
    if not national:
        return (
            False,
            "Рақами Тоҷикистон нависед "
            "(масалан: +992002119831 ё 002119831).",
            None,
        )
    return True, None, f"+992{national}"
