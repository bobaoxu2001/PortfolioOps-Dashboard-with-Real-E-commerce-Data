from __future__ import annotations

import csv
import pathlib
import sys
import tempfile
import unittest

import duckdb

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run_data_contract_tests  # noqa: E402


class DataContractTests(unittest.TestCase):
    def test_no_canceled_orders_reports_zero_cancellation_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = pathlib.Path(tmp_dir)
            processed_dir = repo_root / "data" / "processed"
            docs_dir = repo_root / "docs"
            processed_dir.mkdir(parents=True)
            docs_dir.mkdir()

            conn = duckdb.connect(str(processed_dir / "olist_reporting.duckdb"))
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
            conn.executemany("INSERT INTO marts.dim_customers VALUES (?)", [("customer-1",), ("customer-2",)])
            conn.executemany("INSERT INTO marts.dim_products VALUES (?)", [("product-1",), ("product-2",)])
            conn.executemany(
                "INSERT INTO marts.fact_order_items VALUES (?, ?, ?, ?)",
                [("order-1", 1, "product-1", 100.0), ("order-2", 1, "product-2", 50.0)],
            )
            conn.executemany(
                "INSERT INTO marts.fact_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    ("order-1", "customer-1", "delivered", 100.0, 100.0, 1, 1, 0, 5.0, 100.0),
                    ("order-2", "customer-2", "delivered", 50.0, 50.0, 1, 0, 0, 1.0, 50.0),
                ],
            )
            conn.close()

            (processed_dir / "kpi_headline.csv").write_text(
                "gmv_revenue_eligible,revenue_eligible_orders,aov_revenue_eligible\n150.0,2,75.0\n",
                encoding="utf-8",
            )
            (processed_dir / "kpi_monthly.csv").write_text(
                "gmv_revenue_eligible,revenue_eligible_orders\n150.0,2\n",
                encoding="utf-8",
            )

            run_data_contract_tests.main(repo_root)

            with (processed_dir / "data_contract_test_results.csv").open(newline="", encoding="utf-8") as results_file:
                results = {row["test_name"]: row for row in csv.DictReader(results_file)}

            self.assertEqual(
                "0.0",
                results["Primary revenue excludes canceled and unavailable orders"]["observed_value"],
            )
            self.assertEqual(
                "PASS",
                results["Primary revenue excludes canceled and unavailable orders"]["status"],
            )


if __name__ == "__main__":
    unittest.main()
