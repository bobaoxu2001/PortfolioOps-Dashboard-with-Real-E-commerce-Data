# Data Contract Test Report

- Total tests: **17**
- Failed tests: **0**
- Critical failed tests: **0**

## Detailed Results

| test_name | severity | status | observed_value | threshold | rationale |
|---|---|---|---:|---|---|
| Fact Orders has one row per order | critical | PASS | 0.000000 | must equal 0 | Order grain must be one row per order_id. |
| Fact Order Items has unique item keys | critical | PASS | 0.000000 | must equal 0 | Item grain must be one row per (order_id, order_item_id). |
| Fact Orders customer foreign key integrity | critical | PASS | 0.000000 | must equal 0 | Orders should always map to a customer dimension row. |
| Fact Order Items product foreign key integrity | critical | PASS | 0.000000 | must equal 0 | Order items should always map to a product dimension row. |
| All-orders GMV reconciles between item and order facts | critical | PASS | -0.000000 | absolute difference < 0.01 | Order-level GMV must reconcile to item-level GMV. |
| Revenue-eligible GMV reconciles across grains | critical | PASS | -0.000000 | absolute difference < 0.01 | Primary revenue KPI must match whether computed from items or orders. |
| Revenue-eligible order count is non-zero | critical | PASS | 98199.000000 | > 0 | Primary revenue KPIs cannot be published with zero qualifying orders. |
| Primary revenue excludes canceled and unavailable orders | critical | PASS | 0.000000 | absolute value < 0.01 | Canceled/unavailable orders are operational outcomes and should not inflate commercial KPIs. |
| Delivered orders have expected on-time logic coverage | warning | PASS | 0.999917 | >= 0.995 | Delivered orders should almost always have enough timestamp data for on-time classification. |
| Headline AOV matches defined formula | critical | PASS | 0.000000 | absolute difference < 0.000001 | AOV must equal revenue-eligible GMV divided by revenue-eligible order count. |
| Monthly primary GMV reconciles to headline primary GMV | critical | PASS | 0.000001 | absolute difference < 0.01 | Roll-up checks prevent hidden leakage between monthly reporting and headline KPIs. |
| Monthly revenue-eligible order count reconciles to headline | critical | PASS | 0.000000 | absolute difference < 0.01 | Primary order volume denominator should align across all executive summary layers. |
| Monthly and headline AOV align under weighted definition | warning | PASS | -0.000000 | absolute difference < 0.000001 | Prevents averaging bias from unweighted monthly AOV rollups. |
| Cancellation rate remains in expected operating band | warning | PASS | 0.012409 | between 0 and 0.20 | A broad sanity check to catch severe status-mapping regressions. |
| On-time KPI coverage remains healthy | warning | PASS | 0.970183 | >= 0.90 | Most orders should be evaluable for on-time delivery after model logic. |
| Late deliveries depress review score (directional test) | info | PASS | 1.730367 | > 0 | On-time deliveries should show higher review scores than late deliveries. |
| Payment value to GMV ratio remains plausible | warning | PASS | 1.010135 | between 0.90 and 1.15 | Detects major revenue/payment mismatches after transformations. |

Interpretation: critical failures block KPI publication; warning/info failures require analyst review.