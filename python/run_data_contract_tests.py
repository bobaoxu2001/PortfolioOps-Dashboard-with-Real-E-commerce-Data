"""Run data contract checks against the reporting layer."""

from __future__ import annotations

import pathlib

import duckdb
import pandas as pd


def _fetch_scalar(conn: duckdb.DuckDBPyConnection, query: str) -> float:
    return conn.execute(query).fetchone()[0]


def main() -> None:
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    processed_dir = repo_root / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    db_path = processed_dir / "olist_reporting.duckdb"
    conn = duckdb.connect(str(db_path))

    tests = []

    def add_test(name: str, severity: str, value: float, passed: bool, threshold: str, rationale: str) -> None:
        tests.append(
            {
                "test_name": name,
                "severity": severity,
                "observed_value": value,
                "threshold": threshold,
                "passed": int(bool(passed)),
                "rationale": rationale,
            }
        )

    order_pk_violations = _fetch_scalar(
        conn,
        "SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM marts.fact_orders",
    )
    add_test(
        "fact_orders_order_id_unique",
        "critical",
        order_pk_violations,
        order_pk_violations == 0,
        "must equal 0",
        "Order grain must be one row per order_id.",
    )

    item_pk_violations = _fetch_scalar(
        conn,
        "SELECT COUNT(*) - COUNT(DISTINCT CONCAT(order_id, '|', CAST(order_item_id AS VARCHAR))) FROM marts.fact_order_items",
    )
    add_test(
        "fact_order_items_key_unique",
        "critical",
        item_pk_violations,
        item_pk_violations == 0,
        "must equal 0",
        "Item grain must be one row per (order_id, order_item_id).",
    )

    missing_customers = _fetch_scalar(
        conn,
        """
        SELECT COUNT(*)
        FROM marts.fact_orders o
        LEFT JOIN marts.dim_customers c ON o.customer_id = c.customer_id
        WHERE c.customer_id IS NULL
        """,
    )
    add_test(
        "fact_orders_customer_fk_integrity",
        "critical",
        missing_customers,
        missing_customers == 0,
        "must equal 0",
        "Orders should always map to a customer dimension row.",
    )

    missing_products = _fetch_scalar(
        conn,
        """
        SELECT COUNT(*)
        FROM marts.fact_order_items i
        LEFT JOIN marts.dim_products p ON i.product_id = p.product_id
        WHERE p.product_id IS NULL
        """,
    )
    add_test(
        "fact_order_items_product_fk_integrity",
        "critical",
        missing_products,
        missing_products == 0,
        "must equal 0",
        "Order items should always map to a product dimension row.",
    )

    gmv_diff = _fetch_scalar(
        conn,
        """
        WITH item_level AS (
            SELECT SUM(gmv) AS total_gmv
            FROM marts.fact_order_items
        ),
        order_level AS (
            SELECT SUM(item_gmv) AS total_gmv
            FROM marts.fact_orders
        )
        SELECT item_level.total_gmv - order_level.total_gmv
        FROM item_level
        CROSS JOIN order_level
        """,
    )
    add_test(
        "gmv_reconciliation_item_vs_order",
        "critical",
        gmv_diff,
        abs(gmv_diff) < 0.01,
        "absolute difference < 0.01",
        "Order-level GMV must reconcile to item-level GMV.",
    )

    cancellation_rate = _fetch_scalar(
        conn,
        "SELECT AVG(CASE WHEN is_canceled_or_unavailable = 1 THEN 1.0 ELSE 0.0 END) FROM marts.fact_orders",
    )
    add_test(
        "cancellation_rate_reasonable_band",
        "warning",
        cancellation_rate,
        0.0 <= cancellation_rate <= 0.2,
        "between 0 and 0.20",
        "A broad sanity check to catch severe status-mapping regressions.",
    )

    on_time_coverage = _fetch_scalar(
        conn,
        "SELECT AVG(CASE WHEN is_on_time_delivery IS NULL THEN 0.0 ELSE 1.0 END) FROM marts.fact_orders",
    )
    add_test(
        "on_time_metric_population_coverage",
        "warning",
        on_time_coverage,
        on_time_coverage >= 0.90,
        ">= 0.90",
        "Most orders should be evaluable for on-time delivery after model logic.",
    )

    late_vs_ontime_gap = _fetch_scalar(
        conn,
        """
        SELECT
            AVG(CASE WHEN is_on_time_delivery = 1 THEN avg_review_score END) -
            AVG(CASE WHEN is_on_time_delivery = 0 THEN avg_review_score END) AS review_gap
        FROM marts.fact_orders
        """,
    )
    add_test(
        "service_quality_signal_direction",
        "info",
        late_vs_ontime_gap,
        late_vs_ontime_gap > 0,
        "> 0",
        "On-time deliveries should show higher review scores than late deliveries.",
    )

    payment_gmv_ratio = _fetch_scalar(
        conn,
        """
        WITH payments AS (
            SELECT SUM(payment_value_total) AS pay_total
            FROM marts.fact_orders
        ),
        gmv AS (
            SELECT SUM(item_gmv) AS gmv_total
            FROM marts.fact_orders
        )
        SELECT pay_total / NULLIF(gmv_total, 0)
        FROM payments
        CROSS JOIN gmv
        """,
    )
    add_test(
        "payment_to_gmv_ratio_sanity",
        "warning",
        payment_gmv_ratio,
        0.90 <= payment_gmv_ratio <= 1.15,
        "between 0.90 and 1.15",
        "Detects major revenue/payment mismatches after transformations.",
    )

    results_df = pd.DataFrame(tests)
    results_df["status"] = results_df["passed"].map({1: "PASS", 0: "FAIL"})
    results_df = results_df[
        ["test_name", "severity", "status", "observed_value", "threshold", "rationale"]
    ]
    results_df.to_csv(processed_dir / "data_contract_test_results.csv", index=False)

    summary = {
        "total_tests": len(results_df),
        "failed_tests": int((results_df["status"] == "FAIL").sum()),
        "critical_failed": int(
            ((results_df["status"] == "FAIL") & (results_df["severity"] == "critical")).sum()
        ),
    }
    summary_df = pd.DataFrame([summary])
    summary_df.to_csv(processed_dir / "data_contract_test_summary.csv", index=False)

    report_lines = [
        "# Data Contract Test Report",
        "",
        f"- Total tests: **{summary['total_tests']}**",
        f"- Failed tests: **{summary['failed_tests']}**",
        f"- Critical failed tests: **{summary['critical_failed']}**",
        "",
        "## Detailed Results",
        "",
    ]
    header = "| test_name | severity | status | observed_value | threshold | rationale |"
    divider = "|---|---|---|---:|---|---|"
    report_lines.extend([header, divider])
    for _, row in results_df.iterrows():
        report_lines.append(
            "| "
            + " | ".join(
                [
                    str(row["test_name"]),
                    str(row["severity"]),
                    str(row["status"]),
                    f"{float(row['observed_value']):.6f}",
                    str(row["threshold"]),
                    str(row["rationale"]),
                ]
            )
            + " |"
        )
    report_lines.append("")
    report_lines.append(
        "Interpretation: critical failures block KPI publication; warning/info failures require analyst review."
    )

    report_path = repo_root / "docs" / "data_contract_test_report.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    conn.close()
    print(f"Wrote: {processed_dir / 'data_contract_test_results.csv'}")
    print(f"Wrote: {processed_dir / 'data_contract_test_summary.csv'}")
    print(f"Wrote: {report_path}")

    if summary["critical_failed"] > 0:
        raise SystemExit("Critical data contract tests failed.")


if __name__ == "__main__":
    main()
