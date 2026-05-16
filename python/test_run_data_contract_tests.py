from __future__ import annotations

import pathlib
import tempfile
import unittest

import duckdb
import pandas as pd

import run_data_contract_tests as contracts


class DataContractNullHandlingTest(unittest.TestCase):
    def _write_required_csvs(
        self,
        processed_dir: pathlib.Path,
        gmv_revenue_eligible: float = 100.0,
        revenue_eligible_orders: int = 1,
    ) -> None:
        aov = gmv_revenue_eligible / revenue_eligible_orders if revenue_eligible_orders else 0.0
        pd.DataFrame(
            [
                {
                    "gmv_revenue_eligible": gmv_revenue_eligible,
                    "revenue_eligible_orders": revenue_eligible_orders,
                    "aov_revenue_eligible": aov,
                }
            ]
        ).to_csv(processed_dir / "kpi_headline.csv", index=False)
        pd.DataFrame(
            [
                {
                    "gmv_revenue_eligible": gmv_revenue_eligible,
                    "revenue_eligible_orders": revenue_eligible_orders,
                }
            ]
        ).to_csv(processed_dir / "kpi_monthly.csv", index=False)

    def _create_contract_db(self, processed_dir: pathlib.Path, include_order_item: bool = True) -> None:
        conn = duckdb.connect(str(processed_dir / "olist_reporting.duckdb"))
        conn.execute("CREATE SCHEMA marts")
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
                payment_value_total DOUBLE,
                is_canceled_or_unavailable INTEGER
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
        conn.execute(
            """
            INSERT INTO marts.fact_orders VALUES
                ('order-1', 'customer-1', 100.0, 100.0, 1, 'delivered', 1, 5.0, 100.0, 0)
            """
        )
        if include_order_item:
            conn.execute(
                """
                INSERT INTO marts.fact_order_items VALUES
                    ('order-1', 1, 'product-1', 100.0)
                """
            )
            conn.execute("INSERT INTO marts.dim_products VALUES ('product-1')")
        conn.execute("INSERT INTO marts.dim_customers VALUES ('customer-1')")
        conn.close()

    def test_sparse_noncritical_null_metrics_are_reported_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = pathlib.Path(tmpdir)
            processed_dir = repo_root / "data" / "processed"
            processed_dir.mkdir(parents=True)
            (repo_root / "docs").mkdir()
            self._write_required_csvs(processed_dir)
            self._create_contract_db(processed_dir)

            contracts.main(repo_root)

            results = pd.read_csv(processed_dir / "data_contract_test_results.csv")
            cancellation_row = results.loc[
                results["test_name"] == "Primary revenue excludes canceled and unavailable orders"
            ].iloc[0]
            self.assertEqual(cancellation_row["status"], "PASS")
            self.assertEqual(cancellation_row["observed_value"], 0.0)

            review_gap_row = results.loc[
                results["test_name"] == "Late deliveries depress review score (directional test)"
            ].iloc[0]
            self.assertEqual(review_gap_row["status"], "FAIL")
            self.assertTrue(pd.isna(review_gap_row["observed_value"]))
            report_text = (repo_root / "docs" / "data_contract_test_report.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("Late deliveries depress review score", report_text)
            self.assertIn("NULL", report_text)

    def test_null_critical_metric_is_written_as_failure_before_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = pathlib.Path(tmpdir)
            processed_dir = repo_root / "data" / "processed"
            processed_dir.mkdir(parents=True)
            (repo_root / "docs").mkdir()
            self._write_required_csvs(processed_dir)
            self._create_contract_db(processed_dir, include_order_item=False)

            with self.assertRaises(SystemExit):
                contracts.main(repo_root)

            results = pd.read_csv(processed_dir / "data_contract_test_results.csv")
            gmv_row = results.loc[
                results["test_name"] == "All-orders GMV reconciles between item and order facts"
            ].iloc[0]
            self.assertEqual(gmv_row["status"], "FAIL")
            self.assertTrue(pd.isna(gmv_row["observed_value"]))

            summary = pd.read_csv(processed_dir / "data_contract_test_summary.csv").iloc[0]
            self.assertGreater(summary["critical_failed"], 0)


if __name__ == "__main__":
    unittest.main()
