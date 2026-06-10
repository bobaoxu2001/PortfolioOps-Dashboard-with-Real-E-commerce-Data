from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import duckdb
import pandas as pd

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
                SELECT
                    'order_1'::VARCHAR AS order_id,
                    'customer_1'::VARCHAR AS customer_id,
                    'delivered'::VARCHAR AS order_status,
                    100.0::DOUBLE AS item_gmv,
                    100.0::DOUBLE AS revenue_eligible_gmv,
                    1::INTEGER AS is_revenue_eligible_order,
                    0::INTEGER AS is_canceled_or_unavailable,
                    1::INTEGER AS is_on_time_delivery,
                    5.0::DOUBLE AS avg_review_score,
                    105.0::DOUBLE AS payment_value_total
                """
            )
            conn.execute(
                """
                CREATE TABLE marts.fact_order_items AS
                SELECT
                    'order_1'::VARCHAR AS order_id,
                    1::INTEGER AS order_item_id,
                    'product_1'::VARCHAR AS product_id,
                    100.0::DOUBLE AS gmv
                """
            )
            conn.execute("CREATE TABLE marts.dim_customers AS SELECT 'customer_1'::VARCHAR AS customer_id")
            conn.execute("CREATE TABLE marts.dim_products AS SELECT 'product_1'::VARCHAR AS product_id")
            conn.close()

            pd.DataFrame(
                [
                    {
                        "gmv_revenue_eligible": 100.0,
                        "revenue_eligible_orders": 1,
                        "aov_revenue_eligible": 100.0,
                    }
                ]
            ).to_csv(processed_dir / "kpi_headline.csv", index=False)
            pd.DataFrame(
                [{"gmv_revenue_eligible": 100.0, "revenue_eligible_orders": 1}]
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
