from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_staff
from app.models.user import User
from app.schemas.order import OrderResponse, OrderStatusUpdateRequest
from app.services.order_service import get_order_detail, update_order_status

router = APIRouter()


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    tags=["Order Tracking"],
    summary="Get single order details and progress timeline",
)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Fetches details, item status, and total for a specific order."""
    return await get_order_detail(db, order_id)


@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
    tags=["Order Administration"],
    summary="Update order status (Kitchen & Staff)",
)
async def change_order_status(
    order_id: UUID,
    data: OrderStatusUpdateRequest,
    current_user: User = Depends(require_staff()),
    db: AsyncSession = Depends(get_db),
):
    """
    Advances or changes order status (NEW, CONFIRMED, PREPARING, READY, DISPATCHED, CANCELLED).
    Broadcasts ORDER_STATUS_CHANGED event to table session and KDS channel.
    (FR-M3-07, NFR-02)
    """
    return await update_order_status(
        db=db,
        order_id=order_id,
        new_status_str=data.status,
        restaurant_id=current_user.restaurant_id,
    )
