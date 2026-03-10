"""Materialize Olist reporting layer and export KPI datasets."""

from __future__ import annotations

import pathlib

import duckdb
import pandas as pd


def run_sql_file(conn: duckdb.DuckDBPyConnection, path: pathlib.Path) -> None:
    sql = path.read_text(encoding="utf-8")
    conn.execute(sql)
    print(f"Executed: {path.name}")


def export_query(conn: duckdb.DuckDBPyConnection, query: str, output_path: pathlib.Path) -> None:
    df = conn.execute(query).df()
    df.to_csv(output_path, index=False)
    print(f"Exported: {output_path.name} ({len(df):,} rows)")


def main() -> None:
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    sql_dir = repo_root / "sql"
    processed_dir = repo_root / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    db_path = processed_dir / "olist_reporting.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute("PRAGMA threads = 1")

    for sql_file in ["01_schema.sql", "02_staging.sql", "03_marts.sql"]:
        run_sql_file(conn, sql_dir / sql_file)

    # Executive commercial KPI rule:
    # canceled/unavailable orders are operational outcomes, not realized commercial revenue.
    # Primary revenue metrics therefore use revenue-eligible orders only.
    export_query(
        conn,
        """
        SELECT
            DATE_TRUNC('week', order_purchase_ts)::DATE AS week_start,
            COUNT(*) AS total_orders,
            COUNT(CASE WHEN is_revenue_eligible_order = 1 THEN 1 END) AS revenue_eligible_orders,
            SUM(COALESCE(item_gmv, 0)) AS gmv_all_orders,
            SUM(COALESCE(revenue_eligible_gmv, 0)) AS gmv_revenue_eligible,
            SUM(COALESCE(revenue_eligible_gmv, 0))
                / NULLIF(COUNT(CASE WHEN is_revenue_eligible_order = 1 THEN 1 END), 0) AS aov_revenue_eligible,
            AVG(CASE WHEN is_canceled_or_unavailable = 1 THEN 1.0 ELSE 0.0 END) AS cancellation_rate,
            AVG(avg_review_score) AS avg_review_score,
            AVG(delivery_days) AS avg_delivery_days,
            AVG(CASE WHEN is_on_time_delivery IS NULL THEN NULL ELSE is_on_time_delivery::DOUBLE END) AS on_time_delivery_rate
        FROM marts.fact_orders
        GROUP BY 1
        ORDER BY 1
        """,
        processed_dir / "kpi_weekly_ops.csv",
    )

    export_query(
        conn,
        """
        SELECT
            DATE_TRUNC('month', order_purchase_ts)::DATE AS month_start,
            COUNT(DISTINCT customer_unique_id) AS active_customers
        FROM marts.fact_orders
        GROUP BY 1
        ORDER BY 1
        """,
        processed_dir / "kpi_active_customers_monthly.csv",
    )

    export_query(
        conn,
        """
        WITH first_orders AS (
            SELECT
                customer_unique_id,
                DATE_TRUNC('month', MIN(order_purchase_ts))::DATE AS cohort_month
            FROM marts.fact_orders
            GROUP BY 1
        ),
        customer_months AS (
            SELECT DISTINCT
                customer_unique_id,
                DATE_TRUNC('month', order_purchase_ts)::DATE AS order_month
            FROM marts.fact_orders
        ),
        cohort_activity AS (
            SELECT
                f.cohort_month,
                cm.order_month,
                DATE_DIFF('month', f.cohort_month, cm.order_month) AS month_number,
                COUNT(DISTINCT cm.customer_unique_id) AS active_customers
            FROM customer_months cm
            INNER JOIN first_orders f
                ON cm.customer_unique_id = f.customer_unique_id
            GROUP BY 1, 2, 3
        ),
        cohort_sizes AS (
            SELECT
                cohort_month,
                COUNT(DISTINCT customer_unique_id) AS cohort_size
            FROM first_orders
            GROUP BY 1
        )
        SELECT
            ca.cohort_month,
            ca.order_month,
            ca.month_number,
            cs.cohort_size,
            ca.active_customers,
            ca.active_customers::DOUBLE / NULLIF(cs.cohort_size, 0) AS retention_rate
        FROM cohort_activity ca
        INNER JOIN cohort_sizes cs
            ON ca.cohort_month = cs.cohort_month
        ORDER BY ca.cohort_month, ca.month_number
        """,
        processed_dir / "kpi_customer_cohort_retention.csv",
    )

    export_query(
        conn,
        """
        WITH seller_orders AS (
            SELECT
                i.seller_id,
                i.order_id,
                SUM(i.gmv) AS order_gmv
            FROM marts.fact_order_items i
            GROUP BY 1, 2
        )
        SELECT
            s.seller_id,
            ds.seller_state,
            COUNT(*) AS orders_all,
            COUNT(CASE WHEN fo.is_revenue_eligible_order = 1 THEN 1 END) AS orders_revenue_eligible,
            SUM(CASE WHEN fo.is_revenue_eligible_order = 1 THEN s.order_gmv ELSE 0 END) AS gmv_revenue_eligible,
            AVG(CASE WHEN fo.is_revenue_eligible_order = 1 THEN s.order_gmv END) AS avg_order_gmv_revenue_eligible,
            AVG(CASE WHEN fo.is_on_time_delivery = 0 THEN 1.0 ELSE 0.0 END) AS late_delivery_rate,
            AVG(CASE WHEN fo.is_canceled_or_unavailable = 1 THEN 1.0 ELSE 0.0 END) AS cancellation_rate,
            AVG(fo.avg_review_score) AS avg_review_score
        FROM seller_orders s
        INNER JOIN marts.fact_orders fo
            ON s.order_id = fo.order_id
        LEFT JOIN marts.dim_sellers ds
            ON s.seller_id = ds.seller_id
        GROUP BY 1, 2
        HAVING COUNT(*) >= 30
        ORDER BY gmv_revenue_eligible DESC, s.seller_id
        """,
        processed_dir / "kpi_seller_operational_risk.csv",
    )

    export_query(
        conn,
        """
        SELECT
            DATE_TRUNC('month', order_purchase_ts)::DATE AS month_start,
            COUNT(*) AS total_orders,
            COUNT(CASE WHEN is_revenue_eligible_order = 1 THEN 1 END) AS revenue_eligible_orders,
            SUM(COALESCE(item_gmv, 0)) AS gmv_all_orders,
            SUM(COALESCE(revenue_eligible_gmv, 0)) AS gmv_revenue_eligible,
            SUM(COALESCE(revenue_eligible_gmv, 0))
                / NULLIF(COUNT(CASE WHEN is_revenue_eligible_order = 1 THEN 1 END), 0) AS aov_revenue_eligible,
            AVG(CASE WHEN is_canceled_or_unavailable = 1 THEN 1.0 ELSE 0.0 END) AS cancellation_rate,
            AVG(avg_review_score) AS avg_review_score,
            AVG(delivery_days) AS avg_delivery_days,
            AVG(CASE WHEN is_on_time_delivery IS NULL THEN NULL ELSE is_on_time_delivery::DOUBLE END) AS on_time_delivery_rate
        FROM marts.fact_orders
        GROUP BY 1
        ORDER BY 1
        """,
        processed_dir / "kpi_monthly.csv",
    )

    export_query(
        conn,
        """
        SELECT
            CASE
                WHEN delivery_days IS NULL THEN 'Not Delivered'
                WHEN delivery_days - estimated_delivery_days <= 0 THEN 'On time or early'
                WHEN delivery_days - estimated_delivery_days BETWEEN 1 AND 3 THEN '1-3 days late'
                WHEN delivery_days - estimated_delivery_days BETWEEN 4 AND 7 THEN '4-7 days late'
                ELSE '8+ days late'
            END AS delay_bucket,
            COUNT(*) AS orders,
            AVG(avg_review_score) AS avg_review_score
        FROM marts.fact_orders
        GROUP BY 1
        ORDER BY
            CASE delay_bucket
                WHEN 'On time or early' THEN 1
                WHEN '1-3 days late' THEN 2
                WHEN '4-7 days late' THEN 3
                WHEN '8+ days late' THEN 4
                ELSE 5
            END
        """,
        processed_dir / "kpi_delay_vs_reviews.csv",
    )

    export_query(
        conn,
        """
        SELECT
            COALESCE(p.product_category_name_en, 'unknown') AS category,
            COUNT(DISTINCT i.order_id) AS orders,
            SUM(i.gmv) AS gmv_revenue_eligible,
            AVG(i.gmv) AS avg_item_value_revenue_eligible
        FROM marts.fact_order_items i
        INNER JOIN marts.fact_orders o
            ON i.order_id = o.order_id
           AND o.is_revenue_eligible_order = 1
        LEFT JOIN marts.dim_products p
            ON i.product_id = p.product_id
        GROUP BY 1
        ORDER BY gmv_revenue_eligible DESC, category
        """,
        processed_dir / "kpi_category_performance.csv",
    )

    export_query(
        conn,
        """
        SELECT
            s.seller_state,
            sp.seller_id,
            COUNT(DISTINCT sp.order_id) AS orders,
            SUM(sp.seller_gmv) AS gmv_revenue_eligible,
            AVG(sp.seller_gmv) AS avg_order_gmv_revenue_eligible
        FROM marts.vw_order_seller_performance sp
        INNER JOIN marts.fact_orders o
            ON sp.order_id = o.order_id
           AND o.is_revenue_eligible_order = 1
        LEFT JOIN marts.dim_sellers s
            ON sp.seller_id = s.seller_id
        GROUP BY 1, 2
        ORDER BY gmv_revenue_eligible DESC, sp.seller_id
        """,
        processed_dir / "kpi_seller_performance.csv",
    )

    export_query(
        conn,
        """
        SELECT
            c.customer_state,
            COUNT(DISTINCT o.order_id) AS orders,
            SUM(COALESCE(o.item_gmv, 0)) AS gmv_all_orders,
            SUM(COALESCE(o.revenue_eligible_gmv, 0)) AS gmv_revenue_eligible,
            AVG(o.avg_review_score) AS avg_review_score,
            AVG(o.delivery_days) AS avg_delivery_days
        FROM marts.fact_orders o
        LEFT JOIN marts.dim_customers c
            ON o.customer_id = c.customer_id
        GROUP BY 1
        ORDER BY gmv_revenue_eligible DESC, c.customer_state
        """,
        processed_dir / "kpi_state_performance.csv",
    )

    export_query(
        conn,
        """
        SELECT
            payment_type,
            COUNT(*) AS payment_records,
            SUM(payment_value) AS payment_value,
            AVG(payment_value) AS avg_payment_value
        FROM staging.stg_order_payments
        GROUP BY 1
        ORDER BY payment_value DESC, payment_type
        """,
        processed_dir / "kpi_payment_mix.csv",
    )

    export_query(
        conn,
        """
        WITH seller_gmv AS (
            SELECT
                i.seller_id,
                SUM(i.gmv) AS gmv_revenue_eligible
            FROM marts.fact_order_items i
            INNER JOIN marts.fact_orders o
                ON i.order_id = o.order_id
               AND o.is_revenue_eligible_order = 1
            GROUP BY 1
        ),
        ranked AS (
            SELECT
                seller_id,
                gmv_revenue_eligible,
                ROW_NUMBER() OVER (ORDER BY gmv_revenue_eligible DESC, seller_id) AS seller_rank,
                SUM(gmv_revenue_eligible) OVER () AS total_gmv_revenue_eligible
            FROM seller_gmv
        )
        SELECT
            total_gmv_revenue_eligible,
            SUM(CASE WHEN seller_rank <= 5 THEN gmv_revenue_eligible ELSE 0 END) AS top_5_seller_gmv,
            SUM(CASE WHEN seller_rank <= 10 THEN gmv_revenue_eligible ELSE 0 END) AS top_10_seller_gmv,
            SUM(CASE WHEN seller_rank <= 50 THEN gmv_revenue_eligible ELSE 0 END) AS top_50_seller_gmv,
            SUM(CASE WHEN seller_rank <= 5 THEN gmv_revenue_eligible ELSE 0 END) / NULLIF(total_gmv_revenue_eligible, 0) AS top_5_share,
            SUM(CASE WHEN seller_rank <= 10 THEN gmv_revenue_eligible ELSE 0 END) / NULLIF(total_gmv_revenue_eligible, 0) AS top_10_share,
            SUM(CASE WHEN seller_rank <= 50 THEN gmv_revenue_eligible ELSE 0 END) / NULLIF(total_gmv_revenue_eligible, 0) AS top_50_share
        FROM ranked
        GROUP BY total_gmv_revenue_eligible
        """,
        processed_dir / "kpi_seller_concentration.csv",
    )

    export_query(
        conn,
        """
        SELECT 'orders_missing_purchase_timestamp' AS check_name, COUNT(*) AS issue_rows
        FROM staging.stg_orders
        WHERE order_purchase_ts IS NULL
        UNION ALL
        SELECT 'orders_missing_customer_id', COUNT(*)
        FROM staging.stg_orders
        WHERE customer_id IS NULL
        UNION ALL
        SELECT 'orders_missing_delivered_customer_date_for_delivered_status', COUNT(*)
        FROM staging.stg_orders
        WHERE order_status = 'delivered'
          AND delivered_customer_ts IS NULL
        UNION ALL
        SELECT 'orders_with_estimated_delivery_before_purchase', COUNT(*)
        FROM staging.stg_orders
        WHERE estimated_delivery_ts < order_purchase_ts
        UNION ALL
        SELECT 'duplicate_order_ids_raw', COUNT(*) - COUNT(DISTINCT order_id)
        FROM raw.orders
        UNION ALL
        SELECT 'duplicate_order_item_keys_raw', COUNT(*) - COUNT(DISTINCT CONCAT(order_id, '|', CAST(order_item_id AS VARCHAR)))
        FROM raw.order_items
        UNION ALL
        SELECT 'duplicate_geolocation_zip_prefix_raw', COUNT(*) - COUNT(DISTINCT LPAD(CAST(geolocation_zip_code_prefix AS VARCHAR), 5, '0'))
        FROM raw.geolocation
        ORDER BY issue_rows DESC, check_name
        """,
        processed_dir / "data_quality_summary.csv",
    )

    export_query(
        conn,
        """
        WITH naive_join AS (
            SELECT SUM(oi.price + oi.freight_value) AS naive_gmv
            FROM staging.stg_order_items oi
            JOIN staging.stg_order_payments p
                ON oi.order_id = p.order_id
        ),
        correct_join AS (
            SELECT SUM(item_gmv) AS trusted_gmv_all_orders,
                   SUM(revenue_eligible_gmv) AS trusted_gmv_revenue_eligible
            FROM marts.fact_orders
        )
        SELECT
            n.naive_gmv,
            c.trusted_gmv_all_orders,
            c.trusted_gmv_revenue_eligible,
            n.naive_gmv - c.trusted_gmv_all_orders AS gmv_overstatement_vs_all_orders
        FROM naive_join n
        CROSS JOIN correct_join c
        """,
        processed_dir / "kpi_join_risk_demo.csv",
    )

    export_query(
        conn,
        """
        SELECT * FROM (
            SELECT 'raw.orders' AS table_name, COUNT(*) AS row_count FROM raw.orders
            UNION ALL SELECT 'raw.order_items', COUNT(*) FROM raw.order_items
            UNION ALL SELECT 'raw.order_payments', COUNT(*) FROM raw.order_payments
            UNION ALL SELECT 'raw.order_reviews', COUNT(*) FROM raw.order_reviews
            UNION ALL SELECT 'raw.customers', COUNT(*) FROM raw.customers
            UNION ALL SELECT 'raw.products', COUNT(*) FROM raw.products
            UNION ALL SELECT 'raw.sellers', COUNT(*) FROM raw.sellers
            UNION ALL SELECT 'raw.geolocation', COUNT(*) FROM raw.geolocation
            UNION ALL SELECT 'marts.fact_orders', COUNT(*) FROM marts.fact_orders
            UNION ALL SELECT 'marts.fact_order_items', COUNT(*) FROM marts.fact_order_items
            UNION ALL SELECT 'marts.dim_customers', COUNT(*) FROM marts.dim_customers
            UNION ALL SELECT 'marts.dim_products', COUNT(*) FROM marts.dim_products
            UNION ALL SELECT 'marts.dim_sellers', COUNT(*) FROM marts.dim_sellers
            UNION ALL SELECT 'marts.dim_dates', COUNT(*) FROM marts.dim_dates
            UNION ALL SELECT 'kpi.seller_concentration', COUNT(*) FROM read_csv_auto('data/processed/kpi_seller_concentration.csv', header = TRUE)
            UNION ALL SELECT 'kpi.weekly_ops', COUNT(*) FROM (
                SELECT DATE_TRUNC('week', order_purchase_ts)::DATE AS week_start FROM marts.fact_orders GROUP BY 1
            ) q1
            UNION ALL SELECT 'kpi.customer_cohort_retention', COUNT(*) FROM (
                WITH first_orders AS (
                    SELECT customer_unique_id, DATE_TRUNC('month', MIN(order_purchase_ts))::DATE AS cohort_month
                    FROM marts.fact_orders
                    GROUP BY 1
                ),
                customer_months AS (
                    SELECT DISTINCT customer_unique_id, DATE_TRUNC('month', order_purchase_ts)::DATE AS order_month
                    FROM marts.fact_orders
                )
                SELECT 1
                FROM customer_months cm
                JOIN first_orders f ON cm.customer_unique_id = f.customer_unique_id
                GROUP BY f.cohort_month, cm.order_month
            ) q2
        ) t
        ORDER BY table_name
        """,
        processed_dir / "model_row_counts.csv",
    )

    # Executive headline stats for memo + README.
    headline = conn.execute(
        """
        SELECT
            COUNT(*) AS total_orders,
            COUNT(CASE WHEN is_revenue_eligible_order = 1 THEN 1 END) AS revenue_eligible_orders,
            SUM(COALESCE(item_gmv, 0)) AS gmv_all_orders,
            SUM(COALESCE(revenue_eligible_gmv, 0)) AS gmv_revenue_eligible,
            SUM(COALESCE(revenue_eligible_gmv, 0))
                / NULLIF(COUNT(CASE WHEN is_revenue_eligible_order = 1 THEN 1 END), 0) AS aov_revenue_eligible,
            AVG(CASE WHEN is_canceled_or_unavailable = 1 THEN 1.0 ELSE 0.0 END) AS cancellation_rate,
            AVG(avg_review_score) AS avg_review_score,
            AVG(delivery_days) AS avg_delivery_days,
            AVG(CASE WHEN is_on_time_delivery IS NULL THEN NULL ELSE is_on_time_delivery::DOUBLE END) AS on_time_rate
        FROM marts.fact_orders
        """
    ).df()
    headline.to_csv(processed_dir / "kpi_headline.csv", index=False)
    print("Exported: kpi_headline.csv (1 row)")

    conn.close()
    print(f"Reporting layer ready at: {db_path}")


if __name__ == "__main__":
    pd.set_option("display.float_format", lambda x: f"{x:,.4f}")
    main()
