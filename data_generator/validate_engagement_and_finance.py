"""Independent validator for Customer Tickets, Reviews, and Financial Transactions."""

import sys
from pathlib import Path

DATA_GENERATOR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DATA_GENERATOR_DIR))

from db import get_connection


def validate_engagement_and_finance():
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Counts
            cur.execute("SELECT COUNT(*) AS count FROM financial_transactions")
            total_fin = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) AS count FROM customer_tickets")
            total_tickets = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) AS count FROM reviews")
            total_reviews = cur.fetchone()["count"]

            # 2. Financial transactions invariants
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE ft.amount = 0) AS zero_amount_transactions,
                    COUNT(*) FILTER (WHERE o.order_id IS NULL AND ft.order_id IS NOT NULL) AS orphan_fin_orders,
                    COUNT(*) FILTER (WHERE p.payment_id IS NULL AND ft.payment_id IS NOT NULL) AS orphan_fin_payments,
                    COUNT(*) FILTER (WHERE s.shipment_id IS NULL AND ft.shipment_id IS NOT NULL) AS orphan_fin_shipments,
                    COUNT(*) FILTER (
                        WHERE ft.transaction_type = 'Revenue' AND ft.amount <= 0
                    ) AS negative_revenue,
                    COUNT(*) FILTER (
                        WHERE ft.transaction_type IN ('Refund', 'ShippingCost', 'COGS') AND ft.amount >= 0
                    ) AS positive_costs
                FROM financial_transactions ft
                LEFT JOIN orders o ON ft.order_id = o.order_id
                LEFT JOIN payments p ON ft.payment_id = p.payment_id
                LEFT JOIN shipments s ON ft.shipment_id = s.shipment_id
            """)
            fin_checks = cur.fetchone()

            # 3. Customer Tickets invariants
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE c.customer_id IS NULL) AS orphan_ticket_customers,
                    COUNT(*) FILTER (WHERE o.order_id IS NULL AND t.order_id IS NOT NULL) AS orphan_ticket_orders,
                    COUNT(*) FILTER (WHERE t.resolved_at IS NOT NULL AND t.resolved_at < t.created_at) AS resolved_before_created,
                    COUNT(*) FILTER (WHERE t.satisfaction_score < 0 OR t.satisfaction_score > 5) AS invalid_satisfaction,
                    COUNT(*) FILTER (WHERE t.order_id IS NOT NULL AND t.created_at < o.order_timestamp) AS ticket_before_order
                FROM customer_tickets t
                LEFT JOIN customers c ON t.customer_id = c.customer_id
                LEFT JOIN orders o ON t.order_id = o.order_id
            """)
            ticket_checks = cur.fetchone()

            # 4. Reviews invariants
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE c.customer_id IS NULL) AS orphan_review_customers,
                    COUNT(*) FILTER (WHERE o.order_id IS NULL) AS orphan_review_orders,
                    COUNT(*) FILTER (WHERE p.product_id IS NULL) AS orphan_review_products,
                    COUNT(*) FILTER (WHERE r.rating < 1 OR r.rating > 5) AS invalid_ratings,
                    COUNT(*) FILTER (WHERE r.sentiment_score < -1 OR r.sentiment_score > 1) AS invalid_sentiment
                FROM reviews r
                LEFT JOIN customers c ON r.customer_id = c.customer_id
                LEFT JOIN orders o ON r.order_id = o.order_id
                LEFT JOIN products p ON r.product_id = p.product_id
            """)
            review_checks = cur.fetchone()

    report = {
        "total_financial_transactions": total_fin,
        "total_customer_tickets": total_tickets,
        "total_reviews": total_reviews,
        **fin_checks,
        **ticket_checks,
        **review_checks,
    }

    print("=" * 65)
    print("ENGAGEMENT & FINANCE INDEPENDENT VALIDATION REPORT")
    print("=" * 65)
    for k, v in report.items():
        print(f"  {k}: {v}")

    violations = sum(
        v for k, v in report.items()
        if k not in ("total_financial_transactions", "total_customer_tickets", "total_reviews")
    )

    if violations > 0:
        raise SystemExit(f"\nFAILED: Found {violations} invariant violation(s) in engagement/finance domain!")

    print("\nPASSED: All engagement and finance invariants hold completely.")


if __name__ == "__main__":
    validate_engagement_and_finance()
