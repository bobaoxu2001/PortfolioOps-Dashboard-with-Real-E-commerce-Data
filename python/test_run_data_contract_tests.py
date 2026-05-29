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
    def test_no_canceled_orders_does_not_crash_cancellation_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = pathlib.Path(tmp_dir)
            processed_dir = repo_root / "data" / "processed"
            processed_dir.mkdir(parents=True)
            (repo_root / "docs").mkdir()

            conn = duckdb.connect(str(processed_dir / "olist_reporting.duckdb"))
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
                        ('order_1', 'customer_1', 'delivered', 100.0, 100.0, 1, 1, 0, 5.0, 100.0),
                        ('order_2', 'customer_2', 'delivered', 200.0, 200.0, 1, 0, 0, 3.0, 200.0)
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
                conn.execute("CREATE TABLE marts.dim_customers AS SELECT 'customer_1' AS customer_id UNION ALL SELECT 'customer_2'")
                conn.execute("CREATE TABLE marts.dim_products AS SELECT 'product_1' AS product_id UNION ALL SELECT 'product_2'")
            finally:
                conn.close()

            pd.DataFrame(
                [
                    {
                        "gmv_revenue_eligible": 300.0,
                        "revenue_eligible_orders": 2,
                        "aov_revenue_eligible": 150.0,
                    }
                ]
            ).to_csv(processed_dir / "kpi_headline.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "gmv_revenue_eligible": 300.0,
                        "revenue_eligible_orders": 2,
                    }
                ]
            ).to_csv(processed_dir / "kpi_monthly.csv", index=False)

            run_data_contract_tests.main(repo_root)

            summary = pd.read_csv(processed_dir / "data_contract_test_summary.csv").iloc[0]
            self.assertEqual(summary["critical_failed"], 0)


if __name__ == "__main__":
    unittest.main()
