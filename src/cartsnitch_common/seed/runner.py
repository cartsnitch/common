"""Seed runner: orchestrates generation and DB insertion in FK-safe order."""

import random
import time
from typing import Any

from faker import Faker
from sqlalchemy import text
from sqlalchemy.orm import Session

from cartsnitch_common.database import get_sync_session_factory
from cartsnitch_common.models.coupon import Coupon
from cartsnitch_common.models.price import PriceHistory
from cartsnitch_common.models.product import NormalizedProduct
from cartsnitch_common.models.purchase import Purchase, PurchaseItem
from cartsnitch_common.models.shrinkflation import ShrinkflationEvent
from cartsnitch_common.models.store import Store, StoreLocation
from cartsnitch_common.models.user import User, UserStoreAccount
from cartsnitch_common.seed.config import SEED_VALUE
from cartsnitch_common.seed.generators.coupons import generate_coupons
from cartsnitch_common.seed.generators.prices import generate_price_history
from cartsnitch_common.seed.generators.products import generate_products
from cartsnitch_common.seed.generators.purchases import generate_purchase_items, generate_purchases
from cartsnitch_common.seed.generators.shrinkflation import generate_shrinkflation_events
from cartsnitch_common.seed.generators.stores import generate_store_locations, generate_stores
from cartsnitch_common.seed.generators.users import generate_user_store_accounts, generate_users

# FK-safe truncation order (reverse of insertion order)
_TRUNCATE_TABLES: list[str] = [
    "shrinkflation_events",
    "coupons",
    "price_history",
    "purchase_items",
    "purchases",
    "user_store_accounts",
    "normalized_products",
    "users",
    "store_locations",
    "stores",
]


def _log(msg: str) -> None:
    print(msg, flush=True)


def _bulk_insert(session: Session, model: type, rows: list[dict[str, Any]]) -> None:
    """Insert rows using core INSERT for performance, stripping private keys."""
    if not rows:
        return
    # Strip internal keys (prefixed with _)
    clean = [{k: v for k, v in row.items() if not k.startswith("_")} for row in rows]
    session.execute(model.__table__.insert(), clean)  # type: ignore[attr-defined]


def run_seed(
    database_url: str | None = None,
    seed_value: int = SEED_VALUE,
    dry_run: bool = False,
) -> None:
    """Generate and insert all seed data.

    Args:
        database_url: Optional override for the DB connection URL.
        seed_value: Random seed for deterministic output.
        dry_run: If True, print planned counts without touching the DB.
    """
    random.seed(seed_value)
    fake = Faker()
    Faker.seed(seed_value)

    _log("=== CartSnitch Seed Data Generator ===")
    _log(f"Seed: {seed_value}")

    # --- Generation phase ---
    t0 = time.monotonic()

    _log("Generating stores...")
    stores = generate_stores()
    _log(f"  {len(stores)} stores ({time.monotonic() - t0:.2f}s)")

    _log("Generating store locations...")
    store_locations = generate_store_locations(stores)
    _log(f"  {len(store_locations)} store locations ({time.monotonic() - t0:.2f}s)")

    _log("Generating users...")
    users = generate_users(fake)
    _log(f"  {len(users)} users ({time.monotonic() - t0:.2f}s)")

    _log("Generating user store accounts...")
    user_store_accounts = generate_user_store_accounts(users, stores)
    _log(f"  {len(user_store_accounts)} user store accounts ({time.monotonic() - t0:.2f}s)")

    _log("Generating products...")
    products = generate_products(fake)
    _log(f"  {len(products)} products ({time.monotonic() - t0:.2f}s)")

    _log("Generating purchases...")
    purchases = generate_purchases(users, stores, store_locations)
    _log(f"  {len(purchases)} purchases ({time.monotonic() - t0:.2f}s)")

    _log("Generating purchase items...")
    purchase_items = generate_purchase_items(purchases, products)
    _log(f"  {len(purchase_items)} purchase items ({time.monotonic() - t0:.2f}s)")

    _log("Generating price history...")
    price_history = generate_price_history(products, stores, purchase_items)
    _log(f"  {len(price_history)} price history records ({time.monotonic() - t0:.2f}s)")

    _log("Generating coupons...")
    coupons = generate_coupons(fake, products, stores)
    _log(f"  {len(coupons)} coupons ({time.monotonic() - t0:.2f}s)")

    _log("Generating shrinkflation events...")
    shrinkflation_events = generate_shrinkflation_events(products)
    _log(f"  {len(shrinkflation_events)} shrinkflation events ({time.monotonic() - t0:.2f}s)")

    _log("")
    _log("=== Summary ===")
    _log(f"  stores:               {len(stores)}")
    _log(f"  store_locations:      {len(store_locations)}")
    _log(f"  users:                {len(users)}")
    _log(f"  user_store_accounts:  {len(user_store_accounts)}")
    _log(f"  normalized_products:  {len(products)}")
    _log(f"  purchases:            {len(purchases)}")
    _log(f"  purchase_items:       {len(purchase_items)}")
    _log(f"  price_history:        {len(price_history)}")
    _log(f"  coupons:              {len(coupons)}")
    _log(f"  shrinkflation_events: {len(shrinkflation_events)}")

    if dry_run:
        _log("")
        _log("Dry run — no data written.")
        return

    # --- DB insertion phase ---
    factory = get_sync_session_factory(database_url)
    with factory() as session:
        _log("")
        _log("Truncating tables (reverse FK order)...")
        for table in _TRUNCATE_TABLES:
            session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        _log("  done")

        _log("Inserting stores...")
        _bulk_insert(session, Store, stores)
        _log(f"  {len(stores)} inserted")

        _log("Inserting store locations...")
        _bulk_insert(session, StoreLocation, store_locations)
        _log(f"  {len(store_locations)} inserted")

        _log("Inserting users...")
        _bulk_insert(session, User, users)
        _log(f"  {len(users)} inserted")

        _log("Inserting user store accounts...")
        _bulk_insert(session, UserStoreAccount, user_store_accounts)
        _log(f"  {len(user_store_accounts)} inserted")

        _log("Inserting products...")
        _bulk_insert(session, NormalizedProduct, products)
        _log(f"  {len(products)} inserted")

        _log("Inserting purchases...")
        _bulk_insert(session, Purchase, purchases)
        _log(f"  {len(purchases)} inserted")

        _log("Inserting purchase items...")
        _bulk_insert(session, PurchaseItem, purchase_items)
        _log(f"  {len(purchase_items)} inserted")

        _log("Inserting price history...")
        _bulk_insert(session, PriceHistory, price_history)
        _log(f"  {len(price_history)} inserted")

        _log("Inserting coupons...")
        _bulk_insert(session, Coupon, coupons)
        _log(f"  {len(coupons)} inserted")

        _log("Inserting shrinkflation events...")
        _bulk_insert(session, ShrinkflationEvent, shrinkflation_events)
        _log(f"  {len(shrinkflation_events)} inserted")

        session.commit()

    elapsed = time.monotonic() - t0
    _log("")
    _log(f"Seed complete in {elapsed:.1f}s")
