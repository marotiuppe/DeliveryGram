from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class StoreTypeOut(ORM):
    id: int
    code: str
    name: str
    name_hi: str | None
    needs_prescription: bool
    has_time_slots: bool
    catalog_mode: str
    safety_notice: str | None


class WardOut(ORM):
    id: int
    number: int
    name: str | None


class VillageOut(ORM):
    id: int
    name: str
    district: str | None
    state: str | None
    wards: list[WardOut]
    delivery_fee_paise: int = 0  # effective fee (village override or default), charged once per checkout
    min_order_paise: int = 0


class CatalogItemOut(ORM):
    id: int
    code: str
    store_type_id: int
    subcategory: str
    name: str
    name_hi: str | None
    unit_type: str | None
    pack_sizes: str | None
    requires_prescription: bool
    time_sensitive: bool
    image_path: str | None


class StoreOut(ORM):
    id: int
    name: str
    store_type_id: int
    village_id: int
    phone: str | None
    is_open: bool


class StoreItemOut(ORM):
    id: int
    store_id: int
    catalog_item_id: int | None
    name: str
    name_hi: str | None
    price_paise: int
    available: bool
    requires_prescription: bool
    image_path: str | None


class SearchHit(BaseModel):
    store_item_id: int
    store_id: int
    store_name: str
    name: str
    name_hi: str | None
    price_paise: int
    image_path: str | None
    requires_prescription: bool


class OrderLineIn(BaseModel):
    store_item_id: int
    quantity: int = Field(gt=0, le=100)


class ShopOrderIn(BaseModel):
    """The part of the cart that comes from one shop; becomes one order (one bill)."""
    store_id: int
    payment_method: str = Field(default="cod", pattern=r"^(cod|upi|khata)$")
    fulfillment: str = Field(default="delivery", pattern=r"^(delivery|pickup)$")
    prescription_ref: str | None = Field(default=None, max_length=300)
    items: list[OrderLineIn] = Field(min_length=1, max_length=100)


class CheckoutIn(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=64)
    customer_phone: str = Field(pattern=r"^[6-9]\d{9}$")
    customer_name: str | None = Field(default=None, max_length=80)
    village_id: int
    ward_id: int | None = None
    landmark: str = Field(min_length=2, max_length=200)
    address_details: str | None = Field(default=None, max_length=500)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    source: str = Field(default="app", pattern=r"^(app|whatsapp|phone)$")
    shops: list[ShopOrderIn] = Field(min_length=1, max_length=10)


class OrderLineOut(ORM):
    store_item_id: int
    name: str
    unit_price_paise: int
    quantity: int


class OrderOut(ORM):
    """One bill. The bill number is the order id."""
    id: int
    delivery_id: int
    status: str
    store_id: int
    store_name: str
    store_phone: str | None = None
    payment_method: str
    fulfillment: str
    prescription_ref: str | None = None  # shown to the pharmacist
    source: str
    contact_phone: str
    landmark: str
    subtotal_paise: int
    tax_paise: int
    total_paise: int
    items: list[OrderLineOut]


class DeliveryOut(ORM):
    id: int
    status: str
    created_at: datetime
    contact_phone: str
    village_id: int
    village_name: str
    ward_id: int | None
    ward_number: int | None = None
    landmark: str
    address_details: str | None
    delivery_fee_paise: int
    delivery_code_required: bool
    delivery_code: str | None = None  # only the customer, the staff who placed it, and admin see it
    rider_id: int | None
    orders: list[OrderOut]
    bills_total_paise: int = 0  # sum of the bills that are still live
    grand_total_paise: int = 0  # bills + delivery fee
    cash_to_collect_paise: int = 0  # live non-khata, non-prepaid bills + delivery fee


class StatusChange(BaseModel):
    status: str = Field(pattern=r"^(PLACED|ACCEPTED|READY|DELIVERED|REJECTED|CANCELLED)$")
    delivery_code: str | None = Field(default=None, pattern=r"^\d{4}$")  # to hand over a pickup order


class CompleteDelivery(BaseModel):
    delivery_code: str | None = Field(default=None, pattern=r"^\d{4}$")


class KhataAccountOut(ORM):
    store_id: int
    store_name: str
    customer_id: int
    customer_name: str | None
    customer_phone: str | None
    credit_limit_paise: int
    enabled: bool
    balance_paise: int  # what the customer owes this shop


class KhataEntryOut(ORM):
    id: int
    kind: str
    amount_paise: int
    order_id: int | None
    note: str | None
    created_at: datetime


class KhataAccountIn(BaseModel):
    credit_limit_paise: int = Field(ge=0, le=100_000_000)
    enabled: bool = True


class KhataEntryIn(BaseModel):
    kind: str = Field(pattern=r"^(SALE|PAYMENT)$")
    amount_paise: int = Field(gt=0, le=100_000_000)
    note: str | None = Field(default=None, max_length=200)
