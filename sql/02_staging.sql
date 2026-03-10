-- 02_staging.sql
-- Purpose: Type-cast, deduplicate, normalize keys, and resolve join-risk tables.

CREATE OR REPLACE TABLE staging.stg_orders AS
WITH typed AS (
    SELECT
        CAST(order_id AS VARCHAR) AS order_id,
        CAST(customer_id AS VARCHAR) AS customer_id,
        LOWER(TRIM(CAST(order_status AS VARCHAR))) AS order_status,
        TRY_STRPTIME(CAST(order_purchase_timestamp AS VARCHAR), '%Y-%m-%d %H:%M:%S') AS order_purchase_ts,
        TRY_STRPTIME(CAST(order_approved_at AS VARCHAR), '%Y-%m-%d %H:%M:%S') AS order_approved_ts,
        TRY_STRPTIME(CAST(order_delivered_carrier_date AS VARCHAR), '%Y-%m-%d %H:%M:%S') AS delivered_carrier_ts,
        TRY_STRPTIME(CAST(order_delivered_customer_date AS VARCHAR), '%Y-%m-%d %H:%M:%S') AS delivered_customer_ts,
        TRY_STRPTIME(CAST(order_estimated_delivery_date AS VARCHAR), '%Y-%m-%d %H:%M:%S') AS estimated_delivery_ts
    FROM raw.orders
)
SELECT * EXCLUDE (rn)
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY order_id
            ORDER BY
                order_purchase_ts DESC NULLS LAST,
                customer_id,
                order_status
        ) AS rn
    FROM typed
)
WHERE rn = 1;

CREATE OR REPLACE TABLE staging.stg_order_items AS
WITH typed AS (
    SELECT
        CAST(order_id AS VARCHAR) AS order_id,
        CAST(order_item_id AS INTEGER) AS order_item_id,
        CAST(product_id AS VARCHAR) AS product_id,
        CAST(seller_id AS VARCHAR) AS seller_id,
        TRY_STRPTIME(CAST(shipping_limit_date AS VARCHAR), '%Y-%m-%d %H:%M:%S') AS shipping_limit_ts,
        CAST(price AS DOUBLE) AS price,
        CAST(freight_value AS DOUBLE) AS freight_value
    FROM raw.order_items
)
SELECT * EXCLUDE (rn)
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY order_id, order_item_id
            ORDER BY
                shipping_limit_ts DESC NULLS LAST,
                seller_id,
                product_id,
                price DESC NULLS LAST,
                freight_value DESC NULLS LAST
        ) AS rn
    FROM typed
)
WHERE rn = 1;

CREATE OR REPLACE TABLE staging.stg_order_payments AS
WITH typed AS (
    SELECT
        CAST(order_id AS VARCHAR) AS order_id,
        CAST(payment_sequential AS INTEGER) AS payment_sequential,
        LOWER(TRIM(CAST(payment_type AS VARCHAR))) AS payment_type,
        CAST(payment_installments AS INTEGER) AS payment_installments,
        CAST(payment_value AS DOUBLE) AS payment_value
    FROM raw.order_payments
)
SELECT * EXCLUDE (rn)
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY order_id, payment_sequential
            ORDER BY
                payment_value DESC NULLS LAST,
                payment_type,
                payment_installments DESC NULLS LAST
        ) AS rn
    FROM typed
)
WHERE rn = 1;

CREATE OR REPLACE TABLE staging.stg_order_reviews AS
WITH typed AS (
    SELECT
        CAST(review_id AS VARCHAR) AS review_id,
        CAST(order_id AS VARCHAR) AS order_id,
        CAST(review_score AS INTEGER) AS review_score,
        NULLIF(TRIM(CAST(review_comment_title AS VARCHAR)), '') AS review_comment_title,
        NULLIF(TRIM(CAST(review_comment_message AS VARCHAR)), '') AS review_comment_message,
        TRY_STRPTIME(CAST(review_creation_date AS VARCHAR), '%Y-%m-%d %H:%M:%S') AS review_creation_ts,
        TRY_STRPTIME(CAST(review_answer_timestamp AS VARCHAR), '%Y-%m-%d %H:%M:%S') AS review_answer_ts
    FROM raw.order_reviews
)
SELECT * EXCLUDE (rn)
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY review_id
            ORDER BY
                review_answer_ts DESC NULLS LAST,
                order_id,
                review_score DESC NULLS LAST
        ) AS rn
    FROM typed
)
WHERE rn = 1;

CREATE OR REPLACE TABLE staging.stg_customers AS
WITH typed AS (
    SELECT
        CAST(customer_id AS VARCHAR) AS customer_id,
        CAST(customer_unique_id AS VARCHAR) AS customer_unique_id,
        LPAD(CAST(customer_zip_code_prefix AS VARCHAR), 5, '0') AS customer_zip_code_prefix,
        LOWER(TRIM(CAST(customer_city AS VARCHAR))) AS customer_city,
        UPPER(TRIM(CAST(customer_state AS VARCHAR))) AS customer_state
    FROM raw.customers
)
SELECT * EXCLUDE (rn)
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY customer_id
            ORDER BY
                customer_unique_id,
                customer_zip_code_prefix,
                customer_state,
                customer_city
        ) AS rn
    FROM typed
)
WHERE rn = 1;

CREATE OR REPLACE TABLE staging.stg_products AS
SELECT
    CAST(p.product_id AS VARCHAR) AS product_id,
    CAST(p.product_category_name AS VARCHAR) AS product_category_name_pt,
    COALESCE(
        CAST(t.product_category_name_english AS VARCHAR),
        'unknown'
    ) AS product_category_name_en,
    CAST(p.product_name_lenght AS INTEGER) AS product_name_length,
    CAST(p.product_description_lenght AS INTEGER) AS product_description_length,
    CAST(p.product_photos_qty AS INTEGER) AS product_photos_qty,
    CAST(p.product_weight_g AS DOUBLE) AS product_weight_g,
    CAST(p.product_length_cm AS DOUBLE) AS product_length_cm,
    CAST(p.product_height_cm AS DOUBLE) AS product_height_cm,
    CAST(p.product_width_cm AS DOUBLE) AS product_width_cm
FROM raw.products p
LEFT JOIN raw.category_translation t
    ON p.product_category_name = t.product_category_name;

CREATE OR REPLACE TABLE staging.stg_sellers AS
WITH typed AS (
    SELECT
        CAST(seller_id AS VARCHAR) AS seller_id,
        LPAD(CAST(seller_zip_code_prefix AS VARCHAR), 5, '0') AS seller_zip_code_prefix,
        LOWER(TRIM(CAST(seller_city AS VARCHAR))) AS seller_city,
        UPPER(TRIM(CAST(seller_state AS VARCHAR))) AS seller_state
    FROM raw.sellers
)
SELECT * EXCLUDE (rn)
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY seller_id
            ORDER BY
                seller_zip_code_prefix,
                seller_state,
                seller_city
        ) AS rn
    FROM typed
)
WHERE rn = 1;

-- Critical join-risk fix:
-- Geolocation has many rows per zip prefix. This table enforces one row per prefix.
CREATE OR REPLACE TABLE staging.stg_geolocation_zip AS
SELECT
    LPAD(CAST(geolocation_zip_code_prefix AS VARCHAR), 5, '0') AS zip_code_prefix,
    AVG(CAST(geolocation_lat AS DOUBLE)) AS avg_latitude,
    AVG(CAST(geolocation_lng AS DOUBLE)) AS avg_longitude,
    MODE() WITHIN GROUP (ORDER BY LOWER(TRIM(CAST(geolocation_city AS VARCHAR)))) AS primary_city,
    MODE() WITHIN GROUP (ORDER BY UPPER(TRIM(CAST(geolocation_state AS VARCHAR)))) AS primary_state
FROM raw.geolocation
GROUP BY 1;
