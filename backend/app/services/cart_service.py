from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.session import TableSession, SessionStatus, Diner, CartItem, CartItemModifier
from app.models.table import Table
from app.models.restaurant import Restaurant
from app.schemas.session import (
    CartResponse,
    CartItemResponse,
    CartItemModifierResponse,
    DinerResponse,
)
from app.services.pricing_service import validate_and_compute_item_price
from app.services.realtime import session_connection_manager


async def get_authoritative_cart(
    db: AsyncSession, session_id: UUID
) -> CartResponse:
    """
    Constructs the authoritative cart snapshot with server-recalculated prices (NFR-06).
    """
    # 1. Fetch Session with Table & Restaurant
    sess_query = (
        select(TableSession, Table, Restaurant)
        .join(Table, TableSession.table_id == Table.id)
        .join(Restaurant, TableSession.restaurant_id == Restaurant.id)
        .where(TableSession.id == session_id)
    )
    sess_res = await db.execute(sess_query)
    row = sess_res.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )
    session, table, restaurant = row

    # 2. Fetch Active Diners in Session
    diner_query = (
        select(Diner)
        .where(Diner.session_id == session_id, Diner.is_active == True)
        .order_by(Diner.joined_at)
    )
    diner_res = await db.execute(diner_query)
    diners = list(diner_res.scalars().all())

    # 3. Fetch Cart Items with Item, Diner, and Modifiers
    items_query = (
        select(CartItem)
        .where(CartItem.session_id == session_id)
        .options(
            selectinload(CartItem.item),
            selectinload(CartItem.diner),
            selectinload(CartItem.modifiers).selectinload(CartItemModifier.modifier_option),
        )
        .order_by(CartItem.created_at)
    )
    items_res = await db.execute(items_query)
    cart_items = items_res.scalars().all()

    # 4. Authoritatively calculate line items and totals
    subtotal = Decimal("0.00")
    item_responses: List[CartItemResponse] = []
    total_qty = 0

    for ci in cart_items:
        base_price = Decimal(str(ci.item.price))
        mods_delta = Decimal("0.00")
        mod_resps: List[CartItemModifierResponse] = []

        for cim in ci.modifiers:
            delta = Decimal(str(cim.price_delta_cached))
            mods_delta += delta
            mod_resps.append(
                CartItemModifierResponse(
                    id=cim.id,
                    modifier_option_id=cim.modifier_option_id,
                    option_name=cim.option_name_cached or "Option",
                    price_delta=delta,
                )
            )

        unit_price = max(Decimal("0.00"), base_price + mods_delta)
        line_total = unit_price * ci.quantity
        subtotal += line_total
        total_qty += ci.quantity

        item_responses.append(
            CartItemResponse(
                id=ci.id,
                session_id=ci.session_id,
                item_id=ci.item_id,
                item_name=ci.item.name,
                item_name_ur=ci.item.name_ur,
                base_price=base_price,
                diner_id=ci.diner_id,
                diner_name=ci.diner.display_name if ci.diner else "Guest",
                avatar_color=ci.diner.avatar_color if ci.diner else "#F59E0B",
                quantity=ci.quantity,
                special_instructions=ci.special_instructions,
                modifiers=mod_resps,
                unit_price=unit_price,
                line_total=line_total,
                created_at=ci.created_at,
            )
        )

    tax_amount = Decimal("0.00")
    total_amount = subtotal + tax_amount

    # Cache calculated total on session
    session.total_amount = total_amount
    await db.commit()

    return CartResponse(
        session_id=session.id,
        restaurant_id=restaurant.id,
        table_id=table.id,
        table_number=table.table_number,
        status=session.status.value,
        items=item_responses,
        diners=[DinerResponse.model_validate(d) for d in diners],
        subtotal=subtotal,
        tax_amount=tax_amount,
        total_amount=total_amount,
        currency=restaurant.currency,
        item_count=total_qty,
    )


async def add_item_to_cart(
    db: AsyncSession,
    session_id: UUID,
    diner_id: UUID,
    item_id: UUID,
    selected_modifier_option_ids: List[UUID],
    quantity: int = 1,
    special_instructions: Optional[str] = None,
) -> CartResponse:
    """
    Atomically adds an item to the shared table cart, enforcing availability,
    modifier bounds, and broadcasting the update to the table in < 2 seconds.
    (FR-M3-03, FR-M3-04, NFR-02, NFR-06)
    """
    # 1. Verify Session Status
    sess_query = select(TableSession).where(TableSession.id == session_id)
    sess_res = await db.execute(sess_query)
    session = sess_res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    if session.status == SessionStatus.SUBMITTING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order is currently being submitted by another diner. Cart is locked.",
        )
    if session.status in [SessionStatus.COMPLETED, SessionStatus.CLOSED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This dining session has ended.",
        )

    # 2. Verify Diner belongs to this session
    diner_query = select(Diner).where(Diner.id == diner_id, Diner.session_id == session_id)
    diner_res = await db.execute(diner_query)
    diner = diner_res.scalar_one_or_none()
    if not diner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Diner does not belong to this session.")

    # 3. Validate Price, 86 Availability, and Modifier Bounds (Server Authority)
    menu_item, modifier_options, unit_price = await validate_and_compute_item_price(
        db=db,
        item_id=item_id,
        selected_modifier_option_ids=selected_modifier_option_ids,
    )

    # 4. Check for Identical Existing Item for this Diner (Deduplication)
    existing_items_query = (
        select(CartItem)
        .where(
            CartItem.session_id == session_id,
            CartItem.diner_id == diner_id,
            CartItem.item_id == item_id,
            CartItem.special_instructions == (special_instructions or None),
        )
        .options(selectinload(CartItem.modifiers))
    )
    existing_res = await db.execute(existing_items_query)
    existing_items = existing_res.scalars().all()

    target_existing_item = None
    target_mod_ids_set = set(selected_modifier_option_ids)

    for ex in existing_items:
        ex_mod_ids = {m.modifier_option_id for m in ex.modifiers}
        if ex_mod_ids == target_mod_ids_set:
            target_existing_item = ex
            break

    if target_existing_item:
        target_existing_item.quantity += quantity
        target_item_id = target_existing_item.id
    else:
        new_cart_item = CartItem(
            session_id=session_id,
            item_id=item_id,
            diner_id=diner_id,
            quantity=quantity,
            special_instructions=special_instructions.strip() if special_instructions else None,
        )
        db.add(new_cart_item)
        await db.flush()
        target_item_id = new_cart_item.id

        for opt in modifier_options:
            cmod = CartItemModifier(
                cart_item_id=new_cart_item.id,
                modifier_option_id=opt.id,
                option_name_cached=opt.name,
                price_delta_cached=opt.price_delta,
            )
            db.add(cmod)
        await db.flush()

    await db.commit()

    # 5. Get authoritative cart snapshot
    cart = await get_authoritative_cart(db, session_id)

    # 6. Real-time broadcast: CART_UPDATED (< 2s)
    await session_connection_manager.publish_event(
        session_id=session_id,
        event_data={
            "event": "CART_UPDATED",
            "session_id": str(session_id),
            "action": "ITEM_ADDED",
            "actor_diner_name": diner.display_name,
            "cart": cart.model_dump(mode="json"),
        },
    )

    return cart


async def update_cart_item(
    db: AsyncSession,
    session_id: UUID,
    diner_id: UUID,
    cart_item_id: UUID,
    quantity: Optional[int] = None,
    special_instructions: Optional[str] = None,
) -> CartResponse:
    """Updates cart item quantity or cooking instructions, or removes if quantity is 0."""
    ci_query = select(CartItem).where(
        CartItem.id == cart_item_id,
        CartItem.session_id == session_id,
    )
    ci_res = await db.execute(ci_query)
    cart_item = ci_res.scalar_one_or_none()
    if not cart_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found.")

    diner_res = await db.execute(select(Diner).where(Diner.id == diner_id))
    diner = diner_res.scalar_one_or_none()
    actor_name = diner.display_name if diner else "Someone"

    if quantity is not None:
        if quantity <= 0:
            await db.delete(cart_item)
        else:
            cart_item.quantity = quantity

    if special_instructions is not None and quantity != 0:
        cart_item.special_instructions = special_instructions.strip() or None

    await db.commit()

    cart = await get_authoritative_cart(db, session_id)

    await session_connection_manager.publish_event(
        session_id=session_id,
        event_data={
            "event": "CART_UPDATED",
            "session_id": str(session_id),
            "action": "ITEM_UPDATED",
            "actor_diner_name": actor_name,
            "cart": cart.model_dump(mode="json"),
        },
    )

    return cart


async def remove_cart_item(
    db: AsyncSession,
    session_id: UUID,
    diner_id: UUID,
    cart_item_id: UUID,
) -> CartResponse:
    """Deletes an item from the collective cart."""
    ci_query = select(CartItem).where(
        CartItem.id == cart_item_id,
        CartItem.session_id == session_id,
    )
    ci_res = await db.execute(ci_query)
    cart_item = ci_res.scalar_one_or_none()
    if not cart_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found.")

    diner_res = await db.execute(select(Diner).where(Diner.id == diner_id))
    diner = diner_res.scalar_one_or_none()
    actor_name = diner.display_name if diner else "Someone"

    await db.delete(cart_item)
    await db.commit()

    cart = await get_authoritative_cart(db, session_id)

    await session_connection_manager.publish_event(
        session_id=session_id,
        event_data={
            "event": "CART_UPDATED",
            "session_id": str(session_id),
            "action": "ITEM_REMOVED",
            "actor_diner_name": actor_name,
            "cart": cart.model_dump(mode="json"),
        },
    )

    return cart


async def clear_cart(
    db: AsyncSession,
    session_id: UUID,
    diner_id: UUID,
) -> CartResponse:
    """Empties the collective cart."""
    diner_res = await db.execute(select(Diner).where(Diner.id == diner_id))
    diner = diner_res.scalar_one_or_none()
    actor_name = diner.display_name if diner else "Someone"

    del_stmt = delete(CartItem).where(CartItem.session_id == session_id)
    await db.execute(del_stmt)
    await db.commit()

    cart = await get_authoritative_cart(db, session_id)

    await session_connection_manager.publish_event(
        session_id=session_id,
        event_data={
            "event": "CART_UPDATED",
            "session_id": str(session_id),
            "action": "CART_CLEARED",
            "actor_diner_name": actor_name,
            "cart": cart.model_dump(mode="json"),
        },
    )

    return cart
