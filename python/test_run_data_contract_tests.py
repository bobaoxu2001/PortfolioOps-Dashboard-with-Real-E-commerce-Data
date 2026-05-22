"""Regression tests for data contract checks."""

from __future__ import annotations

import pathlib
import tempfile
import unittest

import duckdb
import pandas as pd

from python import run_data_contract_tests


class DataContractRunnerTests(unittest.TestCase):
    def test_no_canceled_orders_reports_zero_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = pathlib.Path(temp_dir)
            processed_dir = repo_root / "data" / "processed"
            processed_dir.mkdir(parents=True)
            (repo_root / "docs").mkdir()

            self._write_minimal_kpi_exports(processed_dir)
            self._write_minimal_reporting_db(processed_dir / "olist_reporting.duckdb")

            run_data_contract_tests.main(repo_root=repo_root)

            results = pd.read_csv(processed_dir / "data_contract_test_results.csv")
            cancellation_test = results.loc[
                results["test_name"] == "Primary revenue excludes canceled and unavailable orders"
            ].iloc[0]
            self.assertEqual(cancellation_test["status"], "PASS")
            self.assertEqual(cancellation_test["observed_value"], 0)

            summary = pd.read_csv(processed_dir / "data_contract_test_summary.csv").iloc[0]
            self.assertEqual(summary["critical_failed"], 0)

    @staticmethod
    def _write_minimal_kpi_exports(processed_dir: pathlib.Path) -> None:
        (processed_dir / "kpi_headline.csv").write_text(
            "gmv_revenue_eligible,revenue_eligible_orders,aov_revenue_eligible\n"
            "100.0,2,50.0\n",
            encoding="utf-8",
        )
        (processed_dir / "kpi_monthly.csv").write_text(
            "gmv_revenue_eligible,revenue_eligible_orders\n"
            "100.0,2\n",
            encoding="utf-8",
        )

    @staticmethod
    def _write_minimal_reporting_db(db_path: pathlib.Path) -> None:
        conn = duckdb.connect(str(db_path))
        conn.execute("CREATE SCHEMA marts")
        conn.execute("CREATE TABLE marts.dim_customers (customer_id VARCHAR)")
        conn.execute("CREATE TABLE marts.dim_products (product_id VARCHAR)")
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
        conn.execute("INSERT INTO marts.dim_customers VALUES ('customer-1'), ('customer-2')")
        conn.execute("INSERT INTO marts.dim_products VALUES ('product-1'), ('product-2')")
        conn.execute(
            """
            INSERT INTO marts.fact_order_items VALUES
                ('order-1', 1, 'product-1', 42.0),
                ('order-2', 1, 'product-2', 58.0)
            """
        )
        conn.execute(
            """
            INSERT INTO marts.fact_orders VALUES
                ('order-1', 'customer-1', 42.0, 42.0, 1, 'delivered', 1, 5.0, 0, 42.0),
                ('order-2', 'customer-2', 58.0, 58.0, 1, 'delivered', 0, 2.0, 0, 58.0)
            """
        )
        conn.close()


if __name__ == "__main__":
    unittest.main()
