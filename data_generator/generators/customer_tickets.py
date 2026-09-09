"""Generate customer tickets aligned with orders, shipments, and customer experience.

Categories: 'Delivery', 'Payment', 'ProductQuality', 'Refund', 'Order', 'Other'.
Priorities: 'Low', 'Medium', 'High', 'Critical'.
Statuses: 'Open', 'InProgress', 'Resolved', 'Closed'.
"""

import sys
import random
from datetime import datetime, time, timezone, timedelta
from pathlib import Path

DATA_GENERATOR_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATA_GENERATOR_DIR))

from db import get_connection
from config import SEED

RANDOM_SEED = SEED + 16
random.seed(RANDOM_SEED)


def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS count FROM customer_tickets")
            if cur.fetchone()["count"] > 0:
                print("customer_tickets already populated. Skipping.")
                return

            rows = []

            # 1. Tickets for Refunded orders (Customer requesting refund / complaints)
            cur.execute("""
                SELECT o.order_id, o.customer_id, o.order_timestamp
                FROM orders o
                WHERE o.order_status = 'Refunded'
            """)
            refunded_orders = cur.fetchall()

            for o in refunded_orders:
                created_at = o["order_timestamp"] + timedelta(hours=random.randint(12, 72))
                res_hours = round(random.uniform(4.0, 48.0), 2)
                resolved_at = created_at + timedelta(hours=res_hours)
                rows.append((
                    o["customer_id"],
                    o["order_id"],
                    created_at,
                    resolved_at,
                    random.choice(["Refund", "ProductQuality"]),
                    "High",
                    "Resolved",
                    res_hours,
                    round(random.uniform(3.5, 4.8), 2),
                ))

            # 2. Tickets for shipments with long delays or Returned status
            cur.execute("""
                SELECT s.order_id, o.customer_id, s.shipment_timestamp, s.shipment_status
                FROM shipments s
                JOIN orders o ON s.order_id = o.order_id
                WHERE s.shipment_status IN ('Returned', 'Delivered')
            """)
            shipment_orders = cur.fetchall()

            for s in shipment_orders:
                # 15% rate of delivery inquiry
                if random.random() < 0.15:
                    created_at = s["shipment_timestamp"] + timedelta(hours=random.randint(24, 96))
                    res_hours = round(random.uniform(6.0, 72.0), 2)
                    status = random.choice(["Resolved", "Closed"])
                    resolved_at = created_at + timedelta(hours=res_hours)
                    rows.append((
                        s["customer_id"],
                        s["order_id"],
                        created_at,
                        resolved_at,
                        "Delivery",
                        random.choice(["Medium", "High"]),
                        status,
                        res_hours,
                        round(random.uniform(2.5, 4.5), 2),
                    ))

            # 3. Tickets for Cancelled orders
            cur.execute("""
                SELECT o.order_id, o.customer_id, o.order_timestamp
                FROM orders o
                WHERE o.order_status = 'Cancelled'
            """)
            cancelled_orders = cur.fetchall()

            for o in cancelled_orders:
                if random.random() < 0.40:
                    created_at = o["order_timestamp"] + timedelta(minutes=random.randint(10, 180))
                    res_hours = round(random.uniform(1.0, 12.0), 2)
                    rows.append((
                        o["customer_id"],
                        o["order_id"],
                        created_at,
                        created_at + timedelta(hours=res_hours),
                        "Order",
                        "Medium",
                        "Closed",
                        res_hours,
                        round(random.uniform(3.0, 4.2), 2),
                    ))

            # 4. General customer inquiries (without specific order or open status)
            cur.execute("SELECT customer_id, registration_date FROM customers")
            customers = cur.fetchall()

            for c in customers:
                if random.random() < 0.20:
                    reg_date = c["registration_date"]
                    created_at = datetime.combine(reg_date, time(10, 0), tzinfo=timezone.utc)
                    # Some tickets still InProgress or Open
                    is_open = random.random() < 0.10
                    if is_open:
                        rows.append((
                            c["customer_id"],
                            None,
                            created_at,
                            None,
                            "Other",
                            "Low",
                            "Open",
                            None,
                            None,
                        ))
                    else:
                        res_hours = round(random.uniform(2.0, 24.0), 2)
                        rows.append((
                            c["customer_id"],
                            None,
                            created_at,
                            created_at + timedelta(hours=res_hours),
                            "Other",
                            "Low",
                            "Resolved",
                            res_hours,
                            round(random.uniform(4.0, 5.0), 2),
                        ))

            cur.executemany("""
                INSERT INTO customer_tickets (
                    customer_id,
                    order_id,
                    created_at,
                    resolved_at,
                    category,
                    priority,
                    status,
                    resolution_time_hours,
                    satisfaction_score
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, rows)

            conn.commit()
            print(f"Inserted customer_tickets: {len(rows)}")


if __name__ == "__main__":
    main()
