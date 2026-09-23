from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Product


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_products(self) -> list[Product]:
        stmt = (
            select(Product)
            .where(Product.is_active.is_(True))
            .order_by(Product.diamonds.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, product_id: int) -> Optional[Product]:
        stmt = select(Product).where(Product.id == product_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        name: str,
        diamonds: int,
        price: Decimal,
        currency: str = "TJS",
        is_active: bool = True,
    ) -> Product:
        product = Product(
            name=name,
            diamonds=diamonds,
            price=price,
            currency=currency,
            is_active=is_active,
        )
        self.session.add(product)
        await self.session.flush()
        return product

    async def set_active(self, product_id: int, is_active: bool) -> Optional[Product]:
        product = await self.get_by_id(product_id)
        if product is None:
            return None
        product.is_active = is_active
        await self.session.flush()
        return product

    async def update_price(
        self, product_id: int, price: Decimal, currency: Optional[str] = None
    ) -> Optional[Product]:
        product = await self.get_by_id(product_id)
        if product is None:
            return None
        product.price = price
        if currency:
            product.currency = currency
        await self.session.flush()
        return product

    async def list_all(self, limit: int = 100) -> list[Product]:
        stmt = select(Product).order_by(Product.diamonds.asc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
