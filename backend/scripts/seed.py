import asyncio
import os
import sys
import uuid
from decimal import Decimal

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import Base
from app.models import (
    Restaurant,
    Table,
    TableStatus,
    MenuCategory,
    MenuItem,
    User,
    UserProfile,
    UserRole,
)
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def run_seed():
    print(f"Connecting to database: {settings.DATABASE_URL} ...")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as session:
        # 1. Create or get Demo Restaurant
        query = select(Restaurant).where(Restaurant.slug == "demo-bistro")
        result = await session.execute(query)
        restaurant = result.scalar_one_or_none()

        if not restaurant:
            restaurant = Restaurant(
                name="MezFlow Bistro",
                slug="demo-bistro",
                address="F-7 Markaz, Islamabad, Pakistan",
                phone="+92-51-1234567",
                currency="PKR",
                is_active=True,
            )
            session.add(restaurant)
            await session.flush()
            print(f"✓ Created Demo Restaurant: {restaurant.name} (ID: {restaurant.id})")
        else:
            print(f"✓ Found existing Demo Restaurant: {restaurant.name}")

        # 2. Seed Tables 1 through 10
        for i in range(1, 11):
            token = f"mez-t{i}"
            tbl_query = select(Table).where(Table.restaurant_id == restaurant.id, Table.table_number == i)
            tbl_res = await session.execute(tbl_query)
            if not tbl_res.scalar_one_or_none():
                table = Table(
                    restaurant_id=restaurant.id,
                    table_number=i,
                    name=f"Table {i}",
                    qr_code_token=token,
                    capacity=4 if i <= 8 else 8,
                    status=TableStatus.AVAILABLE,
                )
                session.add(table)
        print("✓ Tables 1 through 10 initialized.")

        # 3. Seed Menu Categories
        categories_data = [
            ("Starters", "Appetizers, soups, and light finger food", 1),
            ("BBQ & Grill", "Charcoal grilled kebabs, tikkas, and platters", 2),
            ("Traditional Karahi", "Freshly prepared chicken and mutton karahis", 3),
            ("Fast Food", "Burgers, crispy sandwiches, and fries", 4),
            ("Beverages", "Fresh juices, mocktails, chai, and sodas", 5),
        ]

        cat_map = {}
        for name, desc, order in categories_data:
            cat_query = select(MenuCategory).where(
                MenuCategory.restaurant_id == restaurant.id,
                MenuCategory.name == name,
            )
            cat_res = await session.execute(cat_query)
            cat = cat_res.scalar_one_or_none()
            if not cat:
                cat = MenuCategory(
                    restaurant_id=restaurant.id,
                    name=name,
                    description=desc,
                    sort_order=order,
                    is_active=True,
                )
                session.add(cat)
                await session.flush()
            cat_map[name] = cat.id
        print("✓ Menu categories initialized.")

        # 4. Seed Menu Items
        dishes = [
            {
                "category": "Starters",
                "name": "Crispy Garlic Wings",
                "desc": "Crispy chicken wings tossed in garlic herb butter",
                "price": Decimal("850.00"),
                "prep": 12,
                "station": "fry",
                "attrs": {
                    "heat_level": "mild",
                    "flavor": "garlic & savory",
                    "texture": "crispy",
                    "portion_size": "6 pieces",
                    "ingredients": ["chicken wings", "garlic", "butter", "herbs"],
                },
            },
            {
                "category": "BBQ & Grill",
                "name": "Chicken Seekh Kebab",
                "desc": "Minced chicken skewers flavored with aromatic spices and herbs",
                "price": Decimal("1150.00"),
                "prep": 18,
                "station": "grill",
                "attrs": {
                    "heat_level": "medium",
                    "flavor": "smoky & savory",
                    "texture": "succulent",
                    "portion_size": "4 skewers",
                    "ingredients": ["minced chicken", "onion", "garam masala", "mint"],
                },
            },
            {
                "category": "BBQ & Grill",
                "name": "Reshmi Malai Tikka",
                "desc": "Boneless chicken chunks marinated in rich cream, yogurt and mild spices",
                "price": Decimal("1350.00"),
                "prep": 20,
                "station": "grill",
                "attrs": {
                    "heat_level": "mild",
                    "flavor": "creamy & aromatic",
                    "texture": "melt-in-mouth tender",
                    "portion_size": "serves 1-2",
                    "ingredients": ["boneless chicken", "cream", "white pepper", "cardamom"],
                },
            },
            {
                "category": "Traditional Karahi",
                "name": "Chicken Shinwari Karahi (Full)",
                "desc": "Signature Peshawar-style chicken karahi cooked in natural fats, tomatoes and salt",
                "price": Decimal("2450.00"),
                "prep": 25,
                "station": "hot_kitchen",
                "attrs": {
                    "heat_level": "mild to medium",
                    "flavor": "pure tomato & savory chicken",
                    "texture": "rich gravy with tender bone-in chicken",
                    "portion_size": "serves 3-4",
                    "ingredients": ["bone-in chicken", "tomatoes", "green chilies", "ginger"],
                },
            },
            {
                "category": "Fast Food",
                "name": "Smash Beef Burger",
                "desc": "Double smashed beef patty with melted cheddar, pickles and house secret sauce",
                "price": Decimal("1190.00"),
                "prep": 15,
                "station": "grill",
                "attrs": {
                    "heat_level": "mild",
                    "flavor": "savory, cheesy & tangy",
                    "texture": "crispy crust with juicy center",
                    "portion_size": "serves 1 with fries",
                    "ingredients": ["prime beef patty", "cheddar cheese", "brioche bun", "pickles"],
                },
            },
            {
                "category": "Beverages",
                "name": "Mint Lemonade Cooler",
                "desc": "Refreshing crushed ice drink with fresh mint, lemon and black salt",
                "price": Decimal("420.00"),
                "prep": 5,
                "station": "beverage",
                "attrs": {
                    "heat_level": "none",
                    "flavor": "citrusy, sweet & refreshing",
                    "texture": "slushy chilled",
                    "portion_size": "450ml glass",
                    "ingredients": ["fresh lemon juice", "mint leaves", "sugar", "black salt", "soda"],
                },
            },
        ]

        for dish in dishes:
            dish_query = select(MenuItem).where(
                MenuItem.restaurant_id == restaurant.id,
                MenuItem.name == dish["name"],
            )
            dish_res = await session.execute(dish_query)
            if not dish_res.scalar_one_or_none():
                item = MenuItem(
                    restaurant_id=restaurant.id,
                    category_id=cat_map[dish["category"]],
                    name=dish["name"],
                    description=dish["desc"],
                    price=dish["price"],
                    expected_prep_minutes=dish["prep"],
                    kitchen_station=dish["station"],
                    structured_attributes=dish["attrs"],
                    is_available=True,
                )
                session.add(item)
        print("✓ Menu dishes with structured AI attributes seeded.")

        # 5. Seed Test Users
        test_users = [
            ("manager@mezflow.com", "manager123", UserRole.MANAGER, "Farooq (Manager)"),
            ("kitchen@mezflow.com", "kitchen123", UserRole.KITCHEN_STAFF, "Chef Talha"),
            ("service@mezflow.com", "service123", UserRole.SERVICE_STAFF, "Sail (Captain)"),
            ("cashier@mezflow.com", "cashier123", UserRole.CASHIER, "Khizar (Cashier)"),
            ("customer@mezflow.com", "customer123", UserRole.CUSTOMER, "Guest Diner"),
        ]

        for email, password, role, name in test_users:
            u_query = select(User).where(User.restaurant_id == restaurant.id, User.email == email)
            u_res = await session.execute(u_query)
            user = u_res.scalar_one_or_none()
            if not user:
                user = User(
                    restaurant_id=restaurant.id,
                    email=email,
                    hashed_password=pwd_context.hash(password),
                    role=role,
                    is_active=True,
                    is_verified=True,
                )
                session.add(user)
                await session.flush()

                profile = UserProfile(
                    user_id=user.id,
                    display_name=name,
                    preferred_language="en",
                    push_notifications_enabled=True,
                )
                session.add(profile)
        print("✓ Test user accounts across 5 roles initialized.")

        await session.commit()
        print("\n🎉 MezFlow database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_seed())
