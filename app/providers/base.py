from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional


@dataclass(slots=True)
class PaymentRequest:
    order_id: int
    amount: Decimal
    currency: str
    description: str = ""
    return_url: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


@dataclass(slots=True)
class PaymentResponse:
    payment_url: str
    provider_payment_id: str
    raw: Optional[dict[str, Any]] = None


@dataclass(slots=True)
class PaymentVerification:
    success: bool
    transaction_id: str
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    raw: Optional[dict[str, Any]] = None


class PaymentProvider(ABC):
    """Abstraction over an external payment gateway."""

    name: str = "base"

    @abstractmethod
    async def create_payment(self, request: PaymentRequest) -> PaymentResponse:
        raise NotImplementedError

    @abstractmethod
    async def verify_payment(self, payload: dict[str, Any]) -> PaymentVerification:
        raise NotImplementedError

    async def close(self) -> None:  # pragma: no cover - optional cleanup
        return None


@dataclass(slots=True)
class TopUpRequest:
    uid: str
    product: str
    order_id: int
    amount: Optional[Decimal] = None
    metadata: Optional[dict[str, Any]] = None


@dataclass(slots=True)
class TopUpResult:
    success: bool
    provider_reference: str
    message: str = ""
    raw: Optional[dict[str, Any]] = None
    # Submitted to the provider, completion arrives asynchronously.
    pending: bool = False


@dataclass(slots=True)
class AccountInfo:
    found: bool
    nickname: str = ""
    game: str = ""
    uid: str = ""
    message: str = ""
    verified: bool = False


class TopUpProvider(ABC):
    """Abstraction over an authorized Free Fire top-up provider."""

    name: str = "base"

    @abstractmethod
    async def topup(
        self,
        uid: str,
        product: str,
        order_id: int,
        sku: Optional[str] = None,
    ) -> TopUpResult:
        raise NotImplementedError

    async def lookup_account(self, uid: str, game: str = "ff") -> AccountInfo:
        """Return account nickname for a game UID so the user can confirm it."""
        raise NotImplementedError

    async def close(self) -> None:  # pragma: no cover - optional cleanup
        return None
