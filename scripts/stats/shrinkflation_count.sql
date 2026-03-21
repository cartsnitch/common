-- =============================================================================
-- Stat 1: Products that shrank in the past 12 months
-- Validates: "847 products that shrank in the past 12 months" (launch announcement)
--
-- Run against production Postgres once infrastructure is available.
-- Results will drift as the 12-month window slides forward from execution date.
-- =============================================================================

-- Primary count: distinct products with ≥1 shrinkflation event in the past year
SELECT
    COUNT(DISTINCT se.normalized_product_id) AS shrinkflation_product_count
FROM shrinkflation_events se
WHERE se.detected_date >= CURRENT_DATE - INTERVAL '12 months';


-- Breakdown by product category (for deeper reporting)
SELECT
    COALESCE(np.category, 'unknown')       AS category,
    COUNT(DISTINCT se.normalized_product_id) AS products_with_shrinkflation
FROM shrinkflation_events se
JOIN normalized_products np ON np.id = se.normalized_product_id
WHERE se.detected_date >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY np.category
ORDER BY products_with_shrinkflation DESC;


-- Breakdown by confidence band (high/medium/low events)
-- Confidence >= 0.80 = "clear" shrinkflation signal
SELECT
    CASE
        WHEN se.confidence >= 0.80 THEN 'high (>=0.80)'
        WHEN se.confidence >= 0.50 THEN 'medium (0.50-0.79)'
        ELSE 'low (<0.50)'
    END                                      AS confidence_band,
    COUNT(DISTINCT se.normalized_product_id) AS products
FROM shrinkflation_events se
WHERE se.detected_date >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY confidence_band
ORDER BY MIN(se.confidence) DESC;
