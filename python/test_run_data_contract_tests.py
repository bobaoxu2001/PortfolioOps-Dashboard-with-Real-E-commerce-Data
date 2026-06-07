from __future__ import annotations

import csv
import pathlib
import tempfile
import unittest

import duckdb

from python import run_data_contract_tests


class DataContractTests(unittest.TestCase):
    def test_no_canceled_or_unavailable_orders_do_not_crash_contract_runner(self) -> None:
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
                    CREATE TABLE marts.fact_orders AS
                    SELECT * FROM (VALUES
                        ('order_1', 'customer_1', 100.0::DOUBLE, 100.0::DOUBLE, 1, 'delivered', 1, 5.0::DOUBLE, 0, 100.0::DOUBLE),
                        ('order_2', 'customer_2',  50.0::DOUBLE,  50.0::DOUBLE, 1, 'delivered', 0, 3.0::DOUBLE, 0,  50.0::DOUBLE)
                    ) AS t(
                        order_id,
                        customer_id,
                        item_gmv,
                        revenue_eligible_gmv,
                        is_revenue_eligible_order,
                        order_status,
                        is_on_time_delivery,
                        avg_review_score,
                        is_canceled_or_unavailable,
                        payment_value_total
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE marts.fact_order_items AS
                    SELECT * FROM (VALUES
                        ('order_1', 1, 'product_1', 100.0::DOUBLE),
                        ('order_2', 1, 'product_2',  50.0::DOUBLE)
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
            finally:
                conn.close()

            (processed_dir / "kpi_headline.csv").write_text(
                "gmv_revenue_eligible,revenue_eligible_orders,aov_revenue_eligible\n"
                "150.0,2,75.0\n",
                encoding="utf-8",
            )
            (processed_dir / "kpi_monthly.csv").write_text(
                "gmv_revenue_eligible,revenue_eligible_orders\n"
                "150.0,2\n",
                encoding="utf-8",
            )

            run_data_contract_tests.main(repo_root)

            with (processed_dir / "data_contract_test_summary.csv").open(newline="", encoding="utf-8") as csv_file:
                summary = next(csv.DictReader(csv_file))
            self.assertEqual(summary["critical_failed"], "0")

            with (processed_dir / "data_contract_test_results.csv").open(newline="", encoding="utf-8") as csv_file:
                results = {row["test_name"]: row for row in csv.DictReader(csv_file)}
            self.assertEqual(
                results["Primary revenue excludes canceled and unavailable orders"]["observed_value"],
                "0.0",
            )


if __name__ == "__main__":
    unittest.main()
