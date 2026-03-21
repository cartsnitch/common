# Launch Announcement Validation Queries

Scripts to validate the two statistics cited in the CartSnitch launch announcement:

1. **847 products that shrank in the past 12 months**
2. **$336/year potential savings from buying the same items at the cheapest store**

## Status

These queries are written against the production data model but **cannot be run yet** — production infrastructure (CAR-99, CAR-104) is still being deployed. Once production data is available, run these scripts to confirm the cited numbers.

## Queries

### Stat 1: Shrinkflation count (`shrinkflation_count.sql`)

Counts distinct `normalized_product_id` values with at least one `ShrinkflationEvent` where `detected_date` falls within the past 12 months.

**Key assumptions:**
- "Past 12 months" is relative to query execution date (`CURRENT_DATE - INTERVAL '12 months'`).
- A product counts once even if it has multiple shrinkflation events in the window.
- The 847 figure was generated from a specific date — re-running will drift as the window slides.

### Stat 2: Annual savings potential (`savings_potential.sql`)

**Methodology:**

For each `normalized_product_id` with price observations from **two or more distinct stores** in the past 90 days:

1. Take the **most recent `regular_price`** per `(normalized_product_id, store_id)` pair.
2. Compute `cheapest_price` = MIN across stores, `avg_price` = AVG across stores.
3. `savings_per_purchase` = `avg_price - cheapest_price`.

To arrive at **annual** savings per family:

- Assume a **typical family purchases each product ~N times per year** (see `PURCHASE_FREQUENCY_PER_YEAR` constant in `validate_launch_stats.py`).
- Default assumption: products purchased on average 26×/year (~every 2 weeks for regularly bought items).
- Sum across all eligible products: `Σ(savings_per_purchase × frequency)`.

**Sensitivity knobs:**
- `PURCHASE_FREQUENCY_PER_YEAR` — adjust purchase cadence assumption
- `LOOKBACK_DAYS` — how recent a price observation must be to be "current" (default: 90 days)
- `MIN_STORES_FOR_COMPARISON` — minimum number of stores a product must appear at (default: 2)

The $336 figure assumes the defaults above. If actual purchase frequencies differ significantly, rerun `validate_launch_stats.py --freq <N>`.

## Running

```bash
# Requires DATABASE_URL env var pointing at production Postgres
python scripts/stats/validate_launch_stats.py

# Adjust purchase frequency assumption (default: 26 times/year)
python scripts/stats/validate_launch_stats.py --freq 20

# Run just stat 1 or stat 2
python scripts/stats/validate_launch_stats.py --stat 1
python scripts/stats/validate_launch_stats.py --stat 2
```

Raw SQL files (`shrinkflation_count.sql`, `savings_potential.sql`) can also be run directly with `psql`.
