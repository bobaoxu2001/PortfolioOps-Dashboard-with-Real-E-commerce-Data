# KPI QA Framework (Interview-Ready Governance)

This document explains how KPI reliability is protected before executive dashboards are published.

## QA Layers

1. **Source checks (raw/staging)**
   - Null checks for required keys and timestamps
   - Duplicate key checks
   - Invalid timestamp logic checks (estimated date before purchase)

2. **Model checks (marts and exports)**
   - Primary key uniqueness (`fact_orders`, `fact_order_items`)
   - Foreign-key integrity (`fact -> dim`)
   - Revenue reconciliation (`fact_order_items.gmv` vs `fact_orders.item_gmv`)
   - Revenue-eligible reconciliation (`fact_order_items` filtered vs `fact_orders.revenue_eligible_gmv`)

3. **Business sanity checks**
   - Primary revenue excludes canceled/unavailable orders
   - Headline AOV matches published definition
   - Revenue-eligible order count is non-zero
   - Delivered-order on-time logic coverage is within expected range
   - Monthly KPI rollups reconcile to headline KPIs
   - Cancellation rate and payment-to-GMV ratio stay in expected bands

## Automation

- Script: `python/run_data_contract_tests.py`
- Outputs:
  - `data/processed/data_contract_test_results.csv`
  - `data/processed/data_contract_test_summary.csv`
  - `docs/data_contract_test_report.md`

## Business-readable test catalog

Critical checks (publication blockers):
- Fact Orders has one row per order
- Fact Order Items has unique item keys
- Fact Orders customer foreign key integrity
- Fact Order Items product foreign key integrity
- Revenue-eligible GMV reconciles across grains
- Revenue-eligible order count is non-zero
- Primary revenue excludes canceled and unavailable orders
- Headline AOV matches defined formula
- Monthly primary GMV reconciles to headline primary GMV
- Monthly revenue-eligible order count reconciles to headline

## Publication Rule

- **Critical test failure:** block dashboard publication
- **Warning/info failure:** dashboard may publish only with analyst note and caveat

This governance approach mirrors consulting engagements where trust in metrics is as important as the metrics themselves.
