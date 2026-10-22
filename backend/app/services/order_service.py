from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.session import TableSession, SessionStatus, Diner, CartItem, CartItemModifier
from app.models.order import Order, OrderStatus, OrderItem, OrderItemModifier
from app.models.table import Table
from app.models.restaurant import Restaurant
from app.schemas.order import (
    OrderResponse,
    OrderItemResponse,
    OrderItemModifierResponse,
)
from app.services.realtime import session_connection_manager


async def submit_table_order(
    db: AsyncSession,
    session_id: UUID,
    placed_by_diner_id: UUID,
    notes: Optional[str] = None,
) -> OrderResponse:
    """
    Submits the shared table cart as a finalized Order.
    Enforces atomic double-submission lock (NFR-04), generates daily sequential order number,
    snapshots items with station tags, dispatches to KDS, and broadcasts live order event (< 2s).
    (FR-M3-05, FR-M3-06, NFR-02, NFR-06)
    """
    # 1. Atomic Double-Submission Mutex Lock
    lock_stmt = (
        update(TableSession)
        .where(
            TableSession.id == session_id,
            TableSession.status == SessionStatus.ACTIVE,
        )
        .values(status=SessionStatus.SUBMITTING)
    )
    lock_res = await db.execute(lock_stmt)
    if lock_res.rowcount == 0:
        # Check current status for clear error message
        chk = await db.execute(select(TableSession.status).where(TableSession.id == session_id))
        curr_status = chk.scalar_one_or_none()
        if curr_status == SessionStatus.SUBMITTING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Order is currently being submitted by another diner. Please wait.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit order in session state: {curr_status}.",
        )

    # 2. Fetch Session, Table, Restaurant, and Diner
    sess_query = (
        select(TableSession, Table, Restaurant)
        .join(Table, TableSession.table_id == Table.id)
        .join(Restaurant, TableSession.restaurant_id == Restaurant.id)
        .where(TableSession.id == session_id)
    )
    sess_res = await db.execute(sess_query)
    session, table, restaurant = sess_res.first()

    diner_res = await db.execute(select(Diner).where(Diner.id == placed_by_diner_id))
    placing_diner = diner_res.scalar_one_or_none()
    placing_diner_name = placing_diner.display_name if placing_diner else "Guest"

    # 3. Load Cart Items with Modifiers
    cart_query = (
        select(CartItem)
        .where(CartItem.session_id == session_id)
        .options(
            selectinload(CartItem.item),
            selectinload(CartItem.diner),
            selectinload(CartItem.modifiers),
        )
    )
    cart_res = await db.execute(cart_query)
    cart_items = list(cart_res.scalars().all())

    if not cart_items:
        # Release lock and reject
        await db.execute(
            update(TableSession)
            .where(TableSession.id == session_id)
            .values(status=SessionStatus.ACTIVE)
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit an empty cart. Please add dishes first.",
        )

    # 4. Generate Daily Sequential Order Number (e.g. ORD-042)
    daily_num_query = select(func.coalesce(func.max(Order.order_number), 0)).where(
        Order.restaurant_id == restaurant.id,
        func.date(Order.placed_at) == func.current_date(),
    )
    daily_res = await db.execute(daily_num_query)
    max_num = daily_res.scalar_one() or 0
    next_order_num = max_num + 1
    display_num = f"ORD-{next_order_num:03d}"

    # 5. Compute Subtotal and Snapshot Items
    subtotal = Decimal("0.00")
    order_items_to_create = []

    for ci in cart_items:
        base_price = Decimal(str(ci.item.price))
        mods_delta = sum((Decimal(str(m.price_delta_cached)) for m in ci.modifiers), Decimal("0.00"))
        unit_price = max(Decimal("0.00"), base_price + mods_delta)
        total_price = unit_price * ci.quantity
        subtotal += total_price

        order_items_to_create.append((ci, unit_price, total_price))

    tax_amount = Decimal("0.00")
    total_amount = subtotal + tax_amount

    # 6. Create Order Record
    order = Order(
        restaurant_id=restaurant.id,
        table_id=table.id,
        session_id=session.id,
        order_number=next_order_num,
        display_number=display_num,
        status=OrderStatus.NEW,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total_amount=total_amount,
        placed_by_diner_id=placed_by_diner_id,
        notes=notes.strip() if notes else None,
        placed_at=datetime.now(timezone.utc),
    )
    db.add(order)
    await db.flush()

    # 7. Create OrderItems & OrderItemModifiers
    order_item_resps: List[OrderItemResponse] = []

    for ci, unit_price, total_price in order_items_to_create:
        oi = OrderItem(
            order_id=order.id,
            item_id=ci.item_id,
            diner_id=ci.diner_id,
            item_name=ci.item.name,
            kitchen_station=ci.item.kitchen_station or "hot_kitchen",
            quantity=ci.quantity,
            unit_price=unit_price,
            total_price=total_price,
            special_instructions=ci.special_instructions,
            status="PENDING",
        )
        db.add(oi)
        await db.flush()

        created_mods = []
        for cim in ci.modifiers:
            oim = OrderItemModifier(
                order_item_id=oi.id,
                modifier_option_id=cim.modifier_option_id,
                option_name=cim.option_name_cached or "Option",
                price_delta=cim.price_delta_cached,
            )
            db.add(oim)
            created_mods.append(oim)

        await db.flush()

        mod_resps: List[OrderItemModifierResponse] = [
            OrderItemModifierResponse(
                id=oim.id,
                modifier_option_id=oim.modifier_option_id,
                option_name=oim.option_name,
                price_delta=Decimal(str(oim.price_delta)),
            )
            for oim in created_mods
        ]

        order_item_resps.append(
            OrderItemResponse(
                id=oi.id,
                item_id=oi.item_id,
                diner_id=oi.diner_id,
                diner_name=ci.diner.display_name if ci.diner else "Guest",
                item_name=oi.item_name,
                kitchen_station=oi.kitchen_station,
                quantity=oi.quantity,
                unit_price=oi.unit_price,
                total_price=oi.total_price,
                special_instructions=oi.special_instructions,
                status=oi.status,
                modifiers=mod_resps,
                created_at=oi.created_at,
            )
        )

    # 8. Empty Cart for Next Ordering Round and Restore Session Status
    del_stmt = delete(CartItem).where(CartItem.session_id == session.id)
    await db.execute(del_stmt)

    session.status = SessionStatus.ACTIVE  # Kept active for additional ordering rounds
    session.total_amount = Decimal("0.00")
    await db.commit()

    order_response = OrderResponse(
        id=order.id,
        restaurant_id=restaurant.id,
        table_id=table.id,
        table_number=table.table_number,
        session_id=session.id,
        order_number=order.order_number,
        display_number=order.display_number,
        status=order.status.value,
        subtotal=order.subtotal,
        tax_amount=order.tax_amount,
        total_amount=order.total_amount,
        placed_by_diner_name=placing_diner_name,
        notes=order.notes,
        placed_at=order.placed_at,
        items=order_item_resps,
        currency=restaurant.currency,
    )

    # 9. Real-time broadcast to Diners: ORDER_SUBMITTED (< 2s)
    await session_connection_manager.publish_event(
        session_id=session.id,
        event_data={
            "event": "ORDER_SUBMITTED",
            "session_id": str(session.id),
            "order_id": str(order.id),
            "order_number": order.order_number,
            "display_number": order.display_number,
            "total_amount": float(order.total_amount),
            "placed_by": placing_diner_name,
            "status": order.status.value,
            "placed_at": order.placed_at.isoformat(),
        },
    )

    # 10. Real-time broadcast to KDS (Kitchen Display System bridge)
    await session_connection_manager.publish_kds_order(
        restaurant_id=restaurant.id,
        order_data={
            "event": "NEW_ORDER",
            "order_id": str(order.id),
            "table_number": table.table_number,
            "display_number": order.display_number,
            "status": order.status.value,
            "total_amount": float(order.total_amount),
            "placed_at": order.placed_at.isoformat(),
            "items": [
                {
                    "item_name": oi.item_name,
                    "kitchen_station": oi.kitchen_station,
                    "quantity": oi.quantity,
                    "special_instructions": oi.special_instructions,
                    "modifiers": [m.option_name for m in oi.modifiers],
                }
                for oi in order_item_resps
            ],
        },
    )

    return order_response


async def get_session_orders(
    db: AsyncSession, session_id: UUID
) -> List[OrderResponse]:
    """Retrieves all orders placed during an active dining session."""
    query = (
        select(Order, Table, Restaurant, Diner)
        .join(Table, Order.table_id == Table.id)
        .join(Restaurant, Order.restaurant_id == Restaurant.id)
        .outerjoin(Diner, Order.placed_by_diner_id == Diner.id)
        .where(Order.session_id == session_id)
        .options(
            selectinload(Order.items).selectinload(OrderItem.modifiers),
            selectinload(Order.items).selectinload(OrderItem.diner),
        )
        .order_by(Order.placed_at.desc())
    )
    res = await db.execute(query)
    rows = res.all()

    order_responses: List[OrderResponse] = []
    for order, table, restaurant, diner in rows:
        item_resps: List[OrderItemResponse] = []
        for oi in order.items:
            mod_resps = [
                OrderItemModifierResponse(
                    id=m.id,
                    modifier_option_id=m.modifier_option_id,
                    option_name=m.option_name,
                    price_delta=Decimal(str(m.price_delta)),
                )
                for m in oi.modifiers
            ]
            item_resps.append(
                OrderItemResponse(
                    id=oi.id,
                    item_id=oi.item_id,
                    diner_id=oi.diner_id,
                    diner_name=oi.diner.display_name if oi.diner else "Guest",
                    item_name=oi.item_name,
                    kitchen_station=oi.kitchen_station,
                    quantity=oi.quantity,
                    unit_price=Decimal(str(oi.unit_price)),
                    total_price=Decimal(str(oi.total_price)),
                    special_instructions=oi.special_instructions,
                    status=oi.status,
                    modifiers=mod_resps,
                    created_at=oi.created_at,
                )
            )

        order_responses.append(
            OrderResponse(
                id=order.id,
                restaurant_id=restaurant.id,
                table_id=table.id,
                table_number=table.table_number,
                session_id=order.session_id,
                order_number=order.order_number,
                display_number=order.display_number,
                status=order.status.value,
                subtotal=Decimal(str(order.subtotal)),
                tax_amount=Decimal(str(order.tax_amount)),
                total_amount=Decimal(str(order.total_amount)),
                placed_by_diner_name=diner.display_name if diner else "Guest",
                notes=order.notes,
                placed_at=order.placed_at,
                items=item_resps,
                currency=restaurant.currency,
            )
        )
    return order_responses


async def get_order_detail(
    db: AsyncSession, order_id: UUID
) -> OrderResponse:
    """Fetches details for a single order."""
    query = (
        select(Order, Table, Restaurant, Diner)
        .join(Table, Order.table_id == Table.id)
        .join(Restaurant, Order.restaurant_id == Restaurant.id)
        .outerjoin(Diner, Order.placed_by_diner_id == Diner.id)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.items).selectinload(OrderItem.modifiers),
            selectinload(Order.items).selectinload(OrderItem.diner),
        )
    )
    res = await db.execute(query)
    row = res.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    order, table, restaurant, diner = row
    item_resps: List[OrderItemResponse] = []
    for oi in order.items:
        mod_resps = [
            OrderItemModifierResponse(
                id=m.id,
                modifier_option_id=m.modifier_option_id,
                option_name=m.option_name,
                price_delta=Decimal(str(m.price_delta)),
            )
            for m in oi.modifiers
        ]
        item_resps.append(
            OrderItemResponse(
                id=oi.id,
                item_id=oi.item_id,
                diner_id=oi.diner_id,
                diner_name=oi.diner.display_name if oi.diner else "Guest",
                item_name=oi.item_name,
                kitchen_station=oi.kitchen_station,
                quantity=oi.quantity,
                unit_price=Decimal(str(oi.unit_price)),
                total_price=Decimal(str(oi.total_price)),
                special_instructions=oi.special_instructions,
                status=oi.status,
                modifiers=mod_resps,
                created_at=oi.created_at,
            )
        )

    return OrderResponse(
        id=order.id,
        restaurant_id=restaurant.id,
        table_id=table.id,
        table_number=table.table_number,
        session_id=order.session_id,
        order_number=order.order_number,
        display_number=order.display_number,
        status=order.status.value,
        subtotal=Decimal(str(order.subtotal)),
        tax_amount=Decimal(str(order.tax_amount)),
        total_amount=Decimal(str(order.total_amount)),
        placed_by_diner_name=diner.display_name if diner else "Guest",
        notes=order.notes,
        placed_at=order.placed_at,
        items=item_resps,
        currency=restaurant.currency,
    )


async def update_order_status(
    db: AsyncSession,
    order_id: UUID,
    new_status_str: str,
    restaurant_id: Optional[UUID] = None,
) -> OrderResponse:
    """Updates order status and broadcasts ORDER_STATUS_CHANGED to table and KDS."""
    query = select(Order).where(Order.id == order_id)
    if restaurant_id:
        query = query.where(Order.restaurant_id == restaurant_id)

    res = await db.execute(query)
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    try:
        new_status = OrderStatus(new_status_str.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid order status '{new_status_str}'. Allowed: {[s.value for s in OrderStatus]}",
        )

    prev_status = order.status.value
    order.status = new_status
    await db.commit()

    # Broadcast to session if active
    if order.session_id:
        await session_connection_manager.publish_event(
            session_id=order.session_id,
            event_data={
                "event": "ORDER_STATUS_CHANGED",
                "order_id": str(order.id),
                "order_number": order.order_number,
                "display_number": order.display_number,
                "previous_status": prev_status,
                "new_status": new_status.value,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    return await get_order_detail(db, order_id)
