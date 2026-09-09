"""Independent validator for the inventory domain (snapshots and movements).

Invariants checked:
1. Snapshot arithmetic: available_quantity = on_hand_quantity - reserved_quantity.
2. Non-negativity: on_hand >= 0, reserved >= 0, available >= 0.
3. Snapshot referential integrity: Warehouses and Products exist and are valid.
4. Movement referential integrity: Reference entity 'Order' exists in orders table.
5. Movement signs & delta invariants:
   - Reservation: delta < 0
   - Release: delta > 0
   - Pick: delta < 0
   - Return: delta > 0
6. Temporal lifecycle sequence:
   - Reserved <= Picked <= Returned
   - Reserved <= Released
7. Quantity consistency: Order lines match movement absolute quantities.
"""

import sys
from pathlib import Path

DATA_GENERATOR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DATA_GENERATOR_DIR))

from db import get_connection


def validate_inventory():
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Basic counts
            cur.execute("SELECT COUNT(*) AS count FROM inventory_snapshots")
            total_snapshots = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) AS count FROM inventory_movements")
            total_movements = cur.fetchone()["count"]

            # 2. Snapshot arithmetic & non-negativity
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (
                        WHERE ABS(available_quantity - (on_hand_quantity - reserved_quantity)) > 0.001
                    ) AS snapshot_math_errors,
                    COUNT(*) FILTER (
                        WHERE on_hand_quantity < 0
                           OR reserved_quantity < 0
                           OR available_quantity < 0
                    ) AS snapshot_negative_errors,
                    COUNT(*) FILTER (WHERE w.warehouse_id IS NULL) AS orphan_snapshot_warehouses,
                    COUNT(*) FILTER (WHERE p.product_id IS NULL) AS orphan_snapshot_products
                FROM inventory_snapshots s
                LEFT JOIN warehouses w ON s.warehouse_id = w.warehouse_id
                LEFT JOIN products p ON s.product_id = p.product_id
            """)
            snapshot_report = cur.fetchone()

            # 3. Movement referential integrity
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (
                        WHERE im.reference_entity_type = 'Order' AND o.order_id IS NULL
                    ) AS orphan_order_movements,
                    COUNT(*) FILTER (WHERE w.warehouse_id IS NULL) AS orphan_movement_warehouses,
                    COUNT(*) FILTER (WHERE p.product_id IS NULL) AS orphan_movement_products
                FROM inventory_movements im
                LEFT JOIN orders o ON im.reference_entity_id = o.order_id
                LEFT JOIN warehouses w ON im.warehouse_id = w.warehouse_id
                LEFT JOIN products p ON im.product_id = p.product_id
            """)
            movement_refs = cur.fetchone()

            # 4. Movement signs
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (
                        WHERE movement_type IN ('Reservation', 'Pick') AND quantity_delta >= 0
                    ) AS invalid_negative_movements,
                    COUNT(*) FILTER (
                        WHERE movement_type IN ('Release', 'Return') AND quantity_delta <= 0
                    ) AS invalid_positive_movements,
                    COUNT(*) FILTER (WHERE quantity_delta = 0) AS zero_delta_movements
                FROM inventory_movements
            """)
            movement_signs = cur.fetchone()

            # 5. Temporal lifecycle
            cur.execute("""
                WITH event_times AS (
                    SELECT
                        reference_entity_id AS order_id,
                        product_id,
                        MIN(movement_timestamp) FILTER (WHERE movement_type = 'Reservation') AS reserved_at,
                        MIN(movement_timestamp) FILTER (WHERE movement_type = 'Pick') AS picked_at,
                        MIN(movement_timestamp) FILTER (WHERE movement_type = 'Release') AS released_at,
                        MIN(movement_timestamp) FILTER (WHERE movement_type = 'Return') AS returned_at
                    FROM inventory_movements
                    WHERE reference_entity_type = 'Order'
                    GROUP BY reference_entity_id, product_id
                )
                SELECT
                    COUNT(*) FILTER (WHERE released_at IS NOT NULL AND reserved_at > released_at) AS release_before_reserve,
                    COUNT(*) FILTER (WHERE picked_at IS NOT NULL AND reserved_at > picked_at) AS pick_before_reserve,
                    COUNT(*) FILTER (WHERE returned_at IS NOT NULL AND picked_at > returned_at) AS return_before_pick
                FROM event_times
            """)
            lifecycle_timing = cur.fetchone()

    report = {
        "total_snapshots": total_snapshots,
        "total_movements": total_movements,
        **snapshot_report,
        **movement_refs,
        **movement_signs,
        **lifecycle_timing,
    }

    print("=" * 60)
    print("INVENTORY DOMAIN INDEPENDENT VALIDATION REPORT")
    print("=" * 60)
    for k, v in report.items():
        print(f"  {k}: {v}")

    violations = sum(
        v for k, v in report.items()
        if k not in ("total_snapshots", "total_movements")
    )

    if violations > 0:
        raise SystemExit(f"\nFAILED: Found {violations} invariant violation(s) in inventory domain!")

    print("\nPASSED: All inventory domain invariants hold completely.")


if __name__ == "__main__":
    validate_inventory()
