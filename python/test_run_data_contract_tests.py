from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

import duckdb
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run_data_contract_tests  # noqa: E402


class RunDataContractTests(unittest.TestCase):
    def test_cancellation_leakage_check_handles_no_canceled_orders(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = pathlib.Path(tmpdir)
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
                    is_revenue_eligible_order INTEGER,
                    revenue_eligible_gmv DOUBLE,
                    item_gmv DOUBLE,
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
                    ('order_on_time', 'customer_1', 'delivered', 1, 100.0, 100.0, 1, 0, 5.0, 100.0),
                    ('order_late', 'customer_2', 'delivered', 1, 50.0, 50.0, 0, 0, 2.0, 50.0)
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
                    ('order_on_time', 1, 'product_1', 100.0),
                    ('order_late', 1, 'product_2', 50.0)
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
                        "gmv_revenue_eligible": 150.0,
                        "aov_revenue_eligible": 75.0,
                    }
                ]
            ).to_csv(processed_dir / "kpi_headline.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "month_start": "2018-01-01",
                        "revenue_eligible_orders": 2,
                        "gmv_revenue_eligible": 150.0,
                    }
                ]
            ).to_csv(processed_dir / "kpi_monthly.csv", index=False)

            run_data_contract_tests.main(repo_root)

            results = pd.read_csv(processed_dir / "data_contract_test_results.csv")
            cancellation_check = results.loc[
                results["test_name"] == "Primary revenue excludes canceled and unavailable orders"
            ].iloc[0]

            self.assertEqual(cancellation_check["status"], "PASS")
            self.assertEqual(float(cancellation_check["observed_value"]), 0.0)


if __name__ == "__main__":
    unittest.main()
