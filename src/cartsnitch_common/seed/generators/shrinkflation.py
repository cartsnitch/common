"""Generate ShrinkflationEvent seed data."""

import random
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from cartsnitch_common.constants import SizeUnit
from cartsnitch_common.seed.config import (
    NUM_SHRINKFLATION_EVENTS,
    SEED_END_DATE,
    SEED_START_DATE,
)

_DATE_RANGE_DAYS = (SEED_END_DATE - SEED_START_DATE).days

# Shrinkflation patterns: (old_size, new_size, unit, size_reduction_pct)
_SHRINK_PATTERNS: list[tuple[str, str, SizeUnit, float]] = [
    ("16", "14", SizeUnit.OZ, 0.125),
    ("32", "28", SizeUnit.OZ, 0.125),
    ("64", "56", SizeUnit.FL_OZ, 0.125),
    ("18", "16", SizeUnit.OZ, 0.111),
    ("20", "18", SizeUnit.OZ, 0.10),
    ("2", "1.75", SizeUnit.LB, 0.125),
    ("24", "21", SizeUnit.OZ, 0.125),
    ("12", "10.5", SizeUnit.OZ, 0.125),
    ("48", "42", SizeUnit.OZ, 0.125),
    ("8", "7", SizeUnit.OZ, 0.125),
    ("1", "0.875", SizeUnit.LB, 0.125),
    ("36", "32", SizeUnit.OZ, 0.111),
    ("6", "5", SizeUnit.CT, 0.167),
    ("12", "10", SizeUnit.CT, 0.167),
    ("100", "90", SizeUnit.CT, 0.10),
    ("16.9", "15", SizeUnit.FL_OZ, 0.112),
    ("3", "2.5", SizeUnit.LB, 0.167),
    ("40", "35", SizeUnit.OZ, 0.125),
    ("28", "24", SizeUnit.OZ, 0.143),
    ("14.5", "12.5", SizeUnit.OZ, 0.138),
]


def _decimal(val: float) -> Decimal:
    return Decimal(str(round(val, 2)))


def generate_shrinkflation_events(products: list[dict]) -> list[dict]:
    """Return NUM_SHRINKFLATION_EVENTS shrinkflation event records.

    Selects products and assigns size changes where price is maintained or
    increased despite the smaller package — valid inputs for ShrinkRay.
    """
    now = datetime.now(tz=UTC)
    events = []

    # Pick NUM_SHRINKFLATION_EVENTS unique products (prefer pantry/snacks/household)
    from cartsnitch_common.constants import ProductCategory

    preferred_cats = {
        ProductCategory.PANTRY,
        ProductCategory.SNACKS,
        ProductCategory.HOUSEHOLD,
        ProductCategory.PERSONAL_CARE,
        ProductCategory.FROZEN,
        ProductCategory.DAIRY,
        ProductCategory.BEVERAGES,
    }
    preferred = [p for p in products if p.get("category") in preferred_cats]
    fallback = [p for p in products if p not in preferred]
    pool = preferred + fallback

    selected = random.sample(pool, min(NUM_SHRINKFLATION_EVENTS, len(pool)))

    for i, product in enumerate(selected):
        pattern = _SHRINK_PATTERNS[i % len(_SHRINK_PATTERNS)]
        old_size, new_size, unit, reduction_pct = pattern

        # Detection date: at least 60 days into window so there's history before
        min_day = 60
        detected_day = random.randint(min_day, _DATE_RANGE_DAYS)
        detected_date = SEED_START_DATE + timedelta(days=detected_day)

        # Price maintained or slightly increased despite size reduction
        base_price = random.uniform(2.99, 12.99)
        price_at_old_size = _decimal(base_price)
        # flat or small increase despite size reduction
        price_at_new_size = _decimal(base_price * random.uniform(0.98, 1.08))

        confidence = _decimal(random.uniform(0.70, 0.99))

        notes = (
            f"Package reduced from {old_size}{unit} to {new_size}{unit} "
            f"({reduction_pct * 100:.1f}% reduction). "
            f"Price {'increased' if price_at_new_size > price_at_old_size else 'held steady'}."
        )

        events.append(
            {
                "id": uuid.uuid4(),
                "normalized_product_id": product["id"],
                "detected_date": detected_date,
                "old_size": old_size,
                "new_size": new_size,
                "old_unit": unit,
                "new_unit": unit,
                "price_at_old_size": price_at_old_size,
                "price_at_new_size": price_at_new_size,
                "confidence": confidence,
                "notes": notes,
                "created_at": now,
                "updated_at": now,
            }
        )

    return events
