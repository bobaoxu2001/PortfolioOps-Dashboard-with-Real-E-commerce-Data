# Metric Definitions (Trusted Reporting Layer)

Author: **Allen Xu**

## Design Principles

1. Metrics are calculated from a **single reporting layer** (`marts` schema), not directly from raw tables.
2. Every KPI includes a grain definition and caveats.
3. Revenue metrics are protected from duplication by aggregating item and payment tables to order grain before joins.

---

## Core Executive KPIs

| Metric | Definition | SQL Logic (Conceptual) | Grain | Caveats |
|---|---|---|---|---|
| Total Orders | Count of all orders in `fact_orders` | `COUNT(*)` | Order | Includes canceled/unavailable unless filtered. |
| GMV (Revenue Proxy) | Sum of item price + freight | `SUM(item_gmv)` | Order (aggregated from item) | Proxy for gross sales, not net margin. |
| Average Order Value (AOV) | GMV divided by order count | `AVG(item_gmv)` | Order | Includes low/zero-value orders if present. |
| Cancellation Rate | Share of orders with status canceled or unavailable | `AVG(is_canceled_or_unavailable)` | Order | Combines canceled + unavailable by design. |
| Avg Review Score | Mean customer review score | `AVG(avg_review_score)` | Order | Orders without reviews are excluded from numerator/denominator in score average. |
| Avg Delivery Days | Purchase-to-delivery elapsed days | `AVG(delivery_days)` | Delivered order | Null when order not delivered. |
| On-Time Delivery Rate | Share of delivered orders received on/before estimated date | `AVG(is_on_time_delivery)` | Delivered order | Requires both delivered and estimated timestamps. |
| Repeat Customer Rate | Share of unique customers with >1 orders | `repeat_customers / total_customers` | Customer | Uses `customer_unique_id`. |

---

## Operational / Commercial KPIs

| Metric | Definition | Grain | Why it matters |
|---|---|---|---|
| Seller GMV | GMV attributed to each seller | Seller x Order | Identifies high-impact seller relationships and concentration risk. |
| Category GMV | GMV by product category | Category | Supports assortment and pricing strategy. |
| Payment Mix | Share of payment value by payment type | Payment Type | Indicates payment dependence and financing behavior. |
| Delay Bucket Review Score | Avg review by delivery delay bucket | Delay Bucket | Quantifies CX impact of fulfillment delays. |
| State Performance | Orders/GMV/review/delivery by customer state | State | Reveals regional operational variability. |
| Weekly Ops Trend | Weekly trend of orders/GMV/service KPIs | Week | Supports operator cadence in weekly business reviews. |
| Seller Operational Risk | Seller-level late/cancel/review profile | Seller | Helps prioritize seller quality interventions beyond pure revenue ranking. |
| Cohort Retention Rate | Active customers in month N / cohort size | Cohort Month x Month Number | Tracks customer retention and repeat behavior over time. |

---

## Delay Bucket Logic

Using `delivery_days - estimated_delivery_days`:

- `<= 0`: On time or early
- `1-3`: 1-3 days late
- `4-7`: 4-7 days late
- `>= 8`: 8+ days late
- null delivery: Not Delivered

---

## KPI Reliability Guardrails

### Guardrail 1: Grain-safe joins
- `fact_order_items` stays at item grain.
- `fact_orders` stays at order grain with pre-aggregated item/payment/review rollups.
- Avoid direct joins of `order_items` and `order_payments` without pre-aggregation.

### Guardrail 2: Geolocation de-duplication
- Raw geolocation has many rows per zip prefix.
- `stg_geolocation_zip` consolidates to one row per zip prefix for dimension joins.

### Guardrail 3: Explicit revenue eligibility flag
- `is_revenue_eligible_order = 1` when order not canceled/unavailable and GMV present.
- Allows leadership views that separate booked GMV from in-flight/canceled orders.
