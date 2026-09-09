"""Generate payments and payment status history consistently with orders.

Business rules:
- Exactly one payment record per order.
- Payment amount equals orders.total_amount.
- Payment method failure_rate_baseline controls initial payment failure.
- Successful payments finish at Captured.
- Refunded orders finish at Refunded after Captured.
- Pending orders remain Initiated or end in Failed.
- Payment status history records the complete lifecycle.
- This generator refuses to append to an existing payment domain.
"""

import random
import sys
from datetime import timedelta
from pathlib import Path

DATA_GENERATOR_DIR = Path(__file__).resolve().parents[1]
GENERATORS_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(DATA_GENERATOR_DIR))
sys.path.insert(0, str(GENERATORS_DIR))

from config import SEED
from db import get_connection


PAYMENT_SEED = SEED + 7

SUCCESS_ORDER_STATUSES = {
    "Paid",
    "Fulfilled",
    "Shipped",
    "Delivered",
}

REFUNDED_ORDER_STATUS = "Refunded"
PENDING_ORDER_STATUS = "Pending"
CANCELLED_ORDER_STATUS = "Cancelled"


def add_minutes(timestamp, rng, minimum=1, maximum=10):
    """Return a timestamp after a realistic short processing interval."""
    return timestamp + timedelta(
        minutes=rng.randint(minimum, maximum)
    )


def add_refund_delay(timestamp, rng):
    """Refund occurs after the original capture, not immediately."""
    return timestamp + timedelta(
        hours=rng.randint(6, 72),
        minutes=rng.randint(0, 59),
    )


def failure_probability_value(failure_rate_baseline):
    """Normalize the database baseline into a probability."""
    probability = float(failure_rate_baseline)

    if probability < 0:
        return 0.0

    if probability > 1:
        return 1.0

    return probability


def build_success_history(order_timestamp, failure_rate_baseline, rng):
    """Build a successful payment lifecycle.

    A payment may have one failed initial attempt before succeeding.
    """

    history = []

    initiated_timestamp = add_minutes(
        order_timestamp,
        rng,
        minimum=1,
        maximum=10,
    )

    history.append(
        {
            "status": "Initiated",
            "timestamp": initiated_timestamp,
            "failure_code": None,
        }
    )

    failure_probability = failure_probability_value(
        failure_rate_baseline
    )

    if rng.random() < failure_probability:
        failed_timestamp = add_minutes(
            initiated_timestamp,
            rng,
            minimum=1,
            maximum=5,
        )

        history.append(
            {
                "status": "Failed",
                "timestamp": failed_timestamp,
                "failure_code": rng.choice(
                    [
                        "PAYMENT_DECLINED",
                        "PROVIDER_TIMEOUT",
                        "INSUFFICIENT_FUNDS",
                        "PROCESSING_ERROR",
                    ]
                ),
            }
        )

        retry_timestamp = add_minutes(
            failed_timestamp,
            rng,
            minimum=2,
            maximum=15,
        )

        history.append(
            {
                "status": "Initiated",
                "timestamp": retry_timestamp,
                "failure_code": None,
            }
        )

        initiated_timestamp = retry_timestamp

    authorized_timestamp = add_minutes(
        initiated_timestamp,
        rng,
        minimum=1,
        maximum=5,
    )

    history.append(
        {
            "status": "Authorized",
            "timestamp": authorized_timestamp,
            "failure_code": None,
        }
    )

    captured_timestamp = add_minutes(
        authorized_timestamp,
        rng,
        minimum=1,
        maximum=5,
    )

    history.append(
        {
            "status": "Captured",
            "timestamp": captured_timestamp,
            "failure_code": None,
        }
    )

    return history



def build_pending_history(order_timestamp, failure_rate_baseline, rng):
    """Pending order: payment is either still initiated or failed."""
    initiated_timestamp = add_minutes(
        order_timestamp,
        rng,
        minimum=1,
        maximum=10,
    )

    if rng.random() < failure_probability_value(
        failure_rate_baseline
    ):
        failed_timestamp = add_minutes(
            initiated_timestamp,
            rng,
            minimum=1,
            maximum=5,
        )

        return [
            {
                "status": "Initiated",
                "timestamp": initiated_timestamp,
                "failure_code": None,
            },
            {
                "status": "Failed",
                "timestamp": failed_timestamp,
                "failure_code": rng.choice(
                    [
                        "PAYMENT_DECLINED",
                        "PROVIDER_TIMEOUT",
                        "INSUFFICIENT_FUNDS",
                        "PROCESSING_ERROR",
                    ]
                ),
            },
        ]

    return [
        {
            "status": "Initiated",
            "timestamp": initiated_timestamp,
            "failure_code": None,
        }
    ]


def build_cancelled_history(order_timestamp, failure_rate_baseline, rng):
    """Cancelled order.

    Cancelled orders are cancelled before payment completes or fail during payment.
    Orders that were captured and refunded have order_status == 'Refunded'.
    """

    initiated_timestamp = add_minutes(
        order_timestamp,
        rng,
        minimum=1,
        maximum=10,
    )

    history = [
        {
            "status": "Initiated",
            "timestamp": initiated_timestamp,
            "failure_code": None,
        }
    ]

    failed_timestamp = add_minutes(
        initiated_timestamp,
        rng,
        minimum=1,
        maximum=5,
    )

    baseline = failure_probability_value(
        failure_rate_baseline
    )

    if rng.random() < baseline:
        failure_code = "PAYMENT_METHOD_FAILURE"
    else:
        failure_code = rng.choice(
            [
                "ORDER_CANCELLED_BEFORE_PAYMENT",
                "CUSTOMER_CANCELLED",
                "PAYMENT_NOT_COMPLETED",
            ]
        )

    history.append(
        {
            "status": "Failed",
            "timestamp": failed_timestamp,
            "failure_code": failure_code,
        }
    )

    return history


def load_reference_data(cur):
    """Load orders and active payment methods."""
    cur.execute(
        """
        SELECT
            order_id,
            order_timestamp,
            total_amount,
            currency_code,
            order_status
        FROM orders
        ORDER BY order_timestamp, order_id
        """
    )

    orders = cur.fetchall()

    cur.execute(
        """
        SELECT
            payment_method_id,
            method_name,
            failure_rate_baseline
        FROM payment_methods
        WHERE status = 'Active'
        ORDER BY payment_method_id
        """
    )

    payment_methods = cur.fetchall()

    if not orders:
        raise RuntimeError(
            "No orders found. Generate the Order domain first."
        )

    if not payment_methods:
        raise RuntimeError(
            "No active payment methods found."
        )

    return orders, payment_methods


def assert_payment_domain_empty(cur):
    """Refuse to append to an existing payment domain."""
    cur.execute(
        "SELECT COUNT(*) AS row_count FROM payments"
    )
    payment_count = cur.fetchone()["row_count"]

    cur.execute(
        """
        SELECT COUNT(*) AS row_count
        FROM payment_status_history
        """
    )
    history_count = cur.fetchone()["row_count"]

    if payment_count or history_count:
        raise RuntimeError(
            f"Payment domain is not empty "
            f"({payment_count} payments, "
            f"{history_count} history rows). "
            "Do not append or patch it. "
            "Reset the derived Payment domain first."
        )


def validate_generated_payments(cur, expected_orders):
    """Validate core payment invariants before commit."""

    cur.execute(
        """
        SELECT COUNT(*) AS row_count
        FROM payments
        """
    )
    payment_count = cur.fetchone()["row_count"]

    if payment_count != expected_orders:
        raise RuntimeError(
            f"Payment count mismatch: "
            f"expected {expected_orders}, got {payment_count}."
        )

    cur.execute(
        """
        SELECT COUNT(*) AS mismatch_count
        FROM payments p
        JOIN orders o
          ON o.order_id = p.order_id
        WHERE ABS(p.amount - o.total_amount) > 0.01
           OR p.currency_code <> o.currency_code
        """
    )
    amount_currency_mismatches = cur.fetchone()["mismatch_count"]

    cur.execute(
        """
        SELECT COUNT(*) AS duplicate_order_payments
        FROM (
            SELECT order_id
            FROM payments
            GROUP BY order_id
            HAVING COUNT(*) <> 1
        ) x
        """
    )
    duplicate_order_payments = cur.fetchone()["duplicate_order_payments"]

    cur.execute(
        """
        SELECT COUNT(*) AS orphan_payments
        FROM payments p
        LEFT JOIN orders o
          ON o.order_id = p.order_id
        WHERE o.order_id IS NULL
        """
    )
    orphan_payments = cur.fetchone()["orphan_payments"]

    cur.execute(
        """
        SELECT COUNT(*) AS invalid_statuses
        FROM payments
        WHERE payment_status NOT IN (
            'Initiated',
            'Authorized',
            'Captured',
            'Failed',
            'Refunded'
        )
        """
    )
    invalid_statuses = cur.fetchone()["invalid_statuses"]

    cur.execute(
        """
        SELECT COUNT(*) AS history_mismatches
        FROM payments p
        LEFT JOIN LATERAL (
            SELECT status
            FROM payment_status_history h
            WHERE h.payment_id = p.payment_id
            ORDER BY h.status_timestamp DESC
            LIMIT 1
        ) h ON TRUE
        WHERE h.status IS NULL
           OR h.status <> p.payment_status
        """
    )
    history_mismatches = cur.fetchone()["history_mismatches"]

    cur.execute(
        """
        SELECT COUNT(*) AS invalid_refunds
        FROM payments p
        JOIN orders o
          ON o.order_id = p.order_id
        WHERE p.payment_status = 'Refunded'
          AND o.order_status <> 'Refunded'
        """
    )
    invalid_refunds = cur.fetchone()["invalid_refunds"]

    cur.execute(
        """
        SELECT COUNT(*) AS invalid_failed_final
        FROM payments p
        JOIN orders o
          ON o.order_id = p.order_id
        WHERE o.order_status IN (
            'Paid',
            'Fulfilled',
            'Shipped',
            'Delivered'
        )
        AND p.payment_status <> 'Captured'
        """
    )
    invalid_success_statuses = cur.fetchone()["invalid_failed_final"]

    failures = (
        amount_currency_mismatches
        + duplicate_order_payments
        + orphan_payments
        + invalid_statuses
        + history_mismatches
        + invalid_refunds
        + invalid_success_statuses
    )

    if failures:
        raise RuntimeError(
            "Payment validation failed: "
            f"amount_currency={amount_currency_mismatches}, "
            f"duplicate_orders={duplicate_order_payments}, "
            f"orphans={orphan_payments}, "
            f"invalid_status={invalid_statuses}, "
            f"history={history_mismatches}, "
            f"refunds={invalid_refunds}, "
            f"success_status={invalid_success_statuses}."
        )

    return {
        "payments": payment_count,
        "amount_currency_mismatches": 0,
        "duplicate_order_payments": 0,
        "orphan_payments": 0,
        "invalid_statuses": 0,
        "history_mismatches": 0,
        "invalid_refunds": 0,
        "invalid_success_statuses": 0,
    }


def main():
    rng = random.Random(PAYMENT_SEED)

    with get_connection() as conn:
        with conn.cursor() as cur:
            assert_payment_domain_empty(cur)

            orders, payment_methods = load_reference_data(cur)

            payment_rows = []
            history_rows = []

            for order in orders:
                order_id = order["order_id"]
                order_timestamp = order["order_timestamp"]
                total_amount = order["total_amount"]
                currency_code = order["currency_code"]
                order_status = order["order_status"]

                payment_method = rng.choice(payment_methods)

                payment_method_id = payment_method["payment_method_id"]
                failure_rate_baseline = (
                    payment_method["failure_rate_baseline"]
                )

                if order_status in SUCCESS_ORDER_STATUSES:
                    history = build_success_history(
                        order_timestamp,
                        failure_rate_baseline,
                        rng,
                    )

                elif order_status == PENDING_ORDER_STATUS:
                    history = build_pending_history(
                        order_timestamp,
                        failure_rate_baseline,
                        rng,
                    )

                elif order_status == CANCELLED_ORDER_STATUS:
                    history = build_cancelled_history(
                        order_timestamp,
                        failure_rate_baseline,
                        rng,
                    )

                elif order_status == REFUNDED_ORDER_STATUS:
                    history = build_success_history(
                        order_timestamp,
                        failure_rate_baseline,
                        rng,
                    )

                    captured_timestamp = history[-1]["timestamp"]

                    refunded_timestamp = add_refund_delay(
                        captured_timestamp,
                        rng,
                    )

                    history.append(
                        {
                            "status": "Refunded",
                            "timestamp": refunded_timestamp,
                            "failure_code": None,
                        }
                    )

                else:
                    raise RuntimeError(
                        f"Unsupported order status: {order_status}"
                    )

                final_status = history[-1]["status"]

                payment_timestamp = history[-1]["timestamp"]

                provider_reference = (
                    f"TXN-{PAYMENT_SEED}-{len(payment_rows) + 1:06d}"
                )

                payment_rows.append(
                    (
                        order_id,
                        payment_method_id,
                        payment_timestamp,
                        total_amount,
                        currency_code,
                        final_status,
                        provider_reference,
                    )
                )

                # Payment ID is generated by PostgreSQL, so insert payments
                # first and then create history using RETURNING.
                cur.execute(
                    """
                    INSERT INTO payments (
                        order_id,
                        payment_method_id,
                        payment_timestamp,
                        amount,
                        currency_code,
                        payment_status,
                        provider_transaction_ref
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING payment_id
                    """,
                    payment_rows[-1],
                )

                payment_id = cur.fetchone()["payment_id"]

                for event in history:
                    history_rows.append(
                        (
                            payment_id,
                            event["status"],
                            event["timestamp"],
                            event["failure_code"],
                        )
                    )

                    cur.execute(
                        """
                        INSERT INTO payment_status_history (
                            payment_id,
                            status,
                            status_timestamp,
                            failure_code
                        )
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            payment_id,
                            event["status"],
                            event["timestamp"],
                            event["failure_code"],
                        ),
                    )

            validation = validate_generated_payments(
                cur,
                expected_orders=len(orders),
            )

        conn.commit()

    print(
        f"Inserted payments: {len(payment_rows)}"
    )

    print(
        f"Inserted payment history rows: "
        f"{len(history_rows)}"
    )

    print(
        f"Payment validation passed: {validation}"
    )


if __name__ == "__main__":
    main()