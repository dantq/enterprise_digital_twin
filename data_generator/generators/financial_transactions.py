"""Generate financial transactions from payments, orders, and shipments.

Transaction Types:
- Revenue: Positive inflow when payment is Captured.
- Refund: Negative outflow when payment is Refunded.
- ShippingCost: Negative outflow for logistics cost per shipment.
- COGS: Cost of Goods Sold (approx 65% of subtotal) for fulfilled/delivered orders.
"""

import sys
import random
from datetime import timedelta
from pathlib import Path

DATA_GENERATOR_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATA_GENERATOR_DIR))

from db import get_connection
from config import SEED

RANDOM_SEED = SEED + 15
random.seed(RANDOM_SEED)


def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Check if financial_transactions already has data
            cur.execute("SELECT COUNT(*) AS count FROM financial_transactions")
            if cur.fetchone()["count"] > 0:
                print("financial_transactions already populated. Skipping.")
                return

            rows = []

            # 1. Revenue from Captured payments
            cur.execute("""
                SELECT
                    p.payment_id,
                    p.order_id,
                    p.payment_timestamp,
                    p.amount,
                    p.currency_code
                FROM payments p
                WHERE p.payment_status IN ('Captured', 'Refunded')
            """)
            captured_payments = cur.fetchall()

            for p in captured_payments:
                rows.append((
                    p["payment_timestamp"],
                    "Revenue",
                    p["amount"],
                    p["currency_code"],
                    p["order_id"],
                    p["payment_id"],
                    None,  # purchase_order_id
                    None,  # shipment_id
                    None,  # campaign_id
                    f"REV-{p['payment_id']}",
                ))

            # 2. Refund from Refunded payments
            cur.execute("""
                SELECT
                    p.payment_id,
                    p.order_id,
                    psh.status_timestamp AS refund_timestamp,
                    p.amount,
                    p.currency_code
                FROM payments p
                JOIN payment_status_history psh ON p.payment_id = psh.payment_id AND psh.status = 'Refunded'
                WHERE p.payment_status = 'Refunded'
            """)
            refunded_payments = cur.fetchall()

            for p in refunded_payments:
                rows.append((
                    p["refund_timestamp"],
                    "Refund",
                    -p["amount"],
                    p["currency_code"],
                    p["order_id"],
                    p["payment_id"],
                    None,
                    None,
                    None,
                    f"REF-{p['payment_id']}",
                ))

            # 3. ShippingCost from shipments
            cur.execute("""
                SELECT
                    s.shipment_id,
                    s.order_id,
                    s.shipment_timestamp,
                    COALESCE(o.shipping_fee, 30000.00) AS shipping_fee,
                    COALESCE(o.currency_code, 'VND') AS currency_code
                FROM shipments s
                JOIN orders o ON s.order_id = o.order_id
            """)
            shipments = cur.fetchall()

            for s in shipments:
                # Logistics cost paid to carrier (estimated at 85% of shipping fee or min 15,000)
                cost = max(15000.00, round(float(s["shipping_fee"]) * 0.85, 2))
                rows.append((
                    s["shipment_timestamp"],
                    "ShippingCost",
                    -cost,
                    s["currency_code"],
                    s["order_id"],
                    None,
                    None,
                    s["shipment_id"],
                    None,
                    f"SHIP-{s['shipment_id']}",
                ))

            # 4. COGS from completed/fulfilled orders
            cur.execute("""
                SELECT
                    o.order_id,
                    o.order_timestamp,
                    o.subtotal,
                    o.currency_code
                FROM orders o
                WHERE o.order_status IN ('Paid', 'Fulfilled', 'Shipped', 'Delivered', 'Refunded')
            """)
            orders = cur.fetchall()

            for o in orders:
                # Cost of goods sold: roughly 65% of subtotal
                cogs = round(float(o["subtotal"]) * 0.65, 2)
                if cogs > 0:
                    rows.append((
                        o["order_timestamp"] + timedelta(hours=1),
                        "COGS",
                        -cogs,
                        o["currency_code"],
                        o["order_id"],
                        None,
                        None,
                        None,
                        None,
                        f"COGS-{o['order_id']}",
                    ))

            # Insert all financial transactions
            cur.executemany("""
                INSERT INTO financial_transactions (
                    transaction_timestamp,
                    transaction_type,
                    amount,
                    currency_code,
                    order_id,
                    payment_id,
                    purchase_order_id,
                    shipment_id,
                    campaign_id,
                    reference_code
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (reference_code) DO NOTHING
            """, rows)

            conn.commit()
            print(f"Inserted financial_transactions: {len(rows)}")


if __name__ == "__main__":
    main()
