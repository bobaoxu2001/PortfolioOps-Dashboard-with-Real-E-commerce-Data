"""Generate portfolio dashboard screenshots and PDF from processed KPI files."""

from __future__ import annotations

import pathlib

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages


def format_millions(value: float) -> str:
    return f"R${value / 1_000_000:.2f}M"


def format_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def add_kpi_card(ax, title: str, value: str, subtitle: str = "") -> None:
    ax.axis("off")
    ax.set_facecolor("#F7F8FA")
    ax.text(0.03, 0.75, title, fontsize=10, color="#3B3E45", fontweight="bold", transform=ax.transAxes)
    ax.text(0.03, 0.35, value, fontsize=16, color="#0B1F44", fontweight="bold", transform=ax.transAxes)
    if subtitle:
        ax.text(0.03, 0.1, subtitle, fontsize=9, color="#6C7280", transform=ax.transAxes)


def save_page(fig: plt.Figure, path: pathlib.Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")


def build_architecture_diagram(output_path: pathlib.Path) -> None:
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.axis("off")

    boxes = [
        (0.03, 0.55, 0.2, 0.3, "#E8F1FD", "Raw Sources\n(9 Olist CSV tables)"),
        (0.28, 0.55, 0.2, 0.3, "#EAF8EF", "Staging Layer\nType casting + dedupe + key fixes"),
        (0.53, 0.55, 0.2, 0.3, "#FFF3DF", "Reporting Marts\nfact_orders / fact_order_items\n+ dimensions"),
        (0.78, 0.55, 0.19, 0.3, "#F5EBFF", "BI & Executive Outputs\nDashboard + memo + KPI docs"),
    ]

    for x, y, w, h, color, label in boxes:
        rect = plt.Rectangle((x, y), w, h, color=color, ec="#3B3E45", lw=1.2, transform=ax.transAxes)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=11, fontweight="bold", transform=ax.transAxes)

    arrows = [
        (0.23, 0.7, 0.05, 0.0),
        (0.48, 0.7, 0.05, 0.0),
        (0.73, 0.7, 0.05, 0.0),
    ]
    for x, y, dx, dy in arrows:
        ax.arrow(x, y, dx, dy, head_width=0.03, head_length=0.015, fc="#3B3E45", ec="#3B3E45", length_includes_head=True, transform=ax.transAxes)

    ax.text(
        0.03,
        0.2,
        "Governance controls: duplicate key checks, null checks, invalid timestamp checks,\n"
        "and join-risk guardrails (order grain vs item grain) before KPI publication.",
        fontsize=11,
        color="#3B3E45",
        transform=ax.transAxes,
    )
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    processed_dir = repo_root / "data" / "processed"
    screenshot_dir = repo_root / "dashboard" / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    monthly = pd.read_csv(processed_dir / "kpi_monthly.csv", parse_dates=["month_start"])
    headline = pd.read_csv(processed_dir / "kpi_headline.csv").iloc[0]
    delay = pd.read_csv(processed_dir / "kpi_delay_vs_reviews.csv")
    category = pd.read_csv(processed_dir / "kpi_category_performance.csv")
    seller = pd.read_csv(processed_dir / "kpi_seller_performance.csv")
    state = pd.read_csv(processed_dir / "kpi_state_performance.csv")
    payment = pd.read_csv(processed_dir / "kpi_payment_mix.csv")
    dq = pd.read_csv(processed_dir / "data_quality_summary.csv")
    join_risk = pd.read_csv(processed_dir / "kpi_join_risk_demo.csv").iloc[0]

    sns.set_theme(style="whitegrid")

    trend = monthly[monthly["total_orders"] > 100].copy()

    # Page 1 - Executive Overview
    fig1 = plt.figure(figsize=(16, 9))
    gs1 = fig1.add_gridspec(3, 4, height_ratios=[1, 2.3, 2.3])
    card_axes = [fig1.add_subplot(gs1[0, i]) for i in range(4)]
    add_kpi_card(card_axes[0], "GMV", format_millions(headline["total_gmv"]), "Reporting layer total")
    add_kpi_card(card_axes[1], "Orders", f"{int(headline['total_orders']):,}", "All order statuses")
    add_kpi_card(card_axes[2], "AOV", f"R${headline['aov']:.2f}", "GMV / orders")
    add_kpi_card(card_axes[3], "Cancellation Rate", format_pct(headline["cancellation_rate"]), "Canceled + unavailable")

    ax11 = fig1.add_subplot(gs1[1, :2])
    ax12 = fig1.add_subplot(gs1[1, 2:])
    ax13 = fig1.add_subplot(gs1[2, :2])
    ax14 = fig1.add_subplot(gs1[2, 2:])

    ax11.plot(trend["month_start"], trend["total_gmv"], color="#1B5E9A", linewidth=2.2)
    ax11.set_title("Monthly GMV Trend")
    ax11.set_ylabel("GMV (R$)")

    ax12.plot(trend["month_start"], trend["total_orders"], color="#2E7D32", linewidth=2.2)
    ax12.set_title("Monthly Order Volume")
    ax12.set_ylabel("Orders")

    ax13.plot(trend["month_start"], trend["on_time_delivery_rate"], color="#6A1B9A", linewidth=2.2, label="On-time rate")
    ax13.plot(trend["month_start"], trend["cancellation_rate"], color="#D84315", linewidth=2.2, label="Cancellation rate")
    ax13.legend(loc="best")
    ax13.set_title("Service Reliability Trends")
    ax13.set_ylabel("Rate")

    ax14.plot(trend["month_start"], trend["avg_review_score"], color="#00838F", linewidth=2.2, label="Review score")
    ax14_t = ax14.twinx()
    ax14_t.plot(trend["month_start"], trend["avg_delivery_days"], color="#F9A825", linewidth=2.2, label="Delivery days")
    ax14.set_title("Customer Experience Trends")
    ax14.set_ylabel("Avg review")
    ax14_t.set_ylabel("Avg days")

    fig1.suptitle("Page 1 - Executive Overview", fontsize=16, fontweight="bold")
    save_page(fig1, screenshot_dir / "page_1_executive_overview.png")

    # Page 2 - Customer Experience & Fulfillment
    fig2 = plt.figure(figsize=(16, 9))
    gs2 = fig2.add_gridspec(2, 2)
    ax21 = fig2.add_subplot(gs2[0, 0])
    ax22 = fig2.add_subplot(gs2[0, 1])
    ax23 = fig2.add_subplot(gs2[1, 0])
    ax24 = fig2.add_subplot(gs2[1, 1])

    delay_sorted = delay.set_index("delay_bucket").reindex(
        ["On time or early", "1-3 days late", "4-7 days late", "8+ days late", "Not Delivered"]
    ).reset_index()
    sns.barplot(data=delay_sorted, x="delay_bucket", y="orders", ax=ax21, color="#1B5E9A")
    ax21.tick_params(axis="x", rotation=20)
    ax21.set_title("Order Count by Delay Bucket")
    ax21.set_xlabel("")

    sns.barplot(data=delay_sorted, x="delay_bucket", y="avg_review_score", ax=ax22, color="#6A1B9A")
    ax22.tick_params(axis="x", rotation=20)
    ax22.set_ylim(0, 5)
    ax22.set_title("Average Review Score by Delay Bucket")
    ax22.set_xlabel("")

    state_top = state.nlargest(10, "orders")
    sns.barplot(data=state_top, y="customer_state", x="avg_delivery_days", ax=ax23, color="#F9A825")
    ax23.set_title("Avg Delivery Days (Top 10 Order States)")
    ax23.set_xlabel("Days")
    ax23.set_ylabel("State")

    sns.barplot(data=state_top, y="customer_state", x="avg_review_score", ax=ax24, color="#00838F")
    ax24.set_xlim(0, 5)
    ax24.set_title("Avg Review Score (Top 10 Order States)")
    ax24.set_xlabel("Score")
    ax24.set_ylabel("State")

    fig2.suptitle("Page 2 - Customer Experience & Fulfillment", fontsize=16, fontweight="bold")
    save_page(fig2, screenshot_dir / "page_2_customer_fulfillment.png")

    # Page 3 - Commercial Performance
    fig3 = plt.figure(figsize=(16, 9))
    gs3 = fig3.add_gridspec(2, 2)
    ax31 = fig3.add_subplot(gs3[0, 0])
    ax32 = fig3.add_subplot(gs3[0, 1])
    ax33 = fig3.add_subplot(gs3[1, 0])
    ax34 = fig3.add_subplot(gs3[1, 1])

    category_top = category.nlargest(12, "gmv")
    sns.barplot(data=category_top, y="category", x="gmv", ax=ax31, color="#2E7D32")
    ax31.set_title("Top Categories by GMV")
    ax31.set_xlabel("GMV (R$)")
    ax31.set_ylabel("")

    seller_top = seller.nlargest(12, "gmv")
    sns.barplot(data=seller_top, y="seller_id", x="gmv", ax=ax32, color="#1B5E9A")
    ax32.set_title("Top Sellers by GMV")
    ax32.set_xlabel("GMV (R$)")
    ax32.set_ylabel("")

    state_gmv = state.nlargest(10, "gmv")
    sns.barplot(data=state_gmv, x="customer_state", y="gmv", ax=ax33, color="#6A1B9A")
    ax33.set_title("Top States by GMV")
    ax33.set_xlabel("State")
    ax33.set_ylabel("GMV (R$)")

    ax34.pie(payment["payment_value"], labels=payment["payment_type"], autopct="%1.1f%%", startangle=130)
    ax34.set_title("Payment Mix by Value")

    fig3.suptitle("Page 3 - Commercial Performance", fontsize=16, fontweight="bold")
    save_page(fig3, screenshot_dir / "page_3_commercial_performance.png")

    # Page 4 - Data Quality / KPI Reliability
    fig4 = plt.figure(figsize=(16, 9))
    gs4 = fig4.add_gridspec(2, 2)
    ax41 = fig4.add_subplot(gs4[:, 0])
    ax42 = fig4.add_subplot(gs4[0, 1])
    ax43 = fig4.add_subplot(gs4[1, 1])

    dq_plot = dq.sort_values("issue_rows", ascending=False)
    sns.barplot(data=dq_plot, y="check_name", x="issue_rows", ax=ax41, color="#D84315")
    ax41.set_title("Data Quality Findings (Raw and Staging)")
    ax41.set_xlabel("Issue Rows")
    ax41.set_ylabel("")

    ax42.axis("off")
    ax42.text(0, 0.9, "KPI Reliability Notes", fontsize=14, fontweight="bold")
    ax42.text(
        0,
        0.68,
        (
            f"Naive join GMV: R${join_risk['naive_gmv']:,.0f}\n"
            f"Trusted GMV: R${join_risk['trusted_gmv']:,.0f}\n"
            f"Overstatement risk: R${join_risk['gmv_overstatement']:,.0f}"
        ),
        fontsize=12,
    )
    ax42.text(
        0,
        0.25,
        "Root cause:\nJoining item-level rows directly to payment rows creates\n"
        "many-to-many duplication. Trusted model aggregates each\n"
        "source at order grain before combining.",
        fontsize=11,
    )

    ax43.axis("off")
    ax43.text(0, 0.85, "Governance Actions", fontsize=14, fontweight="bold")
    ax43.text(
        0,
        0.55,
        "1) Enforced unique keys in staging tables\n"
        "2) Consolidated geolocation to one row per zip prefix\n"
        "3) Flagged late/not-delivered orders separately\n"
        "4) Defined revenue eligibility logic by order status",
        fontsize=12,
    )

    fig4.suptitle("Page 4 - Data Quality / KPI Reliability", fontsize=16, fontweight="bold")
    save_page(fig4, screenshot_dir / "page_4_data_quality_reliability.png")

    pdf_path = repo_root / "dashboard" / "dashboard_export.pdf"
    with PdfPages(pdf_path) as pdf:
        for fig in [fig1, fig2, fig3, fig4]:
            pdf.savefig(fig, bbox_inches="tight")

    for fig in [fig1, fig2, fig3, fig4]:
        plt.close(fig)

    build_architecture_diagram(repo_root / "docs" / "architecture_diagram.png")
    print(f"Dashboard pages exported to: {pdf_path}")


if __name__ == "__main__":
    main()
