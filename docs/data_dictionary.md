# Data Dictionary

Author: **Allen Xu**  
Project: Olist Centralized Reporting Layer

## 1) Raw Source Tables

| Table | Grain | Primary Key (Expected) | Notes |
|---|---|---|---|
| `raw.orders` | One row per order | `order_id` | Contains lifecycle status and core timestamps. |
| `raw.order_items` | One row per order item | (`order_id`, `order_item_id`) | Transactional item pricing and freight. |
| `raw.order_payments` | One row per payment record | (`order_id`, `payment_sequential`) | Multiple payment rows per order possible. |
| `raw.order_reviews` | One row per review record | `review_id` | Multiple reviews can map to one order. |
| `raw.customers` | One row per customer_id | `customer_id` | Includes `customer_unique_id` for repeat behavior. |
| `raw.products` | One row per product | `product_id` | Product attributes and category in Portuguese. |
| `raw.sellers` | One row per seller | `seller_id` | Seller zip/city/state fields. |
| `raw.geolocation` | Many rows per zip prefix | None (non-unique) | High-duplication lookup data. |
| `raw.category_translation` | One row per category mapping | `product_category_name` | Portuguese-to-English category mapping. |

---

## 2) Staging Tables (`staging`)

| Table | Grain | Key Transformations |
|---|---|---|
| `stg_orders` | Order | Timestamp parsing, status normalization, order_id dedupe rule. |
| `stg_order_items` | Order Item | Numeric casting, timestamp parsing, key dedupe rule. |
| `stg_order_payments` | Payment record | Numeric casting, payment type normalization. |
| `stg_order_reviews` | Review | Timestamp parsing, blank comment nullification, review dedupe rule. |
| `stg_customers` | Customer ID | Zip standardization (`LPAD`), city/state normalization. |
| `stg_products` | Product | Category translation join and attribute casting. |
| `stg_sellers` | Seller | Zip/city/state normalization and seller dedupe rule. |
| `stg_geolocation_zip` | Zip Prefix | Consolidated to one row per zip prefix using aggregated lat/lng and modal city/state. |

---

## 3) Reporting Layer (`marts`)

### `marts.fact_orders` (Order Grain)

| Column | Type | Description |
|---|---|---|
| `order_id` | VARCHAR | Unique order identifier. |
| `customer_id` | VARCHAR | Customer key from source orders. |
| `customer_unique_id` | VARCHAR | Cross-order customer identifier. |
| `order_status` | VARCHAR | Normalized order status. |
| `order_purchase_ts` | TIMESTAMP | Purchase timestamp. |
| `delivered_customer_ts` | TIMESTAMP | Actual customer delivery timestamp. |
| `estimated_delivery_ts` | TIMESTAMP | Estimated delivery timestamp. |
| `item_count` | BIGINT | Number of items in order. |
| `item_price_value` | DOUBLE | Sum of item prices. |
| `item_freight_value` | DOUBLE | Sum of freight value. |
| `item_gmv` | DOUBLE | Revenue proxy (`price + freight`). |
| `payment_value_total` | DOUBLE | Sum of payment records per order. |
| `avg_review_score` | DOUBLE | Average review score per order. |
| `delivery_days` | BIGINT | Days from purchase to delivery. |
| `estimated_delivery_days` | BIGINT | Days from purchase to estimated delivery. |
| `is_on_time_delivery` | INTEGER | 1 on-time, 0 late, null if not evaluable. |
| `is_canceled_or_unavailable` | INTEGER | KPI flag for cancel rate. |
| `is_revenue_eligible_order` | INTEGER | 1 when order is non-canceled and has GMV. |
| `customer_order_sequence` | BIGINT | Order sequence per unique customer. |

### `marts.fact_order_items` (Item Grain)

| Column | Type | Description |
|---|---|---|
| `order_id` | VARCHAR | Order identifier. |
| `order_item_id` | INTEGER | Item position in order. |
| `product_id` | VARCHAR | Product key. |
| `seller_id` | VARCHAR | Seller key. |
| `price` | DOUBLE | Item price. |
| `freight_value` | DOUBLE | Freight value. |
| `gmv` | DOUBLE | Item-level GMV proxy (`price + freight`). |

### Dimensions

| Table | Key | Description |
|---|---|---|
| `marts.dim_customers` | `customer_id` | Customer profile + first/last order timestamps + geo coordinates. |
| `marts.dim_products` | `product_id` | Product attributes + translated category. |
| `marts.dim_sellers` | `seller_id` | Seller location and geo coordinates. |
| `marts.dim_dates` | `date_day` | Calendar attributes for time-series analysis. |
| `marts.dim_geography` | `zip_code_prefix` | Zip-prefix normalized city/state/lat/lng lookup. |

### Supporting View

| Object | Description |
|---|---|
| `marts.vw_order_seller_performance` | Seller x order rollup for commercial performance analysis. |
