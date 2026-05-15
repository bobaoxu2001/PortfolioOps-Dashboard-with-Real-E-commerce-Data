from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

import duckdb
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run_data_contract_tests


class DataContractRunnerTests(unittest.TestCase):
    def test_no_canceled_orders_produces_zero_leakage_instead_of_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = pathlib.Path(temp_dir)
            processed_dir = repo_root / "data" / "processed"
            processed_dir.mkdir(parents=True)
            (repo_root / "docs").mkdir()

            conn = duckdb.connect(str(processed_dir / "olist_reporting.duckdb"))
            try:
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
                    INSERT INTO marts.fact_orders VALUES
                        ('order-1', 'customer-1', 'delivered', 100.0, 100.0, 100.0, 5.0, 1, 0, 1)
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
                conn.execute("INSERT INTO marts.fact_order_items VALUES ('order-1', 1, 'product-1', 100.0)")
                conn.execute("CREATE TABLE marts.dim_customers (customer_id VARCHAR)")
                conn.execute("INSERT INTO marts.dim_customers VALUES ('customer-1')")
                conn.execute("CREATE TABLE marts.dim_products (product_id VARCHAR)")
                conn.execute("INSERT INTO marts.dim_products VALUES ('product-1')")
            finally:
                conn.close()

            (processed_dir / "kpi_headline.csv").write_text(
                "gmv_revenue_eligible,revenue_eligible_orders,aov_revenue_eligible\n"
                "100.0,1,100.0\n",
                encoding="utf-8",
            )
            (processed_dir / "kpi_monthly.csv").write_text(
                "gmv_revenue_eligible,revenue_eligible_orders\n"
                "100.0,1\n",
                encoding="utf-8",
            )

            run_data_contract_tests.main(repo_root=repo_root)

            results = pd.read_csv(processed_dir / "data_contract_test_results.csv")
            leakage_result = results.loc[
                results["test_name"] == "Primary revenue excludes canceled and unavailable orders"
            ].iloc[0]
            self.assertEqual("PASS", leakage_result["status"])
            self.assertEqual(0.0, float(leakage_result["observed_value"]))

            summary = pd.read_csv(processed_dir / "data_contract_test_summary.csv").iloc[0]
            self.assertEqual(0, int(summary["critical_failed"]))


if __name__ == "__main__":
    unittest.main()
