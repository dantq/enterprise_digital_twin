"""Generate inventory movements from existing order-line business events.

This generator is intentionally source-driven: every order-related movement has
an ``Order`` reference and its quantity is copied from the corresponding
``order_items`` row.  It never invents receipts or adjustments because this
seed dataset does not yet contain purchase orders or inventory-count documents
to support those event types.
"""

import random
import sys
from datetime import timedelta
from pathlib import Path

DATA_GENERATOR_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATA_GENERATOR_DIR))

from config import SEED
from db import get_connection


RANDOM = random.Random(SEED + 12)


def load_order_lines(cur):
    """Return the existing, valid order lines in deterministic event order."""
    cur.execute(
        """
        SELECT
            o.order_id,
            o.warehouse_id,
            o.order_timestamp,
            o.order_status,
            oi.product_id,
            oi.quantity
        FROM orders AS o
        JOIN order_items AS oi ON oi.order_id = o.order_id
        ORDER BY o.order_timestamp, o.order_id, oi.product_id
        """
    )
    return cur.fetchall()


def event_time(order_timestamp, minimum_minutes, maximum_minutes):
    return order_timestamp + timedelta(
        minutes=RANDOM.randint(minimum_minutes, maximum_minutes)
    )


def add_reservation(rows, order_id, warehouse_id, product_id, quantity, timestamp):
    rows.append(
        (
            warehouse_id,
            product_id,
            event_time(timestamp, 1, 30),
            "Reservation",
            -quantity,
            "Order",
            order_id,
            "Order allocation",
        )
    )


def movements_for_order_line(order_line):
    """Build a complete, status-appropriate event sequence for one line."""
    if isinstance(order_line, dict):
        order_id = order_line["order_id"]
        warehouse_id = order_line["warehouse_id"]
        order_timestamp = order_line["order_timestamp"]
        order_status = order_line["order_status"]
        product_id = order_line["product_id"]
        quantity = order_line["quantity"]
    else:
        order_id, warehouse_id, order_timestamp, order_status, product_id, quantity = order_line
    rows = []

    if order_status in {"Pending", "Paid"}:
        add_reservation(
            rows, order_id, warehouse_id, product_id, quantity, order_timestamp
        )

    elif order_status == "Cancelled":
        add_reservation(
            rows, order_id, warehouse_id, product_id, quantity, order_timestamp
        )
        rows.append(
            (
                warehouse_id,
                product_id,
                event_time(order_timestamp, 31, 180),
                "Release",
                quantity,
                "Order",
                order_id,
                "Order cancellation",
            )
        )

    elif order_status in {"Fulfilled", "Shipped", "Delivered"}:
        add_reservation(
            rows, order_id, warehouse_id, product_id, quantity, order_timestamp
        )
        rows.append(
            (
                warehouse_id,
                product_id,
                event_time(order_timestamp, 31, 180),
                "Pick",
                -quantity,
                "Order",
                order_id,
                "Order fulfilment",
            )
        )

    elif order_status == "Refunded":
        add_reservation(
            rows, order_id, warehouse_id, product_id, quantity, order_timestamp
        )
        rows.append(
            (
                warehouse_id,
                product_id,
                event_time(order_timestamp, 31, 180),
                "Pick",
                -quantity,
                "Order",
                order_id,
                "Order fulfilment before refund",
            )
        )
        rows.append(
            (
                warehouse_id,
                product_id,
                event_time(order_timestamp, 24 * 60, 14 * 24 * 60),
                "Return",
                quantity,
                "Order",
                order_id,
                "Customer return after refund",
            )
        )

    else:
        raise ValueError(f"Unsupported order status: {order_status}")

    return rows


def build_rows(order_lines):
    rows = []
    for order_line in order_lines:
        rows.extend(movements_for_order_line(order_line))
    return rows


def validate_source_data(cur):
    cur.execute("SELECT COUNT(*) AS count FROM inventory_movements")
    res = cur.fetchone()
    existing_movements = res["count"] if isinstance(res, dict) else res[0]
    if existing_movements:
        raise RuntimeError(
            "inventory_movements already contains data; refusing to duplicate "
            "the source-derived event ledger."
        )

    cur.execute(
        """
        SELECT COUNT(*) AS count
        FROM order_items AS oi
        LEFT JOIN orders AS o ON o.order_id = oi.order_id
        WHERE o.order_id IS NULL
           OR oi.quantity <= 0
           OR o.warehouse_id IS NULL
        """
    )
    res = cur.fetchone()
    invalid_lines = res["count"] if isinstance(res, dict) else res[0]
    if invalid_lines:
        raise RuntimeError(f"Found {invalid_lines} invalid order-item source rows.")

    cur.execute(
        """
        SELECT
            COUNT(*) AS snapshot_count,
            MIN(snapshot_timestamp) AS first_snapshot,
            MAX(snapshot_timestamp) AS last_snapshot
        FROM inventory_snapshots
        """
    )
    snap_res = cur.fetchone()
    if isinstance(snap_res, dict):
        snapshot_count = snap_res["snapshot_count"]
        first_snapshot = snap_res["first_snapshot"]
        last_snapshot = snap_res["last_snapshot"]
    else:
        snapshot_count, first_snapshot, last_snapshot = snap_res

    if not snapshot_count:
        raise RuntimeError(
            "No inventory snapshots found. Generate and validate snapshots first."
        )

    print(
        "Snapshot coverage: "
        f"{snapshot_count} rows from {first_snapshot} to {last_snapshot}."
    )


def validate_inserted_movements(cur):
    """Fail the transaction unless references, signs, and lifecycles are sound."""
    checks = {
        "invalid references": """
            SELECT COUNT(*)
            FROM inventory_movements AS im
            LEFT JOIN orders AS o ON o.order_id = im.reference_entity_id
            WHERE im.reference_entity_type <> 'Order'
               OR im.reference_entity_id IS NULL
               OR o.order_id IS NULL
        """,
        "invalid movement signs": """
            SELECT COUNT(*)
            FROM inventory_movements
            WHERE (movement_type IN ('Reservation', 'Pick') AND quantity_delta >= 0)
               OR (movement_type IN ('Release', 'Return') AND quantity_delta <= 0)
               OR quantity_delta = 0
        """,
        "unexpected or missing order-line events": """
            WITH expected AS (
                SELECT o.order_id, o.warehouse_id, oi.product_id,
                       v.movement_type, v.quantity_delta
                FROM orders AS o
                JOIN order_items AS oi ON oi.order_id = o.order_id
                CROSS JOIN LATERAL (
                    VALUES
                        ('Reservation'::varchar, -oi.quantity),
                        ('Release'::varchar,
                            CASE WHEN o.order_status = 'Cancelled' THEN oi.quantity END),
                        ('Pick'::varchar,
                            CASE WHEN o.order_status IN ('Fulfilled', 'Shipped', 'Delivered', 'Refunded')
                                 THEN -oi.quantity END),
                        ('Return'::varchar,
                            CASE WHEN o.order_status = 'Refunded' THEN oi.quantity END)
                ) AS v(movement_type, quantity_delta)
                WHERE v.quantity_delta IS NOT NULL
            ),
            expected_events AS (
                SELECT order_id, warehouse_id, product_id, movement_type,
                       SUM(quantity_delta) AS quantity_delta
                FROM expected
                GROUP BY order_id, warehouse_id, product_id, movement_type
            ),
            actual_events AS (
                SELECT reference_entity_id AS order_id, warehouse_id, product_id,
                       movement_type, SUM(quantity_delta) AS quantity_delta
                FROM inventory_movements
                GROUP BY reference_entity_id, warehouse_id, product_id, movement_type
            )
            SELECT COUNT(*)
            FROM expected_events AS e
            FULL OUTER JOIN actual_events AS a
              ON a.order_id = e.order_id
             AND a.warehouse_id = e.warehouse_id
             AND a.product_id = e.product_id
             AND a.movement_type = e.movement_type
            WHERE e.order_id IS NULL
               OR a.order_id IS NULL
               OR e.quantity_delta <> a.quantity_delta
        """,
        "invalid lifecycle order": """
            WITH event_times AS (
                SELECT reference_entity_id AS order_id, product_id,
                       MIN(movement_timestamp) FILTER (WHERE movement_type = 'Reservation') AS reserved_at,
                       MIN(movement_timestamp) FILTER (WHERE movement_type = 'Pick') AS picked_at,
                       MIN(movement_timestamp) FILTER (WHERE movement_type = 'Release') AS released_at,
                       MIN(movement_timestamp) FILTER (WHERE movement_type = 'Return') AS returned_at
                FROM inventory_movements
                GROUP BY reference_entity_id, product_id
            )
            SELECT COUNT(*)
            FROM event_times
            WHERE (released_at IS NOT NULL AND reserved_at > released_at)
               OR (picked_at IS NOT NULL AND reserved_at > picked_at)
               OR (returned_at IS NOT NULL AND picked_at > returned_at)
        """,
    }

    for name, query in checks.items():
        cur.execute(query)
        res = cur.fetchone()
        failures = list(res.values())[0] if isinstance(res, dict) else res[0]
        if failures:
            raise RuntimeError(f"Validation failed: {failures} {name}.")


def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            validate_source_data(cur)
            order_lines = load_order_lines(cur)
            if not order_lines:
                raise RuntimeError("No order_items found. Generate order items first.")

            source_orders = {
                (row["order_id"] if isinstance(row, dict) else row[0])
                for row in order_lines
            }
            first_order_time = (
                order_lines[0]["order_timestamp"]
                if isinstance(order_lines[0], dict)
                else order_lines[0][2]
            )
            last_order_time = (
                order_lines[-1]["order_timestamp"]
                if isinstance(order_lines[-1], dict)
                else order_lines[-1][2]
            )
            print(
                "Order source: "
                f"{len(source_orders)} orders and {len(order_lines)} order lines "
                f"from {first_order_time} to {last_order_time}."
            )

            rows = build_rows(order_lines)
            cur.executemany(
                """
                INSERT INTO inventory_movements (
                    warehouse_id,
                    product_id,
                    movement_timestamp,
                    movement_type,
                    quantity_delta,
                    reference_entity_type,
                    reference_entity_id,
                    reason_code
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                rows,
            )
            validate_inserted_movements(cur)

        conn.commit()

    print(
        f"Inserted inventory movements: {len(rows)} "
        f"from {len(order_lines)} order lines."
    )


if __name__ == "__main__":
    main()
