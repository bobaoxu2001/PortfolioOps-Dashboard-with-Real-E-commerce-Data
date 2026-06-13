"""Regression tests for data contract checks."""

from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

import duckdb
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run_data_contract_tests


class RunDataContractTestsTest(unittest.TestCase):
    def test_cancellation_contract_passes_when_no_canceled_orders_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = pathlib.Path(tmp)
            processed_dir = repo_root / "data" / "processed"
            processed_dir.mkdir(parents=True)
            (repo_root / "docs").mkdir()

            db_path = processed_dir / "olist_reporting.duckdb"
            conn = duckdb.connect(str(db_path))
            conn.execute("CREATE SCHEMA marts")
            conn.execute(
                """
                CREATE TABLE marts.fact_orders AS
                SELECT * FROM (
                    VALUES
                        ('order_1', 'customer_1', 'delivered', 100.0, 100.0, 1, 1, 0, 5.0, 100.0),
                        ('order_2', 'customer_2', 'delivered', 50.0, 50.0, 1, 0, 0, 2.0, 50.0)
                ) AS t(
                    order_id,
                    customer_id,
                    order_status,
                    item_gmv,
                    revenue_eligible_gmv,
                    is_revenue_eligible_order,
                    is_on_time_delivery,
                    is_canceled_or_unavailable,
                    avg_review_score,
                    payment_value_total
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE marts.fact_order_items AS
                SELECT * FROM (
                    VALUES
                        ('order_1', 1, 'product_1', 100.0),
                        ('order_2', 1, 'product_2', 50.0)
                ) AS t(order_id, order_item_id, product_id, gmv)
                """
            )
            conn.execute(
                """
                CREATE TABLE marts.dim_customers AS
                SELECT * FROM (VALUES ('customer_1'), ('customer_2')) AS t(customer_id)
                """
            )
            conn.execute(
                """
                CREATE TABLE marts.dim_products AS
                SELECT * FROM (VALUES ('product_1'), ('product_2')) AS t(product_id)
                """
            )
            conn.close()

            pd.DataFrame(
                [
                    {
                        "gmv_revenue_eligible": 150.0,
                        "revenue_eligible_orders": 2,
                        "aov_revenue_eligible": 75.0,
                    }
                ]
            ).to_csv(processed_dir / "kpi_headline.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "gmv_revenue_eligible": 150.0,
                        "revenue_eligible_orders": 2,
                    }
                ]
            ).to_csv(processed_dir / "kpi_monthly.csv", index=False)

            run_data_contract_tests.main(repo_root)

            results = pd.read_csv(processed_dir / "data_contract_test_results.csv")
            cancellation_contract = results.loc[
                results["test_name"] == "Primary revenue excludes canceled and unavailable orders"
            ].iloc[0]

            self.assertEqual(cancellation_contract["status"], "PASS")
            self.assertEqual(float(cancellation_contract["observed_value"]), 0.0)


if __name__ == "__main__":
    unittest.main()
