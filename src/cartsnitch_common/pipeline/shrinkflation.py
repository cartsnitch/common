"""Shrinkflation detection — compare unit sizes across price history.

Flags cases where a product's size decreased while price stayed flat or increased.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from cartsnitch_common.constants import SizeUnit
from cartsnitch_common.models.product import NormalizedProduct
from cartsnitch_common.models.shrinkflation import ShrinkflationEvent

# Conversion factors to a common base unit (grams for weight, ml for volume, count for discrete)
_WEIGHT_TO_GRAMS: dict[SizeUnit, Decimal] = {
    SizeUnit.G: Decimal("1"),
    SizeUnit.KG: Decimal("1000"),
    SizeUnit.OZ: Decimal("28.3495"),
    SizeUnit.LB: Decimal("453.592"),
}

_VOLUME_TO_ML: dict[SizeUnit, Decimal] = {
    SizeUnit.ML: Decimal("1"),
    SizeUnit.L: Decimal("1000"),
    SizeUnit.FL_OZ: Decimal("29.5735"),
}

_COUNT_UNITS: set[SizeUnit] = {SizeUnit.CT, SizeUnit.PK}


def _to_comparable(size: str, unit: SizeUnit) -> Decimal | None:
    """Convert a size+unit to a comparable numeric value.

    Returns None if units are not comparable (different measurement systems).
    """
    try:
        size_val = Decimal(size)
    except Exception:
        return None

    if unit in _WEIGHT_TO_GRAMS:
        return size_val * _WEIGHT_TO_GRAMS[unit]
    if unit in _VOLUME_TO_ML:
        return size_val * _VOLUME_TO_ML[unit]
    if unit in _COUNT_UNITS:
        return size_val
    return None


def _units_comparable(unit_a: SizeUnit, unit_b: SizeUnit) -> bool:
    """Check if two units are in the same measurement system."""
    if unit_a in _WEIGHT_TO_GRAMS and unit_b in _WEIGHT_TO_GRAMS:
        return True
    if unit_a in _VOLUME_TO_ML and unit_b in _VOLUME_TO_ML:
        return True
    return unit_a in _COUNT_UNITS and unit_b in _COUNT_UNITS


@dataclass(frozen=True)
class ShrinkflationCandidate:
    """A potential shrinkflation detection before writing to DB."""

    product: NormalizedProduct
    old_size: str
    new_size: str
    old_unit: SizeUnit
    new_unit: SizeUnit
    old_price: Decimal | None
    new_price: Decimal | None
    confidence: Decimal
    size_change_pct: Decimal


def detect_shrinkflation(
    session: Session,
    product: NormalizedProduct,
    new_size: str,
    new_unit: SizeUnit,
    new_price: Decimal | None = None,
    detected_date: date | None = None,
    min_size_decrease_pct: Decimal = Decimal("1"),
) -> ShrinkflationEvent | None:
    """Check if a product's size has decreased (shrinkflation).

    Compares the new size against the product's recorded size.
    If size decreased while price stayed flat or increased, records a shrinkflation event.

    Returns the ShrinkflationEvent if detected, None otherwise.
    """
    if not product.size or not product.size_unit:
        return None

    old_unit = SizeUnit(product.size_unit)
    if not _units_comparable(old_unit, new_unit):
        return None

    old_comparable = _to_comparable(product.size, old_unit)
    new_comparable = _to_comparable(new_size, new_unit)

    if old_comparable is None or new_comparable is None:
        return None

    if new_comparable >= old_comparable:
        return None  # Size didn't decrease

    size_change_pct = ((old_comparable - new_comparable) / old_comparable * 100).quantize(
        Decimal("0.01")
    )
    if size_change_pct < min_size_decrease_pct:
        return None

    # Check existing events to avoid duplicates
    existing = session.execute(
        select(ShrinkflationEvent).where(
            and_(
                ShrinkflationEvent.normalized_product_id == product.id,
                ShrinkflationEvent.old_size == product.size,
                ShrinkflationEvent.new_size == new_size,
            )
        )
    ).scalar_one_or_none()

    if existing:
        return existing

    # Confidence: higher if size change is significant and price didn't drop
    confidence = Decimal("0.70")
    if size_change_pct >= Decimal("5"):
        confidence = Decimal("0.85")
    if size_change_pct >= Decimal("10"):
        confidence = Decimal("0.95")

    # Get the last known price for comparison
    old_price: Decimal | None = None
    if product.price_histories:
        latest = max(product.price_histories, key=lambda ph: ph.observed_date)
        old_price = latest.regular_price

    if old_price is not None and new_price is not None and new_price < old_price:
        # Price actually dropped — less likely to be shrinkflation
        confidence = max(Decimal("0.30"), confidence - Decimal("0.30"))

    event = ShrinkflationEvent(
        id=uuid.uuid4(),
        normalized_product_id=product.id,
        detected_date=detected_date or date.today(),
        old_size=product.size,
        new_size=new_size,
        old_unit=old_unit,
        new_unit=new_unit,
        price_at_old_size=old_price,
        price_at_new_size=new_price,
        confidence=confidence,
        notes=(
            f"Size decreased {size_change_pct}%"
            f" ({product.size} {old_unit} → {new_size} {new_unit})"
        ),
    )
    session.add(event)
    session.flush()

    return event
