from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

import duckdb
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import run_data_contract_tests


class DataContractRunnerTests(unittest.TestCase):
    def test_cancellation_contract_handles_no_canceled_orders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = pathlib.Path(tmp)
            processed_dir = repo_root / "data" / "processed"
            processed_dir.mkdir(parents=True)
            (repo_root / "docs").mkdir()

            conn = duckdb.connect(str(processed_dir / "olist_reporting.duckdb"))
            conn.execute("CREATE SCHEMA marts")
            conn.execute(
                """
                CREATE TABLE marts.fact_orders AS
                SELECT * FROM (VALUES
                    ('order-1', 'customer-1', 125.0, 125.0, 'delivered', 1, 1, 5.0, 0, 130.0),
                    ('order-2', 'customer-2', 75.0, 75.0, 'delivered', 1, 0, 3.0, 0, 80.0)
                ) AS t(
                    order_id,
                    customer_id,
                    item_gmv,
                    revenue_eligible_gmv,
                    order_status,
                    is_revenue_eligible_order,
                    is_on_time_delivery,
                    avg_review_score,
                    is_canceled_or_unavailable,
                    payment_value_total
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE marts.fact_order_items AS
                SELECT * FROM (VALUES
                    ('order-1', 1, 'product-1', 125.0),
                    ('order-2', 1, 'product-2', 75.0)
                ) AS t(order_id, order_item_id, product_id, gmv)
                """
            )
            conn.execute(
                """
                CREATE TABLE marts.dim_customers AS
                SELECT * FROM (VALUES ('customer-1'), ('customer-2')) AS t(customer_id)
                """
            )
            conn.execute(
                """
                CREATE TABLE marts.dim_products AS
                SELECT * FROM (VALUES ('product-1'), ('product-2')) AS t(product_id)
                """
            )
            conn.close()

            pd.DataFrame(
                [
                    {
                        "gmv_revenue_eligible": 200.0,
                        "revenue_eligible_orders": 2,
                        "aov_revenue_eligible": 100.0,
                    }
                ]
            ).to_csv(processed_dir / "kpi_headline.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "gmv_revenue_eligible": 200.0,
                        "revenue_eligible_orders": 2,
                    }
                ]
            ).to_csv(processed_dir / "kpi_monthly.csv", index=False)

            run_data_contract_tests.main(repo_root)

            results = pd.read_csv(processed_dir / "data_contract_test_results.csv")
            cancellation_result = results.loc[
                results["test_name"] == "Primary revenue excludes canceled and unavailable orders"
            ].iloc[0]
            self.assertEqual("PASS", cancellation_result["status"])
            self.assertEqual(0.0, cancellation_result["observed_value"])

            summary = pd.read_csv(processed_dir / "data_contract_test_summary.csv").iloc[0]
            self.assertEqual(0, summary["critical_failed"])


if __name__ == "__main__":
    unittest.main()
