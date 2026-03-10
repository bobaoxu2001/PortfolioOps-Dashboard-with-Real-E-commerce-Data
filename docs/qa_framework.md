# KPI QA Framework (Interview-Ready Governance)

This document explains how KPI reliability is protected before executive dashboards are published.

## QA Layers

1. **Source checks (raw/staging)**
   - Null checks for required keys and timestamps
   - Duplicate key checks
   - Invalid timestamp logic checks (estimated date before purchase)

2. **Model checks (marts)**
   - Primary key uniqueness (`fact_orders`, `fact_order_items`)
   - Foreign-key integrity (`fact -> dim`)
   - Revenue reconciliation (`fact_order_items.gmv` vs `fact_orders.item_gmv`)

3. **Business sanity checks**
   - Cancellation rate in expected range
   - On-time metric coverage above threshold
   - Service quality directionality (late deliveries should have lower review score)
   - Payment-to-GMV ratio sanity band

## Automation

- Script: `python/run_data_contract_tests.py`
- Outputs:
  - `data/processed/data_contract_test_results.csv`
  - `data/processed/data_contract_test_summary.csv`
  - `docs/data_contract_test_report.md`

## Publication Rule

- **Critical test failure:** block dashboard publication
- **Warning/info failure:** dashboard may publish only with analyst note and caveat

This governance approach mirrors consulting engagements where trust in metrics is as important as the metrics themselves.
