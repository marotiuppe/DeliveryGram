from tests.conftest import checkout_body, shop_block


def post(client, world, body, who="customer"):
    return client.post("/api/checkout", json=body, headers=world["auth"][who])


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_store_types_flag_pharmacy(client, world):
    types = {t["code"]: t for t in client.get("/api/store-types").json()}
    assert types["medical"]["needs_prescription"] is True
    assert types["medical"]["safety_notice"]
    assert types["kirana"]["needs_prescription"] is False


def test_catalog_filter_and_search(client, world):
    names = [i["name"] for i in client.get("/api/catalog/items", params={"store_type": "medical"}).json()]
    assert set(names) == {"Paracetamol", "Antibiotics"}
    assert [i["name"] for i in client.get("/api/catalog/items", params={"q": "atta"}).json()] == ["Wheat Atta"]


def test_store_items_expose_rx_flag(client, world):
    items = {i["name"]: i for i in client.get(f"/api/stores/{world['pharmacy'].id}/items").json()}
    assert items["Antibiotics"]["requires_prescription"] is True
    assert items["Paracetamol"]["requires_prescription"] is False


def test_search_finds_item_in_other_shops_cheapest_first(client, world):
    hits = client.get("/api/search/items", params={"q": "atta", "village_id": world["village"].id}).json()
    assert [h["store_name"] for h in hits] == ["Verma General", "Sharma Kirana"]  # Rs 420 before Rs 450
    assert hits[0]["price_paise"] == 42000


def test_search_finds_custom_items_and_skips_unavailable_and_closed(client, world, db):
    assert [h["name"] for h in client.get("/api/search/items", params={"q": "pickle"}).json()] == ["Homemade pickle"]
    assert client.get("/api/search/items", params={"q": "sold out"}).json() == []  # unavailable
    world["shop2"].is_open = False
    db.commit()
    assert [h["store_name"] for h in client.get("/api/search/items", params={"q": "atta"}).json()] == ["Sharma Kirana"]


def test_search_scoped_to_village(client, world):
    assert client.get("/api/search/items", params={"q": "atta", "village_id": world["other"].id}).json() == []


def test_checkout_totals_use_integer_paise(client, world):
    r = post(client, world, checkout_body(world))
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["orders"][0]["subtotal_paise"] == 90000  # 2 x Rs 450
    assert d["delivery_fee_paise"] == 2000
    assert d["grand_total_paise"] == 92000 and d["cash_to_collect_paise"] == 92000
    assert d["orders"][0]["status"] == "PLACED"


def test_checkout_is_idempotent(client, world):
    first = post(client, world, checkout_body(world))
    again = post(client, world, checkout_body(world))
    assert first.status_code == 201 and again.status_code == 200
    assert first.json()["id"] == again.json()["id"]
    assert len(client.get("/api/orders", headers=world["auth"]["customer"]).json()) == 1


def test_minimum_order_enforced(client, world):
    body = checkout_body(world, key="key-00000002", shops=[shop_block(world["pharmacy"], [(world["items"]["para"], 1)])])  # Rs 30 < Rs 100
    assert post(client, world, body).status_code == 422


def test_prescription_required_for_rx_item(client, world):
    shops = [shop_block(world["pharmacy"], [(world["items"]["amox"], 1)])]
    assert post(client, world, checkout_body(world, key="key-00000003", shops=shops)).status_code == 422
    shops[0]["prescription_ref"] = "rx/abc.jpg"
    r = post(client, world, checkout_body(world, key="key-00000004", shops=shops))
    assert r.status_code == 201
    assert r.json()["orders"][0]["status"] == "PENDING_PRESCRIPTION_REVIEW"


def test_unavailable_item_rejected(client, world):
    shops = [shop_block(world["shop"], [(world["items"]["out"], 1)])]
    assert post(client, world, checkout_body(world, key="key-00000005", shops=shops)).status_code == 409


def test_item_from_other_store_rejected(client, world):
    shops = [shop_block(world["shop"], [(world["items"]["para"], 5)])]
    assert post(client, world, checkout_body(world, key="key-00000006", shops=shops)).status_code == 422


def test_ward_must_belong_to_village(client, world):
    assert post(client, world, checkout_body(world, key="key-00000007", ward_id=world["other"].wards[0].id)).status_code == 422


def test_invalid_phone_rejected(client, world):
    assert post(client, world, checkout_body(world, key="key-00000008", customer_phone="12345")).status_code == 422


def test_checkout_requires_login(client, world):
    assert client.post("/api/checkout", json=checkout_body(world)).status_code == 401


def test_villages_expose_fee_and_minimum_for_the_cart(client, world):
    v = next(x for x in client.get("/api/villages").json() if x["id"] == world["village"].id)
    assert v["delivery_fee_paise"] == 2000 and v["min_order_paise"] == 10000 and len(v["wards"]) == 2


def test_get_single_store(client, world):
    assert client.get(f"/api/stores/{world['shop'].id}").json()["name"] == "Sharma Kirana"
    assert client.get("/api/stores/9999").status_code == 404
