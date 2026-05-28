"""Regression tests for data contract execution."""

from __future__ import annotations

import pathlib
import tempfile
import unittest

import duckdb
import pandas as pd

from python import run_data_contract_tests


class DataContractTests(unittest.TestCase):
    def test_no_canceled_orders_does_not_crash_contract_runner(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = pathlib.Path(temp_dir)
            processed_dir = repo_root / "data" / "processed"
            processed_dir.mkdir(parents=True)
            (repo_root / "docs").mkdir()

            db_path = processed_dir / "olist_reporting.duckdb"
            conn = duckdb.connect(str(db_path))
            try:
                conn.execute("CREATE SCHEMA marts")
                conn.execute(
                    """
                    CREATE TABLE marts.fact_orders (
                        order_id VARCHAR,
                        customer_id VARCHAR,
                        order_status VARCHAR,
                        item_gmv DOUBLE,
                        revenue_eligible_gmv DOUBLE,
                        is_revenue_eligible_order INTEGER,
                        is_on_time_delivery INTEGER,
                        is_canceled_or_unavailable INTEGER,
                        avg_review_score DOUBLE,
                        payment_value_total DOUBLE
                    )
                    """
                )
                conn.execute(
                    """
                    INSERT INTO marts.fact_orders VALUES
                        ('order-1', 'customer-1', 'delivered', 10.0, 10.0, 1, 1, 0, 5.0, 10.0),
                        ('order-2', 'customer-2', 'delivered', 20.0, 20.0, 1, 0, 0, 3.0, 20.0)
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE marts.fact_order_items (
                        order_id VARCHAR,
                        order_item_id INTEGER,
                        product_id VARCHAR,
                        gmv DOUBLE
                    )
                    """
                )
                conn.execute(
                    """
                    INSERT INTO marts.fact_order_items VALUES
                        ('order-1', 1, 'product-1', 10.0),
                        ('order-2', 1, 'product-2', 20.0)
                    """
                )
                conn.execute("CREATE TABLE marts.dim_customers (customer_id VARCHAR)")
                conn.execute("INSERT INTO marts.dim_customers VALUES ('customer-1'), ('customer-2')")
                conn.execute("CREATE TABLE marts.dim_products (product_id VARCHAR)")
                conn.execute("INSERT INTO marts.dim_products VALUES ('product-1'), ('product-2')")
            finally:
                conn.close()

            pd.DataFrame(
                [
                    {
                        "gmv_revenue_eligible": 30.0,
                        "revenue_eligible_orders": 2,
                        "aov_revenue_eligible": 15.0,
                    }
                ]
            ).to_csv(processed_dir / "kpi_headline.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "order_month": "2026-01-01",
                        "gmv_revenue_eligible": 30.0,
                        "revenue_eligible_orders": 2,
                    }
                ]
            ).to_csv(processed_dir / "kpi_monthly.csv", index=False)

            run_data_contract_tests.main(repo_root)

            results = pd.read_csv(processed_dir / "data_contract_test_results.csv")
            cancellation_test = results.loc[
                results["test_name"] == "Primary revenue excludes canceled and unavailable orders"
            ].iloc[0]
            self.assertEqual("PASS", cancellation_test["status"])
            self.assertEqual(0.0, cancellation_test["observed_value"])


if __name__ == "__main__":
    unittest.main()
