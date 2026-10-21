"""Data model. Money is integer paise. Rates are basis points (100 bps = 1%). Timestamps are UTC."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StoreType(Base):
    """Shop kinds are config rows, not hardcoded verticals."""
    __tablename__ = "store_types"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    name_hi: Mapped[str | None] = mapped_column(String(80))
    needs_prescription: Mapped[bool] = mapped_column(Boolean, default=False)
    has_time_slots: Mapped[bool] = mapped_column(Boolean, default=False)
    catalog_mode: Mapped[str] = mapped_column(String(20), default="structured")  # structured | photo_or_text | fixed_menu
    commission_bps: Mapped[int] = mapped_column(Integer, default=500)
    tax_bps: Mapped[int] = mapped_column(Integer, default=0)
    safety_notice: Mapped[str | None] = mapped_column(Text)


class Village(Base):
    __tablename__ = "villages"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    district: Mapped[str | None] = mapped_column(String(80))
    state: Mapped[str | None] = mapped_column(String(80))
    delivery_fee_paise: Mapped[int | None] = mapped_column(Integer)  # zone fee override
    wards: Mapped[list["Ward"]] = relationship(back_populates="village")


class Ward(Base):
    __tablename__ = "wards"
    __table_args__ = (UniqueConstraint("village_id", "number"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    village_id: Mapped[int] = mapped_column(ForeignKey("villages.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    name: Mapped[str | None] = mapped_column(String(80))
    village: Mapped[Village] = relationship(back_populates="wards")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str | None] = mapped_column(String(15), unique=True)
    email: Mapped[str | None] = mapped_column(String(120), unique=True)
    name: Mapped[str | None] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(20), default="customer")  # customer | merchant | rider | agent | admin
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    pin_hash: Mapped[str | None] = mapped_column(String(200))
    pin_must_change: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_pin_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class OtpCode(Base):
    __tablename__ = "otp_codes"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(120), index=True)
    code_hash: Mapped[str] = mapped_column(String(100))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Store(Base):
    __tablename__ = "stores"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    store_type_id: Mapped[int] = mapped_column(ForeignKey("store_types.id"), index=True)
    village_id: Mapped[int] = mapped_column(ForeignKey("villages.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(15))
    address_text: Mapped[str | None] = mapped_column(Text)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    fssai_no: Mapped[str | None] = mapped_column(String(20))
    drug_licence_no: Mapped[str | None] = mapped_column(String(40))
    commission_bps: Mapped[int | None] = mapped_column(Integer)  # overrides the store type rate
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    store_type: Mapped[StoreType] = relationship()


class CatalogItem(Base):
    """Master catalog (generic items). Shops list them with their own price."""
    __tablename__ = "catalog_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True)
    store_type_id: Mapped[int] = mapped_column(ForeignKey("store_types.id"), index=True)
    subcategory: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(120))
    name_hi: Mapped[str | None] = mapped_column(String(120))
    unit_type: Mapped[str | None] = mapped_column(String(40))
    pack_sizes: Mapped[str | None] = mapped_column(String(120))
    rural_demand: Mapped[str | None] = mapped_column(String(10))
    time_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_prescription: Mapped[bool] = mapped_column(Boolean, default=False)
    image_path: Mapped[str | None] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    store_type: Mapped[StoreType] = relationship()


class StoreItem(Base):
    __tablename__ = "store_items"
    __table_args__ = (UniqueConstraint("store_id", "catalog_item_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    catalog_item_id: Mapped[int | None] = mapped_column(ForeignKey("catalog_items.id"), index=True)
    custom_name: Mapped[str | None] = mapped_column(String(120))  # for items not in the master catalog
    price_paise: Mapped[int] = mapped_column(Integer)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    catalog_item: Mapped[CatalogItem | None] = relationship()


class Delivery(Base):
    """One checkout = one delivery: one rider, one address, one delivery fee, one handover code. Holds one Order (bill) per shop."""
    __tablename__ = "deliveries"
    id: Mapped[int] = mapped_column(primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    placed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))  # customer, or staff ordering on their behalf
    contact_phone: Mapped[str] = mapped_column(String(15))
    village_id: Mapped[int] = mapped_column(ForeignKey("villages.id"))
    ward_id: Mapped[int | None] = mapped_column(ForeignKey("wards.id"))
    landmark: Mapped[str] = mapped_column(String(200))
    address_details: Mapped[str | None] = mapped_column(Text)
    lat: Mapped[float | None] = mapped_column()
    lon: Mapped[float | None] = mapped_column()
    delivery_fee_paise: Mapped[int] = mapped_column(Integer)  # charged once, not per shop
    delivery_code: Mapped[str] = mapped_column(String(4))
    delivery_code_required: Mapped[bool] = mapped_column(Boolean, default=False)
    rider_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True)  # OPEN | OUT_FOR_DELIVERY | DELIVERED | FAILED | CANCELLED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    orders: Mapped[list["Order"]] = relationship(back_populates="delivery")
    village: Mapped[Village] = relationship()
    ward: Mapped[Ward | None] = relationship()

    @property
    def village_name(self) -> str:
        return self.village.name

    @property
    def ward_number(self) -> int | None:
        return self.ward.number if self.ward else None


class Order(Base):
    """One shop's part of a delivery: its own bill (subtotal + tax = total) and payment method."""
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    delivery_id: Mapped[int] = mapped_column(ForeignKey("deliveries.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    placed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    contact_phone: Mapped[str] = mapped_column(String(15))
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="PLACED", index=True)
    source: Mapped[str] = mapped_column(String(20), default="app")  # app | whatsapp | phone
    payment_method: Mapped[str] = mapped_column(String(10), default="cod")  # cod | upi | khata
    fulfillment: Mapped[str] = mapped_column(String(10), default="delivery")  # delivery (rider) | pickup (customer collects at the shop)
    village_id: Mapped[int] = mapped_column(ForeignKey("villages.id"))
    ward_id: Mapped[int | None] = mapped_column(ForeignKey("wards.id"))
    landmark: Mapped[str] = mapped_column(String(200))
    address_details: Mapped[str | None] = mapped_column(Text)
    prescription_ref: Mapped[str | None] = mapped_column(String(300))
    subtotal_paise: Mapped[int] = mapped_column(Integer)
    tax_paise: Mapped[int] = mapped_column(Integer, default=0)
    commission_paise: Mapped[int] = mapped_column(Integer, default=0)
    total_paise: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    delivery: Mapped[Delivery] = relationship(back_populates="orders")
    store: Mapped[Store] = relationship()
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")

    @property
    def store_name(self) -> str:
        return self.store.name

    @property
    def store_phone(self) -> str | None:
        return self.store.phone


class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    store_item_id: Mapped[int] = mapped_column(ForeignKey("store_items.id"))
    name: Mapped[str] = mapped_column(String(120))  # snapshot at order time
    unit_price_paise: Mapped[int] = mapped_column(Integer)  # snapshot at order time
    quantity: Mapped[int] = mapped_column(Integer)
    order: Mapped[Order] = relationship(back_populates="items")


class KhataAccount(Base):
    """A shop's credit account for one customer (the village 'khata book')."""
    __tablename__ = "khata_accounts"
    __table_args__ = (UniqueConstraint("store_id", "customer_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    credit_limit_paise: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class KhataEntry(Base):
    """amount_paise > 0 increases what the customer owes (SALE); < 0 reduces it (PAYMENT)."""
    __tablename__ = "khata_entries"
    __table_args__ = (UniqueConstraint("order_id", "kind"),)  # an order is posted to the ledger at most once
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("khata_accounts.id"), index=True)
    kind: Mapped[str] = mapped_column(String(10))  # SALE | PAYMENT
    amount_paise: Mapped[int] = mapped_column(Integer)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"))
    note: Mapped[str | None] = mapped_column(String(200))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
