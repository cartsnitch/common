"""End-to-end integration tests for the data pipeline.

Tests the full flow: scraper output → normalization → product matching → DB storage
→ price tracking → shrinkflation detection → event publishing.

Uses real test fixtures with an in-memory SQLite database, not mocks.
"""

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from cartsnitch_common.constants import (
    EventType,
    SizeUnit,
    StoreSlug,
)
from cartsnitch_common.events import publish_event
from cartsnitch_common.models import (
    Base,
    NormalizedProduct,
    PriceHistory,
    Purchase,
    PurchaseItem,
    ShrinkflationEvent,
    Store,
    User,
)
from cartsnitch_common.pipeline.matching import ProductMatcher
from cartsnitch_common.pipeline.price_tracking import (
    PriceDelta,
    get_price_trend,
    record_price_from_item,
)
from cartsnitch_common.pipeline.receipt import normalize_receipt, parse_meijer_item
from cartsnitch_common.pipeline.shrinkflation import detect_shrinkflation
from cartsnitch_common.schemas.events import EventEnvelope
from cartsnitch_common.schemas.purchase import PurchaseCreate

# ---------------------------------------------------------------------------
# Fixtures: realistic scraper output from Meijer
# ---------------------------------------------------------------------------

MEIJER_RECEIPT_FIXTURE = {
    "receiptId": "MJ-2026-03-15-00042",
    "date": "2026-03-15",
    "total": "47.82",
    "subtotal": "44.50",
    "taxAmount": "3.32",
    "totalSavings": "6.20",
    "items": [
        {
            "description": "  Meijer Whole Milk 1 Gallon  ",
            "upcCode": "00041250010001",
            "quantity": 1,
            "unitPrice": "3.29",
            "extendedPrice": "3.29",
            "regularPrice": "3.49",
            "salePrice": "3.29",
            "category": "Dairy",
        },
        {
            "name": "BARILLA SPAGHETTI 16 OZ",
            "upc": "076808280753",
            "qty": 2,
            "price": "1.69",
            "totalPrice": "3.38",
            "regularPrice": "1.89",
            "couponDiscount": "0.40",
            "department": "Pantry",
        },
        {
            "description": "Meijer Lean Ground Beef 1 lb",
            "upcCode": "00041250022004",
            "quantity": 1,
            "unitPrice": "5.99",
            "extendedPrice": "5.99",
            "regularPrice": "6.49",
            "loyaltyDiscount": "0.50",
            "category": "Meat",
        },
        {
            "description": "Cheerios Original 12 oz",
            "upcCode": "016000275645",
            "quantity": 1,
            "unitPrice": "4.49",
            "extendedPrice": "4.49",
            "regularPrice": "4.49",
            "category": "Snacks",
        },
        {
            "description": "Fresh Bananas",
            "quantity": 1,
            "unitPrice": "0.69",
            "extendedPrice": "0.69",
            "category": "Produce",
        },
    ],
}

MEIJER_RECEIPT_SECOND_VISIT = {
    "receiptId": "MJ-2026-03-18-00099",
    "date": "2026-03-18",
    "total": "12.47",
    "items": [
        {
            "description": "Meijer Whole Milk 1 Gallon",
            "upcCode": "00041250010001",
            "quantity": 1,
            "unitPrice": "3.49",
            "extendedPrice": "3.49",
            "regularPrice": "3.49",
            "category": "Dairy",
        },
        {
            "description": "BARILLA SPAGHETTI 16 OZ",
            "upc": "076808280753",
            "qty": 1,
            "price": "1.99",
            "totalPrice": "1.99",
            "regularPrice": "1.99",
            "department": "Pantry",
        },
        {
            "description": "Cheerios Original 10.8 oz",
            "upcCode": "016000275645",
            "quantity": 1,
            "unitPrice": "4.49",
            "extendedPrice": "4.49",
            "regularPrice": "4.49",
            "category": "Snacks",
        },
    ],
}


@pytest.fixture
def e2e_engine():
    """In-memory SQLite engine for E2E tests."""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def e2e_session(e2e_engine):
    """SQLAlchemy session with pre-seeded store and user."""
    factory = sessionmaker(bind=e2e_engine)
    with factory() as sess:
        yield sess


@pytest.fixture
def store(e2e_session: Session) -> Store:
    """Seed a Meijer store."""
    s = Store(id=uuid.uuid4(), name="Meijer", slug=StoreSlug.MEIJER)
    e2e_session.add(s)
    e2e_session.flush()
    return s


@pytest.fixture
def user(e2e_session: Session) -> User:
    """Seed a test user."""
    u = User(
        id=uuid.uuid4(),
        email="tester@cartsnitch.com",
        hashed_password="hashed_test_password",
        display_name="Test User",
    )
    e2e_session.add(u)
    e2e_session.flush()
    return u


@pytest.fixture
def redis_mock():
    """A lightweight Redis mock that captures published messages."""
    client = MagicMock()
    published: list[tuple[str, str]] = []

    def _publish(channel: str, message: str) -> int:
        published.append((channel, message))
        return 1

    client.publish = MagicMock(side_effect=_publish)
    client._published = published
    return client


# ===========================================================================
# Test class: Full pipeline E2E — scraper → normalization → matching → storage
# ===========================================================================


class TestFullPipelineE2E:
    """Scraper output → normalize_receipt → ProductMatcher → DB storage."""

    def test_normalize_meijer_receipt(self, user: User, store: Store):
        """Raw Meijer receipt normalizes into a valid PurchaseCreate."""
        purchase = normalize_receipt(
            MEIJER_RECEIPT_FIXTURE,
            user_id=str(user.id),
            store_id=str(store.id),
        )

        assert isinstance(purchase, PurchaseCreate)
        assert purchase.receipt_id == "MJ-2026-03-15-00042"
        assert purchase.purchase_date == date(2026, 3, 15)
        assert purchase.total == Decimal("47.82")
        assert purchase.subtotal == Decimal("44.50")
        assert purchase.tax == Decimal("3.32")
        assert purchase.savings_total == Decimal("6.20")
        assert len(purchase.items) == 5
        assert purchase.raw_data == MEIJER_RECEIPT_FIXTURE

    def test_item_field_normalization(self, user: User, store: Store):
        """Items parse correctly regardless of field name variants."""
        purchase = normalize_receipt(
            MEIJER_RECEIPT_FIXTURE,
            user_id=str(user.id),
            store_id=str(store.id),
        )

        # Item using 'description' / 'upcCode' fields
        milk = purchase.items[0]
        assert milk.product_name_raw == "Meijer Whole Milk 1 Gallon"
        assert milk.upc == "41250010001"  # leading zeros stripped
        assert milk.unit_price == Decimal("3.29")

        # Item using 'name' / 'upc' / 'qty' / 'price' / 'totalPrice' fields
        pasta = purchase.items[1]
        assert pasta.product_name_raw == "BARILLA SPAGHETTI 16 OZ"
        assert pasta.upc == "76808280753"
        assert pasta.quantity == Decimal("2")
        assert pasta.extended_price == Decimal("3.38")
        assert pasta.coupon_discount == Decimal("0.40")

    def test_upc_product_matching_and_storage(
        self, e2e_session: Session, user: User, store: Store
    ):
        """Full flow: normalize → match → store in DB. UPC matching works E2E."""
        purchase_schema = normalize_receipt(
            MEIJER_RECEIPT_FIXTURE,
            user_id=str(user.id),
            store_id=str(store.id),
        )

        # Run product matching
        matcher = ProductMatcher(e2e_session, auto_create=True)
        outcomes = matcher.match_items(purchase_schema.items)

        assert len(outcomes) == 5

        # First item has a UPC — auto_create makes a new product
        assert outcomes[0].created_new is True

        # Store the purchase in DB
        purchase_db = Purchase(
            id=uuid.uuid4(),
            user_id=user.id,
            store_id=store.id,
            receipt_id=purchase_schema.receipt_id,
            purchase_date=purchase_schema.purchase_date,
            total=purchase_schema.total,
            subtotal=purchase_schema.subtotal,
            tax=purchase_schema.tax,
            savings_total=purchase_schema.savings_total,
            raw_data=purchase_schema.raw_data,
        )
        e2e_session.add(purchase_db)
        e2e_session.flush()

        # Store items linked to the purchase and matched products
        for _i, item_schema in enumerate(purchase_schema.items):
            item_db = PurchaseItem(
                id=uuid.uuid4(),
                purchase_id=purchase_db.id,
                product_name_raw=item_schema.product_name_raw,
                upc=item_schema.upc,
                quantity=item_schema.quantity,
                unit_price=item_schema.unit_price,
                extended_price=item_schema.extended_price,
                regular_price=item_schema.regular_price,
                sale_price=item_schema.sale_price,
                coupon_discount=item_schema.coupon_discount,
                loyalty_discount=item_schema.loyalty_discount,
                category_raw=item_schema.category_raw,
            )
            e2e_session.add(item_db)
        e2e_session.flush()

        # Verify data persisted correctly
        stored_purchase = e2e_session.execute(
            select(Purchase).where(Purchase.receipt_id == "MJ-2026-03-15-00042")
        ).scalar_one()
        assert stored_purchase.total == Decimal("47.82")
        assert stored_purchase.user_id == user.id
        assert stored_purchase.store_id == store.id

        stored_items = e2e_session.execute(
            select(PurchaseItem).where(PurchaseItem.purchase_id == stored_purchase.id)
        ).scalars().all()
        assert len(stored_items) == 5

        # Verify products were created in normalized_products table
        products = e2e_session.execute(select(NormalizedProduct)).scalars().all()
        assert len(products) == 5  # all 5 items auto-created products

    def test_second_visit_reuses_existing_products(
        self, e2e_session: Session, user: User, store: Store
    ):
        """On second receipt, products matched by UPC reuse existing records."""
        # Ingest first receipt
        first = normalize_receipt(
            MEIJER_RECEIPT_FIXTURE,
            user_id=str(user.id),
            store_id=str(store.id),
        )
        matcher = ProductMatcher(e2e_session, auto_create=True)
        matcher.match_items(first.items)

        products_after_first = e2e_session.execute(select(NormalizedProduct)).scalars().all()
        first_count = len(products_after_first)

        # Ingest second receipt — overlapping UPCs
        second = normalize_receipt(
            MEIJER_RECEIPT_SECOND_VISIT,
            user_id=str(user.id),
            store_id=str(store.id),
        )
        second_outcomes = matcher.match_items(second.items)

        # Milk, pasta, cheerios should match existing by UPC
        assert second_outcomes[0].created_new is False  # milk — UPC match
        assert second_outcomes[1].created_new is False  # pasta — UPC match
        assert second_outcomes[2].created_new is False  # cheerios — UPC match

        products_after_second = e2e_session.execute(select(NormalizedProduct)).scalars().all()
        assert len(products_after_second) == first_count  # no new products created


# ===========================================================================
# Test class: Price tracking and shrinkflation detection E2E
# ===========================================================================


class TestPriceTrackingE2E:
    """Price recording from stored items and price delta detection."""

    def test_price_recorded_from_ingested_receipt(
        self, e2e_session: Session, user: User, store: Store
    ):
        """Ingest receipt → match products → record prices → verify price history."""
        purchase_schema = normalize_receipt(
            MEIJER_RECEIPT_FIXTURE,
            user_id=str(user.id),
            store_id=str(store.id),
        )
        matcher = ProductMatcher(e2e_session, auto_create=True)
        outcomes = matcher.match_items(purchase_schema.items)

        # Record prices for each matched item
        price_entries = []
        for i, item_schema in enumerate(purchase_schema.items):
            product = (
                outcomes[i].match.product if outcomes[i].match else None
            )
            if product is None:
                # Was auto-created — find the product directly
                products = e2e_session.execute(select(NormalizedProduct)).scalars().all()
                for p in products:
                    if p.canonical_name == item_schema.product_name_raw:
                        product = p
                        break

            if product:
                entry, delta = record_price_from_item(
                    e2e_session,
                    product_id=product.id,
                    store_id=store.id,
                    observed_date=purchase_schema.purchase_date,
                    regular_price=item_schema.regular_price or item_schema.unit_price,
                    sale_price=item_schema.sale_price,
                )
                price_entries.append((entry, delta))

        # First ingestion — no deltas expected
        assert all(delta is None for _, delta in price_entries)

        # Verify price history stored
        all_prices = e2e_session.execute(select(PriceHistory)).scalars().all()
        assert len(all_prices) >= 4  # at least the items with regular_price

    def test_price_increase_detected_on_second_receipt(
        self, e2e_session: Session, user: User, store: Store
    ):
        """Second receipt with higher price triggers a PriceDelta."""
        # Ingest first receipt
        first = normalize_receipt(
            MEIJER_RECEIPT_FIXTURE,
            user_id=str(user.id),
            store_id=str(store.id),
        )
        matcher = ProductMatcher(e2e_session, auto_create=True)
        first_outcomes = matcher.match_items(first.items)

        # Record first prices
        for i, item_schema in enumerate(first.items):
            product = first_outcomes[i].match.product if first_outcomes[i].match else None
            if product is None:
                products = e2e_session.execute(select(NormalizedProduct)).scalars().all()
                for p in products:
                    if p.canonical_name == item_schema.product_name_raw:
                        product = p
                        break
            if product:
                record_price_from_item(
                    e2e_session,
                    product_id=product.id,
                    store_id=store.id,
                    observed_date=first.purchase_date,
                    regular_price=item_schema.regular_price or item_schema.unit_price,
                    sale_price=item_schema.sale_price,
                )

        # Ingest second receipt — pasta price went up ($1.89 → $1.99)
        second = normalize_receipt(
            MEIJER_RECEIPT_SECOND_VISIT,
            user_id=str(user.id),
            store_id=str(store.id),
        )
        second_outcomes = matcher.match_items(second.items)

        # Record second prices and capture deltas
        deltas: list[PriceDelta] = []
        for i, item_schema in enumerate(second.items):
            product = second_outcomes[i].match.product if second_outcomes[i].match else None
            if product is None:
                products = e2e_session.execute(select(NormalizedProduct)).scalars().all()
                for p in products:
                    if p.canonical_name == item_schema.product_name_raw:
                        product = p
                        break
            if product:
                _, delta = record_price_from_item(
                    e2e_session,
                    product_id=product.id,
                    store_id=store.id,
                    observed_date=second.purchase_date,
                    regular_price=item_schema.regular_price or item_schema.unit_price,
                    sale_price=item_schema.sale_price,
                )
                if delta:
                    deltas.append(delta)

        # Milk went from $3.49 → $3.49 (no change); pasta from $1.89 → $1.99 (increase)
        price_increases = [d for d in deltas if d.is_increase]
        assert len(price_increases) >= 1

        pasta_delta = next(
            (d for d in price_increases if d.old_price == Decimal("1.89")),
            None,
        )
        assert pasta_delta is not None
        assert pasta_delta.new_price == Decimal("1.99")
        assert pasta_delta.change_amount == Decimal("0.10")
        assert pasta_delta.is_increase is True

    def test_price_trend_across_visits(
        self, e2e_session: Session, user: User, store: Store
    ):
        """get_price_trend returns ordered history after multiple ingestions."""
        # Create a product manually
        product = NormalizedProduct(
            id=uuid.uuid4(),
            canonical_name="Test Product",
            upc_variants=["1234567890"],
        )
        e2e_session.add(product)
        e2e_session.flush()

        # Record 3 prices on different dates
        dates_prices = [
            (date(2026, 3, 10), Decimal("2.99")),
            (date(2026, 3, 13), Decimal("3.19")),
            (date(2026, 3, 16), Decimal("2.79")),
        ]
        for obs_date, price in dates_prices:
            record_price_from_item(
                e2e_session,
                product_id=product.id,
                store_id=store.id,
                observed_date=obs_date,
                regular_price=price,
            )

        trend = get_price_trend(e2e_session, product.id, store.id)
        assert len(trend) == 3
        # Newest first
        assert trend[0].regular_price == Decimal("2.79")
        assert trend[1].regular_price == Decimal("3.19")
        assert trend[2].regular_price == Decimal("2.99")


class TestShrinkflationE2E:
    """Shrinkflation detection integrated with product matching."""

    def test_shrinkflation_detected_from_receipt_data(
        self, e2e_session: Session, user: User, store: Store
    ):
        """Cheerios went from 12 oz → 10.8 oz between receipts. Detect shrinkflation."""
        # Ingest first receipt — creates Cheerios product with size from name
        first = normalize_receipt(
            MEIJER_RECEIPT_FIXTURE,
            user_id=str(user.id),
            store_id=str(store.id),
        )
        matcher = ProductMatcher(e2e_session, auto_create=True)
        first_outcomes = matcher.match_items(first.items)

        # Find the Cheerios product (index 3 in fixture)
        cheerios_product = None
        for outcome in first_outcomes:
            if outcome.match and outcome.match.product:
                p = outcome.match.product
            else:
                # Check auto-created products
                products = e2e_session.execute(select(NormalizedProduct)).scalars().all()
                for p in products:
                    if "cheerios" in p.canonical_name.lower():
                        cheerios_product = p
                        break
                if cheerios_product:
                    break
        else:
            products = e2e_session.execute(select(NormalizedProduct)).scalars().all()
            for p in products:
                if "cheerios" in p.canonical_name.lower():
                    cheerios_product = p
                    break

        assert cheerios_product is not None
        # The auto-created product should have extracted "12" and "oz" from name
        assert cheerios_product.size == "12"
        assert cheerios_product.size_unit == SizeUnit.OZ

        # Now detect shrinkflation: 12 oz → 10.8 oz
        event = detect_shrinkflation(
            e2e_session,
            product=cheerios_product,
            new_size="10.8",
            new_unit=SizeUnit.OZ,
            new_price=Decimal("4.49"),
            detected_date=date(2026, 3, 18),
        )

        assert event is not None
        assert isinstance(event, ShrinkflationEvent)
        assert event.old_size == "12"
        assert event.new_size == "10.8"
        assert event.old_unit == SizeUnit.OZ
        assert event.new_unit == SizeUnit.OZ
        assert event.confidence >= Decimal("0.85")  # 10% decrease → 0.95

        # Verify stored in DB
        stored = e2e_session.execute(
            select(ShrinkflationEvent).where(
                ShrinkflationEvent.normalized_product_id == cheerios_product.id
            )
        ).scalar_one()
        assert stored.id == event.id

    def test_shrinkflation_dedup_on_repeat_detection(
        self, e2e_session: Session, user: User, store: Store
    ):
        """Same shrinkflation detected twice returns the existing event, not a duplicate."""
        product = NormalizedProduct(
            id=uuid.uuid4(),
            canonical_name="Brand X Cereal 15 oz",
            size="15",
            size_unit=SizeUnit.OZ,
            upc_variants=["999888777"],
        )
        e2e_session.add(product)
        e2e_session.flush()

        first = detect_shrinkflation(
            e2e_session, product, new_size="13.5", new_unit=SizeUnit.OZ
        )
        second = detect_shrinkflation(
            e2e_session, product, new_size="13.5", new_unit=SizeUnit.OZ
        )

        assert first is not None
        assert second is not None
        assert first.id == second.id  # same event, not duplicated

        count = len(
            e2e_session.execute(
                select(ShrinkflationEvent).where(
                    ShrinkflationEvent.normalized_product_id == product.id
                )
            ).scalars().all()
        )
        assert count == 1


# ===========================================================================
# Test class: Event bus pub/sub for pipeline stage transitions
# ===========================================================================


class TestEventBusE2E:
    """Redis event publishing at each pipeline stage."""

    def test_receipt_ingested_event(self, redis_mock, user: User, store: Store):
        """publish_event sends a valid EventEnvelope for RECEIPTS_INGESTED."""
        purchase_schema = normalize_receipt(
            MEIJER_RECEIPT_FIXTURE,
            user_id=str(user.id),
            store_id=str(store.id),
        )

        subscribers = publish_event(
            redis_mock,
            EventType.RECEIPTS_INGESTED,
            service="receiptwitness",
            payload={
                "receipt_id": purchase_schema.receipt_id,
                "user_id": str(user.id),
                "store_slug": StoreSlug.MEIJER,
                "item_count": len(purchase_schema.items),
                "total": str(purchase_schema.total),
            },
        )

        assert subscribers == 1
        assert len(redis_mock._published) == 1
        channel, raw_msg = redis_mock._published[0]
        assert channel == EventType.RECEIPTS_INGESTED.value

        # Deserialize and validate the envelope
        envelope = EventEnvelope.model_validate_json(raw_msg)
        assert envelope.event_type == EventType.RECEIPTS_INGESTED
        assert envelope.service == "receiptwitness"
        assert envelope.payload["receipt_id"] == "MJ-2026-03-15-00042"
        assert envelope.payload["item_count"] == 5

    def test_price_updated_event(self, redis_mock, user: User, store: Store):
        """publish_event sends a valid envelope for PRICES_UPDATED."""
        subscribers = publish_event(
            redis_mock,
            EventType.PRICES_UPDATED,
            service="cartsnitch-common",
            payload={
                "product_id": str(uuid.uuid4()),
                "store_slug": StoreSlug.MEIJER,
                "old_price": "1.89",
                "new_price": "1.99",
                "change_percent": "5.29",
            },
        )

        assert subscribers == 1
        channel, raw_msg = redis_mock._published[0]
        assert channel == EventType.PRICES_UPDATED.value

        envelope = EventEnvelope.model_validate_json(raw_msg)
        assert envelope.event_type == EventType.PRICES_UPDATED
        assert envelope.payload["old_price"] == "1.89"

    def test_products_normalized_event(self, redis_mock, user: User, store: Store):
        """publish_event sends a valid envelope for PRODUCTS_NORMALIZED."""
        product_id = str(uuid.uuid4())
        subscribers = publish_event(
            redis_mock,
            EventType.PRODUCTS_NORMALIZED,
            service="cartsnitch-common",
            payload={
                "product_id": product_id,
                "canonical_name": "Barilla Spaghetti",
                "match_method": "upc",
                "confidence": "high",
            },
        )

        assert subscribers == 1
        channel, raw_msg = redis_mock._published[0]
        assert channel == EventType.PRODUCTS_NORMALIZED.value
        envelope = EventEnvelope.model_validate_json(raw_msg)
        assert envelope.payload["confidence"] == "high"

    def test_shrinkflation_alert_event(self, redis_mock, user: User, store: Store):
        """publish_event sends a valid envelope for ALERT_SHRINKFLATION."""
        subscribers = publish_event(
            redis_mock,
            EventType.ALERT_SHRINKFLATION,
            service="shrinkray",
            payload={
                "product_id": str(uuid.uuid4()),
                "product_name": "Cheerios Original",
                "old_size": "12 oz",
                "new_size": "10.8 oz",
                "confidence": "0.95",
            },
        )

        assert subscribers == 1
        channel, raw_msg = redis_mock._published[0]
        assert channel == EventType.ALERT_SHRINKFLATION.value

    def test_full_pipeline_emits_events_at_each_stage(
        self, e2e_session: Session, redis_mock, user: User, store: Store
    ):
        """Full pipeline: ingest → match → record price → publish events at each stage."""
        # Stage 1: Normalize receipt
        purchase_schema = normalize_receipt(
            MEIJER_RECEIPT_FIXTURE,
            user_id=str(user.id),
            store_id=str(store.id),
        )

        # Publish receipt ingested
        publish_event(
            redis_mock,
            EventType.RECEIPTS_INGESTED,
            service="receiptwitness",
            payload={
                "receipt_id": purchase_schema.receipt_id,
                "item_count": len(purchase_schema.items),
            },
        )

        # Stage 2: Match products
        matcher = ProductMatcher(e2e_session, auto_create=True)
        outcomes = matcher.match_items(purchase_schema.items)

        for i, outcome in enumerate(outcomes):
            product = outcome.match.product if outcome.match else None
            if product is None:
                # Auto-created — look up by name
                products = e2e_session.execute(select(NormalizedProduct)).scalars().all()
                for p in products:
                    if p.canonical_name == purchase_schema.items[i].product_name_raw:
                        product = p
                        break
            if product is None:
                continue
            publish_event(
                redis_mock,
                EventType.PRODUCTS_NORMALIZED,
                service="cartsnitch-common",
                payload={
                    "product_id": str(product.id),
                    "match_method": outcome.match.method.value if outcome.match else "auto_create",
                    "confidence": outcome.confidence_level.value,
                },
            )

        # Stage 3: Record prices
        for i, item_schema in enumerate(purchase_schema.items):
            product = outcomes[i].match.product if outcomes[i].match else None
            if product is None:
                products = e2e_session.execute(select(NormalizedProduct)).scalars().all()
                for p in products:
                    if p.canonical_name == item_schema.product_name_raw:
                        product = p
                        break
            if product:
                _, delta = record_price_from_item(
                    e2e_session,
                    product_id=product.id,
                    store_id=store.id,
                    observed_date=purchase_schema.purchase_date,
                    regular_price=item_schema.regular_price or item_schema.unit_price,
                )
                if delta and delta.is_increase:
                    publish_event(
                        redis_mock,
                        EventType.ALERT_PRICE_INCREASE,
                        service="stickershock",
                        payload={
                            "product_id": str(product.id),
                            "old_price": str(delta.old_price),
                            "new_price": str(delta.new_price),
                        },
                    )

        # Verify events published at each stage
        channels = [ch for ch, _ in redis_mock._published]
        assert EventType.RECEIPTS_INGESTED.value in channels
        assert EventType.PRODUCTS_NORMALIZED.value in channels
        # No price increases on first receipt, so no ALERT_PRICE_INCREASE expected

        # All messages are valid EventEnvelopes
        for _, raw_msg in redis_mock._published:
            envelope = EventEnvelope.model_validate_json(raw_msg)
            assert envelope.timestamp is not None
            assert envelope.service


# ===========================================================================
# Test class: Error handling for malformed scraper output
# ===========================================================================


class TestMalformedScraperOutput:
    """Error handling for bad, partial, or unexpected scraper data."""

    def test_missing_item_name_produces_empty_string(self):
        """Item with no description/name field normalizes with empty product_name_raw."""
        item = parse_meijer_item({"unitPrice": "2.99"})
        assert item.product_name_raw == ""
        assert item.unit_price == Decimal("2.99")

    def test_missing_price_defaults_to_zero(self):
        """Item with no price fields defaults to zero."""
        item = parse_meijer_item({"description": "Mystery Product"})
        assert item.unit_price == Decimal("0")
        assert item.extended_price == Decimal("0")

    def test_non_numeric_price_defaults_to_zero(self):
        """Non-numeric price strings safely default to zero."""
        item = parse_meijer_item({
            "description": "Bad Price Item",
            "unitPrice": "not_a_number",
            "extendedPrice": "$$$.xx",
        })
        assert item.unit_price == Decimal("0")
        assert item.extended_price == Decimal("0")

    def test_empty_receipt_produces_empty_items(self, user: User, store: Store):
        """Receipt with no items normalizes cleanly."""
        raw = {"receiptId": "EMPTY-001", "date": "2026-03-15", "total": "0.00"}
        purchase = normalize_receipt(raw, user_id=str(user.id), store_id=str(store.id))

        assert purchase.receipt_id == "EMPTY-001"
        assert purchase.total == Decimal("0.00")
        assert len(purchase.items) == 0

    def test_receipt_missing_date_defaults_to_today(self, user: User, store: Store):
        """Receipt with no date field defaults to today."""
        raw = {"receiptId": "NO-DATE-001", "total": "5.00", "items": []}
        purchase = normalize_receipt(raw, user_id=str(user.id), store_id=str(store.id))
        assert purchase.purchase_date == date.today()

    def test_receipt_missing_id_generates_uuid(self, user: User, store: Store):
        """Receipt with no ID generates a UUID."""
        raw = {"date": "2026-03-15", "total": "10.00", "items": []}
        purchase = normalize_receipt(raw, user_id=str(user.id), store_id=str(store.id))

        # Should be a valid UUID string
        uuid.UUID(purchase.receipt_id)

    def test_item_with_garbage_upc_preserves_it(self):
        """UPC field with non-standard content is preserved as-is after strip."""
        item = parse_meijer_item({
            "description": "Weird UPC Product",
            "upc": "  ABC-NOT-A-UPC  ",
            "unitPrice": "1.99",
        })
        # lstrip("0") on "ABC-NOT-A-UPC" leaves it intact
        assert item.upc == "ABC-NOT-A-UPC"

    def test_negative_prices_pass_through(self):
        """Negative prices (refunds) are preserved, not zeroed."""
        item = parse_meijer_item({
            "description": "Refund Item",
            "unitPrice": "-5.99",
            "extendedPrice": "-5.99",
        })
        assert item.unit_price == Decimal("-5.99")
        assert item.extended_price == Decimal("-5.99")

    def test_extended_price_auto_calculated(self):
        """When extendedPrice is missing, it's calculated from unitPrice * quantity."""
        item = parse_meijer_item({
            "description": "No Extended",
            "unitPrice": "2.50",
            "quantity": "3",
        })
        assert item.extended_price == Decimal("7.50")

    def test_matching_with_malformed_items(self, e2e_session: Session):
        """ProductMatcher handles items with missing/empty names gracefully."""
        matcher = ProductMatcher(e2e_session, auto_create=True)

        bad_items = [
            parse_meijer_item({"description": "", "unitPrice": "1.00"}),
            parse_meijer_item({"unitPrice": "2.00"}),
        ]

        outcomes = matcher.match_items(bad_items)
        assert len(outcomes) == 2
        # Both should auto-create (no match possible for empty names)
        assert all(o.created_new for o in outcomes)

    def test_completely_empty_receipt(self, user: User, store: Store):
        """Totally empty dict produces a valid PurchaseCreate with defaults."""
        purchase = normalize_receipt({}, user_id=str(user.id), store_id=str(store.id))
        assert purchase.total == Decimal("0")
        assert len(purchase.items) == 0
        assert purchase.purchase_date == date.today()

    def test_mixed_valid_and_malformed_items(self, user: User, store: Store):
        """Receipt with a mix of good and bad items processes all of them."""
        raw = {
            "receiptId": "MIX-001",
            "date": "2026-03-15",
            "total": "10.00",
            "items": [
                {
                    "description": "Good Product 8 oz",
                    "upc": "1234567890",
                    "unitPrice": "3.99",
                    "extendedPrice": "3.99",
                },
                {
                    "unitPrice": "not_a_price",
                },
                {
                    "description": "  *** Special Chars !!!  ",
                    "unitPrice": "2.50",
                },
            ],
        }
        purchase = normalize_receipt(raw, user_id=str(user.id), store_id=str(store.id))
        assert len(purchase.items) == 3

        # Good item
        assert purchase.items[0].product_name_raw == "Good Product 8 oz"
        assert purchase.items[0].upc == "1234567890"

        # Bad price item
        assert purchase.items[1].unit_price == Decimal("0")

        # Special chars stripped
        assert purchase.items[2].product_name_raw == "Special Chars"
