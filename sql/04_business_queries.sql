-- 04_business_queries.sql
-- Purpose: Reusable executive and data-quality queries for dashboards.

-- =========================================================
-- Executive monthly KPI trend
-- =========================================================
SELECT
    DATE_TRUNC('month', order_purchase_ts)::DATE AS month_start,
    COUNT(*) AS total_orders,
    SUM(COALESCE(item_gmv, 0)) AS total_gmv,
    AVG(COALESCE(item_gmv, 0)) AS aov,
    AVG(CASE WHEN is_canceled_or_unavailable = 1 THEN 1.0 ELSE 0.0 END) AS cancellation_rate,
    AVG(avg_review_score) AS avg_review_score,
    AVG(delivery_days) AS avg_delivery_days,
    AVG(CASE WHEN is_on_time_delivery IS NULL THEN NULL ELSE is_on_time_delivery::DOUBLE END) AS on_time_delivery_rate
FROM marts.fact_orders
GROUP BY 1
ORDER BY 1;

-- =========================================================
-- Category performance
-- =========================================================
SELECT
    p.product_category_name_en AS category,
    COUNT(DISTINCT i.order_id) AS orders,
    SUM(i.gmv) AS gmv,
    AVG(i.gmv) AS avg_item_value
FROM marts.fact_order_items i
LEFT JOIN marts.dim_products p
    ON i.product_id = p.product_id
GROUP BY 1
ORDER BY gmv DESC;

-- =========================================================
-- Seller performance
-- =========================================================
SELECT
    s.seller_state,
    sp.seller_id,
    COUNT(DISTINCT sp.order_id) AS orders,
    SUM(sp.seller_gmv) AS gmv,
    AVG(sp.seller_gmv) AS avg_order_gmv
FROM marts.vw_order_seller_performance sp
LEFT JOIN marts.dim_sellers s
    ON sp.seller_id = s.seller_id
GROUP BY 1, 2
ORDER BY gmv DESC;

-- =========================================================
-- Delay bucket vs customer satisfaction
-- =========================================================
SELECT
    CASE
        WHEN delivery_days IS NULL THEN 'Not Delivered'
        WHEN delivery_days - estimated_delivery_days <= 0 THEN 'On time or early'
        WHEN delivery_days - estimated_delivery_days BETWEEN 1 AND 3 THEN '1-3 days late'
        WHEN delivery_days - estimated_delivery_days BETWEEN 4 AND 7 THEN '4-7 days late'
        ELSE '8+ days late'
    END AS delay_bucket,
    COUNT(*) AS orders,
    AVG(avg_review_score) AS avg_review_score
FROM marts.fact_orders
GROUP BY 1
ORDER BY
    CASE delay_bucket
        WHEN 'On time or early' THEN 1
        WHEN '1-3 days late' THEN 2
        WHEN '4-7 days late' THEN 3
        WHEN '8+ days late' THEN 4
        ELSE 5
    END;

-- =========================================================
-- Payment mix
-- =========================================================
SELECT
    payment_type,
    COUNT(*) AS payment_records,
    SUM(payment_value) AS payment_value,
    AVG(payment_value) AS avg_payment_value
FROM staging.stg_order_payments
GROUP BY 1
ORDER BY payment_value DESC;

-- =========================================================
-- Geography performance (customer state)
-- =========================================================
SELECT
    c.customer_state,
    COUNT(DISTINCT o.order_id) AS orders,
    SUM(COALESCE(o.item_gmv, 0)) AS gmv,
    AVG(o.avg_review_score) AS avg_review_score,
    AVG(o.delivery_days) AS avg_delivery_days
FROM marts.fact_orders o
LEFT JOIN marts.dim_customers c
    ON o.customer_id = c.customer_id
GROUP BY 1
ORDER BY gmv DESC;

-- =========================================================
-- Data quality audit summary
-- =========================================================
SELECT 'orders_missing_purchase_timestamp' AS check_name, COUNT(*) AS issue_rows
FROM staging.stg_orders
WHERE order_purchase_ts IS NULL
UNION ALL
SELECT 'orders_missing_customer_id', COUNT(*)
FROM staging.stg_orders
WHERE customer_id IS NULL
UNION ALL
SELECT 'orders_missing_delivered_customer_date_for_delivered_status', COUNT(*)
FROM staging.stg_orders
WHERE order_status = 'delivered'
  AND delivered_customer_ts IS NULL
UNION ALL
SELECT 'orders_with_estimated_delivery_before_purchase', COUNT(*)
FROM staging.stg_orders
WHERE estimated_delivery_ts < order_purchase_ts
UNION ALL
SELECT 'duplicate_order_ids_raw', COUNT(*) - COUNT(DISTINCT order_id)
FROM raw.orders
UNION ALL
SELECT 'duplicate_order_item_keys_raw', COUNT(*) - COUNT(DISTINCT CONCAT(order_id, '|', CAST(order_item_id AS VARCHAR)))
FROM raw.order_items
UNION ALL
SELECT 'duplicate_geolocation_zip_prefix_raw', COUNT(*) - COUNT(DISTINCT LPAD(CAST(geolocation_zip_code_prefix AS VARCHAR), 5, '0'))
FROM raw.geolocation;

-- =========================================================
-- Join risk demonstration: naive revenue inflation
-- =========================================================
WITH naive_join AS (
    SELECT SUM(oi.price + oi.freight_value) AS naive_gmv
    FROM staging.stg_order_items oi
    JOIN staging.stg_order_payments p
        ON oi.order_id = p.order_id
),
correct_join AS (
    SELECT SUM(item_gmv) AS trusted_gmv
    FROM marts.fact_orders
)
SELECT
    n.naive_gmv,
    c.trusted_gmv,
    n.naive_gmv - c.trusted_gmv AS gmv_overstatement
FROM naive_join n
CROSS JOIN correct_join c;
