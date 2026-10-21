import pytest

from app import notify
from tests.conftest import checkout_body


@pytest.fixture()
def sent(monkeypatch):
    box = {}
    monkeypatch.setattr(notify, "send_otp_email", lambda to, code: box.__setitem__(to, code))
    return box


def test_orders_require_login(client, world):
    assert client.post("/api/checkout", json=checkout_body(world)).status_code == 401
    assert client.get("/api/me").status_code == 401


def test_email_otp_login_creates_customer(client, db, sent):
    assert client.post("/api/auth/otp/request", json={"email": "Asha@Example.com"}).json() == {"sent": True}
    code = sent["asha@example.com"]
    r = client.post("/api/auth/otp/verify", json={"email": "asha@example.com", "code": code})
    assert r.status_code == 200 and r.json()["role"] == "customer"
    me = client.get("/api/me", headers={"Authorization": "Bearer " + r.json()["access_token"]}).json()
    assert me["email"] == "asha@example.com"


def test_wrong_otp_rejected_and_code_single_use(client, sent):
    client.post("/api/auth/otp/request", json={"email": "a@b.co"})
    code = sent["a@b.co"]
    wrong = "000000" if code != "000000" else "111111"
    assert client.post("/api/auth/otp/verify", json={"email": "a@b.co", "code": wrong}).status_code == 400
    assert client.post("/api/auth/otp/verify", json={"email": "a@b.co", "code": code}).status_code == 200
    assert client.post("/api/auth/otp/verify", json={"email": "a@b.co", "code": code}).status_code == 400


def test_otp_locks_after_too_many_wrong_attempts(client, sent):
    client.post("/api/auth/otp/request", json={"email": "a@b.co"})
    code = sent["a@b.co"]
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        client.post("/api/auth/otp/verify", json={"email": "a@b.co", "code": wrong})
    assert client.post("/api/auth/otp/verify", json={"email": "a@b.co", "code": code}).status_code == 400


def test_otp_request_rate_limited(client, sent):
    codes = [client.post("/api/auth/otp/request", json={"email": "a@b.co"}).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]


def test_self_registration_never_grants_staff_role(client, sent):
    client.post("/api/auth/otp/request", json={"email": "admin@evil.com"})
    r = client.post("/api/auth/otp/verify", json={"email": "admin@evil.com", "code": sent["admin@evil.com"]})
    assert r.json()["role"] == "customer"


def test_assisted_registration_then_pin_login_and_forced_change(client, world):
    reg = client.post("/api/staff/customers", json={"phone": "9123456780", "name": "Kamla", "temp_pin": "1234"}, headers=world["auth"]["agent"])
    assert reg.status_code == 201
    login = client.post("/api/auth/pin/login", json={"phone": "9123456780", "pin": "1234"})
    assert login.status_code == 200 and login.json()["pin_must_change"] is True
    h = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert client.post("/api/auth/pin/change", json={"old_pin": "0000", "new_pin": "4321"}, headers=h).status_code == 403
    assert client.post("/api/auth/pin/change", json={"old_pin": "1234", "new_pin": "4321"}, headers=h).status_code == 200
    again = client.post("/api/auth/pin/login", json={"phone": "9123456780", "pin": "4321"})
    assert again.status_code == 200 and again.json()["pin_must_change"] is False


def test_pin_lockout_after_repeated_failures(client, world):
    client.post("/api/staff/customers", json={"phone": "9123456780", "temp_pin": "1234"}, headers=world["auth"]["agent"])
    for _ in range(5):
        assert client.post("/api/auth/pin/login", json={"phone": "9123456780", "pin": "9999"}).status_code == 401
    assert client.post("/api/auth/pin/login", json={"phone": "9123456780", "pin": "1234"}).status_code == 429


def test_customers_cannot_register_other_customers_or_staff(client, world):
    body = {"phone": "9123456780", "temp_pin": "1234"}
    assert client.post("/api/staff/customers", json=body, headers=world["auth"]["customer"]).status_code == 403
    staff_phone = {"phone": "9000000003", "temp_pin": "1234"}  # the rider's number
    assert client.post("/api/staff/customers", json=staff_phone, headers=world["auth"]["agent"]).status_code == 409


def test_tampered_token_rejected(client, world):
    bad = world["auth"]["admin"]["Authorization"][:-3] + "abc"
    assert client.get("/api/me", headers={"Authorization": bad}).status_code == 401


def test_admin_creates_merchant_and_store(client, world):
    h = world["auth"]["admin"]
    u = client.post("/api/admin/users", json={"role": "merchant", "phone": "9111111111", "name": "Mohan"}, headers=h)
    assert u.status_code == 201
    store = {"owner_id": u.json()["id"], "store_type_code": "kirana", "village_id": world["village"].id, "name": "Mohan Store"}
    assert client.post("/api/admin/stores", json=store, headers=h).status_code == 201
    assert client.post("/api/admin/stores", json=store, headers=world["auth"]["merchant"]).status_code == 403
    pharmacy = {**store, "store_type_code": "medical", "name": "Mohan Medical"}
    assert client.post("/api/admin/stores", json=pharmacy, headers=h).status_code == 422  # needs a drug licence


def test_staff_can_look_up_a_phone_before_registering(client, world):
    h = world["auth"]["agent"]
    assert client.get("/api/staff/customers/9123456780", headers=h).json() == {"registered": False, "name": None, "has_pin": False}
    client.post("/api/staff/customers", json={"phone": "9123456780", "name": "Kamla", "temp_pin": "1234"}, headers=h)
    assert client.get("/api/staff/customers/9123456780", headers=h).json() == {"registered": True, "name": "Kamla", "has_pin": True}


def test_lookup_rejects_bad_numbers_staff_numbers_and_customers(client, world):
    h = world["auth"]["agent"]
    assert client.get("/api/staff/customers/12345", headers=h).status_code == 422
    assert client.get("/api/staff/customers/9000000003", headers=h).status_code == 409  # the rider's number
    assert client.get("/api/staff/customers/9876543210", headers=world["auth"]["customer"]).status_code == 403
    assert client.get("/api/staff/customers/9876543210").status_code == 401
