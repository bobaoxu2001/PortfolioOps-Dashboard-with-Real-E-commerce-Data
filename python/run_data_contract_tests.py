"""Run data contract checks against the reporting layer."""

from __future__ import annotations

import pathlib

import duckdb
import pandas as pd


def _fetch_scalar(conn: duckdb.DuckDBPyConnection, query: str) -> float:
    return conn.execute(query).fetchone()[0]


def _load_single_row_csv(path: pathlib.Path) -> pd.Series:
    df = pd.read_csv(path)
    if len(df) != 1:
        raise ValueError(f"Expected exactly 1 row in {path}, found {len(df)}")
    return df.iloc[0]


def main() -> None:
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    processed_dir = repo_root / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    db_path = processed_dir / "olist_reporting.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute("PRAGMA threads = 1")

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

    order_pk_violations = _fetch_scalar(conn, "SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM marts.fact_orders")
    add_test(
        "Fact Orders has one row per order",
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
        "Fact Order Items has unique item keys",
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
        "Fact Orders customer foreign key integrity",
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
        "Fact Order Items product foreign key integrity",
        "critical",
        missing_products,
        missing_products == 0,
        "must equal 0",
        "Order items should always map to a product dimension row.",
    )

    gmv_diff_all_orders = _fetch_scalar(
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
        "All-orders GMV reconciles between item and order facts",
        "critical",
        gmv_diff_all_orders,
        abs(gmv_diff_all_orders) < 0.01,
        "absolute difference < 0.01",
        "Order-level GMV must reconcile to item-level GMV.",
    )

    gmv_diff_revenue_eligible = _fetch_scalar(
        conn,
        """
        WITH item_level AS (
            SELECT SUM(i.gmv) AS total_gmv
            FROM marts.fact_order_items i
            INNER JOIN marts.fact_orders o
                ON i.order_id = o.order_id
            WHERE o.is_revenue_eligible_order = 1
        ),
        order_level AS (
            SELECT SUM(revenue_eligible_gmv) AS total_gmv
            FROM marts.fact_orders
        )
        SELECT item_level.total_gmv - order_level.total_gmv
        FROM item_level
        CROSS JOIN order_level
        """,
    )
    add_test(
        "Revenue-eligible GMV reconciles across grains",
        "critical",
        gmv_diff_revenue_eligible,
        abs(gmv_diff_revenue_eligible) < 0.01,
        "absolute difference < 0.01",
        "Primary revenue KPI must match whether computed from items or orders.",
    )

    revenue_eligible_order_count = _fetch_scalar(
        conn,
        "SELECT COUNT(*) FROM marts.fact_orders WHERE is_revenue_eligible_order = 1",
    )
    add_test(
        "Revenue-eligible order count is non-zero",
        "critical",
        revenue_eligible_order_count,
        revenue_eligible_order_count > 0,
        "> 0",
        "Primary revenue KPIs cannot be published with zero qualifying orders.",
    )

    cancellation_exclusion_leakage = _fetch_scalar(
        conn,
        """
        SELECT SUM(COALESCE(revenue_eligible_gmv, 0))
        FROM marts.fact_orders
        WHERE order_status IN ('canceled', 'unavailable')
        """,
    )
    add_test(
        "Primary revenue excludes canceled and unavailable orders",
        "critical",
        cancellation_exclusion_leakage,
        abs(cancellation_exclusion_leakage) < 0.01,
        "absolute value < 0.01",
        "Canceled/unavailable orders are operational outcomes and should not inflate commercial KPIs.",
    )

    delivered_logic_coverage = _fetch_scalar(
        conn,
        """
        SELECT
            AVG(CASE WHEN is_on_time_delivery IS NULL THEN 0.0 ELSE 1.0 END)
        FROM marts.fact_orders
        WHERE order_status = 'delivered'
        """,
    )
    add_test(
        "Delivered orders have expected on-time logic coverage",
        "warning",
        delivered_logic_coverage,
        delivered_logic_coverage >= 0.995,
        ">= 0.995",
        "Delivered orders should almost always have enough timestamp data for on-time classification.",
    )

    headline_row = _load_single_row_csv(processed_dir / "kpi_headline.csv")
    headline_aov_expected = (
        float(headline_row["gmv_revenue_eligible"]) / float(headline_row["revenue_eligible_orders"])
        if float(headline_row["revenue_eligible_orders"]) != 0
        else 0.0
    )
    headline_aov_diff = float(headline_row["aov_revenue_eligible"]) - headline_aov_expected
    add_test(
        "Headline AOV matches defined formula",
        "critical",
        headline_aov_diff,
        abs(headline_aov_diff) < 1e-6,
        "absolute difference < 0.000001",
        "AOV must equal revenue-eligible GMV divided by revenue-eligible order count.",
    )

    monthly_df = pd.read_csv(processed_dir / "kpi_monthly.csv")
    monthly_gmv_diff = float(monthly_df["gmv_revenue_eligible"].sum() - float(headline_row["gmv_revenue_eligible"]))
    add_test(
        "Monthly primary GMV reconciles to headline primary GMV",
        "critical",
        monthly_gmv_diff,
        abs(monthly_gmv_diff) < 0.01,
        "absolute difference < 0.01",
        "Roll-up checks prevent hidden leakage between monthly reporting and headline KPIs.",
    )

    monthly_order_diff = float(monthly_df["revenue_eligible_orders"].sum() - float(headline_row["revenue_eligible_orders"]))
    add_test(
        "Monthly revenue-eligible order count reconciles to headline",
        "critical",
        monthly_order_diff,
        abs(monthly_order_diff) < 0.01,
        "absolute difference < 0.01",
        "Primary order volume denominator should align across all executive summary layers.",
    )

    monthly_aov_weighted = (
        float(monthly_df["gmv_revenue_eligible"].sum()) / float(monthly_df["revenue_eligible_orders"].sum())
        if float(monthly_df["revenue_eligible_orders"].sum()) != 0
        else 0.0
    )
    monthly_vs_headline_aov_diff = float(headline_row["aov_revenue_eligible"]) - monthly_aov_weighted
    add_test(
        "Monthly and headline AOV align under weighted definition",
        "warning",
        monthly_vs_headline_aov_diff,
        abs(monthly_vs_headline_aov_diff) < 1e-6,
        "absolute difference < 0.000001",
        "Prevents averaging bias from unweighted monthly AOV rollups.",
    )

    cancellation_rate = _fetch_scalar(
        conn,
        "SELECT AVG(CASE WHEN is_canceled_or_unavailable = 1 THEN 1.0 ELSE 0.0 END) FROM marts.fact_orders",
    )
    add_test(
        "Cancellation rate remains in expected operating band",
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
        "On-time KPI coverage remains healthy",
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
        "Late deliveries depress review score (directional test)",
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
        "Payment value to GMV ratio remains plausible",
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
