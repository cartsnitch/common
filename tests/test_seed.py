"""Tests for the seed data generator."""

import random

from faker import Faker

from cartsnitch_common.seed.config import (
    NUM_ACTIVE_USERS,
    NUM_COUPONS,
    NUM_PRICE_HISTORY,
    NUM_PRODUCTS,
    NUM_PURCHASE_ITEMS,
    NUM_PURCHASES,
    NUM_SHRINKFLATION_EVENTS,
    NUM_STORES,
    NUM_USERS,
    SEED_END_DATE,
    SEED_START_DATE,
    SEED_VALUE,
)
from cartsnitch_common.seed.generators.coupons import generate_coupons
from cartsnitch_common.seed.generators.prices import generate_price_history
from cartsnitch_common.seed.generators.products import generate_products
from cartsnitch_common.seed.generators.purchases import generate_purchase_items, generate_purchases
from cartsnitch_common.seed.generators.shrinkflation import generate_shrinkflation_events
from cartsnitch_common.seed.generators.stores import generate_store_locations, generate_stores
from cartsnitch_common.seed.generators.users import generate_users


def _seed() -> None:
    random.seed(SEED_VALUE)
    Faker.seed(SEED_VALUE)


def _make_fake() -> Faker:
    return Faker()


# ---------------------------------------------------------------------------
# Stores
# ---------------------------------------------------------------------------


def test_generate_stores_count() -> None:
    stores = generate_stores()
    assert len(stores) == NUM_STORES


def test_generate_stores_deterministic() -> None:
    stores_a = generate_stores()
    stores_b = generate_stores()
    # Stores are fixed (no RNG), so slugs are stable
    slugs_a = {s["slug"] for s in stores_a}
    slugs_b = {s["slug"] for s in stores_b}
    assert slugs_a == slugs_b


def test_generate_store_locations_count() -> None:
    stores = generate_stores()
    locs = generate_store_locations(stores)
    assert len(locs) == 15  # 3 stores * 5 locations


def test_generate_store_locations_fk() -> None:
    stores = generate_stores()
    locs = generate_store_locations(stores)
    store_ids = {s["id"] for s in stores}
    for loc in locs:
        assert loc["store_id"] in store_ids


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


def test_generate_users_count() -> None:
    _seed()
    fake = _make_fake()
    users = generate_users(fake)
    assert len(users) == NUM_USERS


def test_generate_users_active_count() -> None:
    _seed()
    fake = _make_fake()
    users = generate_users(fake)
    active = [u for u in users if u["_active"]]
    assert len(active) == NUM_ACTIVE_USERS


def test_generate_users_deterministic() -> None:
    _seed()
    fake_a = _make_fake()
    users_a = generate_users(fake_a)

    _seed()
    fake_b = _make_fake()
    users_b = generate_users(fake_b)

    # Emails should match (same seed → same Faker output)
    emails_a = [u["email"] for u in users_a]
    emails_b = [u["email"] for u in users_b]
    assert emails_a == emails_b


def test_generate_users_unique_emails() -> None:
    _seed()
    fake = _make_fake()
    users = generate_users(fake)
    emails = [u["email"] for u in users]
    assert len(emails) == len(set(emails))


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------


def test_generate_products_count() -> None:
    _seed()
    fake = _make_fake()
    products = generate_products(fake)
    assert len(products) == NUM_PRODUCTS


def test_generate_products_deterministic() -> None:
    _seed()
    fake_a = _make_fake()
    products_a = generate_products(fake_a)

    _seed()
    fake_b = _make_fake()
    products_b = generate_products(fake_b)

    names_a = [p["canonical_name"] for p in products_a]
    names_b = [p["canonical_name"] for p in products_b]
    assert names_a == names_b


def test_generate_products_have_categories() -> None:
    _seed()
    fake = _make_fake()
    products = generate_products(fake)
    for product in products:
        assert product["category"] is not None


def test_generate_products_have_upc_variants() -> None:
    _seed()
    fake = _make_fake()
    products = generate_products(fake)
    for product in products:
        assert product["upc_variants"]
        assert isinstance(product["upc_variants"], list)
        assert len(product["upc_variants"]) >= 1


# ---------------------------------------------------------------------------
# Purchases
# ---------------------------------------------------------------------------


def test_generate_purchases_count() -> None:
    _seed()
    fake = _make_fake()
    stores = generate_stores()
    store_locs = generate_store_locations(stores)
    users = generate_users(fake)
    purchases = generate_purchases(users, stores, store_locs)
    assert len(purchases) == NUM_PURCHASES


def test_generate_purchases_fk() -> None:
    _seed()
    fake = _make_fake()
    stores = generate_stores()
    store_locs = generate_store_locations(stores)
    users = generate_users(fake)
    purchases = generate_purchases(users, stores, store_locs)

    user_ids = {u["id"] for u in users}
    store_ids = {s["id"] for s in stores}
    for p in purchases:
        assert p["user_id"] in user_ids
        assert p["store_id"] in store_ids


def test_generate_purchase_items_count() -> None:
    _seed()
    fake = _make_fake()
    stores = generate_stores()
    store_locs = generate_store_locations(stores)
    users = generate_users(fake)
    purchases = generate_purchases(users, stores, store_locs)
    products = generate_products(fake)
    items = generate_purchase_items(purchases, products)
    # Should be close to target (within 20%)
    assert abs(len(items) - NUM_PURCHASE_ITEMS) < NUM_PURCHASE_ITEMS * 0.20


def test_generate_purchase_items_fk() -> None:
    _seed()
    fake = _make_fake()
    stores = generate_stores()
    store_locs = generate_store_locations(stores)
    users = generate_users(fake)
    purchases = generate_purchases(users, stores, store_locs)
    products = generate_products(fake)
    items = generate_purchase_items(purchases, products)

    purchase_ids = {p["id"] for p in purchases}
    product_ids = {p["id"] for p in products}
    for item in items:
        assert item["purchase_id"] in purchase_ids
        assert item["normalized_product_id"] in product_ids


# ---------------------------------------------------------------------------
# Price History
# ---------------------------------------------------------------------------


def test_generate_price_history_count() -> None:
    _seed()
    fake = _make_fake()
    stores = generate_stores()
    store_locs = generate_store_locations(stores)
    users = generate_users(fake)
    purchases = generate_purchases(users, stores, store_locs)
    products = generate_products(fake)
    items = generate_purchase_items(purchases, products)
    prices = generate_price_history(products, stores, items)
    # Should be within 10% of target
    assert abs(len(prices) - NUM_PRICE_HISTORY) < NUM_PRICE_HISTORY * 0.10


def test_generate_price_history_fk() -> None:
    _seed()
    fake = _make_fake()
    stores = generate_stores()
    store_locs = generate_store_locations(stores)
    users = generate_users(fake)
    purchases = generate_purchases(users, stores, store_locs)
    products = generate_products(fake)
    items = generate_purchase_items(purchases, products)
    prices = generate_price_history(products, stores, items)

    product_ids = {p["id"] for p in products}
    store_ids = {s["id"] for s in stores}
    for ph in prices:
        assert ph["normalized_product_id"] in product_ids
        assert ph["store_id"] in store_ids
        assert ph["regular_price"] > 0


def test_price_history_dates_in_range() -> None:
    _seed()
    fake = _make_fake()
    stores = generate_stores()
    store_locs = generate_store_locations(stores)
    users = generate_users(fake)
    purchases = generate_purchases(users, stores, store_locs)
    products = generate_products(fake)
    items = generate_purchase_items(purchases, products)
    prices = generate_price_history(products, stores, items)

    for ph in prices:
        assert SEED_START_DATE <= ph["observed_date"] <= SEED_END_DATE


# ---------------------------------------------------------------------------
# Coupons
# ---------------------------------------------------------------------------


def test_generate_coupons_count() -> None:
    _seed()
    fake = _make_fake()
    stores = generate_stores()
    products = generate_products(fake)
    coupons = generate_coupons(fake, products, stores)
    assert len(coupons) == NUM_COUPONS


def test_generate_coupons_mix() -> None:
    """Verify ~60% expired and ~40% active."""
    _seed()
    fake = _make_fake()
    stores = generate_stores()
    products = generate_products(fake)
    coupons = generate_coupons(fake, products, stores)

    expired = [c for c in coupons if c["valid_to"] < SEED_END_DATE]
    active = [c for c in coupons if c["valid_to"] >= SEED_END_DATE]
    # Allow ±15% variance from target
    assert len(expired) / NUM_COUPONS > 0.45
    assert len(active) / NUM_COUPONS > 0.25


# ---------------------------------------------------------------------------
# Shrinkflation
# ---------------------------------------------------------------------------


def test_generate_shrinkflation_count() -> None:
    _seed()
    fake = _make_fake()
    products = generate_products(fake)
    events = generate_shrinkflation_events(products)
    assert len(events) == NUM_SHRINKFLATION_EVENTS


def test_generate_shrinkflation_fk() -> None:
    _seed()
    fake = _make_fake()
    products = generate_products(fake)
    events = generate_shrinkflation_events(products)
    product_ids = {p["id"] for p in products}
    for event in events:
        assert event["normalized_product_id"] in product_ids


def test_generate_shrinkflation_price_held_or_increased() -> None:
    """Validate shrinkflation: new_size < old_size, price maintained or up."""
    _seed()
    fake = _make_fake()
    products = generate_products(fake)
    events = generate_shrinkflation_events(products)
    for event in events:
        old_size = float(event["old_size"])
        new_size = float(event["new_size"])
        assert new_size < old_size, f"Expected size reduction: {old_size} -> {new_size}"
        if event["price_at_old_size"] and event["price_at_new_size"]:
            # Price should be maintained or increased (not significantly dropped)
            assert float(event["price_at_new_size"]) >= float(event["price_at_old_size"]) * 0.95


def test_generate_shrinkflation_confidence_range() -> None:
    _seed()
    fake = _make_fake()
    products = generate_products(fake)
    events = generate_shrinkflation_events(products)
    for event in events:
        assert 0 <= float(event["confidence"]) <= 1.0


# ---------------------------------------------------------------------------
# Dry-run smoke test
# ---------------------------------------------------------------------------


def test_dry_run_does_not_raise() -> None:
    """Smoke test the full run_seed in dry-run mode."""
    from cartsnitch_common.seed.runner import run_seed

    run_seed(dry_run=True, seed_value=SEED_VALUE)
