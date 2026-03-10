# Power BI Layout Guide (Executive Dashboard)

This guide maps each visual to business intent so reviewers can quickly assess consulting-grade dashboard design quality.

## Core KPI Convention (must be consistent across all pages)

- **Primary Revenue KPI:** `gmv_revenue_eligible`
- **Primary AOV KPI:** `aov_revenue_eligible`
- **Why:** canceled/unavailable orders are not realized commercial outcomes and should not inflate commercial KPIs.
- **Transparency companion metric:** `gmv_all_orders`

---

## Page 1 - Executive Overview (Audience: CEO / COO / CFO)

| Visual | Business Question | Metric Definition | Recommended Slicers | Audience |
|---|---|---|---|---|
| KPI Card: Primary GMV | What realized commercial value did we generate? | `SUM(gmv_revenue_eligible)` | Date, state, category | CEO/CFO |
| KPI Card: Total Orders | How much order demand is flowing through the system? | `COUNT(order_id)` | Date, state | COO |
| KPI Card: Primary AOV | Is basket economics improving? | `gmv_revenue_eligible / revenue_eligible_orders` | Date, category | CEO/CFO |
| KPI Card: Cancellation Rate | Is order fallout rising? | `AVG(is_canceled_or_unavailable)` | Date, state, seller | COO |
| Line: Monthly Primary GMV | Is top-line trajectory healthy? | Monthly `gmv_revenue_eligible` | Date | CEO/CFO |
| Line: Monthly Orders | Is demand increasing independently of basket value? | Monthly `COUNT(order_id)` | Date | CEO/COO |
| Dual line: On-time vs Cancel | Are reliability issues growing? | On-time rate + cancellation rate | Date, state | COO |
| Dual axis: Review vs Delivery Days | Is service performance visible to customers? | Avg review + avg delivery days | Date, state | COO/Customer Ops |

---

## Page 2 - Customer Experience & Fulfillment (Audience: COO / CX Lead / Logistics Lead)

| Visual | Business Question | Metric Definition | Recommended Slicers | Audience |
|---|---|---|---|---|
| Bar: Delay bucket order count | Where is fulfillment friction concentrated? | Orders by delay bucket | Date, state | COO |
| Bar: Delay bucket review score | How much do delays hurt customer sentiment? | Avg review by delay bucket | Date, category | CX Lead |
| Bar: Avg delivery days by state | Which regions need logistics intervention? | Avg delivery days | Date, state group | Logistics |
| Bar: Avg review by state | Do regional ops issues affect customer satisfaction? | Avg review score | Date, state | CX Lead |

---

## Page 3 - Commercial Performance (Audience: Commercial Director / Category Manager / Seller Ops)

| Visual | Business Question | Metric Definition | Recommended Slicers | Audience |
|---|---|---|---|---|
| Bar: Top categories by primary GMV | Which categories drive monetized volume? | `gmv_revenue_eligible` by category | Date, state | Category Lead |
| Bar: Top sellers by primary GMV | Which sellers are most commercially material? | `gmv_revenue_eligible` by seller | Date, seller state | Seller Ops |
| Bar: Top states by primary GMV | Which markets are strongest commercially? | `gmv_revenue_eligible` by state | Date, category | Commercial Director |
| Pie/100% bar: Payment mix | How concentrated is payment channel dependence? | Share of payment value by type | Date | CFO/Payments |

---

## Page 4 - Data Quality / KPI Reliability (Audience: Leadership + Analytics Governance)

| Visual | Business Question | Metric Definition | Recommended Slicers | Audience |
|---|---|---|---|---|
| Bar: Data quality checks | What source/model risks can distort decisions? | Count by check_name | Data layer | Exec + Data Lead |
| KPI panel: Naive vs Trusted GMV | What is the financial impact of bad joins? | Naive GMV, trusted GMV, overstatement | None | CFO/Data Lead |
| Text panel: Governance actions | What controls are in place before publication? | Narrative from QA framework | None | Leadership |

---

## Global Slicer Set

- Date (month/quarter/year)
- Customer state
- Product category
- Seller state
- Order status
- Revenue inclusion view (`Primary: revenue-eligible` vs `All-orders reference`)

---

## Build Notes

1. Use a clean executive palette (max 5 core colors).
2. Keep chart titles in business language; move technical caveats to tooltips.
3. Add a small subtitle on commercial charts: **"Primary revenue = revenue-eligible orders only."**
