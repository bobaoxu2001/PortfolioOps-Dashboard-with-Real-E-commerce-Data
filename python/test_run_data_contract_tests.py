from __future__ import annotations

import pathlib
import tempfile
import unittest

import duckdb
import pandas as pd

import run_data_contract_tests


class RunDataContractTestsTest(unittest.TestCase):
    def test_no_canceled_orders_does_not_crash_cancellation_contract(self) -> None:
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
                    is_canceled_or_unavailable INTEGER,
                    is_on_time_delivery INTEGER,
                    avg_review_score DOUBLE,
                    payment_value_total DOUBLE
                )
                """
            )
            conn.execute(
                """
                INSERT INTO marts.fact_orders VALUES
                    ('order_1', 'customer_1', 'delivered', 100.0, 100.0, 1, 0, 1, 5.0, 100.0)
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
            conn.execute("INSERT INTO marts.fact_order_items VALUES ('order_1', 1, 'product_1', 100.0)")
            conn.execute("CREATE TABLE marts.dim_customers (customer_id VARCHAR)")
            conn.execute("INSERT INTO marts.dim_customers VALUES ('customer_1')")
            conn.execute("CREATE TABLE marts.dim_products (product_id VARCHAR)")
            conn.execute("INSERT INTO marts.dim_products VALUES ('product_1')")
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
                [
                    {
                        "gmv_revenue_eligible": 100.0,
                        "revenue_eligible_orders": 1,
                        "aov_revenue_eligible": 100.0,
                    }
                ]
            ).to_csv(processed_dir / "kpi_monthly.csv", index=False)

            run_data_contract_tests.main(repo_root)

            results = pd.read_csv(processed_dir / "data_contract_test_results.csv")
            cancellation_result = results.loc[
                results["test_name"] == "Primary revenue excludes canceled and unavailable orders"
            ].iloc[0]
            self.assertEqual(cancellation_result["status"], "PASS")
            self.assertEqual(cancellation_result["observed_value"], 0.0)

            summary = pd.read_csv(processed_dir / "data_contract_test_summary.csv").iloc[0]
            self.assertEqual(summary["critical_failed"], 0)

            report = (repo_root / "docs" / "data_contract_test_report.md").read_text(encoding="utf-8")
            self.assertIn("Primary revenue excludes canceled and unavailable orders", report)
            self.assertIn("NULL", report)

    def test_numeric_predicates_treat_null_as_failure(self) -> None:
        self.assertFalse(run_data_contract_tests._abs_less_than(None, 0.01))
        self.assertFalse(run_data_contract_tests._greater_than(None, 0))
        self.assertFalse(run_data_contract_tests._greater_equal(None, 0.90))
        self.assertFalse(run_data_contract_tests._between_inclusive(None, 0.0, 1.0))
        self.assertEqual(run_data_contract_tests._format_observed_value(None), "NULL")


if __name__ == "__main__":
    unittest.main()
