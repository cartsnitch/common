"""Generate Purchase and PurchaseItem seed data."""

import random
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from cartsnitch_common.seed.config import (
    NUM_PURCHASE_ITEMS,
    NUM_PURCHASES,
    SEED_END_DATE,
    SEED_START_DATE,
)

_DATE_RANGE_DAYS = (SEED_END_DATE - SEED_START_DATE).days


def _random_date() -> date:
    return SEED_START_DATE + timedelta(days=random.randint(0, _DATE_RANGE_DAYS))


def _decimal(val: float, places: int = 2) -> Decimal:
    return Decimal(str(round(val, places)))


def generate_purchases(
    users: list[dict],
    stores: list[dict],
    store_locations: list[dict],
) -> list[dict]:
    """Return NUM_PURCHASES purchase records."""
    now = datetime.now(tz=UTC)
    active_users = [u for u in users if u["_active"]]
    inactive_users = [u for u in users if not u["_active"]]

    # Build location index by store_id
    locs_by_store: dict = {}
    for loc in store_locations:
        locs_by_store.setdefault(loc["store_id"], []).append(loc)

    purchases = []
    seen_receipts: set[tuple] = set()

    # Active users get 80% of purchases
    active_count = int(NUM_PURCHASES * 0.8)
    inactive_count = NUM_PURCHASES - active_count

    def make_purchase(user: dict, store: dict) -> dict | None:
        receipt_id = f"RCT-{random.randint(100000, 999999)}"
        key = (user["id"], store["id"], receipt_id)
        if key in seen_receipts:
            return None
        seen_receipts.add(key)
        subtotal = _decimal(random.uniform(5.0, 150.0))
        tax = _decimal(float(subtotal) * 0.06)
        savings = _decimal(random.uniform(0.0, float(subtotal) * 0.3))
        total = _decimal(float(subtotal) + float(tax) - float(savings))
        purchase_date = _random_date()
        store_locs = locs_by_store.get(store["id"], [])
        store_location_id = random.choice(store_locs)["id"] if store_locs else None
        ingested_at = datetime(
            purchase_date.year, purchase_date.month, purchase_date.day, tzinfo=UTC
        ) + timedelta(hours=random.randint(1, 48))
        return {
            "id": uuid.uuid4(),
            "user_id": user["id"],
            "store_id": store["id"],
            "store_location_id": store_location_id,
            "receipt_id": receipt_id,
            "purchase_date": purchase_date,
            "total": total,
            "subtotal": subtotal,
            "tax": tax,
            "savings_total": savings if float(savings) > 0 else None,
            "source_url": None,
            "raw_data": None,
            "ingested_at": ingested_at,
            "created_at": now,
            "updated_at": now,
        }

    for _ in range(active_count):
        user = random.choice(active_users)
        store = random.choice(stores)
        p = make_purchase(user, store)
        if p:
            purchases.append(p)

    for _ in range(inactive_count):
        user = random.choice(inactive_users)
        store = random.choice(stores)
        p = make_purchase(user, store)
        if p:
            purchases.append(p)

    return purchases[:NUM_PURCHASES]


def generate_purchase_items(
    purchases: list[dict],
    products: list[dict],
) -> list[dict]:
    """Return ~NUM_PURCHASE_ITEMS purchase item records distributed across purchases."""
    now = datetime.now(tz=UTC)
    items: list[dict] = []
    total_target = NUM_PURCHASE_ITEMS
    num_purchases = len(purchases)

    # Distribute items: avg 5 per purchase with variance
    for i, purchase in enumerate(purchases):
        # Remaining purchases get proportional share
        remaining_purchases = num_purchases - i
        remaining_items = total_target - len(items)
        if remaining_purchases <= 0 or remaining_items <= 0:
            break
        avg = remaining_items / remaining_purchases
        count = max(1, min(15, int(random.gauss(avg, 2))))
        count = min(count, remaining_items)

        for _ in range(count):
            product = random.choice(products)
            unit_price = _decimal(random.uniform(0.99, 25.99))
            quantity = Decimal("1.000")
            extended_price = _decimal(float(unit_price) * float(quantity))
            has_sale = random.random() > 0.7
            sale_price = (
                _decimal(float(unit_price) * random.uniform(0.7, 0.95)) if has_sale else None
            )
            has_coupon = random.random() > 0.85
            coupon_discount = _decimal(random.uniform(0.25, 2.00)) if has_coupon else None

            upc = None
            if product["upc_variants"]:
                upc = random.choice(product["upc_variants"])

            items.append(
                {
                    "id": uuid.uuid4(),
                    "purchase_id": purchase["id"],
                    "product_name_raw": product["canonical_name"],
                    "upc": upc,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "extended_price": extended_price,
                    "regular_price": unit_price,
                    "sale_price": sale_price,
                    "coupon_discount": coupon_discount,
                    "loyalty_discount": None,
                    "category_raw": product["category"].value if product["category"] else None,
                    "normalized_product_id": product["id"],
                    "created_at": now,
                    "updated_at": now,
                }
            )

    return items
