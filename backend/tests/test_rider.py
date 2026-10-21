"""What a rider needs to see to do a trip: shops to collect from, where to drop, and what cash to take."""
from tests.conftest import checkout_body, shop_block


def two_shop_ready(client, world):
    shops = [shop_block(world["shop"], [(world["items"]["atta"], 1)]), shop_block(world["shop2"], [(world["items"]["pickle"], 2)])]
    d = client.post("/api/checkout", json=checkout_body(world, key="rider-0000001", shops=shops, address_details="Blue gate"), headers=world["auth"]["customer"]).json()
    owners = {world["shop"].id: "merchant", world["shop2"].id: "merchant3"}
    for o in d["orders"]:
        for st in ("ACCEPTED", "READY"):
            client.post(f"/api/orders/{o['id']}/status", json={"status": st}, headers=world["auth"][owners[o["store_id"]]])
    return d


def test_rider_sees_pickup_shops_and_drop_address(client, world):
    d = two_shop_ready(client, world)
    job = client.get("/api/deliveries", headers=world["auth"]["rider"]).json()[0]
    assert job["id"] == d["id"]
    assert {o["store_name"] for o in job["orders"]} == {"Sharma Kirana", "Verma General"}
    assert job["village_name"] == "Rampur" and job["ward_number"] == 1
    assert job["landmark"] == "Near Hanuman temple" and job["address_details"] == "Blue gate" and job["contact_phone"] == "9876543210"
    assert job["created_at"]


def test_store_phone_is_exposed_for_pickup_calls(client, world, db):
    world["shop"].phone = "9111122222"
    db.commit()
    d = two_shop_ready(client, world)
    job = client.get(f"/api/deliveries/{d['id']}", headers=world["auth"]["rider"]).json()
    assert {o["store_phone"] for o in job["orders"]} == {"9111122222", None}


def test_rider_list_has_open_jobs_and_own_history_only(client, world):
    d = two_shop_ready(client, world)
    client.post(f"/api/deliveries/{d['id']}/claim", headers=world["auth"]["rider"])
    client.post(f"/api/deliveries/{d['id']}/complete", json={}, headers=world["auth"]["rider"])
    mine = client.get("/api/deliveries", headers=world["auth"]["rider"]).json()
    assert [(x["id"], x["status"]) for x in mine] == [(d["id"], "DELIVERED")]
    assert client.get("/api/deliveries", headers=world["auth"]["rider2"]).json() == []  # not another rider's history
    assert mine[0]["cash_to_collect_paise"] == 77000  # what this trip put in the rider's pocket
