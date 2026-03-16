"""Tests for SQLAlchemy ORM models."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import inspect

from cartsnitch_common.constants import (
    AccountStatus,
    DiscountType,
    PriceSource,
    ProductCategory,
    SizeUnit,
    StoreSlug,
)
from cartsnitch_common.models import (
    Coupon,
    NormalizedProduct,
    PriceHistory,
    Purchase,
    PurchaseItem,
    ShrinkflationEvent,
    Store,
    StoreLocation,
    User,
    UserStoreAccount,
)


class TestTableCreation:
    """Verify all expected tables are created."""

    def test_all_tables_exist(self, engine):
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())
        expected = {
            "stores",
            "store_locations",
            "users",
            "user_store_accounts",
            "purchases",
            "purchase_items",
            "normalized_products",
            "price_history",
            "coupons",
            "shrinkflation_events",
        }
        assert expected.issubset(table_names)

    def test_ten_tables_total(self, engine):
        inspector = inspect(engine)
        assert len(inspector.get_table_names()) == 10


class TestUUIDPrimaryKeys:
    """All models use UUID PKs."""

    def test_store_uuid_pk(self, session):
        store = Store(
            id=uuid.uuid4(),
            name="Meijer",
            slug=StoreSlug.MEIJER,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(store)
        session.commit()
        assert isinstance(store.id, uuid.UUID)

    def test_user_uuid_pk(self, session):
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            hashed_password="hashed",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(user)
        session.commit()
        assert isinstance(user.id, uuid.UUID)


class TestStoreModel:
    def test_store_slug_enum(self, session):
        store = Store(
            id=uuid.uuid4(),
            name="Kroger",
            slug=StoreSlug.KROGER,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(store)
        session.commit()
        assert store.slug == StoreSlug.KROGER

    def test_store_unique_slug(self, session):
        s1 = Store(
            id=uuid.uuid4(),
            name="Target",
            slug=StoreSlug.TARGET,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        s2 = Store(
            id=uuid.uuid4(),
            name="Target Duplicate",
            slug=StoreSlug.TARGET,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(s1)
        session.commit()
        session.add(s2)
        with pytest.raises(Exception):  # noqa: B017
            session.commit()
        session.rollback()


class TestStoreLocationModel:
    def test_store_location_fields(self, session):
        store = Store(
            id=uuid.uuid4(),
            name="Meijer",
            slug=StoreSlug.MEIJER,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(store)
        session.flush()
        loc = StoreLocation(
            id=uuid.uuid4(),
            store_id=store.id,
            address="123 Main St",
            city="Ann Arbor",
            state="MI",
            zip="48104",
            lat=42.2808,
            lng=-83.7430,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(loc)
        session.commit()
        assert loc.city == "Ann Arbor"
        assert loc.lat == pytest.approx(42.2808)


class TestUserStoreAccountModel:
    def test_account_status_enum(self, session):
        user = User(
            id=uuid.uuid4(),
            email="test@test.com",
            hashed_password="hashed",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        store = Store(
            id=uuid.uuid4(),
            name="Kroger",
            slug=StoreSlug.KROGER,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add_all([user, store])
        session.flush()
        acct = UserStoreAccount(
            id=uuid.uuid4(),
            user_id=user.id,
            store_id=store.id,
            status=AccountStatus.ACTIVE,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(acct)
        session.commit()
        assert acct.status == AccountStatus.ACTIVE

    def test_unique_user_store_constraint(self, session):
        """One account per user per store."""
        user = User(
            id=uuid.uuid4(),
            email="unique@test.com",
            hashed_password="hashed",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        store = Store(
            id=uuid.uuid4(),
            name="Target",
            slug=StoreSlug.TARGET,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add_all([user, store])
        session.flush()
        a1 = UserStoreAccount(
            id=uuid.uuid4(),
            user_id=user.id,
            store_id=store.id,
            status=AccountStatus.ACTIVE,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        a2 = UserStoreAccount(
            id=uuid.uuid4(),
            user_id=user.id,
            store_id=store.id,
            status=AccountStatus.EXPIRED,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(a1)
        session.commit()
        session.add(a2)
        with pytest.raises(Exception):  # noqa: B017
            session.commit()
        session.rollback()


class TestPurchaseModel:
    def test_purchase_with_items(self, session):
        user = User(
            id=uuid.uuid4(),
            email="buyer@test.com",
            hashed_password="hashed",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        store = Store(
            id=uuid.uuid4(),
            name="Meijer",
            slug=StoreSlug.MEIJER,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add_all([user, store])
        session.flush()
        purchase = Purchase(
            id=uuid.uuid4(),
            user_id=user.id,
            store_id=store.id,
            receipt_id="RCP-001",
            purchase_date=date(2026, 3, 15),
            total=Decimal("42.50"),
            ingested_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(purchase)
        session.flush()
        item = PurchaseItem(
            id=uuid.uuid4(),
            purchase_id=purchase.id,
            product_name_raw="Meijer Whole Milk 1 Gallon",
            upc="0041250000001",
            quantity=Decimal("1"),
            unit_price=Decimal("3.49"),
            extended_price=Decimal("3.49"),
        )
        session.add(item)
        session.commit()
        assert item.product_name_raw == "Meijer Whole Milk 1 Gallon"
        assert item.unit_price == Decimal("3.49")


class TestNormalizedProductModel:
    def test_product_with_upc_variants(self, session):
        product = NormalizedProduct(
            id=uuid.uuid4(),
            canonical_name="Whole Milk, 1 Gallon",
            category=ProductCategory.DAIRY,
            brand="Store Brand",
            size="128",
            size_unit=SizeUnit.FL_OZ,
            upc_variants=["0041250000001", "0041250000002"],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(product)
        session.commit()
        assert product.category == ProductCategory.DAIRY
        assert product.size_unit == SizeUnit.FL_OZ


class TestPriceHistoryModel:
    def test_price_source_enum(self, session):
        store = Store(
            id=uuid.uuid4(),
            name="Kroger",
            slug=StoreSlug.KROGER,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        product = NormalizedProduct(
            id=uuid.uuid4(),
            canonical_name="Eggs, Large, 12ct",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add_all([store, product])
        session.flush()
        ph = PriceHistory(
            id=uuid.uuid4(),
            normalized_product_id=product.id,
            store_id=store.id,
            observed_date=date(2026, 3, 15),
            regular_price=Decimal("4.99"),
            sale_price=Decimal("3.99"),
            source=PriceSource.RECEIPT,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(ph)
        session.commit()
        assert ph.source == PriceSource.RECEIPT
        assert ph.regular_price == Decimal("4.99")


class TestCouponModel:
    def test_coupon_discount_types(self, session):
        store = Store(
            id=uuid.uuid4(),
            name="Target",
            slug=StoreSlug.TARGET,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(store)
        session.flush()
        coupon = Coupon(
            id=uuid.uuid4(),
            store_id=store.id,
            title="$2 off eggs",
            discount_type=DiscountType.FIXED,
            discount_value=Decimal("2.00"),
            requires_clip=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(coupon)
        session.commit()
        assert coupon.discount_type == DiscountType.FIXED
        assert coupon.discount_value == Decimal("2.00")


class TestShrinkflationEventModel:
    def test_shrinkflation_event(self, session):
        product = NormalizedProduct(
            id=uuid.uuid4(),
            canonical_name="Cereal, Honey Oats",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(product)
        session.flush()
        event = ShrinkflationEvent(
            id=uuid.uuid4(),
            normalized_product_id=product.id,
            detected_date=date(2026, 3, 10),
            old_size="18",
            new_size="15.4",
            old_unit=SizeUnit.OZ,
            new_unit=SizeUnit.OZ,
            price_at_old_size=Decimal("4.99"),
            price_at_new_size=Decimal("4.99"),
            confidence=Decimal("0.95"),
            notes="Size reduced by 14.4%, price unchanged",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(event)
        session.commit()
        assert event.confidence == Decimal("0.95")
        assert event.old_unit == SizeUnit.OZ
