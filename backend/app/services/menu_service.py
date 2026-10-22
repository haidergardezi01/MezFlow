from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.restaurant import Restaurant
from app.models.menu import MenuCategory, MenuItem, ItemModifierGroup, ModifierOption
from app.schemas.menu import (
    PublicMenuResponse,
    MenuCategoryResponse,
    MenuItemDetailResponse,
    ModifierGroupResponse,
    ModifierOptionResponse,
    MenuItemCreate,
    MenuItemUpdate,
    MenuCategoryCreate,
    MenuCategoryUpdate,
    ModifierGroupCreate,
    ModifierGroupUpdate,
    ModifierOptionCreate,
    ModifierOptionUpdate,
)
from app.services.realtime import menu_connection_manager


async def get_public_menu(
    db: AsyncSession, restaurant_id: UUID, lang: str = "en"
) -> PublicMenuResponse:
    """Fetches full hierarchical public menu with categories, items, and modifier groups."""
    rest_query = select(Restaurant).where(Restaurant.id == restaurant_id)
    rest_res = await db.execute(rest_query)
    restaurant = rest_res.scalar_one_or_none()

    if not restaurant or not restaurant.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found or is currently inactive.",
        )

    # Fetch active categories with nested items and modifier options
    cat_query = (
        select(MenuCategory)
        .where(
            MenuCategory.restaurant_id == restaurant_id,
            MenuCategory.is_active == True,
        )
        .options(
            selectinload(MenuCategory.items)
            .selectinload(MenuItem.modifier_groups)
            .selectinload(ItemModifierGroup.options)
        )
        .order_by(MenuCategory.sort_order, MenuCategory.name)
    )
    cat_res = await db.execute(cat_query)
    categories = cat_res.scalars().all()

    category_responses = []
    for cat in categories:
        # Sort items by sort_order
        sorted_items = sorted(cat.items, key=lambda x: (x.sort_order, x.name))
        item_responses = []
        for item in sorted_items:
            # Sort modifier groups by sort_order
            sorted_groups = sorted(item.modifier_groups, key=lambda x: (x.sort_order, x.name))
            group_responses = []
            for grp in sorted_groups:
                sorted_options = sorted(grp.options, key=lambda x: (x.sort_order, x.name))
                group_responses.append(
                    ModifierGroupResponse(
                        id=grp.id,
                        restaurant_id=grp.restaurant_id,
                        item_id=grp.item_id,
                        name=grp.name,
                        name_ur=grp.name_ur,
                        selection_type=grp.selection_type,
                        min_selections=grp.min_selections,
                        max_selections=grp.max_selections,
                        is_required=grp.is_required,
                        sort_order=grp.sort_order,
                        options=[ModifierOptionResponse.model_validate(opt) for opt in sorted_options],
                        created_at=grp.created_at,
                    )
                )

            item_responses.append(
                MenuItemDetailResponse(
                    id=item.id,
                    restaurant_id=item.restaurant_id,
                    category_id=item.category_id,
                    name=item.name,
                    name_ur=item.name_ur,
                    description=item.description,
                    description_ur=item.description_ur,
                    price=item.price,
                    image_url=item.image_url,
                    is_available=item.is_available,
                    expected_prep_minutes=item.expected_prep_minutes,
                    kitchen_station=item.kitchen_station,
                    dietary_tags=item.dietary_tags or [],
                    sort_order=item.sort_order,
                    structured_attributes=item.structured_attributes,
                    modifier_groups=group_responses,
                    created_at=item.created_at,
                )
            )

        category_responses.append(
            MenuCategoryResponse(
                id=cat.id,
                restaurant_id=cat.restaurant_id,
                name=cat.name,
                name_ur=cat.name_ur,
                description=cat.description,
                description_ur=cat.description_ur,
                icon_name=cat.icon_name,
                sort_order=cat.sort_order,
                is_active=cat.is_active,
                items=item_responses,
                created_at=cat.created_at,
            )
        )

    return PublicMenuResponse(
        restaurant_id=restaurant.id,
        restaurant_name=restaurant.name,
        currency=restaurant.currency,
        categories=category_responses,
    )


async def get_menu_item_detail(
    db: AsyncSession, restaurant_id: UUID, item_id: UUID
) -> MenuItemDetailResponse:
    """Fetches a single menu item with complete modifier groups and options."""
    query = (
        select(MenuItem)
        .where(
            MenuItem.id == item_id,
            MenuItem.restaurant_id == restaurant_id,
        )
        .options(
            selectinload(MenuItem.modifier_groups)
            .selectinload(ItemModifierGroup.options)
        )
    )
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found.",
        )

    sorted_groups = sorted(item.modifier_groups, key=lambda x: (x.sort_order, x.name))
    group_responses = []
    for grp in sorted_groups:
        sorted_options = sorted(grp.options, key=lambda x: (x.sort_order, x.name))
        group_responses.append(
            ModifierGroupResponse(
                id=grp.id,
                restaurant_id=grp.restaurant_id,
                item_id=grp.item_id,
                name=grp.name,
                name_ur=grp.name_ur,
                selection_type=grp.selection_type,
                min_selections=grp.min_selections,
                max_selections=grp.max_selections,
                is_required=grp.is_required,
                sort_order=grp.sort_order,
                options=[ModifierOptionResponse.model_validate(opt) for opt in sorted_options],
                created_at=grp.created_at,
            )
        )

    return MenuItemDetailResponse(
        id=item.id,
        restaurant_id=item.restaurant_id,
        category_id=item.category_id,
        name=item.name,
        name_ur=item.name_ur,
        description=item.description,
        description_ur=item.description_ur,
        price=item.price,
        image_url=item.image_url,
        is_available=item.is_available,
        expected_prep_minutes=item.expected_prep_minutes,
        kitchen_station=item.kitchen_station,
        dietary_tags=item.dietary_tags or [],
        sort_order=item.sort_order,
        structured_attributes=item.structured_attributes,
        modifier_groups=group_responses,
        created_at=item.created_at,
    )


async def search_menu_items(
    db: AsyncSession,
    restaurant_id: UUID,
    q: Optional[str] = None,
    category_id: Optional[UUID] = None,
    station: Optional[str] = None,
    dietary: Optional[str] = None,
) -> List[MenuItemDetailResponse]:
    """Search and filter menu items."""
    query = (
        select(MenuItem)
        .where(MenuItem.restaurant_id == restaurant_id)
        .options(
            selectinload(MenuItem.modifier_groups)
            .selectinload(ItemModifierGroup.options)
        )
    )

    if category_id:
        query = query.where(MenuItem.category_id == category_id)

    if station:
        query = query.where(MenuItem.kitchen_station == station)

    if q:
        search_pattern = f"%{q.strip()}%"
        query = query.where(
            or_(
                MenuItem.name.ilike(search_pattern),
                MenuItem.name_ur.ilike(search_pattern),
                MenuItem.description.ilike(search_pattern),
                MenuItem.description_ur.ilike(search_pattern),
            )
        )

    result = await db.execute(query)
    items = result.scalars().all()

    if dietary:
        target_tag = dietary.lower().strip()
        items = [i for i in items if i.dietary_tags and target_tag in [t.lower() for t in i.dietary_tags]]

    responses = []
    for item in items:
        sorted_groups = sorted(item.modifier_groups, key=lambda x: (x.sort_order, x.name))
        group_responses = []
        for grp in sorted_groups:
            sorted_options = sorted(grp.options, key=lambda x: (x.sort_order, x.name))
            group_responses.append(
                ModifierGroupResponse(
                    id=grp.id,
                    restaurant_id=grp.restaurant_id,
                    item_id=grp.item_id,
                    name=grp.name,
                    name_ur=grp.name_ur,
                    selection_type=grp.selection_type,
                    min_selections=grp.min_selections,
                    max_selections=grp.max_selections,
                    is_required=grp.is_required,
                    sort_order=grp.sort_order,
                    options=[ModifierOptionResponse.model_validate(opt) for opt in sorted_options],
                    created_at=grp.created_at,
                )
            )

        responses.append(
            MenuItemDetailResponse(
                id=item.id,
                restaurant_id=item.restaurant_id,
                category_id=item.category_id,
                name=item.name,
                name_ur=item.name_ur,
                description=item.description,
                description_ur=item.description_ur,
                price=item.price,
                image_url=item.image_url,
                is_available=item.is_available,
                expected_prep_minutes=item.expected_prep_minutes,
                kitchen_station=item.kitchen_station,
                dietary_tags=item.dietary_tags or [],
                sort_order=item.sort_order,
                structured_attributes=item.structured_attributes,
                modifier_groups=group_responses,
                created_at=item.created_at,
            )
        )
    return responses


async def set_item_availability(
    db: AsyncSession,
    restaurant_id: UUID,
    item_id: UUID,
    is_available: bool,
) -> MenuItem:
    """Toggles item availability (86ing) and broadcasts event in < 2 seconds."""
    query = select(MenuItem).where(
        MenuItem.id == item_id,
        MenuItem.restaurant_id == restaurant_id,
    )
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found.",
        )

    item.is_available = is_available
    await db.commit()
    await db.refresh(item)

    # Real-time WebSocket / Redis Pub/Sub broadcast (< 2s)
    await menu_connection_manager.publish_event(
        restaurant_id=restaurant_id,
        event_data={
            "event": "ITEM_AVAILABILITY_CHANGED",
            "item_id": str(item.id),
            "is_available": item.is_available,
            "name": item.name,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return item
