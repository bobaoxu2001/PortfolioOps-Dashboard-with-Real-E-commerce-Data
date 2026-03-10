# Power BI Layout Guide (Executive Dashboard)

This file documents the intended Power BI implementation of the 4-page dashboard package.

## Page 1 - Executive Overview

**Visuals**
1. KPI cards: GMV, Total Orders, AOV, Cancellation Rate  
   - Why: gives leadership a one-screen health check.
2. Monthly GMV line  
   - Why: shows top-line trajectory and seasonality.
3. Monthly Orders line  
   - Why: separates demand trend from ticket size effects.
4. Service reliability trend (On-time vs Cancellation)  
   - Why: quickly flags operational risk.
5. Customer experience trend (Review + Delivery Days)  
   - Why: connects logistics performance to customer sentiment.

## Page 2 - Customer Experience & Fulfillment

**Visuals**
1. Delay bucket order volume bar chart  
   - Why: quantifies fulfillment exceptions.
2. Delay bucket review score bar chart  
   - Why: ties delay severity to NPS-like experience outcomes.
3. State delivery-time comparison  
   - Why: identifies where to prioritize logistics intervention.
4. State review-score comparison  
   - Why: validates whether service issues are customer-visible.

## Page 3 - Commercial Performance

**Visuals**
1. Top category GMV bar chart  
   - Why: supports assortment and investment allocation.
2. Top seller GMV bar chart  
   - Why: highlights partner concentration and account priorities.
3. State GMV bar chart  
   - Why: informs regional commercial strategy.
4. Payment mix pie chart (or stacked bar in production)  
   - Why: reveals dependence on payment channels.

## Page 4 - Data Quality / KPI Reliability

**Visuals**
1. Data quality issue counts  
   - Why: makes metric risk visible for leadership governance.
2. Join-risk KPI panel (naive vs trusted GMV)  
   - Why: demonstrates why curated marts are mandatory.
3. Governance actions summary  
   - Why: communicates control framework and trust-building actions.

## Recommended Slicers

- Date range (month/quarter/year)
- Customer state
- Product category
- Seller state
- Order status

## Design Notes

- Use a clean executive palette with no more than 5 core colors.
- Keep labels short and business-facing.
- Use tooltips for technical details; keep page-level visuals concise.
