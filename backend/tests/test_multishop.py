"""One cart from several shops: separate bills, one delivery, one rider, one fee, one code."""
from tests.conftest import checkout_body, shop_block


def two_shop_delivery(client, world, key="multi-0000001", **over):
    shops = [
        shop_block(world["shop"], [(world["items"]["atta"], 1)]),          # Rs 450
        shop_block(world["shop2"], [(world["items"]["pickle"], 2)]),       # Rs 300
    ]
    r = client.post("/api/checkout", json=checkout_body(world, key=key, shops=shops, **over), headers=world["auth"]["customer"])
    assert r.status_code == 201, r.text
    return r.json()


def order_status(client, world, order_id, status, who):
    return client.post(f"/api/orders/{order_id}/status", json={"status": status}, headers=world["auth"][who])


def ready_all(client, world, d):
    owners = {world["shop"].id: "merchant", world["shop2"].id: "merchant3"}
    for o in d["orders"]:
        assert order_status(client, world, o["id"], "ACCEPTED", owners[o["store_id"]]).status_code == 200
        assert order_status(client, world, o["id"], "READY", owners[o["store_id"]]).status_code == 200


def test_two_shops_make_two_bills_one_delivery_one_fee(client, world):
    d = two_shop_delivery(client, world)
    assert len(d["orders"]) == 2
    assert {o["store_id"] for o in d["orders"]} == {world["shop"].id, world["shop2"].id}
    assert sorted(o["total_paise"] for o in d["orders"]) == [30000, 45000]  # separate bills
    assert d["delivery_fee_paise"] == 2000  # charged once, not per shop
    assert d["bills_total_paise"] == 75000 and d["grand_total_paise"] == 77000
    assert len({o["delivery_id"] for o in d["orders"]}) == 1


def test_each_merchant_sees_only_their_own_bill(client, world):
    d = two_shop_delivery(client, world)
    mine = client.get("/api/orders", headers=world["auth"]["merchant"]).json()
    theirs = client.get("/api/orders", headers=world["auth"]["merchant3"]).json()
    assert [o["store_id"] for o in mine] == [world["shop"].id] and [o["store_id"] for o in theirs] == [world["shop2"].id]
    other_bill = next(o for o in d["orders"] if o["store_id"] == world["shop2"].id)
    assert client.get(f"/api/orders/{other_bill['id']}", headers=world["auth"]["merchant"]).status_code == 404
    assert client.get(f"/api/deliveries/{d['id']}", headers=world["auth"]["merchant"]).status_code == 404  # not found, not even confirmed to exist


def test_rider_cannot_take_delivery_until_every_shop_is_ready(client, world):
    d = two_shop_delivery(client, world)
    first, second = d["orders"]
    order_status(client, world, first["id"], "ACCEPTED", "merchant" if first["store_id"] == world["shop"].id else "merchant3")
    order_status(client, world, first["id"], "READY", "merchant" if first["store_id"] == world["shop"].id else "merchant3")
    assert client.get("/api/deliveries", headers=world["auth"]["rider"]).json() == []  # one shop still packing
    assert client.post(f"/api/deliveries/{d['id']}/claim", headers=world["auth"]["rider"]).status_code == 404
    ready_all_rest = "merchant" if second["store_id"] == world["shop"].id else "merchant3"
    order_status(client, world, second["id"], "ACCEPTED", ready_all_rest)
    order_status(client, world, second["id"], "READY", ready_all_rest)
    assert [x["id"] for x in client.get("/api/deliveries", headers=world["auth"]["rider"]).json()] == [d["id"]]


def test_one_rider_delivers_all_bills_with_one_handover(client, world):
    d = two_shop_delivery(client, world)
    ready_all(client, world, d)
    claim = client.post(f"/api/deliveries/{d['id']}/claim", headers=world["auth"]["rider"])
    assert claim.status_code == 200 and claim.json()["status"] == "OUT_FOR_DELIVERY"
    assert all(o["status"] == "OUT_FOR_DELIVERY" for o in claim.json()["orders"])
    assert client.post(f"/api/deliveries/{d['id']}/claim", headers=world["auth"]["rider2"]).status_code in (404, 409)  # already taken
    done = client.post(f"/api/deliveries/{d['id']}/complete", json={}, headers=world["auth"]["rider"])
    assert done.status_code == 200
    assert done.json()["status"] == "DELIVERED" and all(o["status"] == "DELIVERED" for o in done.json()["orders"])


def test_rider_sees_cash_to_collect_but_not_the_code(client, world):
    d = two_shop_delivery(client, world)
    ready_all(client, world, d)
    seen = client.get(f"/api/deliveries/{d['id']}", headers=world["auth"]["rider"]).json()
    assert seen["cash_to_collect_paise"] == 77000 and seen["delivery_code"] is None
    assert client.get(f"/api/deliveries/{d['id']}", headers=world["auth"]["customer"]).json()["delivery_code"] == d["delivery_code"]


def test_rejected_shop_does_not_block_the_rest(client, world):
    d = two_shop_delivery(client, world)
    pickle_bill = next(o for o in d["orders"] if o["store_id"] == world["shop2"].id)
    atta_bill = next(o for o in d["orders"] if o["store_id"] == world["shop"].id)
    assert order_status(client, world, pickle_bill["id"], "REJECTED", "merchant3").status_code == 200
    order_status(client, world, atta_bill["id"], "ACCEPTED", "merchant")
    order_status(client, world, atta_bill["id"], "READY", "merchant")
    got = client.get(f"/api/deliveries/{d['id']}", headers=world["auth"]["rider"]).json()
    assert got["bills_total_paise"] == 45000 and got["cash_to_collect_paise"] == 47000  # only the live bill + fee


def test_delivery_cancelled_when_every_bill_is_rejected(client, world):
    d = two_shop_delivery(client, world)
    for o in d["orders"]:
        order_status(client, world, o["id"], "REJECTED", "merchant" if o["store_id"] == world["shop"].id else "merchant3")
    got = client.get(f"/api/deliveries/{d['id']}", headers=world["auth"]["customer"]).json()
    assert got["status"] == "CANCELLED" and got["cash_to_collect_paise"] == 0


def test_same_shop_twice_in_cart_is_rejected(client, world):
    shops = [shop_block(world["shop"], [(world["items"]["atta"], 1)]), shop_block(world["shop"], [(world["items"]["out"], 1)])]
    r = client.post("/api/checkout", json=checkout_body(world, key="multi-dup-001", shops=shops), headers=world["auth"]["customer"])
    assert r.status_code == 422


def test_minimum_order_applies_to_whole_cart(client, world):
    shops = [shop_block(world["pharmacy"], [(world["items"]["para"], 1)]), shop_block(world["shop2"], [(world["items"]["pickle"], 1)])]  # 30 + 150
    r = client.post("/api/checkout", json=checkout_body(world, key="multi-min-001", shops=shops), headers=world["auth"]["customer"])
    assert r.status_code == 201  # each is small, together above Rs 100


def test_failed_delivery_marks_all_bills_failed(client, world):
    d = two_shop_delivery(client, world)
    ready_all(client, world, d)
    client.post(f"/api/deliveries/{d['id']}/claim", headers=world["auth"]["rider"])
    r = client.post(f"/api/deliveries/{d['id']}/fail", headers=world["auth"]["rider"])
    assert r.json()["status"] == "FAILED" and all(o["status"] == "FAILED" for o in r.json()["orders"])


def test_customer_cancels_one_bill_before_acceptance(client, world):
    d = two_shop_delivery(client, world)
    pickle_bill = next(o for o in d["orders"] if o["store_id"] == world["shop2"].id)
    assert order_status(client, world, pickle_bill["id"], "CANCELLED", "customer").status_code == 200
    got = client.get(f"/api/deliveries/{d['id']}", headers=world["auth"]["customer"]).json()
    assert got["bills_total_paise"] == 45000 and got["status"] == "OPEN"
