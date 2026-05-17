"""Regression tests for the data contract runner."""

from __future__ import annotations

import importlib.util
import pathlib
import tempfile
import unittest

import duckdb
import pandas as pd


MODULE_PATH = pathlib.Path(__file__).with_name("run_data_contract_tests.py")


def _load_contract_module():
    spec = importlib.util.spec_from_file_location("run_data_contract_tests", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DataContractRunnerTest(unittest.TestCase):
    def test_empty_cancellation_slice_does_not_crash(self) -> None:
        module = _load_contract_module()

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = pathlib.Path(tmp)
            processed_dir = repo_root / "data" / "processed"
            processed_dir.mkdir(parents=True)
            (repo_root / "docs").mkdir()

            conn = duckdb.connect(str(processed_dir / "olist_reporting.duckdb"))
            conn.execute("CREATE SCHEMA marts")
            conn.execute(
                """
                CREATE TABLE marts.fact_orders AS
                SELECT
                    'o1' AS order_id,
                    'c1' AS customer_id,
                    'delivered' AS order_status,
                    10.0 AS item_gmv,
                    10.0 AS revenue_eligible_gmv,
                    1 AS is_revenue_eligible_order,
                    1 AS is_on_time_delivery,
                    0 AS is_canceled_or_unavailable,
                    5.0 AS avg_review_score,
                    10.0 AS payment_value_total
                """
            )
            conn.execute(
                """
                CREATE TABLE marts.fact_order_items AS
                SELECT
                    'o1' AS order_id,
                    1 AS order_item_id,
                    'p1' AS product_id,
                    10.0 AS gmv
                """
            )
            conn.execute("CREATE TABLE marts.dim_customers AS SELECT 'c1' AS customer_id")
            conn.execute("CREATE TABLE marts.dim_products AS SELECT 'p1' AS product_id")
            conn.close()

            pd.DataFrame(
                [
                    {
                        "gmv_revenue_eligible": 10.0,
                        "revenue_eligible_orders": 1,
                        "aov_revenue_eligible": 10.0,
                    }
                ]
            ).to_csv(processed_dir / "kpi_headline.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "gmv_revenue_eligible": 10.0,
                        "revenue_eligible_orders": 1,
                    }
                ]
            ).to_csv(processed_dir / "kpi_monthly.csv", index=False)

            module.__file__ = str(repo_root / "python" / "run_data_contract_tests.py")
            module.main()

            results = pd.read_csv(processed_dir / "data_contract_test_results.csv")
            cancellation_result = results.loc[
                results["test_name"] == "Primary revenue excludes canceled and unavailable orders"
            ].iloc[0]
            self.assertEqual(cancellation_result["status"], "PASS")
            self.assertEqual(float(cancellation_result["observed_value"]), 0.0)

            summary = pd.read_csv(processed_dir / "data_contract_test_summary.csv").iloc[0]
            self.assertEqual(int(summary["critical_failed"]), 0)


if __name__ == "__main__":
    unittest.main()
