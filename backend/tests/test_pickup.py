"""Pickup at the shop: the customer collects, no rider and no delivery fee for that bill."""
from tests.conftest import checkout_body, shop_block


def place(client, world, shops, key="pickup-0000001"):
    r = client.post("/api/checkout", json=checkout_body(world, key=key, shops=shops), headers=world["auth"]["customer"])
    assert r.status_code == 201, r.text
    return r.json()


def status(client, world, order_id, to, who, code=None):
    body = {"status": to, **({"delivery_code": code} if code else {})}
    return client.post(f"/api/orders/{order_id}/status", json=body, headers=world["auth"][who])


def make_ready(client, world, order_id, who="merchant"):
    assert status(client, world, order_id, "ACCEPTED", who).status_code == 200
    assert status(client, world, order_id, "READY", who).status_code == 200


def test_pickup_only_order_has_no_delivery_fee_or_rider_job(client, world):
    d = place(client, world, [shop_block(world["shop"], [(world["items"]["atta"], 2)], fulfillment="pickup")])
    assert d["delivery_fee_paise"] == 0 and d["grand_total_paise"] == 90000 and d["cash_to_collect_paise"] == 0
    assert d["orders"][0]["fulfillment"] == "pickup"
    make_ready(client, world, d["orders"][0]["id"])
    assert client.get("/api/deliveries", headers=world["auth"]["rider"]).json() == []  # nothing for a rider to carry


def test_shop_hands_over_pickup_order_and_delivery_completes(client, world):
    d = place(client, world, [shop_block(world["shop"], [(world["items"]["atta"], 2)], fulfillment="pickup")])
    oid = d["orders"][0]["id"]
    make_ready(client, world, oid)
    assert status(client, world, oid, "DELIVERED", "merchant").status_code == 200
    assert client.get(f"/api/deliveries/{d['id']}", headers=world["auth"]["customer"]).json()["status"] == "DELIVERED"


def test_pickup_handover_checks_code_when_required(client, world):
    shops = [shop_block(world["shop"], [(world["items"]["atta"], 2)], payment_method="upi", fulfillment="pickup")]
    d = place(client, world, shops)
    assert d["delivery_code_required"] is True
    oid = d["orders"][0]["id"]
    make_ready(client, world, oid)
    assert status(client, world, oid, "DELIVERED", "merchant").status_code == 422
    assert status(client, world, oid, "DELIVERED", "merchant", d["delivery_code"]).status_code == 200


def test_mixed_cart_rider_carries_only_delivery_bills(client, world):
    shops = [
        shop_block(world["shop"], [(world["items"]["atta"], 1)], fulfillment="pickup"),     # Rs 450, customer collects
        shop_block(world["shop2"], [(world["items"]["pickle"], 2)], fulfillment="delivery"),  # Rs 300, rider brings
    ]
    d = place(client, world, shops)
    assert d["delivery_fee_paise"] == 2000
    assert d["cash_to_collect_paise"] == 32000  # only the carried cash bill + fee; the pickup bill is paid at the shop
    pickup = next(o for o in d["orders"] if o["fulfillment"] == "pickup")
    carried = next(o for o in d["orders"] if o["fulfillment"] == "delivery")
    make_ready(client, world, carried["id"], "merchant3")  # pickup bill still PLACED: must not block the rider
    assert [x["id"] for x in client.get("/api/deliveries", headers=world["auth"]["rider"]).json()] == [d["id"]]
    assert client.post(f"/api/deliveries/{d['id']}/claim", headers=world["auth"]["rider"]).status_code == 200
    done = client.post(f"/api/deliveries/{d['id']}/complete", json={}, headers=world["auth"]["rider"]).json()
    statuses = {o["id"]: o["status"] for o in done["orders"]}
    assert statuses[carried["id"]] == "DELIVERED" and statuses[pickup["id"]] == "PLACED"  # pickup bill is untouched by the rider


def test_shop_cannot_hand_over_a_delivery_bill(client, world):
    d = place(client, world, [shop_block(world["shop"], [(world["items"]["atta"], 2)])])
    oid = d["orders"][0]["id"]
    make_ready(client, world, oid)
    assert status(client, world, oid, "DELIVERED", "merchant").status_code == 409


def test_pickup_khata_bill_is_posted_when_handed_over(client, world):
    client.put(f"/api/merchant/stores/{world['shop'].id}/khata/9876543210", json={"credit_limit_paise": 200000}, headers=world["auth"]["merchant"])
    d = place(client, world, [shop_block(world["shop"], [(world["items"]["atta"], 2)], payment_method="khata", fulfillment="pickup")])
    oid = d["orders"][0]["id"]
    make_ready(client, world, oid)
    assert client.get("/api/khata", headers=world["auth"]["customer"]).json()[0]["balance_paise"] == 0
    status(client, world, oid, "DELIVERED", "merchant")
    assert client.get("/api/khata", headers=world["auth"]["customer"]).json()[0]["balance_paise"] == 90000


def test_cancelled_delivery_bill_leaves_pickup_bill_without_fee(client, world):
    shops = [shop_block(world["shop"], [(world["items"]["atta"], 1)], fulfillment="pickup"),
             shop_block(world["shop2"], [(world["items"]["pickle"], 2)])]
    d = place(client, world, shops)
    carried = next(o for o in d["orders"] if o["fulfillment"] == "delivery")
    assert status(client, world, carried["id"], "CANCELLED", "customer").status_code == 200
    got = client.get(f"/api/deliveries/{d['id']}", headers=world["auth"]["customer"]).json()
    assert got["status"] == "OPEN" and got["cash_to_collect_paise"] == 0 and got["grand_total_paise"] == 45000  # fee dropped
