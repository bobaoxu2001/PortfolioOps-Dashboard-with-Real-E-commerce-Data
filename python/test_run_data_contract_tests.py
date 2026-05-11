"""Regression tests for data contract runner edge cases."""

from __future__ import annotations

import pathlib
import tempfile
import unittest

import duckdb
import pandas as pd

import run_data_contract_tests


def _write_empty_reporting_layer(repo_root: pathlib.Path) -> None:
    processed_dir = repo_root / "data" / "processed"
    docs_dir = repo_root / "docs"
    processed_dir.mkdir(parents=True)
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
            payment_value_total DOUBLE,
            avg_review_score DOUBLE,
            is_on_time_delivery INTEGER,
            is_canceled_or_unavailable INTEGER,
            is_revenue_eligible_order INTEGER
        )
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
    conn.execute("CREATE TABLE marts.dim_customers (customer_id VARCHAR)")
    conn.execute("CREATE TABLE marts.dim_products (product_id VARCHAR)")
    conn.close()

    pd.DataFrame(
        [
            {
                "total_orders": 0,
                "revenue_eligible_orders": 0,
                "gmv_revenue_eligible": 0.0,
                "aov_revenue_eligible": 0.0,
            }
        ]
    ).to_csv(processed_dir / "kpi_headline.csv", index=False)
    pd.DataFrame(
        [
            {
                "month_start": "2026-01-01",
                "gmv_revenue_eligible": 0.0,
                "revenue_eligible_orders": 0,
            }
        ]
    ).to_csv(processed_dir / "kpi_monthly.csv", index=False)


class DataContractNullHandlingTests(unittest.TestCase):
    def test_null_aggregates_are_reported_without_type_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = pathlib.Path(temp_dir)
            _write_empty_reporting_layer(repo_root)

            with self.assertRaises(SystemExit) as raised:
                run_data_contract_tests.main(repo_root)

            self.assertEqual(str(raised.exception), "Critical data contract tests failed.")

            results_path = repo_root / "data" / "processed" / "data_contract_test_results.csv"
            report_path = repo_root / "docs" / "data_contract_test_report.md"

            results = pd.read_csv(results_path)
            gap_result = results.loc[
                results["test_name"] == "Late deliveries depress review score (directional test)"
            ].iloc[0]
            payment_result = results.loc[
                results["test_name"] == "Payment value to GMV ratio remains plausible"
            ].iloc[0]

            self.assertEqual(gap_result["status"], "FAIL")
            self.assertTrue(pd.isna(gap_result["observed_value"]))
            self.assertEqual(payment_result["status"], "FAIL")
            self.assertTrue(pd.isna(payment_result["observed_value"]))
            self.assertIn("NULL", report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
