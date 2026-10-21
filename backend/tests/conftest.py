import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.main import app
from app.core.config import settings
from app.core.database import Base, get_db
from app.models.restaurant import Restaurant
from app.models.user import User, UserProfile, UserRole
from app.core.security import get_password_hash
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

DEMO_RESTAURANT_A_ID = uuid.UUID("52dc0556-c8c6-4131-be96-6643f9cc35b0")
DEMO_RESTAURANT_B_ID = uuid.UUID("a1111111-1111-1111-1111-111111111111")

test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Ensures database tables exist and seeds test restaurants and initial staff."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        # 1. Restaurant A
        res_a = await session.execute(select(Restaurant).where(Restaurant.id == DEMO_RESTAURANT_A_ID))
        rest_a = res_a.scalar_one_or_none()
        if not rest_a:
            rest_a = Restaurant(
                id=DEMO_RESTAURANT_A_ID,
                name="MezFlow Bistro (Test A)",
                slug="demo-bistro",
                currency="PKR",
                is_active=True,
            )
            session.add(rest_a)
            await session.flush()

        # 2. Restaurant B (For multi-tenant testing)
        res_b = await session.execute(select(Restaurant).where(Restaurant.id == DEMO_RESTAURANT_B_ID))
        rest_b = res_b.scalar_one_or_none()
        if not rest_b:
            rest_b = Restaurant(
                id=DEMO_RESTAURANT_B_ID,
                name="Other Bistro (Test B)",
                slug="other-bistro",
                currency="PKR",
                is_active=True,
            )
            session.add(rest_b)
            await session.flush()

        # 3. Manager A
        user_res = await session.execute(select(User).where(User.email == "manager@mezflow.com"))
        if not user_res.scalar_one_or_none():
            mgr_a = User(
                restaurant_id=DEMO_RESTAURANT_A_ID,
                email="manager@mezflow.com",
                hashed_password=get_password_hash("manager123"),
                role=UserRole.MANAGER,
                is_active=True,
                is_verified=True,
            )
            session.add(mgr_a)
            await session.flush()
            session.add(UserProfile(user_id=mgr_a.id, display_name="Manager A", preferred_language="en"))

        # 4. Manager B (for cross-tenant checks)
        user_b_res = await session.execute(select(User).where(User.email == "manager-b@mezflow.com"))
        if not user_b_res.scalar_one_or_none():
            mgr_b = User(
                restaurant_id=DEMO_RESTAURANT_B_ID,
                email="manager-b@mezflow.com",
                hashed_password=get_password_hash("manager123"),
                role=UserRole.MANAGER,
                is_active=True,
                is_verified=True,
            )
            session.add(mgr_b)
            await session.flush()
            session.add(UserProfile(user_id=mgr_b.id, display_name="Manager B", preferred_language="en"))

        # 5. Kitchen Staff A
        kitchen_res = await session.execute(select(User).where(User.email == "kitchen@mezflow.com"))
        if not kitchen_res.scalar_one_or_none():
            kitchen = User(
                restaurant_id=DEMO_RESTAURANT_A_ID,
                email="kitchen@mezflow.com",
                hashed_password=get_password_hash("kitchen123"),
                role=UserRole.KITCHEN_STAFF,
                is_active=True,
                is_verified=True,
            )
            session.add(kitchen)
            await session.flush()
            session.add(UserProfile(user_id=kitchen.id, display_name="Kitchen Chef", preferred_language="en"))

        await session.commit()


@pytest_asyncio.fixture
async def client():
    """Async HTTP client fixture for testing FastAPI endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
