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
    def test_no_canceled_orders_reports_zero_cancellation_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = pathlib.Path(tmp)
            processed_dir = repo_root / "data" / "processed"
            processed_dir.mkdir(parents=True)
            (repo_root / "docs").mkdir()

            self._create_delivered_only_fixture(processed_dir / "olist_reporting.duckdb")
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
                        "month_start": "2018-01-01",
                        "gmv_revenue_eligible": 150.0,
                        "revenue_eligible_orders": 2,
                    }
                ]
            ).to_csv(processed_dir / "kpi_monthly.csv", index=False)

            run_data_contract_tests.main(repo_root)

            results = pd.read_csv(processed_dir / "data_contract_test_results.csv")
            summary = pd.read_csv(processed_dir / "data_contract_test_summary.csv").iloc[0]
            cancellation_test = results[
                results["test_name"] == "Primary revenue excludes canceled and unavailable orders"
            ].iloc[0]

            self.assertEqual(int(summary["critical_failed"]), 0)
            self.assertEqual(cancellation_test["status"], "PASS")
            self.assertEqual(float(cancellation_test["observed_value"]), 0.0)

    def _create_delivered_only_fixture(self, db_path: pathlib.Path) -> None:
        conn = duckdb.connect(str(db_path))
        conn.execute("CREATE SCHEMA marts")
        conn.execute(
            """
            CREATE TABLE marts.fact_orders (
                order_id VARCHAR,
                customer_id VARCHAR,
                item_gmv DOUBLE,
                revenue_eligible_gmv DOUBLE,
                is_revenue_eligible_order INTEGER,
                order_status VARCHAR,
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
                ('order_1', 'customer_1', 100.0, 100.0, 1, 'delivered', 1, 5.0, 0, 100.0),
                ('order_2', 'customer_2', 50.0, 50.0, 1, 'delivered', 0, 3.0, 0, 50.0)
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
                ('order_2', 1, 'product_2', 50.0)
            """
        )
        conn.execute("CREATE TABLE marts.dim_customers (customer_id VARCHAR)")
        conn.execute("INSERT INTO marts.dim_customers VALUES ('customer_1'), ('customer_2')")
        conn.execute("CREATE TABLE marts.dim_products (product_id VARCHAR)")
        conn.execute("INSERT INTO marts.dim_products VALUES ('product_1'), ('product_2')")
        conn.close()


if __name__ == "__main__":
    unittest.main()
