# Metric Caveats for Dashboard Consumers

Use this table as a quick interpretation aid during executive reviews.

| Metric | What it includes | What it excludes / caveat | Why it matters for decisions |
|---|---|---|---|
| Primary GMV (`gmv_revenue_eligible`) | GMV from revenue-eligible orders | Excludes canceled/unavailable orders | Prevents operational fallout from overstating commercial performance. |
| GMV (All Orders Reference) | GMV across all orders | Includes canceled/unavailable outcomes | Useful for QA transparency, not for primary commercial target tracking. |
| Primary AOV | Primary GMV / revenue-eligible order count | Sensitive to eligibility logic changes | Keeps AOV aligned with monetized order base. |
| Cancellation Rate | Canceled + unavailable share | Does not include detailed reason taxonomy | Signals process friction but not root cause specifics. |
| On-Time Delivery Rate | Deliveries with sufficient timestamp coverage | Null where on-time logic cannot be evaluated | Pair with coverage checks before trend interpretation. |
| Avg Review Score | Average review score where reviews exist | Missing review bias may exist | Trend is useful directionally, not as a complete sentiment census. |
| Seller Concentration (Top 10 Share) | Share of primary GMV from top 10 sellers | Not adjusted for category mix or seasonality | Indicates concentration risk and account dependency. |
