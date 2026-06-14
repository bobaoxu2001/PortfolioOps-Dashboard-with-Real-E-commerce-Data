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
    def _write_common_inputs(
        self,
        repo_root: pathlib.Path,
        *,
        fact_orders_rows: list[tuple[object, ...]],
        fact_order_items_rows: list[tuple[object, ...]],
        headline_row: dict[str, float],
        monthly_row: dict[str, float],
    ) -> None:
        processed_dir = repo_root / "data" / "processed"
        docs_dir = repo_root / "docs"
        processed_dir.mkdir(parents=True)
        docs_dir.mkdir(parents=True)

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
        conn.executemany(
            "INSERT INTO marts.fact_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            fact_orders_rows,
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
        conn.executemany(
            "INSERT INTO marts.fact_order_items VALUES (?, ?, ?, ?)",
            fact_order_items_rows,
        )
        conn.execute("CREATE TABLE marts.dim_customers (customer_id VARCHAR)")
        conn.execute("INSERT INTO marts.dim_customers VALUES ('c1')")
        conn.execute("CREATE TABLE marts.dim_products (product_id VARCHAR)")
        conn.execute("INSERT INTO marts.dim_products VALUES ('p1')")
        conn.close()

        pd.DataFrame([headline_row]).to_csv(processed_dir / "kpi_headline.csv", index=False)
        pd.DataFrame([monthly_row]).to_csv(processed_dir / "kpi_monthly.csv", index=False)

    def test_no_canceled_orders_reports_zero_cancellation_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = pathlib.Path(tmpdir)
            self._write_common_inputs(
                repo_root,
                fact_orders_rows=[
                    ("o1", "c1", "delivered", 100.0, 100.0, 1, 1, 0, 5.0, 100.0),
                ],
                fact_order_items_rows=[
                    ("o1", 1, "p1", 100.0),
                ],
                headline_row={
                    "gmv_revenue_eligible": 100.0,
                    "revenue_eligible_orders": 1.0,
                    "aov_revenue_eligible": 100.0,
                },
                monthly_row={
                    "gmv_revenue_eligible": 100.0,
                    "revenue_eligible_orders": 1.0,
                    "aov_revenue_eligible": 100.0,
                },
            )

            run_data_contract_tests.main(repo_root)

            results = pd.read_csv(repo_root / "data" / "processed" / "data_contract_test_results.csv")
            cancellation_test = results.loc[
                results["test_name"] == "Primary revenue excludes canceled and unavailable orders"
            ].iloc[0]
            self.assertEqual(cancellation_test["status"], "PASS")
            self.assertEqual(cancellation_test["observed_value"], 0.0)

    def test_zero_revenue_eligible_orders_writes_critical_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = pathlib.Path(tmpdir)
            self._write_common_inputs(
                repo_root,
                fact_orders_rows=[
                    ("o1", "c1", "canceled", 50.0, 0.0, 0, None, 1, 1.0, 50.0),
                ],
                fact_order_items_rows=[
                    ("o1", 1, "p1", 50.0),
                ],
                headline_row={
                    "gmv_revenue_eligible": 0.0,
                    "revenue_eligible_orders": 0.0,
                    "aov_revenue_eligible": 0.0,
                },
                monthly_row={
                    "gmv_revenue_eligible": 0.0,
                    "revenue_eligible_orders": 0.0,
                    "aov_revenue_eligible": 0.0,
                },
            )

            with self.assertRaises(SystemExit):
                run_data_contract_tests.main(repo_root)

            summary = pd.read_csv(repo_root / "data" / "processed" / "data_contract_test_summary.csv")
            self.assertGreater(int(summary.loc[0, "critical_failed"]), 0)
            results = pd.read_csv(repo_root / "data" / "processed" / "data_contract_test_results.csv")
            zero_count_test = results.loc[
                results["test_name"] == "Revenue-eligible order count is non-zero"
            ].iloc[0]
            self.assertEqual(zero_count_test["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
