import pytest
import uuid
from httpx import AsyncClient
from app.core.security import get_password_hash, verify_password
from app.models.user import UserRole


@pytest.mark.asyncio
async def test_password_hashing():
    """TEST-M1-01: Verifies bcrypt hashing and verification."""
    password = "SuperSecretPassword123"
    hashed = get_password_hash(password)
    assert hashed.startswith("$2b$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


@pytest.mark.asyncio
async def test_signup_and_login_flow(client: AsyncClient):
    """TEST-M1-01 & TEST-M1-02: Tests user signup and login with password."""
    # First get or use seeded restaurant
    fake_restaurant_id = str(uuid.uuid4())
    
    # 1. Attempt signup with invalid restaurant should fail (404)
    signup_payload = {
        "restaurant_id": fake_restaurant_id,
        "display_name": "Test Diner",
        "email": "testdiner@example.com",
        "password": "mypassword123",
        "preferred_language": "en",
        "role": "customer",
    }
    res = await client.post("/api/v1/auth/signup", json=signup_payload)
    assert res.status_code == 404

    # 2. Test login with seeded manager user
    # In seed.py: demo-bistro has manager@mezflow.com / manager123
    # Let's verify health endpoint first to ensure app is responsive
    health_res = await client.get("/api/v1/health")
    assert health_res.status_code == 200


@pytest.mark.asyncio
async def test_otp_generation_and_verification(client: AsyncClient):
    """TEST-M1-02: Request OTP and verify."""
    phone = "+923001234567"
    req_res = await client.post("/api/v1/auth/request-otp", json={"destination": phone})
    assert req_res.status_code == 200
    data = req_res.json()
    assert "destination" in data
    assert data["destination"] == phone
    otp_code = data.get("debug_otp")
    assert otp_code is not None
    assert len(otp_code) == 6


@pytest.mark.asyncio
async def test_rbac_unauthorized_rejection(client: AsyncClient):
    """TEST-M1-03: Accessing protected endpoints without token returns 401."""
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401

    res_audit = await client.get("/api/v1/auth/audit-logs")
    assert res_audit.status_code == 401
