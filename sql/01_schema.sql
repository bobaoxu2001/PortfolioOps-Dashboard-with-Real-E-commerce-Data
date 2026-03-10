-- 01_schema.sql
-- Purpose: Register raw Olist CSVs and create logical schemas.

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;

CREATE OR REPLACE VIEW raw.orders AS
SELECT *
FROM read_csv_auto('data/raw/olist_orders_dataset.csv', header = TRUE);

CREATE OR REPLACE VIEW raw.order_items AS
SELECT *
FROM read_csv_auto('data/raw/olist_order_items_dataset.csv', header = TRUE);

CREATE OR REPLACE VIEW raw.order_payments AS
SELECT *
FROM read_csv_auto('data/raw/olist_order_payments_dataset.csv', header = TRUE);

CREATE OR REPLACE VIEW raw.order_reviews AS
SELECT *
FROM read_csv_auto('data/raw/olist_order_reviews_dataset.csv', header = TRUE);

CREATE OR REPLACE VIEW raw.customers AS
SELECT *
FROM read_csv_auto('data/raw/olist_customers_dataset.csv', header = TRUE);

CREATE OR REPLACE VIEW raw.products AS
SELECT *
FROM read_csv_auto('data/raw/olist_products_dataset.csv', header = TRUE);

CREATE OR REPLACE VIEW raw.sellers AS
SELECT *
FROM read_csv_auto('data/raw/olist_sellers_dataset.csv', header = TRUE);

CREATE OR REPLACE VIEW raw.geolocation AS
SELECT *
FROM read_csv_auto('data/raw/olist_geolocation_dataset.csv', header = TRUE);

CREATE OR REPLACE VIEW raw.category_translation AS
SELECT *
FROM read_csv_auto('data/raw/product_category_name_translation.csv', header = TRUE);
