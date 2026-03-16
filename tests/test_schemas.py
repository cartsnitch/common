"""Tests for Pydantic v2 schemas."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from cartsnitch_common.constants import (
    AccountStatus,
    DiscountType,
    EventType,
    PriceSource,
    ProductCategory,
    SizeUnit,
    StoreSlug,
)
from cartsnitch_common.schemas import (
    CouponCreate,
    EventEnvelope,
    NormalizedProductCreate,
    PriceHistoryCreate,
    PurchaseCreate,
    PurchaseItemCreate,
    ShrinkflationEventCreate,
    StoreCreate,
    StoreLocationCreate,
    StoreRead,
    UserCreate,
    UserStoreAccountCreate,
)


class TestStoreSchemas:
    def test_store_create_valid(self):
        s = StoreCreate(name="Meijer", slug=StoreSlug.MEIJER)
        assert s.slug == StoreSlug.MEIJER

    def test_store_create_invalid_slug(self):
        with pytest.raises(ValidationError):
            StoreCreate(name="Walmart", slug="walmart")

    def test_store_read_from_attributes(self):
        data = {
            "id": uuid.uuid4(),
            "name": "Kroger",
            "slug": StoreSlug.KROGER,
            "logo_url": None,
            "website_url": None,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        s = StoreRead(**data)
        assert s.slug == StoreSlug.KROGER


class TestStoreLocationSchemas:
    def test_location_create(self):
        loc = StoreLocationCreate(
            store_id=uuid.uuid4(),
            address="456 Oak Ave",
            city="Detroit",
            state="MI",
            zip="48201",
        )
        assert loc.city == "Detroit"


class TestUserSchemas:
    def test_user_create_valid(self):
        u = UserCreate(email="test@example.com", password="secret123")
        assert u.email == "test@example.com"

    def test_user_create_invalid_email(self):
        with pytest.raises(ValidationError):
            UserCreate(email="not-an-email", password="secret123")


class TestUserStoreAccountSchemas:
    def test_account_create_with_status(self):
        a = UserStoreAccountCreate(
            user_id=uuid.uuid4(),
            store_id=uuid.uuid4(),
            status=AccountStatus.EXPIRED,
        )
        assert a.status == AccountStatus.EXPIRED

    def test_account_create_default_status(self):
        a = UserStoreAccountCreate(
            user_id=uuid.uuid4(),
            store_id=uuid.uuid4(),
        )
        assert a.status == AccountStatus.ACTIVE

    def test_account_create_invalid_status(self):
        with pytest.raises(ValidationError):
            UserStoreAccountCreate(
                user_id=uuid.uuid4(),
                store_id=uuid.uuid4(),
                status="invalid_status",
            )


class TestPurchaseSchemas:
    def test_purchase_create_with_items(self):
        p = PurchaseCreate(
            user_id=uuid.uuid4(),
            store_id=uuid.uuid4(),
            receipt_id="RCP-001",
            purchase_date=date(2026, 3, 15),
            total=Decimal("42.50"),
            items=[
                PurchaseItemCreate(
                    product_name_raw="Milk",
                    unit_price=Decimal("3.49"),
                    extended_price=Decimal("3.49"),
                ),
            ],
        )
        assert len(p.items) == 1
        assert p.items[0].quantity == Decimal("1")


class TestNormalizedProductSchemas:
    def test_product_create_with_enums(self):
        p = NormalizedProductCreate(
            canonical_name="Whole Milk, 1 Gallon",
            category=ProductCategory.DAIRY,
            size_unit=SizeUnit.FL_OZ,
            upc_variants=["0041250000001"],
        )
        assert p.category == ProductCategory.DAIRY

    def test_product_create_invalid_category(self):
        with pytest.raises(ValidationError):
            NormalizedProductCreate(
                canonical_name="Test",
                category="invalid_category",
            )


class TestPriceHistorySchemas:
    def test_price_create(self):
        p = PriceHistoryCreate(
            normalized_product_id=uuid.uuid4(),
            store_id=uuid.uuid4(),
            observed_date=date(2026, 3, 15),
            regular_price=Decimal("4.99"),
            source=PriceSource.RECEIPT,
        )
        assert p.source == PriceSource.RECEIPT

    def test_price_create_invalid_source(self):
        with pytest.raises(ValidationError):
            PriceHistoryCreate(
                normalized_product_id=uuid.uuid4(),
                store_id=uuid.uuid4(),
                observed_date=date(2026, 3, 15),
                regular_price=Decimal("4.99"),
                source="invalid_source",
            )


class TestCouponSchemas:
    def test_coupon_create(self):
        c = CouponCreate(
            store_id=uuid.uuid4(),
            title="BOGO Chips",
            discount_type=DiscountType.BOGO,
        )
        assert c.discount_type == DiscountType.BOGO

    def test_coupon_create_invalid_discount_type(self):
        with pytest.raises(ValidationError):
            CouponCreate(
                store_id=uuid.uuid4(),
                title="Test",
                discount_type="free_stuff",
            )


class TestShrinkflationEventSchemas:
    def test_shrinkflation_create(self):
        s = ShrinkflationEventCreate(
            normalized_product_id=uuid.uuid4(),
            detected_date=date(2026, 3, 10),
            old_size="18",
            new_size="15.4",
            old_unit=SizeUnit.OZ,
            new_unit=SizeUnit.OZ,
            confidence=Decimal("0.95"),
        )
        assert s.old_unit == SizeUnit.OZ

    def test_shrinkflation_create_invalid_unit(self):
        with pytest.raises(ValidationError):
            ShrinkflationEventCreate(
                normalized_product_id=uuid.uuid4(),
                detected_date=date(2026, 3, 10),
                old_size="18",
                new_size="15.4",
                old_unit="bushels",
                new_unit=SizeUnit.OZ,
            )


class TestEventEnvelope:
    def test_valid_event(self):
        e = EventEnvelope(
            event_type=EventType.RECEIPTS_INGESTED,
            timestamp=datetime.now(UTC),
            service="receiptwitness",
            payload={"receipt_id": "RCP-001"},
        )
        assert e.event_type == EventType.RECEIPTS_INGESTED

    def test_invalid_event_type(self):
        with pytest.raises(ValidationError):
            EventEnvelope(
                event_type="invalid.event",
                timestamp=datetime.now(UTC),
                service="test",
                payload={},
            )
