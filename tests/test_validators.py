from __future__ import annotations

from decimal import Decimal

import pytest

from app.utils.validators import (
    is_valid_uid,
    normalize_phone,
    validate_phone,
    validate_topup_amount,
    validate_uid,
)


def test_valid_uids():
    assert is_valid_uid("12345678")
    assert is_valid_uid("123456789012")
    ok, err = validate_uid("  12345678  ")
    assert ok and err is None


def test_invalid_uids():
    assert not is_valid_uid("123")
    assert not is_valid_uid("abcdefgh")
    ok, err = validate_uid("abc")
    assert not ok and err


def test_empty_uid():
    ok, err = validate_uid("")
    assert not ok and err


def test_valid_topup_amounts():
    ok, err, amount = validate_topup_amount("10")
    assert ok and err is None and amount == Decimal("10.00")
    ok, err, amount = validate_topup_amount("25.50")
    assert ok and amount == Decimal("25.50")
    ok, err, amount = validate_topup_amount("1,5")
    assert ok and amount == Decimal("1.50")


def test_invalid_topup_amounts():
    assert not validate_topup_amount("")[0]
    assert not validate_topup_amount("abc")[0]
    assert not validate_topup_amount("0")[0]
    assert not validate_topup_amount("-5")[0]
    assert not validate_topup_amount("0.5")[0]
    assert not validate_topup_amount("99999")[0]


def test_valid_phones():
    ok, err, phone = validate_phone("+992901234567")
    assert ok and phone == "+992901234567"
    ok, err, phone = validate_phone("992901234567")
    assert ok and phone == "+992901234567"
    ok, err, phone = validate_phone("901234567")
    assert ok and phone == "+992901234567"
    ok, err, phone = validate_phone("0901234567")
    assert ok and phone == "+992901234567"
    # Operator code 00 (e.g. +992 002119831)
    ok, err, phone = validate_phone("002119831")
    assert ok and phone == "+992002119831"
    ok, err, phone = validate_phone("+992002119831")
    assert ok and phone == "+992002119831"
    ok, err, phone = validate_phone("992002119831")
    assert ok and phone == "+992002119831"
    ok, err, phone = validate_phone("00992002119831")
    assert ok and phone == "+992002119831"


def test_invalid_phones():
    assert not validate_phone("")[0]
    assert not validate_phone("12345")[0]
    assert not validate_phone("+1234567890")[0]
    assert not validate_phone("abcdefghij")[0]
    assert not validate_phone("00211983")[0]  # only 8 digits
    assert not validate_phone("00021198311")[0]  # 11 digits


def test_normalize_phone():
    assert normalize_phone("992901234567") == "+992901234567"
    assert normalize_phone("0901234567") == "+992901234567"
    assert normalize_phone("002119831") == "+992002119831"
    assert normalize_phone("+992002119831") == "+992002119831"
