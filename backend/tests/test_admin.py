from datetime import datetime, timezone

from app.routers.admin import ist_day_start_utc
from tests.conftest import checkout_body, shop_block


def admin(world):
    return world["auth"]["admin"]


def place(client, world, key, qty=2, who="customer"):
    shops = [shop_block(world["shop"], [(world["items"]["atta"], qty)])]
    r = client.post("/api/checkout", json=checkout_body(world, key=key, shops=shops), headers=world["auth"][who])
    assert r.status_code == 201, r.text
    return r.json()


def deliver(client, world, d):
    for o in d["orders"]:
        for st in ("ACCEPTED", "READY"):
            client.post(f"/api/orders/{o['id']}/status", json={"status": st}, headers=world["auth"]["merchant"])
    client.post(f"/api/deliveries/{d['id']}/claim", headers=world["auth"]["rider"])
    client.post(f"/api/deliveries/{d['id']}/complete", json={}, headers=world["auth"]["rider"])


def test_every_admin_route_rejects_other_roles(client, world):
    for who in ("customer", "merchant", "rider", "agent"):
        h = world["auth"][who]
        assert client.get("/api/admin/stats", headers=h).status_code == 403
        assert client.get("/api/admin/users", headers=h).status_code == 403
        assert client.get("/api/admin/stores", headers=h).status_code == 403
        assert client.patch("/api/admin/store-types/1", json={"commission_bps": 0}, headers=h).status_code == 403
        assert client.post("/api/admin/villages", json={"name": "Hack"}, headers=h).status_code == 403
    assert client.get("/api/admin/stats").status_code == 401


def test_indian_day_boundary():
    # 20:00 UTC on the 20th is 01:30 IST on the 21st, so "today" started at 18:30 UTC on the 20th.
    assert ist_day_start_utc(datetime(2026, 10, 20, 20, 0, tzinfo=timezone.utc)) == datetime(2026, 10, 20, 18, 30, tzinfo=timezone.utc)
    assert ist_day_start_utc(datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc)) == datetime(2026, 10, 19, 18, 30, tzinfo=timezone.utc)


def test_stats_count_today_and_only_delivered_money(client, world):
    d1 = place(client, world, "adm-0000001")  # Rs 900 bill
    place(client, world, "adm-0000002", qty=1)  # Rs 450, stays placed
    deliver(client, world, d1)
    s = client.get("/api/admin/stats", headers=admin(world)).json()
    assert s["orders_today"] == 2
    assert s["orders_by_status"] == {"DELIVERED": 1, "PLACED": 1}
    assert s["delivered_sales_paise"] == 90000
    assert s["commission_paise"] == 4500  # kirana default 5%
    assert s["delivery_fees_paise"] == 2000
    assert s["open_deliveries"] == 1 and s["shops"] == 3 and s["riders"] == 2
    assert s["khata_outstanding_paise"] == 0


def test_stats_include_khata_dues(client, world):
    client.put(f"/api/merchant/stores/{world['shop'].id}/khata/9876543210", json={"credit_limit_paise": 200000}, headers=world["auth"]["merchant"])
    cid = client.get("/api/khata", headers=world["auth"]["customer"]).json()[0]["customer_id"]
    client.post(f"/api/merchant/stores/{world['shop'].id}/khata/{cid}/entries", json={"kind": "SALE", "amount_paise": 25000}, headers=world["auth"]["merchant"])
    assert client.get("/api/admin/stats", headers=admin(world)).json()["khata_outstanding_paise"] == 25000


def test_people_list_filter_search(client, world):
    h = admin(world)
    riders = client.get("/api/admin/users", params={"role": "rider"}, headers=h).json()
    assert {u["phone"] for u in riders} == {"9000000003", "9000000004"}
    assert [u["phone"] for u in client.get("/api/admin/users", params={"q": "9000000005"}, headers=h).json()] == ["9000000005"]
    assert client.get("/api/admin/users", params={"role": "boss"}, headers=h).status_code == 422


def test_disabled_person_is_locked_out_and_can_return(client, world):
    h, rider = admin(world), world["users"]["rider"]
    assert client.patch(f"/api/admin/users/{rider.id}", json={"active": False}, headers=h).json()["active"] is False
    assert client.get("/api/me", headers=world["auth"]["rider"]).status_code == 401  # existing token stops working
    client.patch(f"/api/admin/users/{rider.id}", json={"active": True}, headers=h)
    assert client.get("/api/me", headers=world["auth"]["rider"]).status_code == 200


def test_admin_cannot_disable_themselves(client, world):
    assert client.patch(f"/api/admin/users/{world['users']['admin'].id}", json={"active": False}, headers=admin(world)).status_code == 409


def test_reset_pin_forces_change_and_clears_lockout(client, world):
    h, cust = admin(world), world["users"]["customer"]
    client.post("/api/staff/customers", json={"phone": "9876543210", "temp_pin": "1111"}, headers=world["auth"]["agent"])
    for _ in range(5):
        client.post("/api/auth/pin/login", json={"phone": "9876543210", "pin": "9999"})
    assert client.post("/api/auth/pin/login", json={"phone": "9876543210", "pin": "1111"}).status_code == 429
    r = client.patch(f"/api/admin/users/{cust.id}", json={"temp_pin": "2468"}, headers=h)
    assert r.status_code == 200 and r.json()["has_pin"] is True
    login = client.post("/api/auth/pin/login", json={"phone": "9876543210", "pin": "2468"})
    assert login.status_code == 200 and login.json()["pin_must_change"] is True


def test_role_cannot_be_changed_through_patch(client, world):
    rider = world["users"]["rider"]
    client.patch(f"/api/admin/users/{rider.id}", json={"role": "admin"}, headers=admin(world))
    assert client.get(f"/api/admin/users?role=admin", headers=admin(world)).json()[0]["id"] == world["users"]["admin"].id
    assert len(client.get("/api/admin/users?role=admin", headers=admin(world)).json()) == 1


def test_shop_list_and_commission_override_round_trip(client, world):
    h, sid = admin(world), world["shop"].id
    shop = next(s for s in client.get("/api/admin/stores", headers=h).json() if s["id"] == sid)
    assert shop["commission_bps"] is None and shop["effective_commission_bps"] == 500 and shop["village_name"] == "Rampur" and shop["owner_phone"] == "9000000001"
    r = client.patch(f"/api/admin/stores/{sid}", json={"commission_bps": 800}, headers=h).json()
    assert r["commission_bps"] == 800 and r["effective_commission_bps"] == 800
    r = client.patch(f"/api/admin/stores/{sid}", json={"commission_bps": None}, headers=h).json()  # explicit null: back to the type rate
    assert r["commission_bps"] is None and r["effective_commission_bps"] == 500
    assert client.patch(f"/api/admin/stores/{sid}", json={"commission_bps": 9000}, headers=h).status_code == 422
    assert client.patch(f"/api/admin/stores/{sid}", json={"name": "Sharma Kirana & Co"}, headers=h).json()["name"] == "Sharma Kirana & Co"


def test_shop_override_applies_to_new_orders_only(client, world):
    first = place(client, world, "adm-rate-0001")
    client.patch(f"/api/admin/stores/{world['shop'].id}", json={"commission_bps": 1000}, headers=admin(world))
    second = place(client, world, "adm-rate-0002")
    assert first["orders"][0]["id"] != second["orders"][0]["id"]
    stats = client.get("/api/admin/stats", headers=admin(world)).json()
    assert stats["orders_today"] == 2  # sanity; commission is checked via delivered totals below
    deliver(client, world, first)
    deliver(client, world, second)
    assert client.get("/api/admin/stats", headers=admin(world)).json()["commission_paise"] == 4500 + 9000  # 5% then 10%


def test_medical_shop_keeps_its_licence(client, world):
    h, pid = admin(world), world["pharmacy"].id
    assert client.patch(f"/api/admin/stores/{pid}", json={"drug_licence_no": ""}, headers=h).status_code == 422
    assert client.patch(f"/api/admin/stores/{pid}", json={"drug_licence_no": "NEW-77"}, headers=h).json()["drug_licence_no"] == "NEW-77"
    kirana = client.patch(f"/api/admin/stores/{world['shop'].id}", json={"drug_licence_no": ""}, headers=h)
    assert kirana.status_code == 200  # only medical shops need one


def test_deactivated_shop_disappears_and_cannot_be_ordered_from(client, world):
    h, sid = admin(world), world["shop"].id
    assert client.patch(f"/api/admin/stores/{sid}", json={"active": False}, headers=h).json()["active"] is False
    assert sid not in [s["id"] for s in client.get("/api/stores").json()]
    shops = [shop_block(world["shop"], [(world["items"]["atta"], 2)])]
    assert client.post("/api/checkout", json=checkout_body(world, key="adm-gone-001", shops=shops), headers=world["auth"]["customer"]).status_code == 404
    assert sid in [s["id"] for s in client.get("/api/admin/stores", headers=h).json()]  # still visible to admin
    assert client.patch(f"/api/admin/stores/{sid}", json={"active": True}, headers=h).json()["active"] is True


def test_rates_edit_applies_to_new_orders_not_old(client, world):
    h = admin(world)
    rates = {r["code"]: r for r in client.get("/api/admin/store-types", headers=h).json()}
    assert rates["kirana"]["commission_bps"] == 500
    old = place(client, world, "adm-tax-00001")
    r = client.patch(f"/api/admin/store-types/{rates['kirana']['id']}", json={"commission_bps": 700, "tax_bps": 500}, headers=h)
    assert r.status_code == 200 and r.json()["tax_bps"] == 500
    new = place(client, world, "adm-tax-00002")
    assert old["orders"][0]["tax_paise"] == 0 and new["orders"][0]["tax_paise"] == 4500  # 5% of Rs 900, only on the new bill
    assert new["orders"][0]["total_paise"] == 94500


def test_rate_bounds(client, world):
    h = admin(world)
    for body in ({"commission_bps": 5001}, {"commission_bps": -1}, {"tax_bps": 2801}):
        assert client.patch("/api/admin/store-types/1", json=body, headers=h).status_code == 422
    assert client.patch("/api/admin/store-types/999", json={"tax_bps": 0}, headers=h).status_code == 404


def test_create_village_with_numbered_wards_and_fee(client, world):
    h = admin(world)
    r = client.post("/api/admin/villages", json={"name": "Chandpur", "district": "Demo", "delivery_fee_paise": 3000, "ward_count": 4}, headers=h)
    assert r.status_code == 201
    v = r.json()
    assert [w["number"] for w in v["wards"]] == [1, 2, 3, 4] and v["delivery_fee_paise"] == 3000
    assert client.post("/api/admin/villages", json={"name": "chandpur", "district": "Demo"}, headers=h).status_code == 409
    assert any(x["name"] == "Chandpur" for x in client.get("/api/villages").json())  # customers see it


def test_village_fee_override_and_default(client, world):
    h, vid = admin(world), world["village"].id
    assert client.patch(f"/api/admin/villages/{vid}", json={"delivery_fee_paise": 4000}, headers=h).json()["delivery_fee_paise"] == 4000
    assert place(client, world, "adm-fee-00001")["delivery_fee_paise"] == 4000
    assert client.patch(f"/api/admin/villages/{vid}", json={"delivery_fee_paise": None}, headers=h).json()["delivery_fee_paise"] == 2000  # back to default
    assert client.patch(f"/api/admin/villages/{vid}", json={"name": "Rampur Kalan"}, headers=h).json()["name"] == "Rampur Kalan"
    assert client.patch("/api/admin/villages/9999", json={"name": "Nowhere"}, headers=h).status_code == 404


def test_add_ward_and_reject_duplicate(client, world):
    h, vid = admin(world), world["village"].id
    r = client.post(f"/api/admin/villages/{vid}/wards", json={"number": 7, "name": "Mandi side"}, headers=h)
    assert r.status_code == 201 and [w["number"] for w in r.json()["wards"]] == [1, 2, 7]
    assert client.post(f"/api/admin/villages/{vid}/wards", json={"number": 7}, headers=h).status_code == 409
