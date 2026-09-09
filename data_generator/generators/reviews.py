"""Generate customer reviews for purchased products in delivered and fulfilled orders.

Fields:
- customer_id, order_id, product_id
- created_at: Post-delivery timestamp
- rating: 1 to 5 stars
- sentiment_score: -1.0 to +1.0
- review_category: 'Product', 'Delivery', 'Packaging', 'Service'
- Constraint: UNIQUE (customer_id, order_id, product_id)
"""

import sys
import random
from datetime import timedelta
from pathlib import Path

DATA_GENERATOR_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATA_GENERATOR_DIR))

from db import get_connection
from config import SEED

RANDOM_SEED = SEED + 17
random.seed(RANDOM_SEED)


def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS count FROM reviews")
            if cur.fetchone()["count"] > 0:
                print("reviews already populated. Skipping.")
                return

            # Fetch order items for delivered or refunded orders
            cur.execute("""
                SELECT
                    o.order_id,
                    o.customer_id,
                    o.order_timestamp,
                    o.order_status,
                    oi.product_id,
                    s.delivered_timestamp
                FROM orders o
                JOIN order_items oi ON o.order_id = oi.order_id
                LEFT JOIN shipments s ON o.order_id = s.order_id
                WHERE o.order_status IN ('Delivered', 'Refunded', 'Shipped')
                ORDER BY o.order_timestamp, o.order_id, oi.product_id
            """)
            eligible_items = cur.fetchall()

            rows = []
            seen_pairs = set()

            for item in eligible_items:
                # Roughly 45% of items receive a customer review
                if random.random() > 0.45:
                    continue

                key = (item["customer_id"], item["order_id"], item["product_id"])
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)

                base_time = item["delivered_timestamp"] or item["order_timestamp"]
                created_at = base_time + timedelta(
                    days=random.randint(1, 14),
                    hours=random.randint(1, 23),
                    minutes=random.randint(0, 59),
                )

                st = item["order_status"]
                if st == "Refunded":
                    rating = random.choices([1, 2, 3], weights=[0.60, 0.30, 0.10], k=1)[0]
                    sentiment = round(random.uniform(-0.95, -0.25), 4)
                    category = random.choice(["Product", "Service"])
                elif st == "Delivered":
                    rating = random.choices([3, 4, 5], weights=[0.10, 0.35, 0.55], k=1)[0]
                    sentiment = round(random.uniform(0.20, 0.95), 4) if rating >= 4 else round(random.uniform(-0.15, 0.25), 4)
                    category = random.choice(["Product", "Delivery", "Packaging"])
                else:  # Shipped / In-transit
                    rating = random.choices([3, 4], weights=[0.40, 0.60], k=1)[0]
                    sentiment = round(random.uniform(0.10, 0.60), 4)
                    category = "Product"

                rows.append((
                    item["customer_id"],
                    item["order_id"],
                    item["product_id"],
                    created_at,
                    rating,
                    sentiment,
                    category,
                ))

            cur.executemany("""
                INSERT INTO reviews (
                    customer_id,
                    order_id,
                    product_id,
                    created_at,
                    rating,
                    sentiment_score,
                    review_category
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (customer_id, order_id, product_id) DO NOTHING
            """, rows)

            conn.commit()
            print(f"Inserted reviews: {len(rows)}")


if __name__ == "__main__":
    main()
