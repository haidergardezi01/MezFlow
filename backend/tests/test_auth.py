import uuid
import pytest
from httpx import AsyncClient

from app.core.security import get_password_hash, verify_password, decode_access_token
from app.core.config import settings
from tests.conftest import DEMO_RESTAURANT_A_ID, DEMO_RESTAURANT_B_ID


@pytest.mark.asyncio
async def test_password_hashing():
    """TEST-M1-01: Verifies bcrypt hashing, salt resistance, and verification."""
    password = "SuperSecretPassword123"
    hashed = get_password_hash(password)
    assert hashed.startswith("$2b$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


@pytest.mark.asyncio
async def test_successful_staff_login_and_jwt_claims(client: AsyncClient):
    """TEST-M1-02: Tests successful password login for staff and decodes JWT claims."""
    login_payload = {
        "restaurant_id": str(DEMO_RESTAURANT_A_ID),
        "username": "manager@mezflow.com",
        "password": "manager123",
    }
    res = await client.post("/api/v1/auth/login", json=login_payload)
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "manager"
    assert data["restaurant_id"] == str(DEMO_RESTAURANT_A_ID)

    # Decode and verify token claims
    claims = decode_access_token(data["access_token"])
    assert claims is not None
    assert claims["role"] == "manager"
    assert claims["restaurant_id"] == str(DEMO_RESTAURANT_A_ID)


@pytest.mark.asyncio
async def test_login_without_restaurant_id_auto_resolves(client: AsyncClient):
    """TEST-M1-03: Staff can log in with username/password without needing hardcoded restaurant UUID."""
    login_payload = {
        "username": "manager@mezflow.com",
        "password": "manager123",
    }
    res = await client.post("/api/v1/auth/login", json=login_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "manager"
    assert data["restaurant_id"] == str(DEMO_RESTAURANT_A_ID)


@pytest.mark.asyncio
async def test_public_signup_forces_customer_role(client: AsyncClient):
    """TEST-M1-04: Public signup registers users strictly as customers, preventing role escalation."""
    unique_email = f"diner_{uuid.uuid4().hex[:6]}@example.com"
    signup_payload = {
        "restaurant_id": str(DEMO_RESTAURANT_A_ID),
        "display_name": "New Customer",
        "email": unique_email,
        "password": "securepassword123",
        "preferred_language": "en",
    }
    res = await client.post("/api/v1/auth/signup", json=signup_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["role"] == "customer"  # Enforces customer role


@pytest.mark.asyncio
async def test_manager_staff_provisioning(client: AsyncClient):
    """TEST-M1-05: Authenticated Manager can provision staff (Cashier/Kitchen)."""
    # 1. Log in as manager
    mgr_res = await client.post("/api/v1/auth/login", json={"username": "manager@mezflow.com", "password": "manager123"})
    mgr_token = mgr_res.json()["access_token"]

    # 2. Provision new cashier
    new_staff_email = f"cashier_{uuid.uuid4().hex[:6]}@mezflow.com"
    staff_payload = {
        "restaurant_id": str(DEMO_RESTAURANT_A_ID),
        "display_name": "Tariq Cashier",
        "email": new_staff_email,
        "password": "cashierpassword123",
        "role": "cashier",
        "preferred_language": "ur",
    }
    res = await client.post(
        "/api/v1/auth/staff",
        json=staff_payload,
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["role"] == "cashier"
    assert data["email"] == new_staff_email


@pytest.mark.asyncio
async def test_staff_provisioning_forbidden_for_non_manager(client: AsyncClient):
    """TEST-M1-06: Non-manager staff (Kitchen) cannot provision staff members."""
    # 1. Log in as kitchen staff
    k_res = await client.post("/api/v1/auth/login", json={"username": "kitchen@mezflow.com", "password": "kitchen123"})
    k_token = k_res.json()["access_token"]

    # 2. Attempt to provision staff -> 403 Forbidden
    res = await client.post(
        "/api/v1/auth/staff",
        json={
            "restaurant_id": str(DEMO_RESTAURANT_A_ID),
            "display_name": "Illegal Staff",
            "email": f"illegal_{uuid.uuid4().hex[:6]}@mezflow.com",
            "password": "password123",
            "role": "cashier",
            "preferred_language": "en",
        },
        headers={"Authorization": f"Bearer {k_token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_otp_flow_and_prevents_password_login(client: AsyncClient):
    """TEST-M1-07: OTP verification authenticates, and OTP-created account cannot be accessed with password."""
    phone = f"+92300{uuid.uuid4().int % 10000000:07d}"

    # 1. Request OTP
    req_res = await client.post("/api/v1/auth/request-otp", json={"destination": phone})
    assert req_res.status_code == 200
    debug_otp = req_res.json().get("debug_otp")

    # In test environment, if debug_otp is present, verify code
    if debug_otp:
        v_res = await client.post("/api/v1/auth/verify-otp", json={
            "restaurant_id": str(DEMO_RESTAURANT_A_ID),
            "destination": phone,
            "code": debug_otp,
        })
        assert v_res.status_code == 200
        token_data = v_res.json()
        assert token_data["role"] == "customer"

        # 2. Critical Security Check: Ensure this OTP account CANNOT log in via password endpoint!
        # (Verifies fixed 'otp-auto-gen-password' vulnerability is sealed)
        for attempt_pwd in ["otp-auto-gen-password", "password123", ""]:
            bad_login = await client.post("/api/v1/auth/login", json={
                "username": phone,
                "password": attempt_pwd or "dummy",
            })
            assert bad_login.status_code in (400, 401)
            # Must not allow login!
            assert "access_token" not in bad_login.json()


@pytest.mark.asyncio
async def test_rbac_audit_logs_restriction(client: AsyncClient):
    """TEST-M1-08: Audit logs are accessible to Manager, but forbidden to Kitchen staff or Customers."""
    # 1. Unauthenticated -> 401
    assert (await client.get("/api/v1/auth/audit-logs")).status_code == 401

    # 2. Kitchen staff -> 403 Forbidden
    k_res = await client.post("/api/v1/auth/login", json={"username": "kitchen@mezflow.com", "password": "kitchen123"})
    k_token = k_res.json()["access_token"]
    assert (await client.get("/api/v1/auth/audit-logs", headers={"Authorization": f"Bearer {k_token}"})).status_code == 403

    # 3. Manager -> 200 OK
    m_res = await client.post("/api/v1/auth/login", json={"username": "manager@mezflow.com", "password": "manager123"})
    m_token = m_res.json()["access_token"]
    res = await client.get("/api/v1/auth/audit-logs", headers={"Authorization": f"Bearer {m_token}"})
    assert res.status_code == 200
    assert isinstance(res.json(), list)


@pytest.mark.asyncio
async def test_cross_tenant_isolation_enforce_tenant(client: AsyncClient):
    """TEST-M1-09: Manager from Restaurant A cannot provision staff or access data of Restaurant B."""
    # 1. Manager A token
    m_res = await client.post("/api/v1/auth/login", json={"username": "manager@mezflow.com", "password": "manager123"})
    mgr_a_token = m_res.json()["access_token"]

    # 2. Attempt to provision staff in Restaurant B -> 403 Forbidden
    res = await client.post(
        "/api/v1/auth/staff",
        json={
            "restaurant_id": str(DEMO_RESTAURANT_B_ID),  # Different tenant!
            "display_name": "Infiltrator",
            "email": f"infiltrate_{uuid.uuid4().hex[:6]}@other.com",
            "password": "password123",
            "role": "manager",
            "preferred_language": "en",
        },
        headers={"Authorization": f"Bearer {mgr_a_token}"},
    )
    assert res.status_code == 403
    assert "You cannot access data of another restaurant" in res.json()["detail"]

    # 3. Attempt to fetch audit logs of Restaurant B -> 403 Forbidden
    log_res = await client.get(
        f"/api/v1/auth/audit-logs?restaurant_id={DEMO_RESTAURANT_B_ID}",
        headers={"Authorization": f"Bearer {mgr_a_token}"},
    )
    assert log_res.status_code == 403
