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
    def test_no_canceled_orders_do_not_crash_cancellation_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = pathlib.Path(tmpdir)
            processed_dir = repo_root / "data" / "processed"
            processed_dir.mkdir(parents=True)
            (repo_root / "docs").mkdir()

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
                    is_on_time_delivery INTEGER,
                    avg_review_score DOUBLE,
                    is_canceled_or_unavailable INTEGER,
                    payment_value_total DOUBLE
                )
                """
            )
            conn.execute(
                """
                INSERT INTO marts.fact_orders VALUES
                    ('o1', 'c1', 'delivered', 120.0, 120.0, 1, 1, 5.0, 0, 120.0),
                    ('o2', 'c2', 'delivered', 80.0, 80.0, 1, 0, 3.0, 0, 80.0)
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
                    ('o1', 1, 'p1', 120.0),
                    ('o2', 1, 'p2', 80.0)
                """
            )
            conn.execute("CREATE TABLE marts.dim_customers (customer_id VARCHAR)")
            conn.execute("INSERT INTO marts.dim_customers VALUES ('c1'), ('c2')")
            conn.execute("CREATE TABLE marts.dim_products (product_id VARCHAR)")
            conn.execute("INSERT INTO marts.dim_products VALUES ('p1'), ('p2')")
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

            summary = pd.read_csv(processed_dir / "data_contract_test_summary.csv").iloc[0]
            self.assertEqual(summary["critical_failed"], 0)

            results = pd.read_csv(processed_dir / "data_contract_test_results.csv")
            cancellation_result = results.loc[
                results["test_name"] == "Primary revenue excludes canceled and unavailable orders"
            ].iloc[0]
            self.assertEqual(cancellation_result["status"], "PASS")
            self.assertEqual(cancellation_result["observed_value"], 0.0)


if __name__ == "__main__":
    unittest.main()
