from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import duckdb
import pandas as pd

import run_data_contract_tests


class DataContractRegressionTests(unittest.TestCase):
    def test_no_canceled_orders_does_not_crash_contract_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            processed_dir = repo_root / "data" / "processed"
            docs_dir = repo_root / "docs"
            processed_dir.mkdir(parents=True)
            docs_dir.mkdir()

            conn = duckdb.connect(str(processed_dir / "olist_reporting.duckdb"))
            conn.execute("CREATE SCHEMA marts")
            conn.execute(
                """
                CREATE TABLE marts.fact_orders (
                    order_id VARCHAR,
                    customer_id VARCHAR,
                    order_status VARCHAR,
                    item_gmv DOUBLE,
                    revenue_eligible_gmv DOUBLE,
                    payment_value_total DOUBLE,
                    avg_review_score DOUBLE,
                    is_on_time_delivery INTEGER,
                    is_canceled_or_unavailable INTEGER,
                    is_revenue_eligible_order INTEGER
                )
                """
            )
            conn.execute(
                """
                INSERT INTO marts.fact_orders VALUES
                    ('order_1', 'customer_1', 'delivered', 100.0, 100.0, 100.0, 5.0, 1, 0, 1),
                    ('order_2', 'customer_2', 'delivered', 200.0, 200.0, 200.0, 2.0, 0, 0, 1)
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
                    ('order_1', 1, 'product_1', 100.0),
                    ('order_2', 1, 'product_2', 200.0)
                """
            )
            conn.execute("CREATE TABLE marts.dim_customers (customer_id VARCHAR)")
            conn.execute("INSERT INTO marts.dim_customers VALUES ('customer_1'), ('customer_2')")
            conn.execute("CREATE TABLE marts.dim_products (product_id VARCHAR)")
            conn.execute("INSERT INTO marts.dim_products VALUES ('product_1'), ('product_2')")
            conn.close()

            pd.DataFrame(
                [
                    {
                        "total_orders": 2,
                        "revenue_eligible_orders": 2,
                        "gmv_all_orders": 300.0,
                        "gmv_revenue_eligible": 300.0,
                        "aov_revenue_eligible": 150.0,
                        "cancellation_rate": 0.0,
                        "avg_review_score": 3.5,
                        "avg_delivery_days": 1.0,
                        "on_time_rate": 0.5,
                    }
                ]
            ).to_csv(processed_dir / "kpi_headline.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "month_start": "2026-01-01",
                        "total_orders": 2,
                        "revenue_eligible_orders": 2,
                        "gmv_all_orders": 300.0,
                        "gmv_revenue_eligible": 300.0,
                        "aov_revenue_eligible": 150.0,
                    }
                ]
            ).to_csv(processed_dir / "kpi_monthly.csv", index=False)

            run_data_contract_tests.main(repo_root=repo_root)

            summary = pd.read_csv(processed_dir / "data_contract_test_summary.csv").iloc[0]
            self.assertEqual(summary["critical_failed"], 0)

            results = pd.read_csv(processed_dir / "data_contract_test_results.csv")
            revenue_exclusion = results.loc[
                results["test_name"] == "Primary revenue excludes canceled and unavailable orders"
            ].iloc[0]
            self.assertEqual(revenue_exclusion["status"], "PASS")
            self.assertEqual(revenue_exclusion["observed_value"], 0.0)


if __name__ == "__main__":
    unittest.main()
