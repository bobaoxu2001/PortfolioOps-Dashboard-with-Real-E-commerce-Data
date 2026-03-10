# Power BI Rebuild Package (Native Artifact Placeholder)

This folder documents how to rebuild the dashboard in native Power BI (`.pbix`) using the curated reporting outputs.

## Why this folder exists

The repository ships static PNG/PDF assets for portability.  
For interview walkthroughs, this guide enables a reviewer to recreate the dashboard as a native interactive BI file in under 30 minutes.

## Input files

Load from `data/processed/`:

- `kpi_headline.csv`
- `kpi_monthly.csv`
- `kpi_weekly_ops.csv`
- `kpi_category_performance.csv`
- `kpi_seller_performance.csv`
- `kpi_seller_operational_risk.csv`
- `kpi_state_performance.csv`
- `kpi_payment_mix.csv`
- `kpi_delay_vs_reviews.csv`
- `data_quality_summary.csv`
- `kpi_join_risk_demo.csv`
- `kpi_seller_concentration.csv`

## Build sequence

1. Import CSVs in Power BI Desktop.
2. Create relationships where natural keys align (for narrow KPI tables, many visuals can remain disconnected by design).
3. Implement DAX measures from `dashboard/powerbi/measure_definitions.md`.
4. Follow `dashboard/powerbi_layout_guide.md` page-by-page.
5. Add slicers: Date, State, Category, Seller State, Order Status.
6. Export screenshot set + PDF for repo parity.

## Naming convention

- Prefix executive cards with `Primary` where revenue-eligible logic applies.
- Keep all-orders metrics labeled explicitly as `Reference`.

## Validation before publish

Run:

```bash
python3 python/run_data_contract_tests.py
```

Only publish if critical checks pass.
