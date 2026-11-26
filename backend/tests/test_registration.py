import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update

from app.api.v1.endpoints import auth as auth_endpoints
from app.core.config import settings
from app.models.pending_registration import PendingRegistration
from app.services import notify
from tests.conftest import TestSessionLocal

API = "/api/v1/auth"


@pytest.fixture
def outbox(monkeypatch):
    sent = []

    async def fake_send(to, subject, body, html=None):
        sent.append({"to": to, "subject": subject, "body": body, "html": html})

    monkeypatch.setattr(notify, "send_email", fake_send)
    return sent


def _code(mail):
    return re.search(r"\b(\d{6})\b", mail["body"]).group(1)


def _form(email, password="StrongPass123"):
    return {
        "restaurant_name": "Royal Spice Grill",
        "manager_name": "Sheikh Khizar",
        "email": email,
        "password": password,
        "currency": "PKR",
        "phone": "+92 300 1234567",
        "address": "Islamabad",
    }


def _new_email():
    return f"Owner-{uuid.uuid4().hex[:8]}@Example.com"


async def _expire_cooldown(email):
    async with TestSessionLocal() as s:
        await s.execute(
            update(PendingRegistration)
            .where(PendingRegistration.email == email.lower())
            .values(last_sent_at=datetime.now(timezone.utc) - timedelta(minutes=5))
        )
        await s.commit()


@pytest.mark.asyncio
async def test_signup_with_email_code_creates_workspace_and_logs_in(client, outbox):
    email = _new_email()
    start = await client.post(f"{API}/register-restaurant/start", json=_form(email))
    assert start.status_code == 200, start.text
    assert "debug" not in str(start.json())
    assert outbox and outbox[0]["to"] == email.lower()

    # Nothing exists until the code is verified
    assert (await client.post(f"{API}/login", json={"username": email, "password": "StrongPass123"})).status_code == 401

    verify = await client.post(f"{API}/register-restaurant/verify", json={"email": email, "code": _code(outbox[0])})
    assert verify.status_code == 201, verify.text
    body = verify.json()
    assert body["role"] == "manager" and body["access_token"]
    me = await client.get(f"{API}/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200

    # Login works with any capitalisation of the e-mail
    for name in (email, email.lower(), email.upper()):
        res = await client.post(f"{API}/login", json={"username": name, "password": "StrongPass123"})
        assert res.status_code == 200, name

    # The code is single use and the e-mail is now taken
    again = await client.post(f"{API}/register-restaurant/verify", json={"email": email, "code": _code(outbox[0])})
    assert again.status_code == 400
    dup = await client.post(f"{API}/register-restaurant/start", json=_form(email))
    assert dup.status_code == 409


@pytest.mark.asyncio
async def test_existing_email_cannot_take_over_account(client, outbox):
    # Old bug: registering with an existing e-mail and any password returned that manager's token
    res = await client.post(f"{API}/register-restaurant/start", json=_form("manager@mezflow.com", "totally-wrong-pass"))
    assert res.status_code == 409
    assert not outbox
    old = await client.post(f"{API}/register-restaurant", json={**_form("manager@mezflow.com", "totally-wrong-pass")})
    assert old.status_code == 401
    assert "access_token" not in old.json()


@pytest.mark.asyncio
async def test_unverified_clerk_id_in_body_is_rejected(client):
    # Old bug: any made-up clerk_user_id in the body was trusted
    res = await client.post(
        f"{API}/register-restaurant",
        json={"restaurant_name": "Fake Clerk", "manager_name": "Fake", "email": "kitchen@mezflow.com", "clerk_user_id": "user_fake123"},
    )
    assert res.status_code == 401
    forged = await client.post(f"{API}/register-restaurant", json={}, headers={"Authorization": "Bearer not-a-real-clerk-token"})
    assert forged.status_code == 401


@pytest.mark.asyncio
async def test_wrong_code_five_times_burns_it(client, outbox):
    email = _new_email()
    await client.post(f"{API}/register-restaurant/start", json=_form(email))
    code = _code(outbox[0])
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(settings.SIGNUP_CODE_MAX_ATTEMPTS):
        res = await client.post(f"{API}/register-restaurant/verify", json={"email": email, "code": wrong})
        assert res.status_code == 400
    res = await client.post(f"{API}/register-restaurant/verify", json={"email": email, "code": code})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_expired_code_rejected(client, outbox):
    email = _new_email()
    await client.post(f"{API}/register-restaurant/start", json=_form(email))
    async with TestSessionLocal() as s:
        await s.execute(
            update(PendingRegistration)
            .where(PendingRegistration.email == email.lower())
            .values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
        )
        await s.commit()
    res = await client.post(f"{API}/register-restaurant/verify", json={"email": email, "code": _code(outbox[0])})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_resend_cooldown_and_new_code_replaces_old(client, outbox):
    email = _new_email()
    await client.post(f"{API}/register-restaurant/start", json=_form(email))
    too_soon = await client.post(f"{API}/register-restaurant/start", json=_form(email))
    assert too_soon.status_code == 429
    await _expire_cooldown(email)
    assert (await client.post(f"{API}/register-restaurant/start", json=_form(email))).status_code == 200
    first, second = _code(outbox[0]), _code(outbox[1])
    if first != second:
        old = await client.post(f"{API}/register-restaurant/verify", json={"email": email, "code": first})
        assert old.status_code == 400
    ok = await client.post(f"{API}/register-restaurant/verify", json={"email": email, "code": second})
    assert ok.status_code == 201


@pytest.mark.asyncio
async def test_short_password_rejected(client, outbox):
    res = await client.post(f"{API}/register-restaurant/start", json=_form(_new_email(), "short7!"))
    assert res.status_code in (400, 422)
    assert not outbox


@pytest.mark.asyncio
async def test_starter_team_does_not_share_manager_password(client, outbox):
    email = _new_email()
    await client.post(f"{API}/register-restaurant/start", json=_form(email))
    res = await client.post(f"{API}/register-restaurant/verify", json={"email": email, "code": _code(outbox[0])})
    token = res.json()["access_token"]
    staff = await client.get(f"{API}/staff", headers={"Authorization": f"Bearer {token}"})
    chef = next(u["email"] for u in staff.json() if u["role"] == "kitchen_staff")
    login = await client.post(f"{API}/login", json={"username": chef, "password": "StrongPass123"})
    assert login.status_code == 401


@pytest.mark.asyncio
async def test_google_signup_creates_then_reopens_workspace(client, monkeypatch):
    clerk_id = f"user_{uuid.uuid4().hex[:12]}"
    email = f"google-{uuid.uuid4().hex[:8]}@gmail.com"
    monkeypatch.setattr(auth_endpoints, "verify_clerk_session_token", lambda t: {"sub": clerk_id} if t == "good" else None)

    async def fake_email(uid):
        return email if uid == clerk_id else None

    monkeypatch.setattr(auth_endpoints, "fetch_clerk_verified_email", fake_email)
    hdr = {"Authorization": "Bearer good"}
    first = await client.post(f"{API}/register-restaurant", json={"restaurant_name": "Google Grill", "manager_name": "G User"}, headers=hdr)
    assert first.status_code == 201, first.text
    second = await client.post(f"{API}/register-restaurant", json={}, headers=hdr)
    assert second.status_code == 201
    assert second.json()["restaurant_id"] == first.json()["restaurant_id"]


@pytest.mark.asyncio
async def test_google_signin_links_to_form_account_with_same_email(client, outbox, monkeypatch):
    email = _new_email()
    await client.post(f"{API}/register-restaurant/start", json=_form(email))
    form = (await client.post(f"{API}/register-restaurant/verify", json={"email": email, "code": _code(outbox[0])})).json()

    clerk_id = f"user_{uuid.uuid4().hex[:12]}"
    monkeypatch.setattr(auth_endpoints, "verify_clerk_session_token", lambda t: {"sub": clerk_id})

    async def fake_email(uid):
        return email.lower()

    monkeypatch.setattr(auth_endpoints, "fetch_clerk_verified_email", fake_email)
    res = await client.post(f"{API}/register-restaurant", json={}, headers={"Authorization": "Bearer x"})
    assert res.status_code == 201
    assert res.json()["restaurant_id"] == form["restaurant_id"]
    assert res.json()["user_id"] == form["user_id"]
    # Password login still works after linking
    assert (await client.post(f"{API}/login", json={"username": email, "password": "StrongPass123"})).status_code == 200


@pytest.mark.asyncio
async def test_google_with_unverified_email_rejected(client, monkeypatch):
    monkeypatch.setattr(auth_endpoints, "verify_clerk_session_token", lambda t: {"sub": "user_noemail"})

    async def no_email(uid):
        return None

    monkeypatch.setattr(auth_endpoints, "fetch_clerk_verified_email", no_email)
    res = await client.post(f"{API}/register-restaurant", json={}, headers={"Authorization": "Bearer x"})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_production_without_smtp_fails_loudly(client, monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "SMTP_HOST", None)
    res = await client.post(f"{API}/register-restaurant/start", json=_form(_new_email()))
    assert res.status_code == 503
