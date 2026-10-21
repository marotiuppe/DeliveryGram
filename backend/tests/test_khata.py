from tests.conftest import checkout_body, shop_block

CUSTOMER_PHONE = "9876543210"


def give_khata(client, world, limit=100000, who="merchant", store="shop", phone=CUSTOMER_PHONE, enabled=True):
    r = client.put(f"/api/merchant/stores/{world[store].id}/khata/{phone}", json={"credit_limit_paise": limit, "enabled": enabled}, headers=world["auth"][who])
    assert r.status_code == 200, r.text
    return r.json()


def khata_checkout(client, world, key, qty=2, method="khata", shop="shop", item="atta", who="customer"):
    shops = [shop_block(world[shop], [(world["items"][item], qty)], payment_method=method)]
    return client.post("/api/checkout", json=checkout_body(world, key=key, shops=shops), headers=world["auth"][who])


def deliver(client, world, delivery):
    for o in delivery["orders"]:
        owner = "merchant" if o["store_id"] == world["shop"].id else "merchant3"
        client.post(f"/api/orders/{o['id']}/status", json={"status": "ACCEPTED"}, headers=world["auth"][owner])
        client.post(f"/api/orders/{o['id']}/status", json={"status": "READY"}, headers=world["auth"][owner])
    client.post(f"/api/deliveries/{delivery['id']}/claim", headers=world["auth"]["rider"])
    return client.post(f"/api/deliveries/{delivery['id']}/complete", json={"delivery_code": delivery["delivery_code"]}, headers=world["auth"]["rider"])


def my_balance(client, world, store="shop"):
    rows = client.get("/api/khata", headers=world["auth"]["customer"]).json()
    return next(r for r in rows if r["store_id"] == world[store].id)["balance_paise"]


def test_cannot_pay_by_khata_without_an_account(client, world):
    r = khata_checkout(client, world, "khata-000001")
    assert r.status_code == 409 and "khata" in r.json()["detail"]


def test_khata_order_is_posted_to_ledger_on_delivery_not_before(client, world):
    give_khata(client, world)
    d = khata_checkout(client, world, "khata-000002").json()
    assert d["cash_to_collect_paise"] == 2000  # bill is on khata; only the delivery fee is paid in cash
    assert my_balance(client, world) == 0  # nothing owed until it is delivered
    assert deliver(client, world, d).status_code == 200
    assert my_balance(client, world) == 90000
    entries = client.get(f"/api/khata/{world['shop'].id}/entries", headers=world["auth"]["customer"]).json()
    assert [(e["kind"], e["amount_paise"]) for e in entries] == [("SALE", 90000)]


def test_limit_counts_pending_khata_orders(client, world):
    give_khata(client, world, limit=100000)  # Rs 1000
    assert khata_checkout(client, world, "khata-000003", qty=2).status_code == 201  # Rs 900 pending
    over = khata_checkout(client, world, "khata-000004", qty=1)  # another Rs 450 -> Rs 1350 > Rs 1000
    assert over.status_code == 409 and "limit" in over.json()["detail"]


def test_cancelled_order_frees_the_limit(client, world):
    give_khata(client, world, limit=100000)
    d = khata_checkout(client, world, "khata-000005", qty=2).json()
    client.post(f"/api/orders/{d['orders'][0]['id']}/status", json={"status": "CANCELLED"}, headers=world["auth"]["customer"])
    assert khata_checkout(client, world, "khata-000006", qty=2).status_code == 201


def test_failed_delivery_never_reaches_the_ledger(client, world):
    give_khata(client, world)
    d = khata_checkout(client, world, "khata-000007").json()
    for o in d["orders"]:
        client.post(f"/api/orders/{o['id']}/status", json={"status": "ACCEPTED"}, headers=world["auth"]["merchant"])
        client.post(f"/api/orders/{o['id']}/status", json={"status": "READY"}, headers=world["auth"]["merchant"])
    client.post(f"/api/deliveries/{d['id']}/claim", headers=world["auth"]["rider"])
    client.post(f"/api/deliveries/{d['id']}/fail", headers=world["auth"]["rider"])
    assert my_balance(client, world) == 0


def test_payment_reduces_balance_and_cannot_exceed_it(client, world):
    acct = give_khata(client, world)
    d = khata_checkout(client, world, "khata-000008").json()
    deliver(client, world, d)
    cid, sid = acct["customer_id"], world["shop"].id
    pay = lambda amt: client.post(f"/api/merchant/stores/{sid}/khata/{cid}/entries", json={"kind": "PAYMENT", "amount_paise": amt, "note": "cash"}, headers=world["auth"]["merchant"])
    assert pay(100000).status_code == 422  # more than the Rs 900 owed
    r = pay(40000)
    assert r.status_code == 201 and r.json()["balance_paise"] == 50000
    assert my_balance(client, world) == 50000


def test_counter_sale_added_to_khata_by_shopkeeper(client, world):
    acct = give_khata(client, world)
    r = client.post(f"/api/merchant/stores/{world['shop'].id}/khata/{acct['customer_id']}/entries",
                    json={"kind": "SALE", "amount_paise": 25000, "note": "sugar at counter"}, headers=world["auth"]["merchant"])
    assert r.status_code == 201 and r.json()["balance_paise"] == 25000


def test_khata_is_per_shop(client, world):
    give_khata(client, world)  # only at Sharma Kirana
    assert khata_checkout(client, world, "khata-000009", shop="shop2", item="atta2").status_code == 409


def test_paused_khata_blocks_new_orders(client, world):
    give_khata(client, world, enabled=False)
    assert khata_checkout(client, world, "khata-000010").status_code == 409


def test_khata_and_cash_in_one_checkout(client, world):
    give_khata(client, world)
    shops = [
        shop_block(world["shop"], [(world["items"]["atta"], 1)], payment_method="khata"),   # Rs 450 on khata
        shop_block(world["shop2"], [(world["items"]["pickle"], 2)], payment_method="cod"),  # Rs 300 cash
    ]
    d = client.post("/api/checkout", json=checkout_body(world, key="khata-000011", shops=shops), headers=world["auth"]["customer"]).json()
    assert d["cash_to_collect_paise"] == 30000 + 2000  # cash bill + delivery fee; the khata bill is not collected


def test_khata_isolation_between_merchants_and_customers(client, world):
    acct = give_khata(client, world)
    sid, cid = world["shop"].id, acct["customer_id"]
    assert client.get(f"/api/merchant/stores/{sid}/khata", headers=world["auth"]["merchant3"]).status_code == 404  # other shop's owner
    assert client.get(f"/api/merchant/stores/{sid}/khata", headers=world["auth"]["customer"]).status_code == 403
    assert client.post(f"/api/merchant/stores/{sid}/khata/{cid}/entries", json={"kind": "SALE", "amount_paise": 1}, headers=world["auth"]["merchant3"]).status_code == 404
    assert client.get("/api/khata", headers=world["auth"]["customer2"]).json() == []
    assert [a["balance_paise"] for a in client.get(f"/api/merchant/stores/{sid}/khata", headers=world["auth"]["merchant"]).json()] == [0]


def test_khata_cannot_be_given_to_a_staff_phone(client, world):
    r = client.put(f"/api/merchant/stores/{world['shop'].id}/khata/9000000003", json={"credit_limit_paise": 1000}, headers=world["auth"]["merchant"])
    assert r.status_code == 409


def test_staff_phone_order_on_khata_uses_the_villagers_account(client, world):
    give_khata(client, world)
    shops = [shop_block(world["shop"], [(world["items"]["atta"], 1)], payment_method="khata")]
    r = client.post("/api/checkout", json=checkout_body(world, key="khata-000012", shops=shops, source="phone"), headers=world["auth"]["agent"])
    assert r.status_code == 201
