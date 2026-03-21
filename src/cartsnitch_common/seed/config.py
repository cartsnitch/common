"""Seed configuration constants."""

from datetime import date

# Random seed for deterministic output
SEED_VALUE: int = 42

# Date window: 6 months of history ending today (relative to seed baseline)
SEED_BASELINE_DATE: date = date(2026, 3, 21)
SEED_START_DATE: date = date(2025, 9, 21)
SEED_END_DATE: date = date(2026, 3, 21)

# Scale targets
NUM_STORES: int = 3
NUM_LOCATIONS_PER_STORE: int = 5  # 15 total
NUM_USERS: int = 500
NUM_ACTIVE_USERS: int = 50
NUM_USER_STORE_ACCOUNTS: int = 100
NUM_PRODUCTS: int = 500
NUM_PURCHASES: int = 5_000
NUM_PURCHASE_ITEMS: int = 25_000
NUM_PRICE_HISTORY: int = 50_000
NUM_COUPONS: int = 200
NUM_SHRINKFLATION_EVENTS: int = 20

# Price-increase products (for StickerShock detection)
# 10% of products should show a significant price increase (>10%) over the window
NUM_PRICE_INCREASE_PRODUCTS: int = 50  # ~10% of 500

# Coupon mix
COUPON_EXPIRED_PCT: float = 0.60
COUPON_ACTIVE_PCT: float = 0.40

# Items per purchase (target avg to hit 25K total from 5K purchases)
AVG_ITEMS_PER_PURCHASE: int = 5

# Price history: ~100 observations per product (500 products * 100 = 50K)
PRICE_OBS_PER_PRODUCT: int = 100
