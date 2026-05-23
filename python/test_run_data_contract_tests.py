"""Regression tests for the data contract runner."""

from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

import duckdb
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run_data_contract_tests  # noqa: E402


class DataContractRunnerTest(unittest.TestCase):
    def test_no_canceled_orders_reports_zero_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = pathlib.Path(tmp_dir)
            processed_dir = repo_root / "data" / "processed"
            processed_dir.mkdir(parents=True)
            docs_dir = repo_root / "docs"
            docs_dir.mkdir()

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
                    is_canceled_or_unavailable INTEGER,
                    avg_review_score DOUBLE,
                    payment_value_total DOUBLE
                )
                """
            )
            conn.execute(
                """
                INSERT INTO marts.fact_orders VALUES
                    ('o1', 'c1', 'delivered', 100.0, 100.0, 1, 1, 0, 5.0, 100.0),
                    ('o2', 'c2', 'delivered', 50.0, 50.0, 1, 0, 0, 3.0, 50.0)
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
                    ('o2', 1, 'p2', 50.0)
                """
            )
            conn.execute("CREATE TABLE marts.dim_customers (customer_id VARCHAR)")
            conn.execute("INSERT INTO marts.dim_customers VALUES ('c1'), ('c2')")
            conn.execute("CREATE TABLE marts.dim_products (product_id VARCHAR)")
            conn.execute("INSERT INTO marts.dim_products VALUES ('p1'), ('p2')")
            conn.close()

            (processed_dir / "kpi_headline.csv").write_text(
                "gmv_revenue_eligible,revenue_eligible_orders,aov_revenue_eligible\n"
                "150.0,2,75.0\n",
                encoding="utf-8",
            )
            (processed_dir / "kpi_monthly.csv").write_text(
                "month_start,gmv_revenue_eligible,revenue_eligible_orders\n"
                "2018-01-01,150.0,2\n",
                encoding="utf-8",
            )

            run_data_contract_tests.main(repo_root)

            results = pd.read_csv(processed_dir / "data_contract_test_results.csv")
            leakage_row = results.loc[
                results["test_name"] == "Primary revenue excludes canceled and unavailable orders"
            ].iloc[0]
            self.assertEqual(leakage_row["status"], "PASS")
            self.assertEqual(leakage_row["observed_value"], 0.0)


if __name__ == "__main__":
    unittest.main()
