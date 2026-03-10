-- 03_marts.sql
-- Purpose: Build trusted reporting-layer dimensions and facts.

CREATE OR REPLACE TABLE marts.dim_geography AS
SELECT
    zip_code_prefix,
    primary_city AS city,
    primary_state AS state,
    avg_latitude AS latitude,
    avg_longitude AS longitude
FROM staging.stg_geolocation_zip;

CREATE OR REPLACE TABLE marts.dim_customers AS
WITH customer_orders AS (
    SELECT
        o.customer_id,
        MIN(o.order_purchase_ts) AS first_order_ts,
        MAX(o.order_purchase_ts) AS last_order_ts,
        COUNT(*) AS total_orders
    FROM staging.stg_orders o
    GROUP BY 1
)
SELECT
    c.customer_id,
    c.customer_unique_id,
    c.customer_zip_code_prefix,
    c.customer_city,
    c.customer_state,
    g.latitude,
    g.longitude,
    co.first_order_ts,
    co.last_order_ts,
    co.total_orders
FROM staging.stg_customers c
LEFT JOIN customer_orders co
    ON c.customer_id = co.customer_id
LEFT JOIN marts.dim_geography g
    ON c.customer_zip_code_prefix = g.zip_code_prefix;

CREATE OR REPLACE TABLE marts.dim_sellers AS
SELECT
    s.seller_id,
    s.seller_zip_code_prefix,
    s.seller_city,
    s.seller_state,
    g.latitude,
    g.longitude
FROM staging.stg_sellers s
LEFT JOIN marts.dim_geography g
    ON s.seller_zip_code_prefix = g.zip_code_prefix;

CREATE OR REPLACE TABLE marts.dim_products AS
SELECT
    product_id,
    product_category_name_pt,
    product_category_name_en,
    product_name_length,
    product_description_length,
    product_photos_qty,
    product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm,
    (product_length_cm * product_height_cm * product_width_cm) AS product_volume_cm3
FROM staging.stg_products;

CREATE OR REPLACE TABLE marts.fact_order_items AS
SELECT
    oi.order_id,
    oi.order_item_id,
    o.customer_id,
    oi.product_id,
    oi.seller_id,
    o.order_status,
    o.order_purchase_ts::DATE AS purchase_date,
    oi.shipping_limit_ts,
    oi.price,
    oi.freight_value,
    (oi.price + oi.freight_value) AS gmv
FROM staging.stg_order_items oi
INNER JOIN staging.stg_orders o
    ON oi.order_id = o.order_id;

CREATE OR REPLACE TABLE marts.fact_orders AS
WITH order_item_rollup AS (
    SELECT
        order_id,
        COUNT(*) AS item_count,
        SUM(price) AS item_price_value,
        SUM(freight_value) AS item_freight_value,
        SUM(gmv) AS item_gmv
    FROM marts.fact_order_items
    GROUP BY 1
),
payment_rollup AS (
    SELECT
        order_id,
        SUM(payment_value) AS payment_value_total,
        COUNT(*) AS payment_record_count
    FROM staging.stg_order_payments
    GROUP BY 1
),
review_rollup AS (
    SELECT
        order_id,
        AVG(review_score) AS avg_review_score,
        COUNT(*) AS review_count
    FROM staging.stg_order_reviews
    GROUP BY 1
),
orders_enriched AS (
    SELECT
        o.order_id,
        o.customer_id,
        c.customer_unique_id,
        o.order_status,
        o.order_purchase_ts,
        o.order_approved_ts,
        o.delivered_carrier_ts,
        o.delivered_customer_ts,
        o.estimated_delivery_ts,
        i.item_count,
        i.item_price_value,
        i.item_freight_value,
        i.item_gmv,
        p.payment_value_total,
        p.payment_record_count,
        r.avg_review_score,
        r.review_count,
        DATE_DIFF('day', o.order_purchase_ts::DATE, o.delivered_customer_ts::DATE) AS delivery_days,
        DATE_DIFF('day', o.order_purchase_ts::DATE, o.estimated_delivery_ts::DATE) AS estimated_delivery_days
    FROM staging.stg_orders o
    LEFT JOIN order_item_rollup i
        ON o.order_id = i.order_id
    LEFT JOIN payment_rollup p
        ON o.order_id = p.order_id
    LEFT JOIN review_rollup r
        ON o.order_id = r.order_id
    LEFT JOIN staging.stg_customers c
        ON o.customer_id = c.customer_id
)
SELECT
    order_id,
    customer_id,
    customer_unique_id,
    order_status,
    order_purchase_ts,
    order_approved_ts,
    delivered_carrier_ts,
    delivered_customer_ts,
    estimated_delivery_ts,
    item_count,
    item_price_value,
    item_freight_value,
    item_gmv,
    -- Commercial reporting rule:
    -- canceled/unavailable orders are excluded from primary revenue KPIs.
    CASE
        WHEN order_status NOT IN ('canceled', 'unavailable')
            AND item_gmv IS NOT NULL THEN item_gmv
        ELSE 0
    END AS revenue_eligible_gmv,
    payment_value_total,
    payment_record_count,
    avg_review_score,
    review_count,
    delivery_days,
    estimated_delivery_days,
    CASE
        WHEN delivered_customer_ts IS NULL OR estimated_delivery_ts IS NULL THEN NULL
        WHEN delivered_customer_ts <= estimated_delivery_ts THEN 1
        ELSE 0
    END AS is_on_time_delivery,
    CASE WHEN order_status IN ('canceled', 'unavailable') THEN 1 ELSE 0 END AS is_canceled_or_unavailable,
    CASE
        WHEN order_status NOT IN ('canceled', 'unavailable')
            AND item_gmv IS NOT NULL THEN 1
        ELSE 0
    END AS is_revenue_eligible_order,
    ROW_NUMBER() OVER (
        PARTITION BY customer_unique_id
        ORDER BY order_purchase_ts, order_id
    ) AS customer_order_sequence
FROM orders_enriched;

CREATE OR REPLACE TABLE marts.dim_dates AS
WITH bounds AS (
    SELECT
        MIN(order_purchase_ts::DATE) AS min_date,
        MAX(order_purchase_ts::DATE) AS max_date
    FROM staging.stg_orders
)
SELECT
    d::DATE AS date_day,
    EXTRACT(YEAR FROM d) AS year_num,
    EXTRACT(MONTH FROM d) AS month_num,
    STRFTIME(d, '%Y-%m') AS year_month,
    EXTRACT(DAY FROM d) AS day_of_month,
    EXTRACT(WEEK FROM d) AS week_num,
    EXTRACT(DOW FROM d) AS day_of_week_num,
    STRFTIME(d, '%A') AS day_of_week_name,
    CASE WHEN EXTRACT(DOW FROM d) IN (0, 6) THEN 1 ELSE 0 END AS is_weekend
FROM bounds b,
GENERATE_SERIES(b.min_date, b.max_date, INTERVAL 1 DAY) AS t(d);

CREATE OR REPLACE VIEW marts.vw_order_seller_performance AS
SELECT
    oi.seller_id,
    oi.order_id,
    o.order_status,
    o.order_purchase_ts::DATE AS purchase_date,
    SUM(oi.price) AS seller_item_revenue,
    SUM(oi.freight_value) AS seller_freight_revenue,
    SUM(oi.gmv) AS seller_gmv,
    COUNT(*) AS seller_item_count
FROM marts.fact_order_items oi
INNER JOIN marts.fact_orders o
    ON oi.order_id = o.order_id
GROUP BY 1, 2, 3, 4;
