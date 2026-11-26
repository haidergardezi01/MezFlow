import re
import uuid

import pytest

from app.core.config import settings
from app.services import notify
from tests.conftest import DEMO_RESTAURANT_A_ID

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


async def _new_user(client, password="Secret123!"):
    email = f"sec-{uuid.uuid4().hex[:10]}@example.com"
    res = await client.post(f"{API}/signup", json={
        "restaurant_id": str(DEMO_RESTAURANT_A_ID),
        "display_name": "Security Tester",
        "email": email,
        "password": password,
    })
    assert res.status_code == 201, res.text
    return email, password


async def _login(client, email, password):
    return await client.post(f"{API}/login", json={"username": email, "password": password})


@pytest.mark.asyncio
async def test_five_wrong_passwords_lock_the_account(client):
    email, password = await _new_user(client)
    codes = [(await _login(client, email, "wrong-pass-1")).status_code for _ in range(settings.MAX_FAILED_LOGINS)]
    assert codes[:-1] == [401] * (settings.MAX_FAILED_LOGINS - 1) and codes[-1] == 423
    locked = await _login(client, email, password)
    assert locked.status_code == 423
    assert "locked" in locked.json()["detail"]


@pytest.mark.asyncio
async def test_warning_before_lock_and_reset_on_success(client):
    email, password = await _new_user(client)
    for _ in range(settings.MAX_FAILED_LOGINS - 2):
        res = await _login(client, email, "wrong-pass-1")
    assert "attempt(s) left" in res.json()["detail"]
    assert (await _login(client, email, password)).status_code == 200
    # Counter went back to zero: the next wrong one is a plain message again
    assert "attempt(s) left" not in (await _login(client, email, "wrong-pass-1")).json()["detail"]


@pytest.mark.asyncio
async def test_unknown_email_same_message_as_wrong_password(client):
    email, _ = await _new_user(client)
    unknown = await _login(client, "nobody-at-all@example.com", "wrong-pass-1")
    wrong = await _login(client, email, "wrong-pass-1")
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]


@pytest.mark.asyncio
async def test_login_rate_limited(client):
    codes = [(await _login(client, "nobody@example.com", "x" * 8)).status_code for _ in range(31)]
    assert codes[-1] == 429


@pytest.mark.asyncio
async def test_forgot_password_emails_code_and_reset_logs_in(client, outbox):
    email, old = await _new_user(client)
    res = await client.post(f"{API}/forgot-password", json={"email": email.upper()})
    assert res.status_code == 200
    assert outbox and outbox[0]["to"] == email and outbox[0]["html"]
    assert _code(outbox[0]) in outbox[0]["subject"]
    reset = await client.post(f"{API}/reset-password", json={"email": email, "code": _code(outbox[0]), "new_password": "BrandNew456!"})
    assert reset.status_code == 200 and reset.json()["access_token"]
    assert (await _login(client, email, old)).status_code == 401
    assert (await _login(client, email, "BrandNew456!")).status_code == 200
    again = await client.post(f"{API}/reset-password", json={"email": email, "code": _code(outbox[0]), "new_password": "Another789!"})
    assert again.status_code == 400


@pytest.mark.asyncio
async def test_forgot_password_does_not_reveal_who_is_registered(client, outbox):
    email, _ = await _new_user(client)
    known = await client.post(f"{API}/forgot-password", json={"email": email})
    unknown = await client.post(f"{API}/forgot-password", json={"email": "ghost-user@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json()["message"] == unknown.json()["message"]
    assert [m["to"] for m in outbox] == [email]


@pytest.mark.asyncio
async def test_reset_code_wrong_five_times_burns_it(client, outbox):
    email, _ = await _new_user(client)
    await client.post(f"{API}/forgot-password", json={"email": email})
    code = _code(outbox[0])
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(settings.PASSWORD_RESET_MAX_ATTEMPTS):
        res = await client.post(f"{API}/reset-password", json={"email": email, "code": wrong, "new_password": "Guessing123!"})
        assert res.status_code == 400
    res = await client.post(f"{API}/reset-password", json={"email": email, "code": code, "new_password": "Guessing123!"})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_reset_unlocks_locked_account(client, outbox):
    email, _ = await _new_user(client)
    for _ in range(settings.MAX_FAILED_LOGINS):
        await _login(client, email, "wrong-pass-1")
    await client.post(f"{API}/forgot-password", json={"email": email})
    await client.post(f"{API}/reset-password", json={"email": email, "code": _code(outbox[0]), "new_password": "Unlocked123!"})
    assert (await _login(client, email, "Unlocked123!")).status_code == 200


@pytest.mark.asyncio
async def test_reset_password_needs_eight_characters(client, outbox):
    email, _ = await _new_user(client)
    await client.post(f"{API}/forgot-password", json={"email": email})
    res = await client.post(f"{API}/reset-password", json={"email": email, "code": _code(outbox[0]), "new_password": "short7!"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_manager_sets_staff_password_only_in_own_restaurant(client):
    mgr = (await _login(client, "manager@mezflow.com", "manager123")).json()["access_token"]
    hdr = {"Authorization": f"Bearer {mgr}"}
    staff = (await client.get(f"{API}/staff", headers=hdr)).json()
    chef = next(u for u in staff if u["role"] == "kitchen_staff")
    res = await client.patch(f"{API}/staff/{chef['id']}/password", json={"password": "ChefPass2026"}, headers=hdr)
    assert res.status_code == 200
    assert (await _login(client, chef["email"], "ChefPass2026")).status_code == 200
    # restore seeded demo password for other tests
    await client.patch(f"{API}/staff/{chef['id']}/password", json={"password": "kitchen123"}, headers=hdr)

    other = await client.patch(f"{API}/staff/{uuid.uuid4()}/password", json={"password": "Whatever123"}, headers=hdr)
    assert other.status_code == 404
    kitchen = (await _login(client, "kitchen@mezflow.com", "kitchen123")).json()["access_token"]
    forbidden = await client.patch(f"{API}/staff/{chef['id']}/password", json={"password": "Whatever123"}, headers={"Authorization": f"Bearer {kitchen}"})
    assert forbidden.status_code == 403
