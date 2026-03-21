#!/usr/bin/env python3
"""
validate_launch_stats.py — Validate CartSnitch launch announcement statistics.

Validates two statistics from content/marketing/launch-announcement.md:
  1. "847 products that shrank in the past 12 months"
  2. "$336/year potential savings from buying the same items at the cheapest store"

Usage:
    DATABASE_URL=postgresql+asyncpg://... python scripts/stats/validate_launch_stats.py
    python scripts/stats/validate_launch_stats.py --freq 20    # change purchase frequency
    python scripts/stats/validate_launch_stats.py --stat 1     # run stat 1 only
    python scripts/stats/validate_launch_stats.py --stat 2     # run stat 2 only

NOTE: Production infrastructure is not yet deployed (CAR-99, CAR-104). This script
cannot be run against real data until those are complete. The data model has been
verified to support both queries.

Ref: CAR-162
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# ──────────────────────────────────────────────────────────────────────────────
# Configuration / assumptions
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_PURCHASE_FREQUENCY_PER_YEAR: int = 26
"""Default purchase frequency assumption.

26 = roughly every 2 weeks for a typical grocery staple.
Adjust with --freq to explore sensitivity.
"""

PRICE_LOOKBACK_DAYS: int = 90
"""How many days back to look for a "current" price observation."""

MIN_STORES_FOR_COMPARISON: int = 2
"""Minimum number of distinct stores a product must appear at to be eligible."""


# ──────────────────────────────────────────────────────────────────────────────
# Stat 1: shrinkflation count
# ──────────────────────────────────────────────────────────────────────────────

SHRINKFLATION_COUNT_SQL = sa.text("""
    SELECT COUNT(DISTINCT se.normalized_product_id) AS shrinkflation_product_count
    FROM shrinkflation_events se
    WHERE se.detected_date >= CURRENT_DATE - INTERVAL '12 months'
""")

SHRINKFLATION_BY_CATEGORY_SQL = sa.text("""
    SELECT
        COALESCE(np.category, 'unknown') AS category,
        COUNT(DISTINCT se.normalized_product_id) AS product_count
    FROM shrinkflation_events se
    JOIN normalized_products np ON np.id = se.normalized_product_id
    WHERE se.detected_date >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY np.category
    ORDER BY product_count DESC
""")


async def run_stat_1(session: AsyncSession) -> None:
    """Validate: 847 products shrank in the past 12 months."""
    print("\n" + "=" * 70)
    print("STAT 1: Products with shrinkflation events in the past 12 months")
    print("Expected: ~847")
    print("=" * 70)

    result = await session.execute(SHRINKFLATION_COUNT_SQL)
    row = result.fetchone()
    count = row[0] if row else 0
    print(f"\n  Distinct products: {count:,}")

    announced = 847
    delta = count - announced
    pct = (abs(delta) / announced * 100) if announced else 0
    status = "✓ MATCHES" if abs(delta) <= 10 else f"⚠ DIFFERS by {delta:+d} ({pct:.1f}%)"
    print(f"  Announced value:   {announced:,}")
    print(f"  Status:            {status}")

    print("\n  Breakdown by category:")
    cat_result = await session.execute(SHRINKFLATION_BY_CATEGORY_SQL)
    for cat_row in cat_result.fetchall():
        print(f"    {cat_row[0]:<20s}  {cat_row[1]:>5,}")


# ──────────────────────────────────────────────────────────────────────────────
# Stat 2: annual savings potential
# ──────────────────────────────────────────────────────────────────────────────


def savings_summary_sql(freq: int, lookback_days: int, min_stores: int) -> sa.TextClause:
    """Build the savings summary query with runtime parameters."""
    return sa.text(f"""
        WITH latest_prices AS (
            SELECT DISTINCT ON (ph.normalized_product_id, ph.store_id)
                ph.normalized_product_id,
                ph.store_id,
                ph.regular_price AS current_price
            FROM price_history ph
            WHERE ph.observed_date >= CURRENT_DATE - INTERVAL '{lookback_days} days'
              AND ph.regular_price > 0
            ORDER BY ph.normalized_product_id, ph.store_id, ph.observed_date DESC
        ),
        product_price_spread AS (
            SELECT
                lp.normalized_product_id,
                COUNT(DISTINCT lp.store_id)           AS store_count,
                MIN(lp.current_price)                 AS cheapest_price,
                AVG(lp.current_price)                 AS avg_price
            FROM latest_prices lp
            GROUP BY lp.normalized_product_id
            HAVING COUNT(DISTINCT lp.store_id) >= {min_stores}
        )
        SELECT
            COUNT(*)                                           AS eligible_products,
            ROUND(AVG(avg_price - cheapest_price)::numeric, 4) AS avg_savings_per_purchase,
            ROUND(SUM((avg_price - cheapest_price) * {freq})::numeric, 2)
                                                               AS total_annual_savings
        FROM product_price_spread
    """)


def savings_top_products_sql(freq: int, lookback_days: int, min_stores: int) -> sa.TextClause:
    """Top 20 products by annual savings opportunity."""
    return sa.text(f"""
        WITH latest_prices AS (
            SELECT DISTINCT ON (ph.normalized_product_id, ph.store_id)
                ph.normalized_product_id,
                ph.store_id,
                ph.regular_price AS current_price
            FROM price_history ph
            WHERE ph.observed_date >= CURRENT_DATE - INTERVAL '{lookback_days} days'
              AND ph.regular_price > 0
            ORDER BY ph.normalized_product_id, ph.store_id, ph.observed_date DESC
        ),
        product_price_spread AS (
            SELECT
                lp.normalized_product_id,
                COUNT(DISTINCT lp.store_id)  AS store_count,
                MIN(lp.current_price)        AS cheapest_price,
                AVG(lp.current_price)        AS avg_price
            FROM latest_prices lp
            GROUP BY lp.normalized_product_id
            HAVING COUNT(DISTINCT lp.store_id) >= {min_stores}
        )
        SELECT
            np.canonical_name,
            np.brand,
            np.category,
            ROUND((pps.avg_price - pps.cheapest_price)::numeric, 2)        AS savings_per_purchase,
            ROUND(((pps.avg_price - pps.cheapest_price) * {freq})::numeric, 2) AS annual_savings
        FROM product_price_spread pps
        JOIN normalized_products np ON np.id = pps.normalized_product_id
        ORDER BY annual_savings DESC
        LIMIT 20
    """)


async def run_stat_2(session: AsyncSession, freq: int) -> None:
    """Validate: $336/year potential savings from cross-store price comparison."""
    print("\n" + "=" * 70)
    print("STAT 2: Annual savings potential from buying at cheapest store")
    print(
        f"Assumptions: purchase freq={freq}x/year, price lookback={PRICE_LOOKBACK_DAYS}d, "
        f"min_stores={MIN_STORES_FOR_COMPARISON}"
    )
    print("Expected: ~$336/year")
    print("=" * 70)

    result = await session.execute(
        savings_summary_sql(freq, PRICE_LOOKBACK_DAYS, MIN_STORES_FOR_COMPARISON)
    )
    row = result.fetchone()
    if not row or row[0] == 0:
        print("\n  No eligible products found. Is production data loaded?")
        return

    eligible, avg_save, total_annual = row
    print(f"\n  Eligible products (in 2+ stores): {eligible:,}")
    print(f"  Avg savings per purchase:          ${avg_save:.4f}")
    print(f"  Estimated annual savings:          ${total_annual:,.2f}")

    announced = Decimal("336.00")
    delta = total_annual - announced
    pct = abs(delta) / announced * 100
    # Allow ±10% tolerance for frequency assumption variance
    status = "✓ WITHIN 10%" if pct <= 10 else f"⚠ DIFFERS by ${delta:+.2f} ({pct:.1f}%)"
    print(f"  Announced value:                   ${announced:,.2f}")
    print(f"  Status:                            {status}")

    print("\n  Sensitivity (same data, different frequency assumptions):")
    for alt_freq in (13, 20, 26, 40, 52):
        alt = float(avg_save) * int(eligible) * alt_freq
        marker = " ← default" if alt_freq == freq else ""
        print(f"    {alt_freq:>2}x/year:  ${alt:>8,.2f}{marker}")

    print("\n  Top 20 products by annual savings opportunity:")
    top_result = await session.execute(
        savings_top_products_sql(freq, PRICE_LOOKBACK_DAYS, MIN_STORES_FOR_COMPARISON)
    )
    print(f"  {'Product':<40s}  {'Brand':<20s}  {'Save/Buy':>8}  {'Annual':>8}")
    print(f"  {'-' * 40}  {'-' * 20}  {'-' * 8}  {'-' * 8}")
    for r in top_result.fetchall():
        name = (r[0] or "")[:39]
        brand = (r[1] or "")[:19]
        print(f"  {name:<40s}  {brand:<20s}  ${r[3]:>7.2f}  ${r[4]:>7.2f}")


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────


async def main(stat: int | None, freq: int) -> None:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable is not set.", file=sys.stderr)
        print("Set it to your production Postgres URL, e.g.:", file=sys.stderr)
        print("  export DATABASE_URL=postgresql+asyncpg://user:pass@host/db", file=sys.stderr)
        sys.exit(1)

    engine = create_async_engine(db_url, echo=False)
    async with AsyncSession(engine) as session:
        if stat is None or stat == 1:
            await run_stat_1(session)
        if stat is None or stat == 2:
            await run_stat_2(session, freq)

    await engine.dispose()
    print("\nDone.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--stat",
        type=int,
        choices=[1, 2],
        default=None,
        help="Run only stat 1 or stat 2 (default: both)",
    )
    parser.add_argument(
        "--freq",
        type=int,
        default=DEFAULT_PURCHASE_FREQUENCY_PER_YEAR,
        help=(
            "Purchase frequency per product per year "
            f"(default: {DEFAULT_PURCHASE_FREQUENCY_PER_YEAR})"
        ),
    )
    args = parser.parse_args()
    asyncio.run(main(stat=args.stat, freq=args.freq))
