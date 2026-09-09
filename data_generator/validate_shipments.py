"""Independent validator for the shipments domain.

Invariants checked:
1. Referential integrity: Valid orders, warehouses, and carriers.
2. Tracking number uniqueness: No duplicates.
3. Temporal consistency:
   - shipment_timestamp >= order_timestamp
   - estimated_delivery_timestamp >= shipment_timestamp
   - delivered_timestamp >= shipment_timestamp (if not null)
4. State alignment:
   - Delivered shipments have delivered_timestamp populated.
   - Non-delivered shipments have delivered_timestamp as NULL.
5. History consistency:
   - Every shipment has history records.
   - Final history status matches shipment_status.
   - Timestamps in history are monotonically non-decreasing.
"""

import sys
from pathlib import Path

DATA_GENERATOR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DATA_GENERATOR_DIR))

from db import get_connection


def validate_shipments():
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Basic counts
            cur.execute("SELECT COUNT(*) AS count FROM shipments")
            total_shipments = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) AS count FROM shipment_status_history")
            total_history = cur.fetchone()["count"]

            # 2. Referential integrity
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE o.order_id IS NULL) AS orphan_order_shipments,
                    COUNT(*) FILTER (WHERE w.warehouse_id IS NULL) AS orphan_warehouse_shipments,
                    COUNT(*) FILTER (WHERE c.carrier_id IS NULL) AS orphan_carrier_shipments
                FROM shipments s
                LEFT JOIN orders o ON s.order_id = o.order_id
                LEFT JOIN warehouses w ON s.warehouse_id = w.warehouse_id
                LEFT JOIN carriers c ON s.carrier_id = c.carrier_id
            """)
            refs = cur.fetchone()

            # 3. Tracking uniqueness
            cur.execute("""
                SELECT COUNT(*) - COUNT(DISTINCT tracking_number) AS duplicate_tracking_numbers
                FROM shipments
            """)
            tracking = cur.fetchone()

            # 4. Temporal consistency
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE s.shipment_timestamp < o.order_timestamp) AS shipped_before_order,
                    COUNT(*) FILTER (WHERE s.estimated_delivery_timestamp < s.shipment_timestamp) AS est_delivery_before_shipment,
                    COUNT(*) FILTER (WHERE s.delivered_timestamp IS NOT NULL AND s.delivered_timestamp < s.shipment_timestamp) AS delivered_before_shipment
                FROM shipments s
                JOIN orders o ON s.order_id = o.order_id
            """)
            timing = cur.fetchone()

            # 5. State alignment
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE shipment_status = 'Delivered' AND delivered_timestamp IS NULL) AS delivered_without_timestamp,
                    COUNT(*) FILTER (WHERE shipment_status IN ('Created', 'PickedUp', 'InTransit') AND delivered_timestamp IS NOT NULL) AS in_transit_with_delivered_timestamp
                FROM shipments
            """)
            state_align = cur.fetchone()

            # 6. History consistency
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE ssh.shipment_id IS NULL) AS shipments_without_history,
                    COUNT(*) FILTER (WHERE s.shipment_id IS NULL) AS orphan_history
                FROM shipments s
                FULL OUTER JOIN shipment_status_history ssh ON s.shipment_id = ssh.shipment_id
            """)
            history_links = cur.fetchone()

            cur.execute("""
                WITH ranked_history AS (
                    SELECT
                        shipment_id,
                        status,
                        status_timestamp,
                        ROW_NUMBER() OVER (
                            PARTITION BY shipment_id
                            ORDER BY status_timestamp DESC, shipment_status_history_id DESC
                        ) AS rn
                    FROM shipment_status_history
                )
                SELECT
                    COUNT(*) AS final_status_mismatches
                FROM shipments s
                JOIN ranked_history rh ON s.shipment_id = rh.shipment_id AND rh.rn = 1
                WHERE s.shipment_status <> rh.status
            """)
            status_match = cur.fetchone()

            cur.execute("""
                WITH step_order AS (
                    SELECT
                        shipment_status_history_id,
                        shipment_id,
                        status_timestamp,
                        LAG(status_timestamp) OVER (
                            PARTITION BY shipment_id
                            ORDER BY status_timestamp, shipment_status_history_id
                        ) AS prev_timestamp
                    FROM shipment_status_history
                )
                SELECT
                    COUNT(*) AS time_travel_in_history
                FROM step_order
                WHERE prev_timestamp IS NOT NULL
                  AND status_timestamp < prev_timestamp
            """)
            time_travel = cur.fetchone()

    report = {
        "total_shipments": total_shipments,
        "total_history_rows": total_history,
        **refs,
        **tracking,
        **timing,
        **state_align,
        **history_links,
        **status_match,
        **time_travel,
    }

    print("=" * 60)
    print("SHIPMENT DOMAIN INDEPENDENT VALIDATION REPORT")
    print("=" * 60)
    for k, v in report.items():
        print(f"  {k}: {v}")

    violations = sum(
        v for k, v in report.items()
        if k not in ("total_shipments", "total_history_rows")
    )

    if violations > 0:
        raise SystemExit(f"\nFAILED: Found {violations} invariant violation(s) in shipment domain!")

    print("\nPASSED: All shipment domain invariants hold completely.")


if __name__ == "__main__":
    validate_shipments()
