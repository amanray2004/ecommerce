from collections import defaultdict
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.schemas.order import OrderCreate
from app.services.tenant_service import TenantService


class OrderService:
    @staticmethod
    def create_order(db: Session, tenant_name: str, user_id: str, payload: OrderCreate) -> Order:
        tenant = TenantService.get_tenant_by_name(db, tenant_name)

        grouped_quantities: dict[int, int] = defaultdict(int)
        for item in payload.items:
            grouped_quantities[item.product_id] += item.quantity

        try:
            total_quantity = 0
            total_amount = Decimal("0")
            created_items: list[OrderItem] = []

            order = Order(user_id=user_id, tenant_id=tenant.id, total_quantity=0, total_amount=0)
            db.add(order)
            db.flush()

            for product_id, quantity in grouped_quantities.items():
                # Row-level lock prevents stock race conditions in concurrent checkout.
                product = (
                    db.query(Product)
                    .filter(Product.id == product_id, Product.tenant_id == tenant.id)
                    .with_for_update()
                    .first()
                )
                if not product:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {product_id} not found.")

                if quantity > product.quantity:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Only {product.quantity} units of '{product.name}' are available.",
                    )

                product.quantity -= quantity
                line_total = product.price * quantity
                total_quantity += quantity
                total_amount += line_total

                created_items.append(
                    OrderItem(
                        order_id=order.id,
                        product_id=product.id,
                        quantity=quantity,
                        price_at_purchase=product.price,
                    )
                )

            order.total_quantity = total_quantity
            order.total_amount = total_amount
            db.add(order)
            db.add_all(created_items)
            db.commit()
            db.refresh(order)
        except HTTPException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create order.") from exc

        return (
            db.query(Order)
            .options(joinedload(Order.items))
            .filter(Order.id == order.id)
            .first()
        )

    @staticmethod
    def list_user_orders(
        db: Session,
        tenant_name: str,
        user_id: str,
        limit: int,
        offset: int,
    ) -> tuple[list[Order], int]:
        tenant = TenantService.get_tenant_by_name(db, tenant_name)
        query = (
            db.query(Order)
            .options(joinedload(Order.items))
            .filter(Order.tenant_id == tenant.id, Order.user_id == user_id)
            .order_by(Order.id.desc())
        )
        total = query.count()
        items = query.offset(offset).limit(limit).all()
        return items, total

    @staticmethod
    def list_user_orders_all_tenants(
        db: Session,
        user_id: str,
        limit: int,
        offset: int,
    ) -> tuple[list[Order], int]:
        query = (
            db.query(Order)
            .options(joinedload(Order.items))
            .filter(Order.user_id == user_id)
            .order_by(Order.id.desc())
        )
        total = query.count()
        items = query.offset(offset).limit(limit).all()
        return items, total
