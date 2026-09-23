from enum import StrEnum


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


TERMINAL_ORDER_STATUSES = {
    OrderStatus.COMPLETED,
    OrderStatus.FAILED,
    OrderStatus.CANCELLED,
}
