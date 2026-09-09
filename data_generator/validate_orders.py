"""Validate the order financial invariants without changing any data."""

from db import get_connection


def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                WITH item_totals AS (
                    SELECT order_id, SUM(item_total) AS subtotal_from_items
                    FROM order_items
                    GROUP BY order_id
                )
                SELECT
                    COUNT(*) AS total_orders,
                    COUNT(*) FILTER (
                        WHERE ABS(o.subtotal - COALESCE(i.subtotal_from_items, 0)) > 0.01
                    ) AS subtotal_mismatches,
                    COUNT(*) FILTER (
                        WHERE ABS(o.total_amount - (o.subtotal - o.discount_amount + o.shipping_fee)) > 0.01
                    ) AS total_mismatches,
                    COUNT(*) FILTER (WHERE i.order_id IS NULL) AS orders_without_items
                FROM orders AS o
                LEFT JOIN item_totals AS i ON i.order_id = o.order_id
            """)
            order_result = cur.fetchone()

            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE o.order_id IS NULL) AS orphan_order_items,
                    COUNT(*) FILTER (
                        WHERE oi.item_total <> ROUND(oi.quantity * oi.unit_price - oi.discount_amount, 2)
                    ) AS item_total_mismatches
                FROM order_items AS oi
                LEFT JOIN orders AS o ON o.order_id = oi.order_id
            """)
            item_result = cur.fetchone()

            cur.execute("""
                WITH ranked_history AS (
                    SELECT
                        order_id,
                        status,
                        status_timestamp,
                        ROW_NUMBER() OVER (
                            PARTITION BY order_id
                            ORDER BY status_timestamp DESC, order_status_history_id DESC
                        ) AS rn
                    FROM order_status_history
                ),
                history_coverage AS (
                    SELECT
                        COUNT(DISTINCT o.order_id) FILTER (WHERE rh.order_id IS NULL) AS orders_without_history
                    FROM orders o
                    LEFT JOIN ranked_history rh ON o.order_id = rh.order_id AND rh.rn = 1
                ),
                status_matches AS (
                    SELECT
                        COUNT(*) AS order_final_status_mismatches
                    FROM orders o
                    JOIN ranked_history rh ON o.order_id = rh.order_id AND rh.rn = 1
                    WHERE o.order_status <> rh.status
                ),
                timeline_checks AS (
                    SELECT
                        COUNT(*) AS order_history_time_travel
                    FROM (
                        SELECT
                            order_id,
                            status_timestamp,
                            LAG(status_timestamp) OVER (
                                PARTITION BY order_id
                                ORDER BY status_timestamp
                            ) AS prev_timestamp
                        FROM order_status_history
                    ) sub
                    WHERE prev_timestamp IS NOT NULL AND status_timestamp < prev_timestamp
                )
                SELECT * FROM history_coverage, status_matches, timeline_checks
            """)
            history_result = cur.fetchone()

    results = {**order_result, **item_result, **history_result}
    print("Order financial and lifecycle validation:")
    for name, value in results.items():
        print(f"  {name}: {value}")

    failures = sum(value for name, value in results.items() if name != "total_orders")
    if failures:
        raise SystemExit(f"FAILED: {failures} invariant violation(s).")
    print("PASSED: all order financial and lifecycle invariants hold.")


if __name__ == "__main__":
    main()
