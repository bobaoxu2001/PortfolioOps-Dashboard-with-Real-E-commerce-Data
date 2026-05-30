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
    def test_no_canceled_orders_have_zero_cancellation_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = pathlib.Path(tmp_dir)
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
                    item_gmv DOUBLE,
                    revenue_eligible_gmv DOUBLE,
                    is_revenue_eligible_order INTEGER,
                    order_status VARCHAR,
                    is_on_time_delivery INTEGER,
                    avg_review_score DOUBLE,
                    payment_value_total DOUBLE,
                    is_canceled_or_unavailable INTEGER
                )
                """
            )
            conn.execute(
                """
                INSERT INTO marts.fact_orders VALUES
                    ('o1', 'c1', 100.0, 100.0, 1, 'delivered', 1, 5.0, 100.0, 0),
                    ('o2', 'c2', 200.0, 200.0, 1, 'delivered', 0, 1.0, 200.0, 0)
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
                    ('o1', 1, 'p1', 100.0),
                    ('o2', 1, 'p2', 200.0)
                """
            )
            conn.execute("CREATE TABLE marts.dim_customers (customer_id VARCHAR)")
            conn.execute("INSERT INTO marts.dim_customers VALUES ('c1'), ('c2')")
            conn.execute("CREATE TABLE marts.dim_products (product_id VARCHAR)")
            conn.execute("INSERT INTO marts.dim_products VALUES ('p1'), ('p2')")
            conn.close()

            (processed_dir / "kpi_headline.csv").write_text(
                "gmv_revenue_eligible,revenue_eligible_orders,aov_revenue_eligible\n"
                "300.0,2,150.0\n",
                encoding="utf-8",
            )
            (processed_dir / "kpi_monthly.csv").write_text(
                "month_start,gmv_revenue_eligible,revenue_eligible_orders\n"
                "2018-01-01,300.0,2\n",
                encoding="utf-8",
            )

            run_data_contract_tests.main(repo_root)

            summary = pd.read_csv(processed_dir / "data_contract_test_summary.csv")
            self.assertEqual(int(summary.loc[0, "critical_failed"]), 0)

            results = pd.read_csv(processed_dir / "data_contract_test_results.csv")
            leakage_row = results.loc[
                results["test_name"] == "Primary revenue excludes canceled and unavailable orders"
            ].iloc[0]
            self.assertEqual(leakage_row["status"], "PASS")
            self.assertEqual(float(leakage_row["observed_value"]), 0.0)


if __name__ == "__main__":
    unittest.main()
