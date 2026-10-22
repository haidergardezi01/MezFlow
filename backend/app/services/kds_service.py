import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import get_utc_now
from app.models.order import (
    Order,
    OrderStatus,
    OrderItem,
    OrderItemModifier,
    OrderStatusHistory,
)
from app.models.user import User
from app.models.audit import AuditLog
from app.services.realtime import kds_connection_manager, session_connection_manager
from app.schemas.kds import (
    KDSOrderCardResponse,
    KDSItemResponse,
    KDSModifierResponse,
    KDSSummaryResponse,
)

logger = logging.getLogger("mezflow.kds")

# Valid state machine transitions (FR-M4-05, FR-M5-01)
VALID_TRANSITIONS: Dict[OrderStatus, List[OrderStatus]] = {
    OrderStatus.NEW: [
        OrderStatus.CONFIRMED,
        OrderStatus.PREPARING,
        OrderStatus.CANCELLED,
    ],
    OrderStatus.CONFIRMED: [
        OrderStatus.PREPARING,
        OrderStatus.CANCELLED,
    ],
    OrderStatus.PREPARING: [
        OrderStatus.READY,
        OrderStatus.CANCELLED,
    ],
    OrderStatus.READY: [
        OrderStatus.DISPATCHED,
        OrderStatus.PREPARING,  # Reversible recall
    ],
    OrderStatus.DISPATCHED: [],  # Terminal
    OrderStatus.CANCELLED: [],   # Terminal
}


def validate_status_transition(current_status: OrderStatus, target_status: OrderStatus):
    """Validates if transition between order statuses is permitted by state machine."""
    if current_status in (OrderStatus.DISPATCHED, OrderStatus.CANCELLED):
        raise HTTPException(
            status_code=400,
            detail=f"Order is in terminal state '{current_status.value}' and cannot be transitioned.",
        )

    allowed = VALID_TRANSITIONS.get(current_status, [])
    if target_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid state transition from '{current_status.value}' to '{target_status.value}'.",
        )


class KDSService:
    @staticmethod
    async def get_active_orders(
        db: AsyncSession,
        restaurant_id: UUID,
        station_filter: str = "all",
        status_filter: str = "all",
    ) -> List[KDSOrderCardResponse]:
        """Fetches active non-terminal kitchen tickets with station filtering and elapsed timers."""
        stmt = (
            select(Order)
            .where(
                and_(
                    Order.restaurant_id == restaurant_id,
                    Order.status.notin_([OrderStatus.DISPATCHED, OrderStatus.CANCELLED]),
                )
            )
            .options(
                selectinload(Order.table),
                selectinload(Order.placed_by),
                selectinload(Order.items).selectinload(OrderItem.modifiers),
            )
            .order_by(Order.placed_at.asc())
        )

        res = await db.execute(stmt)
        orders = res.scalars().all()

        now = get_utc_now()
        kds_cards: List[KDSOrderCardResponse] = []

        station_filter_clean = station_filter.lower().strip()
        status_filter_clean = status_filter.upper().strip()

        for order in orders:
            # Status filter check
            if status_filter_clean != "ALL" and order.status.value != status_filter_clean:
                continue

            # Filter items by station
            order_items: List[KDSItemResponse] = []
            for item in order.items:
                if (
                    station_filter_clean != "all"
                    and item.kitchen_station.lower() != station_filter_clean
                ):
                    continue

                order_items.append(
                    KDSItemResponse(
                        id=item.id,
                        item_id=item.item_id,
                        item_name=item.item_name,
                        kitchen_station=item.kitchen_station,
                        quantity=item.quantity,
                        special_instructions=item.special_instructions,
                        status=item.status,
                        prepared_at=item.prepared_at,
                        modifiers=[
                            KDSModifierResponse(
                                id=m.id,
                                option_name=m.option_name,
                                price_delta=m.price_delta,
                            )
                            for m in item.modifiers
                        ],
                    )
                )

            # If specific station was filtered and this order has no items for it, skip card
            if station_filter_clean != "all" and len(order_items) == 0:
                continue

            elapsed_seconds = max(0, int((now - order.placed_at).total_seconds()))
            target_prep = order.target_prep_minutes or 15
            target_seconds = target_prep * 60

            # Urgency classification (FR-M4-07)
            if elapsed_seconds > target_seconds or elapsed_seconds >= 900:
                urgency = "DELAYED"
            elif elapsed_seconds >= 600:
                urgency = "WARNING"
            else:
                urgency = "NORMAL"

            table_num = order.table.table_number if order.table else 0
            table_nm = order.table.name if order.table else None
            diner_nm = order.placed_by.display_name if order.placed_by else None

            kds_cards.append(
                KDSOrderCardResponse(
                    id=order.id,
                    restaurant_id=order.restaurant_id,
                    table_id=order.table_id,
                    table_number=table_num,
                    table_name=table_nm,
                    order_number=order.order_number,
                    display_number=order.display_number,
                    status=order.status.value,
                    placed_at=order.placed_at,
                    confirmed_at=order.confirmed_at,
                    preparing_started_at=order.preparing_started_at,
                    ready_at=order.ready_at,
                    dispatched_at=order.dispatched_at,
                    target_prep_minutes=target_prep,
                    elapsed_seconds=elapsed_seconds,
                    urgency_level=urgency,
                    notes=order.notes,
                    placed_by_diner_name=diner_nm,
                    items=order_items,
                )
            )

        return kds_cards

    @staticmethod
    async def get_summary_metrics(
        db: AsyncSession,
        restaurant_id: UUID,
    ) -> KDSSummaryResponse:
        """Aggregates quick status and station metrics for top bar badges."""
        stmt = (
            select(Order)
            .where(
                and_(
                    Order.restaurant_id == restaurant_id,
                    Order.status.notin_([OrderStatus.DISPATCHED, OrderStatus.CANCELLED]),
                )
            )
            .options(selectinload(Order.items))
        )
        res = await db.execute(stmt)
        active_orders = res.scalars().all()

        now = get_utc_now()
        new_count = 0
        preparing_count = 0
        ready_count = 0
        delayed_count = 0
        by_station: Dict[str, int] = {
            "grill": 0,
            "fry": 0,
            "hot_kitchen": 0,
            "beverage": 0,
        }

        for order in active_orders:
            if order.status == OrderStatus.NEW or order.status == OrderStatus.CONFIRMED:
                new_count += 1
            elif order.status == OrderStatus.PREPARING:
                preparing_count += 1
            elif order.status == OrderStatus.READY:
                ready_count += 1

            elapsed = (now - order.placed_at).total_seconds()
            target_secs = (order.target_prep_minutes or 15) * 60
            if elapsed > target_secs or elapsed >= 900:
                delayed_count += 1

            for item in order.items:
                stn = item.kitchen_station.lower()
                by_station[stn] = by_station.get(stn, 0) + item.quantity

        return KDSSummaryResponse(
            total_active=len(active_orders),
            new=new_count,
            preparing=preparing_count,
            ready=ready_count,
            delayed=delayed_count,
            by_station=by_station,
        )

    @staticmethod
    async def bump_order(
        db: AsyncSession,
        order_id: UUID,
        user: User,
        target_status_str: Optional[str] = None,
    ) -> Order:
        """Single-tap bump advances order to next logical state or explicitly provided target."""
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.items),
                selectinload(Order.table),
                selectinload(Order.placed_by),
            )
        )
        res = await db.execute(stmt)
        order = res.scalar_one_or_none()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Verify restaurant tenant isolation
        if order.restaurant_id != user.restaurant_id and user.role.value != "ADMIN":
            raise HTTPException(status_code=403, detail="Access denied to this order")

        prev_status = order.status

        # Determine target status if not explicitly given
        if target_status_str:
            try:
                target_status = OrderStatus(target_status_str.upper())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid target status '{target_status_str}'",
                )
        else:
            if order.status in (OrderStatus.NEW, OrderStatus.CONFIRMED):
                target_status = OrderStatus.PREPARING
            elif order.status == OrderStatus.PREPARING:
                target_status = OrderStatus.READY
            elif order.status == OrderStatus.READY:
                target_status = OrderStatus.DISPATCHED
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot bump order in terminal state '{order.status.value}'",
                )

        # Validate against state machine
        validate_status_transition(order.status, target_status)

        now = get_utc_now()
        order.status = target_status

        # Update lifecycle milestone timestamps
        if target_status == OrderStatus.CONFIRMED:
            order.confirmed_at = now
        elif target_status == OrderStatus.PREPARING:
            order.preparing_started_at = now
            if not order.confirmed_at:
                order.confirmed_at = now
            for itm in order.items:
                if itm.status == "PENDING":
                    itm.status = "PREPARING"
        elif target_status == OrderStatus.READY:
            order.ready_at = now
            for itm in order.items:
                itm.status = "READY"
                if not itm.prepared_at:
                    itm.prepared_at = now
        elif target_status == OrderStatus.DISPATCHED:
            order.dispatched_at = now

        # Record status history
        history = OrderStatusHistory(
            order_id=order.id,
            changed_by_user_id=user.id,
            previous_status=prev_status.value,
            new_status=target_status.value,
            notes=f"Bumped by {user.email}",
        )
        db.add(history)

        # Audit log entry (FR-M1-06)
        audit_log = AuditLog(
            restaurant_id=order.restaurant_id,
            user_id=user.id,
            action="KDS_ORDER_BUMP",
            details={
                "order_id": str(order.id),
                "order_number": order.order_number,
                "previous_status": prev_status.value,
                "new_status": target_status.value,
            },
        )
        db.add(audit_log)

        await db.commit()
        await db.refresh(order)

        # Broadcast events (< 2s sync)
        # 1. To KDS
        await kds_connection_manager.publish_event(
            order.restaurant_id,
            {
                "event": "ORDER_BUMPED",
                "order_id": str(order.id),
                "order_number": order.order_number,
                "previous_status": prev_status.value,
                "new_status": target_status.value,
                "bumped_by": user.email,
                "updated_at": now.isoformat(),
            },
        )

        # 2. To Customer Table Session
        if order.session_id:
            await session_connection_manager.publish_event(
                order.session_id,
                {
                    "event": "ORDER_STATUS_CHANGED",
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                    "previous_status": prev_status.value,
                    "new_status": target_status.value,
                    "updated_at": now.isoformat(),
                },
            )

        return order

    @staticmethod
    async def recall_order(
        db: AsyncSession,
        order_id: UUID,
        user: User,
        reason: Optional[str] = None,
    ) -> Order:
        """Reverts order to previous status within 60-second recall window."""
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.items),
                selectinload(Order.table),
                selectinload(Order.status_history),
            )
        )
        res = await db.execute(stmt)
        order = res.scalar_one_or_none()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.restaurant_id != user.restaurant_id and user.role.value != "ADMIN":
            raise HTTPException(status_code=403, detail="Access denied to this order")

        # Find latest history entry
        if not order.status_history or len(order.status_history) == 0:
            raise HTTPException(
                status_code=400,
                detail="No previous status history found to recall this order.",
            )

        latest_history = order.status_history[0]
        now = get_utc_now()
        seconds_since_bump = (now - latest_history.created_at).total_seconds()

        # 60-second window check (FR-M4-05, WP4.6)
        if seconds_since_bump > 60:
            raise HTTPException(
                status_code=400,
                detail=f"Recall grace period (60 seconds) has expired ({int(seconds_since_bump)}s elapsed).",
            )

        previous_status = OrderStatus(latest_history.previous_status)
        current_status = order.status

        # Revert status
        order.status = previous_status

        # Reset milestone timestamps
        if current_status == OrderStatus.DISPATCHED:
            order.dispatched_at = None
        elif current_status == OrderStatus.READY:
            order.ready_at = None
        elif current_status == OrderStatus.PREPARING:
            order.preparing_started_at = None

        # Add recall history record
        recall_history = OrderStatusHistory(
            order_id=order.id,
            changed_by_user_id=user.id,
            previous_status=current_status.value,
            new_status=previous_status.value,
            notes=reason or f"Recalled by {user.email}",
        )
        db.add(recall_history)

        # Audit log entry
        audit_log = AuditLog(
            restaurant_id=order.restaurant_id,
            user_id=user.id,
            action="KDS_ORDER_RECALL",
            details={
                "order_id": str(order.id),
                "order_number": order.order_number,
                "reverted_from": current_status.value,
                "reverted_to": previous_status.value,
            },
        )
        db.add(audit_log)

        await db.commit()
        await db.refresh(order)

        # Broadcast events
        await kds_connection_manager.publish_event(
            order.restaurant_id,
            {
                "event": "ORDER_RECALLED",
                "order_id": str(order.id),
                "order_number": order.order_number,
                "previous_status": current_status.value,
                "new_status": previous_status.value,
                "updated_at": now.isoformat(),
            },
        )

        if order.session_id:
            await session_connection_manager.publish_event(
                order.session_id,
                {
                    "event": "ORDER_STATUS_CHANGED",
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                    "previous_status": current_status.value,
                    "new_status": previous_status.value,
                    "updated_at": now.isoformat(),
                },
            )

        return order

    @staticmethod
    async def update_item_status(
        db: AsyncSession,
        order_id: UUID,
        item_id: UUID,
        new_status: str,
        user: User,
    ) -> OrderItem:
        """Line cook marks specific dish READY or PREPARING without bumping entire ticket."""
        clean_status = new_status.upper().strip()
        if clean_status not in ("PENDING", "PREPARING", "READY"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid item status '{new_status}'. Must be PENDING, PREPARING, or READY.",
            )

        stmt = (
            select(OrderItem)
            .where(and_(OrderItem.id == item_id, OrderItem.order_id == order_id))
            .options(selectinload(OrderItem.order))
        )
        res = await db.execute(stmt)
        item = res.scalar_one_or_none()

        if not item:
            raise HTTPException(status_code=404, detail="Order item not found")

        order = item.order
        if order.restaurant_id != user.restaurant_id and user.role.value != "ADMIN":
            raise HTTPException(status_code=403, detail="Access denied")

        item.status = clean_status
        now = get_utc_now()
        if clean_status == "READY":
            item.prepared_at = now

        # If all items in this order are now READY, auto-bump order to READY
        stmt_all = select(OrderItem).where(OrderItem.order_id == order_id)
        res_all = await db.execute(stmt_all)
        all_items = res_all.scalars().all()

        all_ready = all(i.status == "READY" for i in all_items)
        if all_ready and order.status in (OrderStatus.NEW, OrderStatus.CONFIRMED, OrderStatus.PREPARING):
            order.status = OrderStatus.READY
            order.ready_at = now

            history = OrderStatusHistory(
                order_id=order.id,
                changed_by_user_id=user.id,
                previous_status="PREPARING",
                new_status="READY",
                notes="Auto-bumped to READY: all items marked prepared",
            )
            db.add(history)

            await kds_connection_manager.publish_event(
                order.restaurant_id,
                {
                    "event": "ORDER_BUMPED",
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                    "previous_status": "PREPARING",
                    "new_status": "READY",
                    "bumped_by": user.email,
                    "updated_at": now.isoformat(),
                },
            )

            if order.session_id:
                await session_connection_manager.publish_event(
                    order.session_id,
                    {
                        "event": "ORDER_STATUS_CHANGED",
                        "order_id": str(order.id),
                        "order_number": order.order_number,
                        "previous_status": "PREPARING",
                        "new_status": "READY",
                        "updated_at": now.isoformat(),
                    },
                )

        await db.commit()
        await db.refresh(item)

        # Broadcast item update
        await kds_connection_manager.publish_event(
            order.restaurant_id,
            {
                "event": "ITEM_STATUS_UPDATED",
                "order_id": str(order.id),
                "item_id": str(item.id),
                "status": clean_status,
                "kitchen_station": item.kitchen_station,
                "updated_at": now.isoformat(),
            },
        )

        return item

    @staticmethod
    async def get_order_history(
        db: AsyncSession,
        restaurant_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> List[KDSOrderCardResponse]:
        """Fetches recently completed/dispatched orders for shift review."""
        stmt = (
            select(Order)
            .where(
                and_(
                    Order.restaurant_id == restaurant_id,
                    Order.status == OrderStatus.DISPATCHED,
                )
            )
            .options(
                selectinload(Order.table),
                selectinload(Order.placed_by),
                selectinload(Order.items).selectinload(OrderItem.modifiers),
            )
            .order_by(Order.dispatched_at.desc())
            .limit(limit)
            .offset(offset)
        )

        res = await db.execute(stmt)
        orders = res.scalars().all()

        now = get_utc_now()
        cards: List[KDSOrderCardResponse] = []

        for order in orders:
            elapsed_seconds = (
                int((order.dispatched_at - order.placed_at).total_seconds())
                if order.dispatched_at
                else 0
            )

            cards.append(
                KDSOrderCardResponse(
                    id=order.id,
                    restaurant_id=order.restaurant_id,
                    table_id=order.table_id,
                    table_number=order.table.table_number if order.table else 0,
                    table_name=order.table.name if order.table else None,
                    order_number=order.order_number,
                    display_number=order.display_number,
                    status=order.status.value,
                    placed_at=order.placed_at,
                    confirmed_at=order.confirmed_at,
                    preparing_started_at=order.preparing_started_at,
                    ready_at=order.ready_at,
                    dispatched_at=order.dispatched_at,
                    target_prep_minutes=order.target_prep_minutes or 15,
                    elapsed_seconds=elapsed_seconds,
                    urgency_level="NORMAL",
                    notes=order.notes,
                    placed_by_diner_name=order.placed_by.display_name if order.placed_by else None,
                    items=[
                        KDSItemResponse(
                            id=item.id,
                            item_id=item.item_id,
                            item_name=item.item_name,
                            kitchen_station=item.kitchen_station,
                            quantity=item.quantity,
                            special_instructions=item.special_instructions,
                            status=item.status,
                            prepared_at=item.prepared_at,
                            modifiers=[
                                KDSModifierResponse(
                                    id=m.id,
                                    option_name=m.option_name,
                                    price_delta=m.price_delta,
                                )
                                for m in item.modifiers
                            ],
                        )
                        for item in order.items
                    ],
                )
            )

        return cards
