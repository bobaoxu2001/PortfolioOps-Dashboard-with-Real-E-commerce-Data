from __future__ import annotations

import csv
import pathlib
import tempfile
import unittest

import duckdb

import run_data_contract_tests


class RunDataContractTestsTest(unittest.TestCase):
    def test_no_canceled_orders_does_not_crash_cancellation_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = pathlib.Path(tmp_dir)
            processed_dir = repo_root / "data" / "processed"
            processed_dir.mkdir(parents=True)
            (repo_root / "docs").mkdir()

            conn = duckdb.connect(str(processed_dir / "olist_reporting.duckdb"))
            conn.execute("CREATE SCHEMA marts")
            conn.execute("CREATE TABLE marts.dim_customers (customer_id VARCHAR)")
            conn.execute("CREATE TABLE marts.dim_products (product_id VARCHAR)")
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
                CREATE TABLE marts.fact_order_items (
                    order_id VARCHAR,
                    order_item_id INTEGER,
                    product_id VARCHAR,
                    gmv DOUBLE
                )
                """
            )

            conn.execute("INSERT INTO marts.dim_customers VALUES ('c1'), ('c2')")
            conn.execute("INSERT INTO marts.dim_products VALUES ('p1'), ('p2')")
            conn.execute(
                """
                INSERT INTO marts.fact_orders VALUES
                    ('o1', 'c1', 'delivered', 100.0, 100.0, 1, 1, 0, 5.0, 100.0),
                    ('o2', 'c2', 'delivered', 50.0, 50.0, 1, 0, 0, 2.0, 50.0)
                """
            )
            conn.execute(
                """
                INSERT INTO marts.fact_order_items VALUES
                    ('o1', 1, 'p1', 100.0),
                    ('o2', 1, 'p2', 50.0)
                """
            )
            conn.close()

            self._write_csv(
                processed_dir / "kpi_headline.csv",
                ["gmv_revenue_eligible", "revenue_eligible_orders", "aov_revenue_eligible"],
                [["150.0", "2", "75.0"]],
            )
            self._write_csv(
                processed_dir / "kpi_monthly.csv",
                ["gmv_revenue_eligible", "revenue_eligible_orders"],
                [["150.0", "2"]],
            )

            run_data_contract_tests.main(repo_root)

            summary = self._read_single_row_csv(processed_dir / "data_contract_test_summary.csv")
            self.assertEqual(summary["critical_failed"], "0")

            results = self._read_rows_csv(processed_dir / "data_contract_test_results.csv")
            cancellation_test = next(
                row
                for row in results
                if row["test_name"] == "Primary revenue excludes canceled and unavailable orders"
            )
            self.assertEqual(cancellation_test["status"], "PASS")
            self.assertEqual(float(cancellation_test["observed_value"]), 0.0)

    def _write_csv(self, path: pathlib.Path, header: list[str], rows: list[list[str]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)

    def _read_single_row_csv(self, path: pathlib.Path) -> dict[str, str]:
        rows = self._read_rows_csv(path)
        self.assertEqual(len(rows), 1)
        return rows[0]

    def _read_rows_csv(self, path: pathlib.Path) -> list[dict[str, str]]:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))


if __name__ == "__main__":
    unittest.main()
