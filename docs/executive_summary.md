# Executive Summary - Olist Reporting Layer Engagement

Author: **Allen Xu**  
Audience: Executive leadership / PE operating team  
Date: March 2026

## 1) Business Context

Leadership lacked a trusted, consolidated view of commerce performance because critical metrics were spread across multiple source tables (orders, items, payments, reviews, customers, and geolocation).  
This engagement built a centralized reporting layer and executive dashboard to improve speed, consistency, and decision confidence.

## 2) Data Challenges Identified

1. **Join grain mismatch risk**  
   Directly joining item-level and payment-level records creates duplicated revenue. In this dataset, a naive join would overstate GMV by **R$723K**.

2. **High-duplication geolocation lookup**  
   Raw geolocation includes **981,148 duplicate zip-prefix rows**, creating one-to-many join risk unless standardized.

3. **Delivery timestamp completeness issues**  
   Even delivered orders have minor timestamp gaps (8 records with missing customer delivery date), requiring KPI caveats.

4. **Status interpretation risk**  
   Canceled and unavailable orders must be explicitly handled to avoid inflating revenue or suppressing service quality issues.

## 3) KPI Highlights (Trusted Model Output)

- **Total orders:** 99,441  
- **GMV (price + freight proxy):** **R$15.85M**  
- **AOV:** **R$159.37**  
- **Cancellation rate (canceled + unavailable):** **1.24%**  
- **Average review score:** **4.09 / 5**  
- **Average delivery time:** **12.5 days**  
- **On-time delivery rate:** **91.9%**

Additional observations:
- Payment concentration is high in **credit card (78.3% of payment value)**.
- Top commercial state is **SP** (R$5.92M GMV), while **RJ** shows large volume with materially slower delivery (15.2 days avg).
- Delay strongly correlates with customer satisfaction:  
  **On-time review = 4.29**, vs **8+ days late review = 1.70**.
- Repeat customer rate is low (**3.1%** of unique customers), indicating retention opportunity.

## 4) Operational Pain Points

1. Late delivery pockets by region (notably CE/BA/PE and portions of RJ).  
2. Noticeable service stress periods (e.g., late-2017 and early-2018 on-time dips).  
3. Category-level customer experience variability (e.g., office furniture underperforms in review score).  
4. KPI credibility risks if analysts bypass curated marts and join raw tables directly.

## 5) Recommendations (Next 90 Days)

1. **Set a delivery recovery program in underperforming states**  
   Launch weekly SLA tracking for CE, BA, PE, and RJ with logistics escalation owners.

2. **Use delay-bucket alerts as an early-warning KPI**  
   Trigger action when 4+ day late bucket exceeds threshold; this has clear review-score impact.

3. **Harden metric governance**  
   Require all executive reporting to use `fact_orders` and approved KPI definitions. Ban raw-table direct joins in production dashboards, and enforce publish-time data contract checks.

4. **Improve retention and lifecycle insights**  
   Add repeat-purchase campaigns and track cohort repurchase given low repeat rate.

5. **Diversify payment risk and monitor approval friction**  
   Credit-card concentration is high; track failure/approval rates by payment type where data becomes available.

## 6) What Leadership Should Monitor Going Forward

- Weekly: on-time delivery rate, 4+ day late share, cancellation rate, review score by delay bucket  
- Monthly: GMV, AOV, top/bottom category profitability proxy, seller concentration, regional SLA variance  
- Quarterly: repeat customer rate, customer retention cohorts, and KPI quality exceptions (nulls/duplicates/join risk flags)
