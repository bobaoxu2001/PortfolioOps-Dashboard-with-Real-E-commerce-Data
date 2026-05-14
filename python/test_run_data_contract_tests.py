from __future__ import annotations

import csv
import pathlib
import sys
import tempfile
import unittest

import duckdb

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import run_data_contract_tests


def _write_csv(path: pathlib.Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


class DataContractNullMetricTests(unittest.TestCase):
    def test_numeric_predicates_fail_closed_for_null_metrics(self) -> None:
        self.assertFalse(run_data_contract_tests._abs_less_than(None, 0.01))
        self.assertFalse(run_data_contract_tests._greater_than(float("nan"), 0))
        self.assertFalse(run_data_contract_tests._between(float("inf"), 0, 1))
        self.assertEqual(run_data_contract_tests._format_observed_value(None), "NULL")
        self.assertEqual(run_data_contract_tests._format_observed_value(float("nan")), "NULL")

    def test_zero_canceled_orders_reports_zero_leakage_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = pathlib.Path(temp_dir)
            processed_dir = repo_root / "data" / "processed"
            processed_dir.mkdir(parents=True)
            (repo_root / "docs").mkdir()

            db_path = processed_dir / "olist_reporting.duckdb"
            conn = duckdb.connect(str(db_path))
            conn.execute("CREATE SCHEMA marts")
            conn.execute(
                """
                CREATE TABLE marts.fact_orders AS
                SELECT
                    'order-1' AS order_id,
                    'customer-1' AS customer_id,
                    'unique-customer-1' AS customer_unique_id,
                    'delivered' AS order_status,
                    100.0 AS item_gmv,
                    100.0 AS revenue_eligible_gmv,
                    1 AS is_revenue_eligible_order,
                    0 AS is_canceled_or_unavailable,
                    1 AS is_on_time_delivery,
                    5.0 AS avg_review_score,
                    100.0 AS payment_value_total
                """
            )
            conn.execute(
                """
                CREATE TABLE marts.fact_order_items AS
                SELECT
                    'order-1' AS order_id,
                    1 AS order_item_id,
                    'product-1' AS product_id,
                    100.0 AS gmv
                """
            )
            conn.execute("CREATE TABLE marts.dim_customers AS SELECT 'customer-1' AS customer_id")
            conn.execute("CREATE TABLE marts.dim_products AS SELECT 'product-1' AS product_id")
            conn.close()

            _write_csv(
                processed_dir / "kpi_headline.csv",
                [
                    {
                        "total_orders": 1,
                        "revenue_eligible_orders": 1,
                        "gmv_all_orders": 100.0,
                        "gmv_revenue_eligible": 100.0,
                        "aov_revenue_eligible": 100.0,
                        "cancellation_rate": 0.0,
                        "avg_review_score": 5.0,
                        "avg_delivery_days": 1.0,
                        "on_time_rate": 1.0,
                    }
                ],
            )
            _write_csv(
                processed_dir / "kpi_monthly.csv",
                [
                    {
                        "month_start": "2024-01-01",
                        "total_orders": 1,
                        "revenue_eligible_orders": 1,
                        "gmv_all_orders": 100.0,
                        "gmv_revenue_eligible": 100.0,
                        "aov_revenue_eligible": 100.0,
                    }
                ],
            )

            run_data_contract_tests.main(repo_root=repo_root)

            with (processed_dir / "data_contract_test_summary.csv").open(encoding="utf-8") as handle:
                summary = next(csv.DictReader(handle))
            self.assertEqual(summary["critical_failed"], "0")

            with (processed_dir / "data_contract_test_results.csv").open(encoding="utf-8") as handle:
                results = {row["test_name"]: row for row in csv.DictReader(handle)}
            leakage_check = results["Primary revenue excludes canceled and unavailable orders"]
            self.assertEqual(leakage_check["status"], "PASS")
            self.assertAlmostEqual(float(leakage_check["observed_value"]), 0.0)

            report = (repo_root / "docs" / "data_contract_test_report.md").read_text(encoding="utf-8")
            self.assertIn("| Late deliveries depress review score (directional test) | info | FAIL | NULL |", report)


if __name__ == "__main__":
    unittest.main()
