"""Generate order status history consistently with orders, payments, and shipments.

Status transition sequence:
- Pending: Order placed
- Paid: Payment captured
- Fulfilled: Warehouse packed and allocated
- Shipped: Handed over to carrier
- Delivered: Successfully delivered to customer
- Cancelled: Cancelled before fulfillment
- Refunded: Returned and refunded post-delivery or post-payment

Invariants enforced:
- First status is always 'Pending' at order_timestamp.
- Final status matches orders.order_status.
- Timestamps are strictly ascending (Pending < Paid < Fulfilled < Shipped < Delivered/Refunded).
- Unique constraint: UNIQUE (order_id, status_timestamp).
"""

import sys
import random
from datetime import timedelta
from pathlib import Path

DATA_GENERATOR_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATA_GENERATOR_DIR))

from db import get_connection
from config import SEED

RANDOM_SEED = SEED + 18
random.seed(RANDOM_SEED)


def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Check if order_status_history already has data
            cur.execute("SELECT COUNT(*) AS count FROM order_status_history")
            if cur.fetchone()["count"] > 0:
                print("order_status_history already populated. Skipping.")
                return

            # Fetch orders along with payment and shipment details
            cur.execute("""
                SELECT
                    o.order_id,
                    o.order_timestamp,
                    o.order_status,
                    p.payment_status,
                    p.payment_timestamp,
                    s.shipment_timestamp,
                    s.delivered_timestamp,
                    (
                        SELECT MIN(psh.status_timestamp)
                        FROM payment_status_history psh
                        WHERE psh.payment_id = p.payment_id
                          AND psh.status = 'Refunded'
                    ) AS payment_refund_timestamp
                FROM orders o
                LEFT JOIN payments p ON o.order_id = p.order_id
                LEFT JOIN shipments s ON o.order_id = s.order_id
                ORDER BY o.order_timestamp, o.order_id
            """)
            orders = cur.fetchall()

            rows = []

            for o in orders:
                order_id = o["order_id"]
                t0 = o["order_timestamp"]
                st = o["order_status"]
                p_time = o["payment_timestamp"] or (t0 + timedelta(minutes=10))
                s_time = o["shipment_timestamp"]
                d_time = o["delivered_timestamp"]
                ref_time = o["payment_refund_timestamp"]

                # Ensure payment time is strictly after order time
                if p_time <= t0:
                    p_time = t0 + timedelta(minutes=5)

                events = []

                # Step 1: Initial creation (Always Pending)
                events.append(("Pending", t0, "Customer", "ORDER_PLACED"))

                if st == "Pending":
                    pass

                elif st == "Cancelled":
                    # Cancelled after some minutes
                    cancel_time = t0 + timedelta(minutes=random.randint(15, 120))
                    events.append(("Cancelled", cancel_time, "Customer", "CUSTOMER_CANCELLED"))

                elif st in ("Paid", "Fulfilled", "Shipped", "Delivered", "Refunded"):
                    # Step 2: Payment captured
                    events.append(("Paid", p_time, "System", "PAYMENT_CAPTURED"))

                    # Step 3: Fulfillment
                    if st in ("Fulfilled", "Shipped", "Delivered", "Refunded"):
                        if s_time and s_time > p_time:
                            # Fulfilled sometime between payment and shipment
                            gap_seconds = int((s_time - p_time).total_seconds())
                            fulfill_offset = max(60, int(gap_seconds * 0.4))
                            fulfill_time = p_time + timedelta(seconds=fulfill_offset)
                        else:
                            fulfill_time = p_time + timedelta(hours=random.randint(2, 6))

                        events.append(("Fulfilled", fulfill_time, "Staff", "ORDER_PACKED"))

                        # Step 4: Shipped
                        if st in ("Shipped", "Delivered", "Refunded") and s_time:
                            ship_time = max(s_time, fulfill_time + timedelta(minutes=30))
                            events.append(("Shipped", ship_time, "Carrier", "DISPATCHED_TO_CARRIER"))

                            # Step 5: Delivered
                            if st in ("Delivered", "Refunded") and d_time:
                                deliver_time = max(d_time, ship_time + timedelta(hours=12))
                                events.append(("Delivered", deliver_time, "Carrier", "PACKAGE_DELIVERED"))

                    # Step 6: Refunded
                    if st == "Refunded":
                        last_time = events[-1][1]
                        if ref_time and ref_time > last_time:
                            refund_timestamp = ref_time
                        else:
                            refund_timestamp = last_time + timedelta(days=random.randint(1, 5))
                        events.append(("Refunded", refund_timestamp, "Staff", "CUSTOMER_RETURN_REFUND"))

                # Guarantee strict timestamp ordering and distinct timestamps
                current_time = t0
                for i in range(len(events)):
                    status, event_time, actor, reason = events[i]
                    if i > 0:
                        prev_time = events[i - 1][1]
                        if event_time <= prev_time:
                            event_time = prev_time + timedelta(minutes=random.randint(5, 30))
                            events[i] = (status, event_time, actor, reason)

                    rows.append((
                        order_id,
                        status,
                        event_time,
                        actor,
                        reason,
                    ))

            cur.executemany("""
                INSERT INTO order_status_history (
                    order_id,
                    status,
                    status_timestamp,
                    actor_type,
                    reason_code
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (order_id, status_timestamp) DO NOTHING
            """, rows)

            conn.commit()
            print(f"Inserted order_status_history: {len(rows)} events across {len(orders)} orders.")


if __name__ == "__main__":
    main()
