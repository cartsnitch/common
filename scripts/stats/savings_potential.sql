-- =============================================================================
-- Stat 2: Annual savings potential from cross-store price comparison
-- Validates: "$336/year potential savings from buying the same items
--             at the cheapest store" (launch announcement)
--
-- Methodology:
--   1. For each (normalized_product_id, store_id), take the MOST RECENT
--      regular_price within the past 90 days ("current" price).
--   2. Keep only products observed at 2+ distinct stores.
--   3. For each product: savings_per_purchase = avg_price - min_price across stores.
--   4. Annualise: multiply by an assumed purchase frequency of 26x/year
--      (~every 2 weeks for regularly purchased grocery items).
--   5. Sum across all eligible products to get total annual savings potential.
--
-- Sensitivity:
--   Change the frequency constant (26) and lookback interval (90 days) to
--   explore how sensitive the $336 figure is to these assumptions.
--
-- Run against production Postgres once infrastructure is available.
-- =============================================================================

-- Step 1: most-recent price per (product, store) within the past 90 days
WITH latest_prices AS (
    SELECT DISTINCT ON (ph.normalized_product_id, ph.store_id)
        ph.normalized_product_id,
        ph.store_id,
        s.slug                 AS store_slug,
        ph.regular_price       AS current_price,
        ph.observed_date
    FROM price_history ph
    JOIN stores s ON s.id = ph.store_id
    WHERE ph.observed_date >= CURRENT_DATE - INTERVAL '90 days'
      AND ph.regular_price   > 0
    ORDER BY
        ph.normalized_product_id,
        ph.store_id,
        ph.observed_date DESC
),

-- Step 2: aggregate per product — only keep products seen at 2+ stores
product_price_spread AS (
    SELECT
        lp.normalized_product_id,
        COUNT(DISTINCT lp.store_id)         AS store_count,
        MIN(lp.current_price)               AS cheapest_price,
        AVG(lp.current_price)               AS avg_price,
        MAX(lp.current_price)               AS most_expensive_price,
        MAX(lp.current_price) - MIN(lp.current_price) AS price_range
    FROM latest_prices lp
    GROUP BY lp.normalized_product_id
    HAVING COUNT(DISTINCT lp.store_id) >= 2
),

-- Step 3: compute savings_per_purchase and annualise
--   Purchase frequency assumption: 26 purchases/year per product (~every 2 weeks)
--   This is a conservative estimate for regularly purchased grocery items.
savings_per_product AS (
    SELECT
        pps.normalized_product_id,
        np.canonical_name,
        np.category,
        pps.store_count,
        pps.cheapest_price,
        pps.avg_price,
        pps.price_range,
        ROUND(pps.avg_price - pps.cheapest_price, 2)             AS savings_per_purchase,
        ROUND((pps.avg_price - pps.cheapest_price) * 26, 2)      AS annual_savings_at_26x
    FROM product_price_spread pps
    JOIN normalized_products np ON np.id = pps.normalized_product_id
)

-- Final summary: total annual savings potential
SELECT
    COUNT(*)                                         AS eligible_product_count,
    ROUND(AVG(savings_per_purchase), 4)              AS avg_savings_per_purchase,
    ROUND(SUM(annual_savings_at_26x), 2)             AS total_annual_savings_26x_freq,
    -- Sensitivity: alternative frequencies
    ROUND(SUM(savings_per_purchase) * 20, 2)         AS total_annual_savings_20x_freq,
    ROUND(SUM(savings_per_purchase) * 52, 2)         AS total_annual_savings_52x_freq
FROM savings_per_product;


-- Per-product detail (top 50 by annual savings opportunity)
WITH latest_prices AS (
    SELECT DISTINCT ON (ph.normalized_product_id, ph.store_id)
        ph.normalized_product_id,
        ph.store_id,
        s.slug   AS store_slug,
        ph.regular_price AS current_price,
        ph.observed_date
    FROM price_history ph
    JOIN stores s ON s.id = ph.store_id
    WHERE ph.observed_date >= CURRENT_DATE - INTERVAL '90 days'
      AND ph.regular_price > 0
    ORDER BY ph.normalized_product_id, ph.store_id, ph.observed_date DESC
),
product_price_spread AS (
    SELECT
        lp.normalized_product_id,
        COUNT(DISTINCT lp.store_id)         AS store_count,
        MIN(lp.current_price)               AS cheapest_price,
        AVG(lp.current_price)               AS avg_price
    FROM latest_prices lp
    GROUP BY lp.normalized_product_id
    HAVING COUNT(DISTINCT lp.store_id) >= 2
)
SELECT
    np.canonical_name,
    np.category,
    np.brand,
    np.size,
    np.size_unit,
    pps.store_count,
    pps.cheapest_price,
    ROUND(pps.avg_price, 2)                              AS avg_price,
    ROUND(pps.avg_price - pps.cheapest_price, 2)         AS savings_per_purchase,
    ROUND((pps.avg_price - pps.cheapest_price) * 26, 2)  AS annual_savings_at_26x
FROM product_price_spread pps
JOIN normalized_products np ON np.id = pps.normalized_product_id
ORDER BY annual_savings_at_26x DESC
LIMIT 50;
