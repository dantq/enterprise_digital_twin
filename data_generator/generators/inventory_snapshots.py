import random
from datetime import datetime, timedelta, timezone

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from db import get_connection
from config import SEED

random.seed(SEED + 11)


def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT warehouse_id
                FROM warehouses
                WHERE status = 'Active'
                ORDER BY warehouse_id
            """)
            warehouses = [row["warehouse_id"] for row in cur.fetchall()]

            cur.execute("""
                SELECT product_id
                FROM products
                WHERE status = 'Active'
                ORDER BY product_id
            """)
            products = [row["product_id"] for row in cur.fetchall()]

            print(
                f"Found {len(warehouses)} active warehouses "
                f"and {len(products)} active products."
            )

            if not warehouses:
                raise RuntimeError("No active warehouses found.")

            if not products:
                raise RuntimeError("No active products found.")

            rows = []

            # 7 daily snapshots per warehouse-product pair.
            # This gives the Digital Twin temporal inventory history.
            end_date = datetime(2026, 8, 28, tzinfo=timezone.utc)
            start_date = end_date - timedelta(days=6)

            for warehouse_id in warehouses:
                for product_id in products:
                    # Product-specific baseline inventory.
                    on_hand = random.randint(20, 500)

                    reorder_point = random.randint(
                        max(5, int(on_hand * 0.15)),
                        max(10, int(on_hand * 0.40)),
                    )

                    for day_offset in range(7):
                        snapshot_time = start_date + timedelta(days=day_offset)

                        # Simulate normal daily inventory fluctuation.
                        if day_offset > 0:
                            movement = random.randint(-35, 35)
                            on_hand = max(0, on_hand + movement)

                        reserved = random.randint(
                            0,
                            int(on_hand * random.uniform(0.05, 0.30))
                        ) if on_hand > 0 else 0

                        available = on_hand - reserved

                        rows.append((
                            warehouse_id,
                            product_id,
                            snapshot_time,
                            on_hand,
                            reserved,
                            available,
                            reorder_point,
                        ))

            cur.executemany(
                """
                INSERT INTO inventory_snapshots (
                    warehouse_id,
                    product_id,
                    snapshot_timestamp,
                    on_hand_quantity,
                    reserved_quantity,
                    available_quantity,
                    reorder_point
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (warehouse_id, product_id, snapshot_timestamp)
                DO NOTHING
                """,
                rows,
            )

        conn.commit()

    print(f"Inserted inventory_snapshots: {len(rows)}")


if __name__ == "__main__":
    main()
