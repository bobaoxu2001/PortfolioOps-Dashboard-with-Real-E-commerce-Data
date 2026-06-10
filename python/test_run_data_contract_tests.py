from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_data_contract_tests import main


class RunDataContractTestsTest(unittest.TestCase):
    def test_no_canceled_orders_does_not_crash_cancellation_exclusion_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            processed_dir = repo_root / "data" / "processed"
            processed_dir.mkdir(parents=True)
            (repo_root / "docs").mkdir()

            conn = duckdb.connect(str(processed_dir / "olist_reporting.duckdb"))
            conn.execute("CREATE SCHEMA marts")
            conn.execute(
                """
                CREATE TABLE marts.fact_orders AS
                SELECT *
                FROM (
                    VALUES
                        (
                            'order_1', 'customer_1', 'delivered', 100.0, 100.0,
                            1, 0, 1, 5.0, 105.0
                        ),
                        (
                            'order_2', 'customer_2', 'delivered', 50.0, 50.0,
                            1, 0, 0, 3.0, 52.5
                        )
                ) AS t(
                    order_id,
                    customer_id,
                    order_status,
                    item_gmv,
                    revenue_eligible_gmv,
                    is_revenue_eligible_order,
                    is_canceled_or_unavailable,
                    is_on_time_delivery,
                    avg_review_score,
                    payment_value_total
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE marts.fact_order_items AS
                SELECT *
                FROM (
                    VALUES
                        ('order_1', 1, 'product_1', 100.0),
                        ('order_2', 1, 'product_1', 50.0)
                ) AS t(order_id, order_item_id, product_id, gmv)
                """
            )
            conn.execute(
                """
                CREATE TABLE marts.dim_customers AS
                SELECT *
                FROM (VALUES ('customer_1'), ('customer_2')) AS t(customer_id)
                """
            )
            conn.execute("CREATE TABLE marts.dim_products AS SELECT 'product_1'::VARCHAR AS product_id")
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
                [{"gmv_revenue_eligible": 150.0, "revenue_eligible_orders": 2}]
            ).to_csv(processed_dir / "kpi_monthly.csv", index=False)

            main(repo_root)

            results = pd.read_csv(processed_dir / "data_contract_test_results.csv")
            cancellation_check = results.loc[
                results["test_name"] == "Primary revenue excludes canceled and unavailable orders"
            ].iloc[0]
            self.assertEqual(cancellation_check["status"], "PASS")
            self.assertEqual(cancellation_check["observed_value"], 0)


if __name__ == "__main__":
    unittest.main()
