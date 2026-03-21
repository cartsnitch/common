"""Generate PriceHistory seed data with realistic patterns for StickerShock detection."""

import random
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from cartsnitch_common.constants import PriceSource
from cartsnitch_common.seed.config import (
    NUM_PRICE_HISTORY,
    NUM_PRICE_INCREASE_PRODUCTS,
    SEED_END_DATE,
    SEED_START_DATE,
)

_DATE_RANGE_DAYS = (SEED_END_DATE - SEED_START_DATE).days

# Holidays within the seed window for seasonal sales (approx)
_SALE_PERIODS: list[tuple[date, date]] = [
    (date(2025, 11, 27), date(2025, 11, 30)),  # Thanksgiving / Black Friday
    (date(2025, 12, 20), date(2025, 12, 26)),  # Christmas
    (date(2026, 1, 1), date(2026, 1, 2)),  # New Year
    (date(2026, 2, 14), date(2026, 2, 15)),  # Valentine's Day
]


def _is_sale_period(d: date) -> bool:
    return any(start <= d <= end for start, end in _SALE_PERIODS)


def _decimal(val: float) -> Decimal:
    return Decimal(str(round(val, 2)))


def _base_price_for_product(product: dict) -> float:
    """Assign a realistic base price based on category."""
    from cartsnitch_common.constants import ProductCategory

    category_ranges: dict[ProductCategory, tuple[float, float]] = {
        ProductCategory.PRODUCE: (1.49, 6.99),
        ProductCategory.DAIRY: (2.99, 8.99),
        ProductCategory.MEAT: (4.99, 19.99),
        ProductCategory.BAKERY: (2.49, 7.99),
        ProductCategory.FROZEN: (3.99, 12.99),
        ProductCategory.PANTRY: (1.99, 9.99),
        ProductCategory.BEVERAGES: (0.99, 6.99),
        ProductCategory.SNACKS: (2.49, 6.99),
        ProductCategory.HOUSEHOLD: (3.99, 19.99),
        ProductCategory.PERSONAL_CARE: (3.99, 14.99),
    }
    cat = product.get("category")
    lo, hi = category_ranges.get(cat, (1.99, 9.99))
    return random.uniform(lo, hi)


def generate_price_history(
    products: list[dict],
    stores: list[dict],
    purchase_items: list[dict],
) -> list[dict]:
    """Return ~NUM_PRICE_HISTORY price history records with realistic patterns.

    Pattern types (assigned per product):
    - sudden_jump: flat then >10% price increase at a random point
    - gradual_creep: slow steady increase over the window
    - stable: nearly flat price with small noise
    - sale_driven: drops during holiday periods, returns after
    - volatile: random walk

    10% of products (NUM_PRICE_INCREASE_PRODUCTS) will show a detectable
    price increase (>10%) that StickerShock can flag.
    """
    now = datetime.now(tz=UTC)
    records: list[dict] = []

    # Build purchase-item lookup: (product_id, store_id) -> [purchase_item_id]
    item_lookup: dict[tuple, list[uuid.UUID]] = {}
    for item in purchase_items:
        key = (item["normalized_product_id"], item.get("_store_id"))
        item_lookup.setdefault(key, []).append(item["id"])

    total = NUM_PRICE_HISTORY
    per_product_per_store = total // (len(products) * len(stores))
    per_product_per_store = max(per_product_per_store, 1)

    # Assign patterns
    product_patterns: list[str] = []
    price_increase_indices = set(random.sample(range(len(products)), NUM_PRICE_INCREASE_PRODUCTS))
    pattern_pool = ["sale_driven", "stable", "gradual_creep", "volatile"]
    for i in range(len(products)):
        if i in price_increase_indices:
            product_patterns.append(random.choice(["sudden_jump", "gradual_creep"]))
        else:
            product_patterns.append(random.choice(pattern_pool))

    for i, product in enumerate(products):
        pattern = product_patterns[i]
        base_price = _base_price_for_product(product)

        # Jump point for sudden_jump (50-80% through window)
        jump_day = int(_DATE_RANGE_DAYS * random.uniform(0.5, 0.8))
        jump_factor = random.uniform(1.10, 1.25)  # 10-25% increase

        for store in stores:
            # Generate obs dates spread across the window
            obs_days = sorted(
                random.sample(
                    range(_DATE_RANGE_DAYS + 1),
                    min(per_product_per_store, _DATE_RANGE_DAYS + 1),
                )
            )

            for day_offset in obs_days:
                obs_date = SEED_START_DATE + timedelta(days=day_offset)
                progress = day_offset / max(_DATE_RANGE_DAYS, 1)

                # Compute regular price by pattern
                if pattern == "sudden_jump":
                    if day_offset < jump_day:
                        price = base_price + random.uniform(-0.05, 0.05)
                    else:
                        price = base_price * jump_factor + random.uniform(-0.05, 0.05)
                elif pattern == "gradual_creep":
                    price = base_price * (1 + 0.12 * progress) + random.uniform(-0.10, 0.10)
                elif pattern == "stable":
                    price = base_price + random.uniform(-0.10, 0.10)
                elif pattern == "volatile":
                    price = base_price * random.uniform(0.85, 1.15)
                else:
                    price = base_price + random.uniform(-0.05, 0.05)

                price = max(0.99, price)
                regular_price = _decimal(price)

                # Sale price during holiday periods
                sale_price: Decimal | None = None
                if _is_sale_period(obs_date):
                    sale_price = _decimal(price * random.uniform(0.75, 0.90))

                records.append(
                    {
                        "id": uuid.uuid4(),
                        "normalized_product_id": product["id"],
                        "store_id": store["id"],
                        "observed_date": obs_date,
                        "regular_price": regular_price,
                        "sale_price": sale_price,
                        "loyalty_price": None,
                        "coupon_price": None,
                        "source": (
                            PriceSource.RECEIPT if random.random() > 0.3 else PriceSource.CATALOG
                        ),
                        "purchase_item_id": None,
                        "created_at": now,
                        "updated_at": now,
                    }
                )

                if len(records) >= NUM_PRICE_HISTORY:
                    return records

    return records
