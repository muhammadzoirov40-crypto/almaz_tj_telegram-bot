from enum import StrEnum


class BalanceTopUpStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class BalanceTopUpMethod(StrEnum):
    ALIF = "alif"
    DS = "ds"
