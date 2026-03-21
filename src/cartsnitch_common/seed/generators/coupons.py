"""Generate Coupon seed data."""

import random
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from faker import Faker

from cartsnitch_common.constants import DiscountType
from cartsnitch_common.seed.config import (
    COUPON_EXPIRED_PCT,
    NUM_COUPONS,
    SEED_END_DATE,
    SEED_START_DATE,
)


def _decimal(val: float) -> Decimal:
    return Decimal(str(round(val, 2)))


_COUPON_TITLES: list[str] = [
    "Save {val} on {product}",
    "{val} off your next {product} purchase",
    "Get {val} off {product}",
    "Buy {product}, save {val}",
    "Weekend special: {val} off {product}",
    "Member exclusive: {val} off {product}",
    "Digital coupon: {val} off {product}",
]


def generate_coupons(
    fake: Faker,
    products: list[dict],
    stores: list[dict],
) -> list[dict]:
    """Return NUM_COUPONS coupon records with realistic mix of active/expired."""
    now = datetime.now(tz=UTC)
    today = SEED_END_DATE
    coupons = []

    num_expired = int(NUM_COUPONS * COUPON_EXPIRED_PCT)
    num_active = NUM_COUPONS - num_expired

    def make_coupon(is_active: bool) -> dict:
        store = random.choice(stores)
        product = random.choice(products) if random.random() > 0.1 else None
        product_name = product["canonical_name"].split(" ", 2)[-1] if product else "any item"

        discount_type = random.choice(list(DiscountType))

        if discount_type == DiscountType.PERCENT:
            discount_value = _decimal(random.choice([5, 10, 15, 20, 25, 30]))
            title = f"Save {int(discount_value)}% on {product_name}"
        elif discount_type == DiscountType.FIXED:
            discount_value = _decimal(random.choice([0.50, 1.00, 1.50, 2.00, 2.50, 3.00, 5.00]))
            title = f"Save ${discount_value} on {product_name}"
        elif discount_type == DiscountType.BOGO:
            discount_value = None
            title = f"BOGO: Buy one {product_name}, get one free"
        else:  # BUY_X_GET_Y
            discount_value = None
            title = f"Buy 2 {product_name}, get 1 free"

        if is_active:
            valid_from = today - timedelta(days=random.randint(1, 30))
            valid_to = today + timedelta(days=random.randint(1, 60))
        else:
            valid_to = today - timedelta(days=random.randint(1, 180))
            valid_from = valid_to - timedelta(days=random.randint(7, 30))

        requires_clip = random.random() > 0.5
        coupon_code = fake.bothify(text="??##-??##").upper() if not requires_clip else None
        min_purchase = _decimal(random.choice([0, 0, 0, 5.00, 10.00, 15.00])) or None

        scraped_at = datetime(
            SEED_START_DATE.year, SEED_START_DATE.month, SEED_START_DATE.day, tzinfo=UTC
        ) + timedelta(days=random.randint(0, 180))

        return {
            "id": uuid.uuid4(),
            "store_id": store["id"],
            "normalized_product_id": product["id"] if product else None,
            "title": title,
            "description": fake.sentence(nb_words=10),
            "discount_type": discount_type,
            "discount_value": discount_value,
            "min_purchase": min_purchase,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "requires_clip": requires_clip,
            "coupon_code": coupon_code,
            "source_url": None,
            "scraped_at": scraped_at,
            "created_at": now,
            "updated_at": now,
        }

    for _ in range(num_expired):
        coupons.append(make_coupon(is_active=False))
    for _ in range(num_active):
        coupons.append(make_coupon(is_active=True))

    random.shuffle(coupons)
    return coupons
