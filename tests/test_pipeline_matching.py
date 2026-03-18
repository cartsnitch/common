"""Tests for product matching & dedup pipeline."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from cartsnitch_common.constants import MatchConfidence
from cartsnitch_common.models.product import NormalizedProduct
from cartsnitch_common.normalization import MatchMethod
from cartsnitch_common.pipeline.matching import (
    ProductMatcher,
    classify_confidence,
    match_purchase_item,
)
from cartsnitch_common.schemas.purchase import PurchaseItemCreate


class TestClassifyConfidence:
    def test_upc_always_high(self):
        assert classify_confidence(1.0, MatchMethod.UPC) == MatchConfidence.HIGH
        assert classify_confidence(0.5, MatchMethod.UPC) == MatchConfidence.HIGH

    def test_name_high(self):
        assert classify_confidence(0.9, MatchMethod.NAME) == MatchConfidence.HIGH
        assert classify_confidence(0.8, MatchMethod.NAME) == MatchConfidence.HIGH

    def test_name_medium(self):
        assert classify_confidence(0.6, MatchMethod.NAME) == MatchConfidence.MEDIUM
        assert classify_confidence(0.5, MatchMethod.NAME) == MatchConfidence.MEDIUM

    def test_name_low(self):
        assert classify_confidence(0.3, MatchMethod.NAME) == MatchConfidence.LOW
        assert classify_confidence(0.0, MatchMethod.NAME) == MatchConfidence.LOW


class TestProductMatcher:
    def _make_item(self, name: str, upc: str | None = None) -> PurchaseItemCreate:
        return PurchaseItemCreate(
            product_name_raw=name,
            upc=upc,
            unit_price=Decimal("3.99"),
            extended_price=Decimal("3.99"),
        )

    def test_match_by_upc(self, session):
        product = NormalizedProduct(
            id=uuid.uuid4(),
            canonical_name="Whole Milk Gallon",
            upc_variants=["041250000001"],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(product)
        session.commit()

        matcher = ProductMatcher(session)
        item = self._make_item("Kroger Milk", upc="041250000001")
        prod, result, confidence = matcher.match_single(item)

        assert prod is not None
        assert prod.id == product.id
        assert result is not None
        assert result.method == MatchMethod.UPC
        assert confidence == MatchConfidence.HIGH

    def test_match_by_name(self, session):
        product = NormalizedProduct(
            id=uuid.uuid4(),
            canonical_name="Whole Milk Gallon",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(product)
        session.commit()

        matcher = ProductMatcher(session, name_threshold=0.3)
        item = self._make_item("Whole Milk Gallon Size")
        prod, result, confidence = matcher.match_single(item)

        assert prod is not None
        assert result is not None
        assert result.method == MatchMethod.NAME

    def test_auto_create_when_no_match(self, session):
        matcher = ProductMatcher(session, auto_create=True)
        item = self._make_item("Unique Product XYZ 16 oz")
        prod, result, confidence = matcher.match_single(item)

        assert prod is not None
        assert result is None  # No match found, was created
        assert confidence == MatchConfidence.LOW
        assert prod.canonical_name == "Unique Product XYZ 16 oz"
        assert prod.size == "16"
        assert prod.size_unit == "oz"

    def test_no_create_when_disabled(self, session):
        matcher = ProductMatcher(session, auto_create=False)
        item = self._make_item("Nonexistent Product")
        prod, result, confidence = matcher.match_single(item)

        assert prod is None
        assert result is None

    def test_batch_match(self, session):
        product = NormalizedProduct(
            id=uuid.uuid4(),
            canonical_name="Large Eggs 12 Count",
            upc_variants=["012345"],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(product)
        session.commit()

        matcher = ProductMatcher(session)
        items = [
            self._make_item("Large Eggs", upc="012345"),
            self._make_item("Brand New Never Seen Product"),
        ]
        outcomes = matcher.match_items(items)

        assert len(outcomes) == 2
        assert outcomes[0].match is not None
        assert outcomes[0].confidence_level == MatchConfidence.HIGH
        assert outcomes[0].created_new is False
        assert outcomes[1].match is None
        assert outcomes[1].created_new is True


class TestMatchPurchaseItem:
    def test_convenience_function(self, session):
        product = NormalizedProduct(
            id=uuid.uuid4(),
            canonical_name="Ground Beef 80/20",
            upc_variants=["999888"],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(product)
        session.commit()

        item = PurchaseItemCreate(
            product_name_raw="Ground Beef",
            upc="999888",
            unit_price=Decimal("5.99"),
            extended_price=Decimal("5.99"),
        )
        prod, confidence = match_purchase_item(session, item)
        assert prod is not None
        assert confidence == MatchConfidence.HIGH

    def test_auto_create_default(self, session):
        item = PurchaseItemCreate(
            product_name_raw="Totally New Item",
            unit_price=Decimal("1.00"),
            extended_price=Decimal("1.00"),
        )
        prod, confidence = match_purchase_item(session, item)
        assert prod is not None
        assert confidence == MatchConfidence.LOW
