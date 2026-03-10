# Raw Data Instructions

Raw Olist CSV files are intentionally excluded from Git to keep the repository lightweight.

To download the official public data mirror:

```bash
python3 python/download_olist_data.py
```

Expected files:

- `olist_orders_dataset.csv`
- `olist_order_items_dataset.csv`
- `olist_order_payments_dataset.csv`
- `olist_order_reviews_dataset.csv`
- `olist_customers_dataset.csv`
- `olist_products_dataset.csv`
- `olist_sellers_dataset.csv`
- `olist_geolocation_dataset.csv`
- `product_category_name_translation.csv`

Source: Olist public datasets from GitHub (`work-at-olist-data` repository).
