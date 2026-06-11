import pathlib
import tempfile
import unittest

import duckdb
import pandas as pd

from python import run_data_contract_tests


class RunDataContractTests(unittest.TestCase):
    def test_no_canceled_orders_treats_cancellation_leakage_as_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = pathlib.Path(temp_dir)
            processed_dir = repo_root / "data" / "processed"
            processed_dir.mkdir(parents=True)
            (repo_root / "docs").mkdir()

            self._write_reporting_fixture(processed_dir / "olist_reporting.duckdb")
            self._write_kpi_exports(processed_dir)

            run_data_contract_tests.main(repo_root)

            summary = pd.read_csv(processed_dir / "data_contract_test_summary.csv").iloc[0]
            self.assertEqual(0, int(summary["critical_failed"]))

            results = pd.read_csv(processed_dir / "data_contract_test_results.csv")
            cancellation_test = results.loc[
                results["test_name"] == "Primary revenue excludes canceled and unavailable orders"
            ].iloc[0]
            self.assertEqual("PASS", cancellation_test["status"])
            self.assertEqual(0.0, float(cancellation_test["observed_value"]))

    def _write_reporting_fixture(self, db_path: pathlib.Path) -> None:
        conn = duckdb.connect(str(db_path))
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
                ('order-1', 'customer-1', 'delivered', 100.0, 100.0, 1, 0, 1, 5.0, 100.0),
                ('order-2', 'customer-2', 'delivered', 200.0, 200.0, 1, 0, 0, 2.0, 200.0)
            """
        )
        conn.execute(
            """
            INSERT INTO marts.fact_order_items VALUES
                ('order-1', 1, 'product-1', 100.0),
                ('order-2', 1, 'product-2', 200.0)
            """
        )
        conn.execute(
            """
            INSERT INTO marts.dim_customers VALUES
                ('customer-1'),
                ('customer-2')
            """
        )
        conn.execute(
            """
            INSERT INTO marts.dim_products VALUES
                ('product-1'),
                ('product-2')
            """
        )
        conn.close()

    def _write_kpi_exports(self, processed_dir: pathlib.Path) -> None:
        pd.DataFrame(
            [
                {
                    "gmv_revenue_eligible": 300.0,
                    "revenue_eligible_orders": 2,
                    "aov_revenue_eligible": 150.0,
                }
            ]
        ).to_csv(processed_dir / "kpi_headline.csv", index=False)
        pd.DataFrame(
            [
                {
                    "gmv_revenue_eligible": 300.0,
                    "revenue_eligible_orders": 2,
                }
            ]
        ).to_csv(processed_dir / "kpi_monthly.csv", index=False)


if __name__ == "__main__":
    unittest.main()
