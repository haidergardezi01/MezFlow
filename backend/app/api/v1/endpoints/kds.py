from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import require_roles
from app.models.user import User, UserRole
from app.schemas.kds import (
    KDSOrderCardResponse,
    KDSSummaryResponse,
    BumpOrderRequest,
    ItemStatusUpdateRequest,
    RecallOrderRequest,
    KDSItemResponse,
)
from app.services.kds_service import KDSService

router = APIRouter()

KDS_ROLES = [
    UserRole.KITCHEN_STAFF,
    UserRole.SERVICE_STAFF,
    UserRole.MANAGER,
]


@router.get("/orders/active", response_model=List[KDSOrderCardResponse])
async def get_active_kds_orders(
    station: str = Query("all", description="Station filter: all, grill, fry, hot_kitchen, beverage"),
    status: str = Query("all", description="Status filter: all, new, preparing, ready"),
    current_user: User = Depends(require_roles(KDS_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetches active kitchen orders for the staff user's restaurant with
    station filtering and real-time elapsed prep seconds. (FR-M4-01, FR-M4-04)
    """
    if not current_user.restaurant_id:
        raise HTTPException(status_code=400, detail="Staff user has no restaurant assigned")

    return await KDSService.get_active_orders(
        db=db,
        restaurant_id=current_user.restaurant_id,
        station_filter=station,
        status_filter=status,
    )


@router.get("/summary", response_model=KDSSummaryResponse)
async def get_kds_summary_metrics(
    current_user: User = Depends(require_roles(KDS_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns aggregated metric counts of active tickets and station loads. (FR-M4-04)
    """
    if not current_user.restaurant_id:
        raise HTTPException(status_code=400, detail="Staff user has no restaurant assigned")

    return await KDSService.get_summary_metrics(
        db=db,
        restaurant_id=current_user.restaurant_id,
    )


@router.patch("/orders/{order_id}/bump")
async def bump_kds_order(
    order_id: UUID,
    payload: BumpOrderRequest = BumpOrderRequest(),
    current_user: User = Depends(require_roles(KDS_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """
    Single-tap bump advances order to the next logical state. (FR-M4-05, FR-M5-01)
    """
    order = await KDSService.bump_order(
        db=db,
        order_id=order_id,
        user=current_user,
        target_status_str=payload.target_status,
    )
    return {
        "success": True,
        "order_id": str(order.id),
        "order_number": order.order_number,
        "display_number": order.display_number,
        "status": order.status.value,
        "message": f"Order bumped to {order.status.value}",
    }


@router.post("/orders/{order_id}/recall")
async def recall_kds_order(
    order_id: UUID,
    payload: RecallOrderRequest = RecallOrderRequest(),
    current_user: User = Depends(require_roles(KDS_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """
    Reverts an accidental bump within a 60-second grace window. (FR-M4-05, WP4.6)
    """
    order = await KDSService.recall_order(
        db=db,
        order_id=order_id,
        user=current_user,
        reason=payload.reason,
    )
    return {
        "success": True,
        "order_id": str(order.id),
        "order_number": order.order_number,
        "display_number": order.display_number,
        "status": order.status.value,
        "message": f"Order successfully recalled back to {order.status.value}",
    }


@router.patch("/orders/{order_id}/items/{item_id}/status")
async def update_kds_item_status(
    order_id: UUID,
    item_id: UUID,
    payload: ItemStatusUpdateRequest,
    current_user: User = Depends(require_roles(KDS_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """
    Line cook marks an individual dish item READY or PREPARING. (FR-M4-02, WP4.6)
    """
    item = await KDSService.update_item_status(
        db=db,
        order_id=order_id,
        item_id=item_id,
        new_status=payload.status,
        user=current_user,
    )
    return {
        "success": True,
        "item_id": str(item.id),
        "status": item.status,
        "kitchen_station": item.kitchen_station,
    }


@router.get("/orders/history", response_model=List[KDSOrderCardResponse])
async def get_kds_order_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_roles(KDS_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns recently dispatched/completed orders for shift review.
    """
    if not current_user.restaurant_id:
        raise HTTPException(status_code=400, detail="Staff user has no restaurant assigned")

    return await KDSService.get_order_history(
        db=db,
        restaurant_id=current_user.restaurant_id,
        limit=limit,
        offset=offset,
    )
