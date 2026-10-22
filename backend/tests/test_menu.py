import uuid
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.menu import MenuCategory, MenuItem, ItemModifierGroup, ModifierOption
from app.models.table import Table, TableStatus
from tests.conftest import DEMO_RESTAURANT_A_ID, DEMO_RESTAURANT_B_ID, TestSessionLocal


@pytest.fixture
async def manager_a_token(client: AsyncClient) -> str:
    res = await client.post(
        "/api/v1/auth/login",
        json={"username": "manager@mezflow.com", "password": "manager123"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture
async def manager_b_token(client: AsyncClient) -> str:
    res = await client.post(
        "/api/v1/auth/login",
        json={"username": "manager-b@mezflow.com", "password": "manager123"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture
async def kitchen_a_token(client: AsyncClient) -> str:
    res = await client.post(
        "/api/v1/auth/login",
        json={"username": "kitchen@mezflow.com", "password": "kitchen123"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_table_lookup_valid_and_invalid(client: AsyncClient):
    """TEST-M2-01: Validates tabletop QR lookup returns correct table & restaurant metadata."""
    # Ensure at least 1 table exists for restaurant A
    async with TestSessionLocal() as session:
        t_res = await session.execute(
            select(Table).where(Table.restaurant_id == DEMO_RESTAURANT_A_ID).limit(1)
        )
        table = t_res.scalar_one_or_none()
        if not table:
            table = Table(
                restaurant_id=DEMO_RESTAURANT_A_ID,
                table_number=1,
                name="Table 1",
                qr_code_token="test_token_valid_12345",
                capacity=4,
                status=TableStatus.AVAILABLE,
            )
            session.add(table)
            await session.commit()
            await session.refresh(table)
        token = table.qr_code_token

    # 1. Valid Token Lookup (Public diner access)
    res = await client.get(f"/api/v1/tables/lookup/{token}")
    assert res.status_code == 200
    data = res.json()
    assert data["restaurant_id"] == str(DEMO_RESTAURANT_A_ID)
    assert data["qr_code_token"] == token
    assert "restaurant_slug" in data
    assert "currency" in data

    # 2. Invalid Token Lookup
    res_bad = await client.get("/api/v1/tables/lookup/non_existent_token_999")
    assert res_bad.status_code == 404


@pytest.mark.asyncio
async def test_public_menu_hierarchical_structure(client: AsyncClient):
    """TEST-M2-02: Public menu returns categories with dishes and structured modifiers."""
    res = await client.get(f"/api/v1/restaurants/{DEMO_RESTAURANT_A_ID}/menu")
    assert res.status_code == 200
    data = res.json()
    assert data["restaurant_id"] == str(DEMO_RESTAURANT_A_ID)
    assert data["currency"] == "PKR"
    assert "categories" in data
    assert len(data["categories"]) > 0

    first_cat = data["categories"][0]
    assert "name" in first_cat
    assert "items" in first_cat


@pytest.mark.asyncio
async def test_menu_item_detail_with_modifiers(client: AsyncClient):
    """TEST-M2-03: Fetches item details including modifier groups and options with price deltas."""
    # Find an item from public menu
    menu_res = await client.get(f"/api/v1/restaurants/{DEMO_RESTAURANT_A_ID}/menu")
    menu = menu_res.json()
    all_items = [item for cat in menu["categories"] for item in cat["items"]]
    assert len(all_items) > 0
    target_item = all_items[0]

    res = await client.get(
        f"/api/v1/restaurants/{DEMO_RESTAURANT_A_ID}/menu/items/{target_item['id']}"
    )
    assert res.status_code == 200
    detail = res.json()
    assert detail["id"] == target_item["id"]
    assert "modifier_groups" in detail
    assert "dietary_tags" in detail
    assert "kitchen_station" in detail


@pytest.mark.asyncio
async def test_menu_search_filtering(client: AsyncClient):
    """TEST-M2-04: Autocomplete text search and dietary filtering."""
    # Search for "kebab" or "wings"
    res = await client.get(
        f"/api/v1/restaurants/{DEMO_RESTAURANT_A_ID}/menu/search?q=kebab"
    )
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)


@pytest.mark.asyncio
async def test_instant_86ing_availability_toggle(
    client: AsyncClient, kitchen_a_token: str
):
    """TEST-M2-05: Kitchen staff or manager can 86 a dish with instant availability toggle."""
    # Get an item
    menu_res = await client.get(f"/api/v1/restaurants/{DEMO_RESTAURANT_A_ID}/menu")
    target_item = menu_res.json()["categories"][0]["items"][0]

    headers = {"Authorization": f"Bearer {kitchen_a_token}"}

    # 1. Toggle to Sold Out (86ed)
    patch_res = await client.patch(
        f"/api/v1/menu/items/{target_item['id']}/availability",
        json={"is_available": False},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["is_available"] is False

    # 2. Toggle back to Available
    patch_back = await client.patch(
        f"/api/v1/menu/items/{target_item['id']}/availability",
        json={"is_available": True},
        headers=headers,
    )
    assert patch_back.status_code == 200
    assert patch_back.json()["is_available"] is True


@pytest.mark.asyncio
async def test_manager_crud_categories_and_items(
    client: AsyncClient, manager_a_token: str
):
    """TEST-M2-06: Manager can create category, item, and attach modifier options."""
    headers = {"Authorization": f"Bearer {manager_a_token}"}

    # 1. Create Category
    cat_payload = {
        "name": f"Chef Specials {uuid.uuid4().hex[:4]}",
        "name_ur": "شیف کی خاص ڈشز",
        "description": "Exclusive limited time items",
        "icon_name": "Sparkles",
        "sort_order": 10,
        "is_active": True,
    }
    cat_res = await client.post(
        "/api/v1/menu/categories", json=cat_payload, headers=headers
    )
    assert cat_res.status_code == 201
    category = cat_res.json()
    cat_id = category["id"]

    # 2. Create Dish in that Category
    item_payload = {
        "category_id": cat_id,
        "name": f"Signature Lamb Chops {uuid.uuid4().hex[:4]}",
        "name_ur": "خاص لیمب چاپس",
        "description": "Tender grilled chops",
        "price": "2850.00",
        "expected_prep_minutes": 22,
        "kitchen_station": "grill",
        "dietary_tags": ["halal"],
        "sort_order": 1,
    }
    item_res = await client.post(
        "/api/v1/menu/items", json=item_payload, headers=headers
    )
    assert item_res.status_code == 201
    item = item_res.json()
    item_id = item["id"]

    # 3. Add Modifier Group (Spice Level)
    grp_payload = {
        "name": "Spice Level",
        "name_ur": "مرچ کا درجہ",
        "selection_type": "single",
        "min_selections": 1,
        "max_selections": 1,
        "is_required": True,
        "sort_order": 1,
    }
    grp_res = await client.post(
        f"/api/v1/menu/items/{item_id}/modifier-groups",
        json=grp_payload,
        headers=headers,
    )
    assert grp_res.status_code == 201
    group = grp_res.json()
    grp_id = group["id"]

    # 4. Add Modifier Option
    opt_payload = {
        "name": "Medium Hot",
        "name_ur": "درمیانی مرچ",
        "price_delta": "0.00",
        "is_default": True,
        "is_available": True,
        "sort_order": 1,
    }
    opt_res = await client.post(
        f"/api/v1/menu/modifier-groups/{grp_id}/options",
        json=opt_payload,
        headers=headers,
    )
    assert opt_res.status_code == 201
    assert opt_res.json()["name"] == "Medium Hot"


@pytest.mark.asyncio
async def test_multitenant_menu_isolation(
    client: AsyncClient, manager_b_token: str
):
    """TEST-M2-07: Multi-tenant security check (NFR-08). Manager B cannot mutate Restaurant A's items."""
    # Find Restaurant A item
    menu_res = await client.get(f"/api/v1/restaurants/{DEMO_RESTAURANT_A_ID}/menu")
    target_item_a = menu_res.json()["categories"][0]["items"][0]

    headers_b = {"Authorization": f"Bearer {manager_b_token}"}

    # Attempt to 86 Restaurant A's item as Manager B
    res = await client.patch(
        f"/api/v1/menu/items/{target_item_a['id']}/availability",
        json={"is_available": False},
        headers=headers_b,
    )
    # Must reject with 404 (item not found in tenant B) or 403
    assert res.status_code in [403, 404]


@pytest.mark.asyncio
async def test_table_qr_generation_and_regeneration(
    client: AsyncClient, manager_a_token: str
):
    """TEST-M2-08: Manager table creation, printable QR generation, and token regeneration."""
    headers = {"Authorization": f"Bearer {manager_a_token}"}

    # 1. Create a table
    tbl_num = 99
    res = await client.post(
        "/api/v1/tables",
        json={"table_number": tbl_num, "name": "VIP Booth", "capacity": 6},
        headers=headers,
    )
    # If table 99 already exists, fetch list
    if res.status_code == 400:
        list_res = await client.get("/api/v1/tables", headers=headers)
        table = [t for t in list_res.json() if t["table_number"] == tbl_num][0]
    else:
        assert res.status_code == 201
        table = res.json()

    table_id = table["id"]
    old_token = table["qr_code_token"]

    # 2. Get Printable QR stand assets
    qr_res = await client.get(f"/api/v1/tables/{table_id}/qr", headers=headers)
    assert qr_res.status_code == 200
    qr_data = qr_res.json()
    assert "svg_data" in qr_data
    assert "png_data_url" in qr_data
    assert qr_data["png_data_url"].startswith("data:image/png;base64,")

    # 3. Regenerate QR Token
    regen_res = await client.post(
        f"/api/v1/tables/{table_id}/regenerate-qr", headers=headers
    )
    assert regen_res.status_code == 200
    new_token = regen_res.json()["qr_code_token"]
    assert new_token != old_token

    # 4. Old token fails, new token works
    lookup_old = await client.get(f"/api/v1/tables/lookup/{old_token}")
    assert lookup_old.status_code == 404

    lookup_new = await client.get(f"/api/v1/tables/lookup/{new_token}")
    assert lookup_new.status_code == 200
