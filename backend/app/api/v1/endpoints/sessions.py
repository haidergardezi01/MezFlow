from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.session import TableSession, Diner
from app.models.table import Table
from app.schemas.session import (
    JoinSessionRequest,
    TableSessionResponse,
    DinerResponse,
    CartResponse,
    CartItemCreate,
    CartItemUpdate,
)
from app.schemas.order import OrderSubmitRequest, OrderResponse
from app.services.session_service import join_or_create_table_session, get_session_by_id
from app.services.cart_service import (
    get_authoritative_cart,
    add_item_to_cart,
    update_cart_item,
    remove_cart_item,
    clear_cart,
)
from app.services.order_service import submit_table_order, get_session_orders

router = APIRouter()


def _parse_diner_id(x_diner_id: Optional[str] = Header(None)) -> UUID:
    """Extracts and validates diner UUID from X-Diner-ID header."""
    if not x_diner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header 'X-Diner-ID' is required for cart mutations.",
        )
    try:
        return UUID(x_diner_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header 'X-Diner-ID' must be a valid UUID.",
        )


@router.post(
    "/join",
    response_model=TableSessionResponse,
    tags=["Collaborative Sessions"],
    summary="Join or initialize collaborative dining table session via table QR code",
)
async def join_session(
    data: JoinSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Scans physical table QR code, joins an active session or creates one,
    marks table OCCUPIED, and registers diner with display name and avatar color.
    (FR-M3-01, FR-M3-02, NFR-15)
    """
    session, diner = await join_or_create_table_session(
        db=db,
        qr_code_token=data.qr_code_token,
        display_name=data.display_name,
        client_session_id=data.client_session_id,
        avatar_color=data.avatar_color,
    )

    cart = await get_authoritative_cart(db, session.id)

    # Fetch table number
    tbl_res = await db.execute(select(Table.table_number).where(Table.id == session.table_id))
    tbl_num = tbl_res.scalar_one_or_none() or 0

    return TableSessionResponse(
        id=session.id,
        restaurant_id=session.restaurant_id,
        table_id=session.table_id,
        table_number=tbl_num,
        session_token=session.session_token,
        status=session.status.value,
        host_diner_id=session.host_diner_id,
        opened_at=session.opened_at,
        total_amount=cart.total_amount,
        current_diner=DinerResponse.model_validate(diner),
        diners=cart.diners,
        cart=cart,
    )


@router.get(
    "/{session_id}/cart",
    response_model=CartResponse,
    tags=["Shared Cart"],
    summary="Fetch authoritative shared table cart with live recalculations",
)
async def fetch_cart(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns live shared cart with per-diner item attribution and server-authoritative totals.
    (FR-M3-03, NFR-06)
    """
    return await get_authoritative_cart(db, session_id)


@router.post(
    "/{session_id}/cart/items",
    response_model=CartResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Shared Cart"],
    summary="Add customized dish to collaborative shared cart with instant broadcast",
)
async def add_item(
    session_id: UUID,
    data: CartItemCreate,
    x_diner_id: UUID = Depends(_parse_diner_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Atomically adds an item to shared cart, enforcing 86ing and modifier bounds.
    Broadcasts CART_UPDATED event to table participants in < 2s.
    (FR-M3-03, FR-M3-04, NFR-02)
    """
    return await add_item_to_cart(
        db=db,
        session_id=session_id,
        diner_id=x_diner_id,
        item_id=data.item_id,
        selected_modifier_option_ids=data.selected_modifier_option_ids,
        quantity=data.quantity,
        special_instructions=data.special_instructions,
    )


@router.patch(
    "/{session_id}/cart/items/{cart_item_id}",
    response_model=CartResponse,
    tags=["Shared Cart"],
    summary="Update cart item quantity or cooking instructions",
)
async def update_item(
    session_id: UUID,
    cart_item_id: UUID,
    data: CartItemUpdate,
    x_diner_id: UUID = Depends(_parse_diner_id),
    db: AsyncSession = Depends(get_db),
):
    """Modifies quantity or special instructions for an item in the collective cart."""
    return await update_cart_item(
        db=db,
        session_id=session_id,
        diner_id=x_diner_id,
        cart_item_id=cart_item_id,
        quantity=data.quantity,
        special_instructions=data.special_instructions,
    )


@router.delete(
    "/{session_id}/cart/items/{cart_item_id}",
    response_model=CartResponse,
    tags=["Shared Cart"],
    summary="Remove an item from the shared cart",
)
async def delete_item(
    session_id: UUID,
    cart_item_id: UUID,
    x_diner_id: UUID = Depends(_parse_diner_id),
    db: AsyncSession = Depends(get_db),
):
    """Removes an item from the collective cart and broadcasts update."""
    return await remove_cart_item(
        db=db,
        session_id=session_id,
        diner_id=x_diner_id,
        cart_item_id=cart_item_id,
    )


@router.delete(
    "/{session_id}/cart",
    response_model=CartResponse,
    tags=["Shared Cart"],
    summary="Clear entire shared cart for the table",
)
async def clear_shared_cart(
    session_id: UUID,
    x_diner_id: UUID = Depends(_parse_diner_id),
    db: AsyncSession = Depends(get_db),
):
    """Empties collective cart and broadcasts CART_CLEARED event."""
    return await clear_cart(
        db=db,
        session_id=session_id,
        diner_id=x_diner_id,
    )


@router.post(
    "/{session_id}/submit",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Order Placement"],
    summary="Submit collective cart to kitchen with single-submission lock",
)
async def submit_order(
    session_id: UUID,
    data: OrderSubmitRequest,
    x_diner_id: UUID = Depends(_parse_diner_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Converts shared cart into official kitchen order with daily order number (e.g. ORD-042).
    Enforces double-submission mutex lock preventing race conditions.
    Dispatches to Kitchen Display System (M4).
    (FR-M3-05, FR-M3-06, NFR-04, NFR-06)
    """
    return await submit_table_order(
        db=db,
        session_id=session_id,
        placed_by_diner_id=x_diner_id,
        notes=data.notes,
    )


@router.get(
    "/{session_id}/orders",
    response_model=List[OrderResponse],
    tags=["Order Placement"],
    summary="List all orders placed during this dining session",
)
async def list_orders(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Returns all orders submitted in this table session with live progress."""
    return await get_session_orders(db, session_id)
