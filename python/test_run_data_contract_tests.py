from __future__ import annotations

import pathlib
import tempfile
import unittest

import duckdb
import pandas as pd

import run_data_contract_tests


class DataContractTests(unittest.TestCase):
    def test_contracts_do_not_crash_when_no_orders_are_canceled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = pathlib.Path(tmpdir)
            processed_dir = repo_root / "data" / "processed"
            processed_dir.mkdir(parents=True)
            (repo_root / "docs").mkdir()

            db_path = processed_dir / "olist_reporting.duckdb"
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
                    is_on_time_delivery INTEGER,
                    is_canceled_or_unavailable INTEGER,
                    avg_review_score DOUBLE,
                    payment_value_total DOUBLE
                )
                """
            )
            conn.execute(
                """
                INSERT INTO marts.fact_orders VALUES
                    ('order_1', 'customer_1', 'delivered', 100.0, 100.0, 1, 1, 0, 5.0, 100.0),
                    ('order_2', 'customer_2', 'delivered', 200.0, 200.0, 1, 0, 0, 1.0, 200.0)
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
            conn.execute(
                """
                INSERT INTO marts.fact_order_items VALUES
                    ('order_1', 1, 'product_1', 100.0),
                    ('order_2', 1, 'product_2', 200.0)
                """
            )
            conn.execute("CREATE TABLE marts.dim_customers (customer_id VARCHAR)")
            conn.execute("INSERT INTO marts.dim_customers VALUES ('customer_1'), ('customer_2')")
            conn.execute("CREATE TABLE marts.dim_products (product_id VARCHAR)")
            conn.execute("INSERT INTO marts.dim_products VALUES ('product_1'), ('product_2')")
            conn.close()

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

            run_data_contract_tests.main(repo_root)

            summary = pd.read_csv(processed_dir / "data_contract_test_summary.csv")
            self.assertEqual(int(summary.loc[0, "critical_failed"]), 0)


if __name__ == "__main__":
    unittest.main()
