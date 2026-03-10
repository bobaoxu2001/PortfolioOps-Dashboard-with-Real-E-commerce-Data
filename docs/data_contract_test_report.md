# Data Contract Test Report

- Total tests: **9**
- Failed tests: **0**
- Critical failed tests: **0**

## Detailed Results

| test_name | severity | status | observed_value | threshold | rationale |
|---|---|---|---:|---|---|
| fact_orders_order_id_unique | critical | PASS | 0.000000 | must equal 0 | Order grain must be one row per order_id. |
| fact_order_items_key_unique | critical | PASS | 0.000000 | must equal 0 | Item grain must be one row per (order_id, order_item_id). |
| fact_orders_customer_fk_integrity | critical | PASS | 0.000000 | must equal 0 | Orders should always map to a customer dimension row. |
| fact_order_items_product_fk_integrity | critical | PASS | 0.000000 | must equal 0 | Order items should always map to a product dimension row. |
| gmv_reconciliation_item_vs_order | critical | PASS | -0.000000 | absolute difference < 0.01 | Order-level GMV must reconcile to item-level GMV. |
| cancellation_rate_reasonable_band | warning | PASS | 0.012409 | between 0 and 0.20 | A broad sanity check to catch severe status-mapping regressions. |
| on_time_metric_population_coverage | warning | PASS | 0.970183 | >= 0.90 | Most orders should be evaluable for on-time delivery after model logic. |
| service_quality_signal_direction | info | PASS | 1.729459 | > 0 | On-time deliveries should show higher review scores than late deliveries. |
| payment_to_gmv_ratio_sanity | warning | PASS | 1.010135 | between 0.90 and 1.15 | Detects major revenue/payment mismatches after transformations. |

Interpretation: critical failures block KPI publication; warning/info failures require analyst review.