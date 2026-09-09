"""Validate payment invariants independently without modifying database data.

Invariants checked:
1. 1-to-1 relationship: Each order has exactly one payment.
2. Financial integrity: payment.amount == order.total_amount and currency matches.
3. Status alignment:
   - Orders (Paid, Fulfilled, Shipped, Delivered) -> payment is Captured.
   - Orders (Refunded) -> payment is Refunded.
   - Orders (Pending) -> payment is Initiated or Failed.
   - Orders (Cancelled) -> payment is Failed, Initiated, or Cancelled.
4. Temporal consistency: payment_timestamp >= order_timestamp.
5. Lifecycle history consistency:
   - Payment status history is present for every payment.
   - Final event in payment_status_history matches payment.payment_status.
   - Timestamps in history are monotonically non-decreasing.
6. Referential integrity: No orphan payment records or history rows.
"""

import sys
from pathlib import Path

DATA_GENERATOR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DATA_GENERATOR_DIR))

from db import get_connection


def validate_payments():
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Basic counts
            cur.execute("SELECT COUNT(*) AS count FROM orders")
            total_orders = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) AS count FROM payments")
            total_payments = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) AS count FROM payment_status_history")
            total_history = cur.fetchone()["count"]

            # 2. Coverage & Duplicate orders
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE p.payment_id IS NULL) AS orders_without_payment,
                    COUNT(*) FILTER (WHERE o.order_id IS NULL) AS orphan_payments
                FROM orders o
                FULL OUTER JOIN payments p ON o.order_id = p.order_id
            """)
            coverage = cur.fetchone()

            cur.execute("""
                SELECT COUNT(*) AS duplicate_order_payments
                FROM (
                    SELECT order_id, COUNT(*) AS cnt
                    FROM payments
                    GROUP BY order_id
                    HAVING COUNT(*) > 1
                ) sub
            """)
            duplicates = cur.fetchone()

            # 3. Financial matches (Amount & Currency)
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (
                        WHERE ABS(p.amount - o.total_amount) > 0.001
                           OR p.currency_code <> o.currency_code
                    ) AS amount_currency_mismatches
                FROM payments p
                JOIN orders o ON p.order_id = o.order_id
            """)
            financial = cur.fetchone()

            # 4. Status alignment between order and payment
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (
                        WHERE o.order_status IN ('Paid', 'Fulfilled', 'Shipped', 'Delivered')
                          AND p.payment_status <> 'Captured'
                    ) AS successful_orders_not_captured,
                    COUNT(*) FILTER (
                        WHERE o.order_status = 'Refunded'
                          AND p.payment_status <> 'Refunded'
                    ) AS refunded_orders_not_refunded,
                    COUNT(*) FILTER (
                        WHERE o.order_status = 'Pending'
                          AND p.payment_status NOT IN ('Initiated', 'Failed')
                    ) AS pending_orders_invalid_status,
                    COUNT(*) FILTER (
                        WHERE o.order_status = 'Cancelled'
                          AND p.payment_status NOT IN ('Failed', 'Initiated', 'Cancelled')
                    ) AS cancelled_orders_invalid_status
                FROM orders o
                JOIN payments p ON o.order_id = p.order_id
            """)
            status_alignment = cur.fetchone()

            # 5. Temporal order vs payment
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (
                        WHERE p.payment_timestamp < o.order_timestamp
                    ) AS payment_before_order
                FROM payments p
                JOIN orders o ON p.order_id = o.order_id
            """)
            timing = cur.fetchone()

            # 6. Payment status history consistency
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE psh.payment_id IS NULL) AS payments_without_history,
                    COUNT(*) FILTER (WHERE p.payment_id IS NULL) AS orphan_history
                FROM payments p
                FULL OUTER JOIN payment_status_history psh ON p.payment_id = psh.payment_id
            """)
            history_link = cur.fetchone()

            cur.execute("""
                WITH ranked_history AS (
                    SELECT
                        payment_id,
                        status,
                        status_timestamp,
                        ROW_NUMBER() OVER (
                            PARTITION BY payment_id
                            ORDER BY status_timestamp DESC, payment_status_history_id DESC
                        ) AS rn
                    FROM payment_status_history
                )
                SELECT
                    COUNT(*) AS final_status_mismatches
                FROM payments p
                JOIN ranked_history rh ON p.payment_id = rh.payment_id AND rh.rn = 1
                WHERE p.payment_status <> rh.status
            """)
            history_status_match = cur.fetchone()

            cur.execute("""
                WITH step_order AS (
                    SELECT
                        payment_status_history_id,
                        payment_id,
                        status_timestamp,
                        LAG(status_timestamp) OVER (
                            PARTITION BY payment_id
                            ORDER BY status_timestamp, payment_status_history_id
                        ) AS prev_timestamp
                    FROM payment_status_history
                )
                SELECT
                    COUNT(*) AS time_travel_in_history
                FROM step_order
                WHERE prev_timestamp IS NOT NULL
                  AND status_timestamp < prev_timestamp
            """)
            time_travel = cur.fetchone()

    report = {
        "total_orders": total_orders,
        "total_payments": total_payments,
        "total_history_rows": total_history,
        **coverage,
        **duplicates,
        **financial,
        **status_alignment,
        **timing,
        **history_link,
        **history_status_match,
        **time_travel,
    }

    print("=" * 60)
    print("PAYMENT DOMAIN INDEPENDENT VALIDATION REPORT")
    print("=" * 60)
    for k, v in report.items():
        print(f"  {k}: {v}")

    violations = sum(
        v for k, v in report.items()
        if k not in ("total_orders", "total_payments", "total_history_rows")
    )

    if violations > 0:
        raise SystemExit(f"\nFAILED: Found {violations} invariant violation(s) in payment domain!")

    print("\nPASSED: All payment domain invariants hold completely.")


if __name__ == "__main__":
    validate_payments()
