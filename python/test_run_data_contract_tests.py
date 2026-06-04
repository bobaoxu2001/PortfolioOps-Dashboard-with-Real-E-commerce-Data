from __future__ import annotations

import pathlib
import tempfile
import unittest

import duckdb
import pandas as pd

import run_data_contract_tests


class RunDataContractTestsRegressionTest(unittest.TestCase):
    def test_no_canceled_or_unavailable_orders_report_zero_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = pathlib.Path(temp_dir)
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
                    is_revenue_eligible_order INTEGER,
                    is_canceled_or_unavailable INTEGER,
                    is_on_time_delivery INTEGER,
                    avg_review_score DOUBLE,
                    payment_value_total DOUBLE
                )
                """
            )
            conn.execute(
                """
                INSERT INTO marts.fact_orders VALUES
                    ('order_1', 'customer_1', 'delivered', 100.0, 100.0, 1, 0, 1, 5.0, 100.0),
                    ('order_2', 'customer_2', 'delivered', 80.0, 80.0, 1, 0, 0, 3.0, 80.0)
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
                    ('order_2', 1, 'product_2', 80.0)
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
                        "gmv_revenue_eligible": 180.0,
                        "revenue_eligible_orders": 2,
                        "aov_revenue_eligible": 90.0,
                    }
                ]
            ).to_csv(processed_dir / "kpi_headline.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "gmv_revenue_eligible": 180.0,
                        "revenue_eligible_orders": 2,
                    }
                ]
            ).to_csv(processed_dir / "kpi_monthly.csv", index=False)

            run_data_contract_tests.main(repo_root)

            results = pd.read_csv(processed_dir / "data_contract_test_results.csv")
            leakage = results.loc[
                results["test_name"] == "Primary revenue excludes canceled and unavailable orders",
                "observed_value",
            ].iloc[0]
            self.assertEqual(leakage, 0.0)

            summary = pd.read_csv(processed_dir / "data_contract_test_summary.csv").iloc[0]
            self.assertEqual(summary["critical_failed"], 0)


if __name__ == "__main__":
    unittest.main()
