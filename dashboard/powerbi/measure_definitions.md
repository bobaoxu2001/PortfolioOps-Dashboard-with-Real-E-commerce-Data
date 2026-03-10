# Recommended Power BI Measures (DAX)

> Note: Source CSVs already include pre-aggregated KPI outputs. These measures are intended for a model built from mart-level extracts or imported order-level table.

## Executive KPI measures

```DAX
Primary GMV = SUM('fact_orders'[revenue_eligible_gmv])
```

```DAX
GMV (All Orders Reference) = SUM('fact_orders'[item_gmv])
```

```DAX
Revenue Eligible Orders =
CALCULATE(
    DISTINCTCOUNT('fact_orders'[order_id]),
    'fact_orders'[is_revenue_eligible_order] = 1
)
```

```DAX
Primary AOV = DIVIDE([Primary GMV], [Revenue Eligible Orders])
```

```DAX
Cancellation Rate = AVERAGE('fact_orders'[is_canceled_or_unavailable])
```

```DAX
On-Time Delivery Rate = AVERAGE('fact_orders'[is_on_time_delivery])
```

```DAX
Avg Review Score = AVERAGE('fact_orders'[avg_review_score])
```

```DAX
Avg Delivery Days = AVERAGE('fact_orders'[delivery_days])
```

## Risk / concentration measures

```DAX
Top 10 Seller GMV Share =
DIVIDE(
    CALCULATE(
        [Primary GMV],
        TOPN(10, VALUES('dim_sellers'[seller_id]), [Primary GMV], DESC)
    ),
    [Primary GMV]
)
```

## Display guidance

- Label primary revenue measures with **Primary** prefix.
- Keep all-orders measures as reference-only in tooltips or QA page.
