"""Tests for shrinkflation detection pipeline."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from cartsnitch_common.constants import SizeUnit
from cartsnitch_common.models.product import NormalizedProduct
from cartsnitch_common.pipeline.shrinkflation import (
    _to_comparable,
    _units_comparable,
    detect_shrinkflation,
)


class TestToComparable:
    def test_oz_to_grams(self):
        result = _to_comparable("16", SizeUnit.OZ)
        assert result is not None
        assert result == Decimal("16") * Decimal("28.3495")

    def test_lb_to_grams(self):
        result = _to_comparable("1", SizeUnit.LB)
        assert result == Decimal("453.592")

    def test_ml_to_ml(self):
        assert _to_comparable("500", SizeUnit.ML) == Decimal("500")

    def test_fl_oz_to_ml(self):
        result = _to_comparable("12", SizeUnit.FL_OZ)
        assert result is not None
        assert result == Decimal("12") * Decimal("29.5735")

    def test_count_units(self):
        assert _to_comparable("12", SizeUnit.CT) == Decimal("12")
        assert _to_comparable("6", SizeUnit.PK) == Decimal("6")

    def test_invalid_size(self):
        assert _to_comparable("abc", SizeUnit.OZ) is None


class TestUnitsComparable:
    def test_weight_comparable(self):
        assert _units_comparable(SizeUnit.OZ, SizeUnit.LB) is True
        assert _units_comparable(SizeUnit.G, SizeUnit.KG) is True

    def test_volume_comparable(self):
        assert _units_comparable(SizeUnit.ML, SizeUnit.L) is True
        assert _units_comparable(SizeUnit.FL_OZ, SizeUnit.ML) is True

    def test_count_comparable(self):
        assert _units_comparable(SizeUnit.CT, SizeUnit.PK) is True

    def test_not_comparable_across_systems(self):
        assert _units_comparable(SizeUnit.OZ, SizeUnit.ML) is False
        assert _units_comparable(SizeUnit.CT, SizeUnit.OZ) is False
        assert _units_comparable(SizeUnit.LB, SizeUnit.L) is False


class TestDetectShrinkflation:
    def _make_product(self, session, size: str, unit: SizeUnit, name: str = "Test Product"):
        product = NormalizedProduct(
            id=uuid.uuid4(),
            canonical_name=name,
            size=size,
            size_unit=unit,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(product)
        session.flush()
        return product

    def test_detects_oz_decrease(self, session):
        product = self._make_product(session, "16", SizeUnit.OZ)
        event = detect_shrinkflation(
            session,
            product=product,
            new_size="14",
            new_unit=SizeUnit.OZ,
            detected_date=date(2026, 3, 15),
        )
        assert event is not None
        assert event.old_size == "16"
        assert event.new_size == "14"
        assert "decreased" in event.notes.lower()

    def test_no_detection_when_size_increases(self, session):
        product = self._make_product(session, "14", SizeUnit.OZ)
        event = detect_shrinkflation(
            session,
            product=product,
            new_size="16",
            new_unit=SizeUnit.OZ,
        )
        assert event is None

    def test_no_detection_same_size(self, session):
        product = self._make_product(session, "16", SizeUnit.OZ)
        event = detect_shrinkflation(
            session,
            product=product,
            new_size="16",
            new_unit=SizeUnit.OZ,
        )
        assert event is None

    def test_no_detection_incompatible_units(self, session):
        product = self._make_product(session, "16", SizeUnit.OZ)
        event = detect_shrinkflation(
            session,
            product=product,
            new_size="400",
            new_unit=SizeUnit.ML,
        )
        assert event is None

    def test_no_detection_without_existing_size(self, session):
        product = NormalizedProduct(
            id=uuid.uuid4(),
            canonical_name="No Size Product",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(product)
        session.flush()

        event = detect_shrinkflation(
            session,
            product=product,
            new_size="12",
            new_unit=SizeUnit.OZ,
        )
        assert event is None

    def test_cross_unit_detection_same_system(self, session):
        # 1 lb = 453.592g, 14 oz = 396.893g → size decreased
        product = self._make_product(session, "1", SizeUnit.LB)
        event = detect_shrinkflation(
            session,
            product=product,
            new_size="14",
            new_unit=SizeUnit.OZ,
            detected_date=date(2026, 3, 15),
        )
        assert event is not None

    def test_count_decrease(self, session):
        product = self._make_product(session, "12", SizeUnit.CT)
        event = detect_shrinkflation(
            session,
            product=product,
            new_size="10",
            new_unit=SizeUnit.CT,
            detected_date=date(2026, 3, 15),
        )
        assert event is not None
        assert event.old_size == "12"
        assert event.new_size == "10"

    def test_dedup_existing_event(self, session):
        product = self._make_product(session, "16", SizeUnit.OZ)

        # First detection
        event1 = detect_shrinkflation(
            session,
            product=product,
            new_size="14",
            new_unit=SizeUnit.OZ,
            detected_date=date(2026, 3, 15),
        )

        # Same detection again — should return existing
        event2 = detect_shrinkflation(
            session,
            product=product,
            new_size="14",
            new_unit=SizeUnit.OZ,
            detected_date=date(2026, 3, 16),
        )

        assert event1 is not None
        assert event2 is not None
        assert event1.id == event2.id

    def test_confidence_scaling(self, session):
        # Small decrease (< 5%) → 0.70
        product1 = self._make_product(session, "100", SizeUnit.G, "Product A")
        event1 = detect_shrinkflation(
            session,
            product=product1,
            new_size="97",
            new_unit=SizeUnit.G,
            detected_date=date(2026, 3, 15),
        )
        assert event1 is not None
        assert event1.confidence == Decimal("0.70")

        # Medium decrease (5-10%) → 0.85
        product2 = self._make_product(session, "100", SizeUnit.G, "Product B")
        event2 = detect_shrinkflation(
            session,
            product=product2,
            new_size="93",
            new_unit=SizeUnit.G,
            detected_date=date(2026, 3, 15),
        )
        assert event2 is not None
        assert event2.confidence == Decimal("0.85")

        # Large decrease (>= 10%) → 0.95
        product3 = self._make_product(session, "100", SizeUnit.G, "Product C")
        event3 = detect_shrinkflation(
            session,
            product=product3,
            new_size="85",
            new_unit=SizeUnit.G,
            detected_date=date(2026, 3, 15),
        )
        assert event3 is not None
        assert event3.confidence == Decimal("0.95")

    def test_min_size_decrease_threshold(self, session):
        product = self._make_product(session, "100", SizeUnit.G)
        # 0.5% decrease — below default 1% threshold
        event = detect_shrinkflation(
            session,
            product=product,
            new_size="99.5",
            new_unit=SizeUnit.G,
            min_size_decrease_pct=Decimal("1"),
        )
        assert event is None
