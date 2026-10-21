from tests.conftest import checkout_body, shop_block


def place(client, world, key="flow-0000001", who="customer", **over):
    r = client.post("/api/checkout", json=checkout_body(world, key=key, **over), headers=world["auth"][who])
    assert r.status_code in (200, 201), r.text
    return r.json()


def order_status(client, world, order_id, status, who):
    return client.post(f"/api/orders/{order_id}/status", json={"status": status}, headers=world["auth"][who])


def make_ready(client, world, d, owner="merchant"):
    for o in d["orders"]:
        assert order_status(client, world, o["id"], "ACCEPTED", owner).status_code == 200
        assert order_status(client, world, o["id"], "READY", owner).status_code == 200


def claim(client, world, d, who="rider"):
    return client.post(f"/api/deliveries/{d['id']}/claim", headers=world["auth"][who])


def complete(client, world, d, who="rider", code=None):
    return client.post(f"/api/deliveries/{d['id']}/complete", json={"delivery_code": code} if code else {}, headers=world["auth"][who])


def test_full_cod_lifecycle_needs_no_code_for_small_order(client, world):
    d = place(client, world)
    assert d["delivery_code_required"] is False  # Rs 920 COD: cash is the confirmation
    make_ready(client, world, d)
    assert claim(client, world, d).status_code == 200
    r = complete(client, world, d)
    assert r.status_code == 200
    assert r.json()["status"] == "DELIVERED" and r.json()["rider_id"] == world["users"]["rider"].id


def test_customer_sees_delivery_code_but_rider_and_merchant_do_not(client, world):
    d = place(client, world)
    assert len(d["delivery_code"]) == 4
    make_ready(client, world, d)
    assert client.get(f"/api/deliveries/{d['id']}", headers=world["auth"]["rider"]).json()["delivery_code"] is None
    assert client.get("/api/orders", headers=world["auth"]["merchant"]).status_code == 200  # orders carry no code at all
    assert "delivery_code" not in client.get(f"/api/orders/{d['orders'][0]['id']}", headers=world["auth"]["merchant"]).json()


def test_upi_order_requires_correct_delivery_code(client, world):
    shops = [shop_block(world["shop"], [(world["items"]["atta"], 2)], payment_method="upi")]
    d = place(client, world, shops=shops)
    assert d["delivery_code_required"] is True
    make_ready(client, world, d)
    claim(client, world, d)
    assert complete(client, world, d).status_code == 422
    wrong = "0000" if d["delivery_code"] != "0000" else "1111"
    assert complete(client, world, d, code=wrong).status_code == 422
    assert complete(client, world, d, code=d["delivery_code"]).status_code == 200


def test_large_cod_order_requires_code(client, world, monkeypatch):
    from app import config
    monkeypatch.setattr(config, "DELIVERY_CODE_THRESHOLD_PAISE", 50000)
    assert place(client, world)["delivery_code_required"] is True


def test_invalid_transitions_and_roles(client, world):
    o = place(client, world)["orders"][0]
    assert order_status(client, world, o["id"], "READY", "merchant").status_code == 409  # must accept first
    assert order_status(client, world, o["id"], "ACCEPTED", "customer").status_code == 403
    assert order_status(client, world, o["id"], "ACCEPTED", "merchant2").status_code == 404  # other store's owner
    assert client.post(f"/api/orders/{o['id']}/status", json={"status": "DELIVERED"}, headers=world["auth"]["rider"]).status_code == 404  # riders do not see bills


def test_rider_cannot_claim_unready_or_foreign_delivery(client, world):
    d = place(client, world)
    assert claim(client, world, d).status_code == 404  # still PLACED, not visible to riders
    make_ready(client, world, d)
    claim(client, world, d)
    assert complete(client, world, d, who="rider2").status_code == 404
    assert client.post(f"/api/deliveries/{d['id']}/complete", json={}, headers=world["auth"]["customer"]).status_code == 403


def test_customer_can_cancel_only_before_acceptance(client, world):
    d = place(client, world)
    assert order_status(client, world, d["orders"][0]["id"], "CANCELLED", "customer").status_code == 200
    d2 = place(client, world, key="flow-0000002")
    order_status(client, world, d2["orders"][0]["id"], "ACCEPTED", "merchant")
    assert order_status(client, world, d2["orders"][0]["id"], "CANCELLED", "customer").status_code == 409


def test_other_customer_cannot_view_or_cancel(client, world):
    d = place(client, world)
    assert client.get(f"/api/deliveries/{d['id']}", headers=world["auth"]["customer2"]).status_code == 404
    assert client.get(f"/api/orders/{d['orders'][0]['id']}", headers=world["auth"]["customer2"]).status_code == 404
    assert order_status(client, world, d["orders"][0]["id"], "CANCELLED", "customer2").status_code == 404


def test_prescription_order_goes_through_pharmacist_review(client, world):
    shops = [shop_block(world["pharmacy"], [(world["items"]["amox"], 1)], prescription_ref="rx/1.jpg")]
    d = place(client, world, key="flow-rx-00001", shops=shops)
    o = d["orders"][0]
    assert o["status"] == "PENDING_PRESCRIPTION_REVIEW" and d["delivery_code_required"] is True
    assert order_status(client, world, o["id"], "ACCEPTED", "merchant2").status_code == 409  # must verify first
    assert order_status(client, world, o["id"], "PLACED", "merchant").status_code == 404  # not their store
    assert order_status(client, world, o["id"], "PLACED", "merchant2").status_code == 200


def test_staff_can_place_phone_order_for_villager(client, world):
    r = client.post("/api/checkout", json=checkout_body(world, key="flow-phone-001", customer_phone="9333333333", customer_name="Bhola", source="phone"),
                    headers=world["auth"]["agent"])
    assert r.status_code == 201
    assert len(r.json()["delivery_code"]) == 4  # the agent can read it out to the customer
    assert client.post("/api/checkout", json=checkout_body(world, key="flow-phone-002"), headers=world["auth"]["rider"]).status_code == 403


def test_staff_cannot_use_a_staff_phone_as_customer(client, world):
    body = checkout_body(world, key="flow-phone-003", customer_phone="9000000003")  # rider's number
    assert client.post("/api/checkout", json=body, headers=world["auth"]["agent"]).status_code == 409


def test_idempotency_key_cannot_be_borrowed_by_another_user(client, world):
    place(client, world, key="flow-borrow-01")
    r = client.post("/api/checkout", json=checkout_body(world, key="flow-borrow-01"), headers=world["auth"]["customer2"])
    assert r.status_code == 409


def test_lists_are_scoped_by_role(client, world):
    d = place(client, world)
    assert [x["id"] for x in client.get("/api/deliveries", headers=world["auth"]["customer"]).json()] == [d["id"]]
    assert client.get("/api/deliveries", headers=world["auth"]["customer2"]).json() == []
    assert [x["id"] for x in client.get("/api/orders", headers=world["auth"]["merchant"]).json()] == [d["orders"][0]["id"]]
    assert client.get("/api/orders", headers=world["auth"]["merchant2"]).json() == []
    assert client.get("/api/deliveries", headers=world["auth"]["rider"]).json() == []  # nothing READY yet
    make_ready(client, world, d)
    assert [x["id"] for x in client.get("/api/deliveries", headers=world["auth"]["rider"]).json()] == [d["id"]]
    assert client.get("/api/orders", headers=world["auth"]["rider"]).status_code == 403


def test_merchant_sets_price_and_availability(client, world):
    h, sid = world["auth"]["merchant"], world["shop"].id
    catalog_id = world["items"]["atta"].catalog_item_id
    r = client.put(f"/api/merchant/stores/{sid}/catalog/{catalog_id}", json={"price_paise": 50000, "available": True}, headers=h)
    assert r.status_code == 200 and r.json()["price_paise"] == 50000
    item_id = r.json()["id"]
    r = client.patch(f"/api/merchant/stores/{sid}/items/{item_id}", json={"price_paise": 50000, "available": False}, headers=h)
    assert r.json()["available"] is False
    shops = [{"store_id": sid, "payment_method": "cod", "items": [{"store_item_id": item_id, "quantity": 3}]}]
    r = client.post("/api/checkout", json=checkout_body(world, key="flow-avail-001", shops=shops), headers=world["auth"]["customer"])
    assert r.status_code == 409  # now unavailable


def test_merchant_cannot_touch_other_stores_or_wrong_type(client, world):
    other_store = world["pharmacy"].id
    para = world["items"]["para"].catalog_item_id
    body = {"price_paise": 1000, "available": True}
    assert client.put(f"/api/merchant/stores/{other_store}/catalog/{para}", json=body, headers=world["auth"]["merchant"]).status_code == 404
    atta = world["items"]["atta"].catalog_item_id  # grocery item into a pharmacy
    assert client.put(f"/api/merchant/stores/{other_store}/catalog/{atta}", json=body, headers=world["auth"]["merchant2"]).status_code == 422
    assert client.put(f"/api/merchant/stores/{world['shop'].id}/catalog/{atta}", json=body, headers=world["auth"]["customer"]).status_code == 403


def test_merchant_custom_item_and_closing_store(client, world):
    h, sid = world["auth"]["merchant"], world["shop"].id
    r = client.post(f"/api/merchant/stores/{sid}/custom-items", json={"name": "Homemade jaggery", "price_paise": 15000}, headers=h)
    assert r.status_code == 201 and r.json()["name"] == "Homemade jaggery"
    assert client.patch(f"/api/merchant/stores/{sid}/open", json={"is_open": False}, headers=h).json()["is_open"] is False
    r = client.post("/api/checkout", json=checkout_body(world, key="flow-closed-01"), headers=world["auth"]["customer"])
    assert r.status_code == 409
