import asyncio
import os
import sys
import uuid
from decimal import Decimal
import secrets
import bcrypt

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
    ItemModifierGroup,
    ModifierOption,
    User,
    UserProfile,
    UserRole,
)


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


DEMO_RESTAURANT_ID = uuid.UUID("52dc0556-c8c6-4131-be96-6643f9cc35b0")


async def run_seed():
    print(f"Connecting to database: {settings.DATABASE_URL} ...")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as session:
        # 1. Create or get Demo Restaurant with fixed deterministic UUID
        query = select(Restaurant).where(Restaurant.slug == "demo-bistro")
        result = await session.execute(query)
        restaurant = result.scalar_one_or_none()

        if not restaurant:
            restaurant = Restaurant(
                id=DEMO_RESTAURANT_ID,
                name="MezFlow Bistro",
                slug="demo-bistro",
                address="F-7 Markaz, Islamabad, Pakistan",
                phone="+92-51-1234567",
                currency="PKR",
                is_active=True,
            )
            session.add(restaurant)
            await session.flush()
            print(f"[OK] Created Demo Restaurant: {restaurant.name} (ID: {restaurant.id})")
        else:
            print(f"[OK] Found existing Demo Restaurant: {restaurant.name}")

        # 2. Seed Tables 1 through 10 with cryptographically secure random tokens
        for i in range(1, 11):
            token = f"t{i}_{secrets.token_urlsafe(16)}"

            tbl_query = select(Table).where(Table.restaurant_id == restaurant.id, Table.table_number == i)
            tbl_res = await session.execute(tbl_query)
            tbl_existing = tbl_res.scalar_one_or_none()
            if not tbl_existing:
                table = Table(
                    restaurant_id=restaurant.id,
                    table_number=i,
                    name=f"Table {i}",
                    qr_code_token=token,
                    capacity=4 if i <= 8 else 8,
                    status=TableStatus.AVAILABLE,
                )
                session.add(table)
            else:
                # Update to cryptographic token if old sequential token was used
                if tbl_existing.qr_code_token.startswith("mez-t"):
                    tbl_existing.qr_code_token = token
        print("[OK] Tables 1 through 10 initialized with cryptographic QR tokens.")

        # 3. Seed Menu Categories with Urdu & Icons
        categories_data = [
            ("Starters", "اسٹارٹرز اور ایپیٹائزرز", "Appetizers, soups, and light finger food", "سوپ، ایپیٹائزر اور ہلکی پھلکی خوراک", 1, "Utensils"),
            ("BBQ & Grill", "باربی کیو اور گرل", "Charcoal grilled kebabs, tikkas, and platters", "کوئلے پر پکے لذیذ کباب، تکے اور پلیٹرز", 2, "Flame"),
            ("Traditional Karahi", "روایتی کڑاہی", "Freshly prepared chicken and mutton karahis", "تازہ تیار کردہ لذیذ دیسی چکن اور مٹن کڑاہی", 3, "Soup"),
            ("Fast Food", "فاسٹ فوڈ اور برگرز", "Burgers, crispy sandwiches, and fries", "خستہ برگر، سینڈوچ اور فرائز", 4, "Sandwich"),
            ("Beverages", "مشروبات اور کولڈ ڈرنکس", "Fresh juices, mocktails, chai, and sodas", "تازہ جوسز، موک ٹیلز، چائے اور ٹھنڈے مشروبات", 5, "Coffee"),
        ]

        cat_map = {}
        for name, name_ur, desc, desc_ur, order, icon in categories_data:
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
                    name_ur=name_ur,
                    description=desc,
                    description_ur=desc_ur,
                    icon_name=icon,
                    sort_order=order,
                    is_active=True,
                )
                session.add(cat)
                await session.flush()
            else:
                cat.name_ur = name_ur
                cat.description_ur = desc_ur
                cat.icon_name = icon
                cat.sort_order = order
            cat_map[name] = cat.id
        print("[OK] Menu categories initialized with Urdu and icons.")

        # 4. Seed Menu Items & Structured Modifiers
        dishes = [
            {
                "category": "Starters",
                "name": "Crispy Garlic Wings",
                "name_ur": "کرسپی گارلک ونگز",
                "desc": "Crispy chicken wings tossed in garlic herb butter",
                "desc_ur": "لہسن اور ہرب مکھن میں تلے ہوئے خستہ چکن ونگز",
                "price": Decimal("850.00"),
                "prep": 12,
                "station": "fry",
                "dietary": ["halal", "spicy"],
                "sort_order": 1,
                "attrs": {
                    "heat_level": "mild",
                    "flavor": "garlic & savory",
                    "texture": "crispy",
                    "portion_size": "6 pieces",
                    "ingredients": ["chicken wings", "garlic", "butter", "herbs"],
                },
                "modifiers": [
                    {
                        "name": "Spice Level",
                        "name_ur": "مرچ کا درجہ",
                        "type": "single",
                        "min": 1,
                        "max": 1,
                        "required": True,
                        "options": [
                            ("Mild Herb", "ہلکا ہرب", Decimal("0.00"), True),
                            ("Spicy Garlic", "تیز لہسن و ہری مرچ", Decimal("0.00"), False),
                            ("Ghost Pepper Fire", "گھوسٹ پیپر تیز", Decimal("50.00"), False),
                        ],
                    },
                    {
                        "name": "Extra Dips",
                        "name_ur": "اضافی سوس",
                        "type": "multiple",
                        "min": 0,
                        "max": 2,
                        "required": False,
                        "options": [
                            ("Ranch Dip", "رانچ سوس", Decimal("100.00"), False),
                            ("Garlic Mayo Dip", "گارلک مایو", Decimal("80.00"), False),
                        ],
                    },
                ],
            },
            {
                "category": "BBQ & Grill",
                "name": "Chicken Seekh Kebab",
                "name_ur": "چکن سیخ کباب",
                "desc": "Minced chicken skewers flavored with aromatic spices and herbs",
                "desc_ur": "خوشبودار مصالحہ جات اور پودینے سے تیار کردہ چکن کے سیخ کباب",
                "price": Decimal("1150.00"),
                "prep": 18,
                "station": "grill",
                "dietary": ["halal", "spicy"],
                "sort_order": 2,
                "attrs": {
                    "heat_level": "medium",
                    "flavor": "smoky & savory",
                    "texture": "succulent",
                    "portion_size": "4 skewers",
                    "ingredients": ["minced chicken", "onion", "garam masala", "mint"],
                },
                "modifiers": [
                    {
                        "name": "Portion Size",
                        "name_ur": "مقدار کا انتخاب",
                        "type": "single",
                        "min": 1,
                        "max": 1,
                        "required": True,
                        "options": [
                            ("Full (4 Skewers)", "فل (4 سیخیں)", Decimal("0.00"), True),
                            ("Half (2 Skewers)", "ہاف (2 سیخیں)", Decimal("-500.00"), False),
                        ],
                    },
                    {
                        "name": "Sides & Breads",
                        "name_ur": "روٹی اور اضافی چیزیں",
                        "type": "multiple",
                        "min": 0,
                        "max": 3,
                        "required": False,
                        "options": [
                            ("Roghni Naan", "روغنی نان", Decimal("90.00"), False),
                            ("Mint Raita", "پودینہ رائتہ", Decimal("80.00"), False),
                            ("Fresh Garden Salad", "تازہ سلاد", Decimal("60.00"), False),
                        ],
                    },
                ],
            },
            {
                "category": "BBQ & Grill",
                "name": "Reshmi Malai Tikka",
                "name_ur": "ریشمی ملائی تکہ",
                "desc": "Boneless chicken chunks marinated in rich cream, yogurt and mild spices",
                "desc_ur": "تازہ ملائی، دہی اور دھیمے مصالحوں میں تیار کردہ نرم چکن تکہ",
                "price": Decimal("1350.00"),
                "prep": 20,
                "station": "grill",
                "dietary": ["halal"],
                "sort_order": 3,
                "attrs": {
                    "heat_level": "mild",
                    "flavor": "creamy & aromatic",
                    "texture": "melt-in-mouth tender",
                    "portion_size": "serves 1-2",
                    "ingredients": ["boneless chicken", "cream", "white pepper", "cardamom"],
                },
                "modifiers": [
                    {
                        "name": "Preparation Style",
                        "name_ur": "پکانے کا انداز",
                        "type": "single",
                        "min": 1,
                        "max": 1,
                        "required": True,
                        "options": [
                            ("Extra Creamy", "اضافی ملائی دار", Decimal("0.00"), True),
                            ("Charcoal Smoky", "کوئلے کا سموکی ٹچ", Decimal("0.00"), False),
                        ],
                    },
                    {
                        "name": "Add-ons",
                        "name_ur": "اضافی لوازمات",
                        "type": "multiple",
                        "min": 0,
                        "max": 2,
                        "required": False,
                        "options": [
                            ("Garlic Naan", "گارلک نان", Decimal("110.00"), False),
                            ("Zeera Raita", "زیرہ رائتہ", Decimal("80.00"), False),
                        ],
                    },
                ],
            },
            {
                "category": "Traditional Karahi",
                "name": "Chicken Shinwari Karahi (Full)",
                "name_ur": "چکن شنواری کڑاہی (فل)",
                "desc": "Signature Peshawar-style chicken karahi cooked in natural fats, tomatoes and salt",
                "desc_ur": "روایتی پشاوری انداز میں ٹماٹر، ہری مرچ اور دیسی گھی میں پکی شنواری کڑاہی",
                "price": Decimal("2450.00"),
                "prep": 25,
                "station": "hot_kitchen",
                "dietary": ["halal"],
                "sort_order": 4,
                "attrs": {
                    "heat_level": "mild to medium",
                    "flavor": "pure tomato & savory chicken",
                    "texture": "rich gravy with tender bone-in chicken",
                    "portion_size": "serves 3-4",
                    "ingredients": ["bone-in chicken", "tomatoes", "green chilies", "ginger"],
                },
                "modifiers": [
                    {
                        "name": "Meat Style",
                        "name_ur": "گوشت کی قسم",
                        "type": "single",
                        "min": 1,
                        "max": 1,
                        "required": True,
                        "options": [
                            ("Bone-in Chicken (Standard)", "ہڈی والا چکن", Decimal("0.00"), True),
                            ("Boneless Chicken Breast", "بون لیس چکن", Decimal("350.00"), False),
                        ],
                    },
                    {
                        "name": "Cooking Medium",
                        "name_ur": "پکانے کا آئل/گھی",
                        "type": "single",
                        "min": 1,
                        "max": 1,
                        "required": True,
                        "options": [
                            ("Standard Vegetable Oil", "معیاری ویجیٹیبل آئل", Decimal("0.00"), True),
                            ("Pure Desi Ghee", "خالص دیسی گھی", Decimal("200.00"), False),
                            ("Olive Oil", "زیتون کا تیل", Decimal("250.00"), False),
                        ],
                    },
                    {
                        "name": "Garnishing & Naan",
                        "name_ur": "گارنش اور نان",
                        "type": "multiple",
                        "min": 0,
                        "max": 2,
                        "required": False,
                        "options": [
                            ("Extra Green Chilies & Julienne Ginger", "اضافی ہری مرچ و ادرک", Decimal("50.00"), False),
                            ("Kandhari Naan (2 Pcs)", "قندھاری نان (2 عدد)", Decimal("140.00"), False),
                        ],
                    },
                ],
            },
            {
                "category": "Fast Food",
                "name": "Smash Beef Burger",
                "name_ur": "سمیش بیف برگر",
                "desc": "Double smashed beef patty with melted cheddar, pickles and house secret sauce",
                "desc_ur": "ڈبل سمیشڈ بیف پیٹی، پگھلا ہوا چیڈر پنیر، اچار اور اسپیشل سوس",
                "price": Decimal("1190.00"),
                "prep": 15,
                "station": "grill",
                "dietary": ["halal"],
                "sort_order": 5,
                "attrs": {
                    "heat_level": "mild",
                    "flavor": "savory, cheesy & tangy",
                    "texture": "crispy crust with juicy center",
                    "portion_size": "serves 1 with fries",
                    "ingredients": ["prime beef patty", "cheddar cheese", "brioche bun", "pickles"],
                },
                "modifiers": [
                    {
                        "name": "Patty Stack",
                        "name_ur": "پیٹی کی تعداد",
                        "type": "single",
                        "min": 1,
                        "max": 1,
                        "required": True,
                        "options": [
                            ("Double Patty (Standard)", "ڈبل پیٹی (معیاری)", Decimal("0.00"), True),
                            ("Triple Patty Monster", "ٹرپل پیٹی", Decimal("380.00"), False),
                        ],
                    },
                    {
                        "name": "Add-ons & Toppings",
                        "name_ur": "اضافی ٹاپنگز",
                        "type": "multiple",
                        "min": 0,
                        "max": 3,
                        "required": False,
                        "options": [
                            ("Extra Melted Cheddar", "اضافی چیڈر چیز", Decimal("150.00"), False),
                            ("Beef Bacon Strips", "بیف بیکن سٹرپس", Decimal("220.00"), False),
                            ("Jalapeno Pickles", "ہلاپینیو پیپرز", Decimal("80.00"), False),
                        ],
                    },
                    {
                        "name": "Ingredient Removal",
                        "name_ur": "اجزاء نکالیں",
                        "type": "multiple",
                        "min": 0,
                        "max": 2,
                        "required": False,
                        "options": [
                            ("No Pickles", "بغیر اچار", Decimal("0.00"), False),
                            ("No House Sauce / Mayo", "بغیر مایو و سوس", Decimal("0.00"), False),
                        ],
                    },
                ],
            },
            {
                "category": "Beverages",
                "name": "Mint Lemonade Cooler",
                "name_ur": "منٹ لیمونیڈ کولر",
                "desc": "Refreshing crushed ice drink with fresh mint, lemon and black salt",
                "desc_ur": "تازہ پودینہ، لیموں کا رس اور کالا نمک سے تیار ٹھنڈا شربت",
                "price": Decimal("420.00"),
                "prep": 5,
                "station": "beverage",
                "dietary": ["vegetarian", "halal"],
                "sort_order": 6,
                "attrs": {
                    "heat_level": "none",
                    "flavor": "citrusy, sweet & refreshing",
                    "texture": "slushy chilled",
                    "portion_size": "450ml glass",
                    "ingredients": ["fresh lemon juice", "mint leaves", "sugar", "black salt", "soda"],
                },
                "modifiers": [
                    {
                        "name": "Sweetness Level",
                        "name_ur": "میٹھے کا تناسب",
                        "type": "single",
                        "min": 1,
                        "max": 1,
                        "required": True,
                        "options": [
                            ("Regular Sweet", "ریگولر میٹھا", Decimal("0.00"), True),
                            ("Less Sweet", "کم میٹھا", Decimal("0.00"), False),
                            ("Sugar-Free (Stevia)", "بغیر چینی (اسٹیویا)", Decimal("30.00"), False),
                        ],
                    },
                    {
                        "name": "Add-ins",
                        "name_ur": "اضافی اجزاء",
                        "type": "multiple",
                        "min": 0,
                        "max": 1,
                        "required": False,
                        "options": [
                            ("Extra Chia Seeds (Tukh Malanga)", "تخم بالنگا", Decimal("50.00"), False),
                        ],
                    },
                ],
            },
        ]

        for dish in dishes:
            dish_query = select(MenuItem).where(
                MenuItem.restaurant_id == restaurant.id,
                MenuItem.name == dish["name"],
            )
            dish_res = await session.execute(dish_query)
            item = dish_res.scalar_one_or_none()
            if not item:
                item = MenuItem(
                    restaurant_id=restaurant.id,
                    category_id=cat_map[dish["category"]],
                    name=dish["name"],
                    name_ur=dish["name_ur"],
                    description=dish["desc"],
                    description_ur=dish["desc_ur"],
                    price=dish["price"],
                    expected_prep_minutes=dish["prep"],
                    kitchen_station=dish["station"],
                    dietary_tags=dish["dietary"],
                    sort_order=dish["sort_order"],
                    structured_attributes=dish["attrs"],
                    is_available=True,
                )
                session.add(item)
                await session.flush()
            else:
                item.name_ur = dish["name_ur"]
                item.description_ur = dish["desc_ur"]
                item.dietary_tags = dish["dietary"]
                item.sort_order = dish["sort_order"]
                item.price = dish["price"]
                item.expected_prep_minutes = dish["prep"]
                item.kitchen_station = dish["station"]
                item.structured_attributes = dish["attrs"]
                await session.flush()

            # Seed modifier groups for this item
            for g_idx, grp_data in enumerate(dish.get("modifiers", [])):
                g_query = select(ItemModifierGroup).where(
                    ItemModifierGroup.item_id == item.id,
                    ItemModifierGroup.name == grp_data["name"],
                )
                g_res = await session.execute(g_query)
                grp = g_res.scalar_one_or_none()
                if not grp:
                    grp = ItemModifierGroup(
                        restaurant_id=restaurant.id,
                        item_id=item.id,
                        name=grp_data["name"],
                        name_ur=grp_data.get("name_ur"),
                        selection_type=grp_data["type"],
                        min_selections=grp_data["min"],
                        max_selections=grp_data["max"],
                        is_required=grp_data["required"],
                        sort_order=g_idx + 1,
                    )
                    session.add(grp)
                    await session.flush()
                else:
                    grp.name_ur = grp_data.get("name_ur")
                    grp.selection_type = grp_data["type"]
                    grp.min_selections = grp_data["min"]
                    grp.max_selections = grp_data["max"]
                    grp.is_required = grp_data["required"]
                    grp.sort_order = g_idx + 1
                    await session.flush()

                # Seed options
                for opt_idx, (opt_name, opt_ur, opt_delta, opt_def) in enumerate(grp_data["options"]):
                    opt_query = select(ModifierOption).where(
                        ModifierOption.group_id == grp.id,
                        ModifierOption.name == opt_name,
                    )
                    opt_res = await session.execute(opt_query)
                    opt = opt_res.scalar_one_or_none()
                    if not opt:
                        opt = ModifierOption(
                            group_id=grp.id,
                            name=opt_name,
                            name_ur=opt_ur,
                            price_delta=opt_delta,
                            is_default=opt_def,
                            is_available=True,
                            sort_order=opt_idx + 1,
                        )
                        session.add(opt)
                    else:
                        opt.name_ur = opt_ur
                        opt.price_delta = opt_delta
                        opt.is_default = opt_def
                        opt.sort_order = opt_idx + 1

        print("[OK] Menu dishes with Urdu translations and modifier groups seeded.")

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
                    hashed_password=get_password_hash(password),
                    role=role,
                    is_active=True,
                    is_verified=True,
                )
                session.add(user)
                await session.flush()

                profile = UserProfile(
                    user_id=user.id,
                    full_name=name,
                    preferred_language="en",
                )
                session.add(profile)

        await session.commit()
        print("[SUCCESS] All seed data populated successfully for MezFlow Bistro!")


if __name__ == "__main__":
    asyncio.run(run_seed())
