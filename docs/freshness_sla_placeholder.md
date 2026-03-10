# Freshness SLA & Anomaly Monitoring Placeholder

This project currently focuses on historical KPI reliability and reproducible rebuilds.  
For a production-like consulting handoff, add the following lightweight monitoring layer:

## Proposed SLA

- **Pipeline frequency:** daily
- **SLA target:** processed KPI tables updated by 07:00 local time
- **Alert threshold:** if latest `order_purchase_ts` is older than 2 days, raise warning

## Suggested checks

1. Freshness check: max purchase date lag
2. Row-count anomaly check: daily order volume z-score vs trailing 28-day average
3. KPI drift check: primary GMV and cancellation rate outside expected band

## Implementation option

- Add `python/run_freshness_checks.py`
- Export:
  - `data/processed/freshness_status.csv`
  - `docs/freshness_status_report.md`
- Add CI job or scheduled workflow for daily health checks.

This placeholder demonstrates forward-thinking governance without overengineering the portfolio project.
