"""Generate internally consistent orders and order items in one transaction.

The order header is calculated from the exact lines written in the same
transaction.  It is therefore impossible for this generator to manufacture an
independent subtotal.
"""

import random
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

DATA_GENERATOR_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATA_GENERATOR_DIR))

GENERATORS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(GENERATORS_DIR))

from config import SEED
from db import get_connection
from order_items import build_order_lines, money


ORDER_COUNT = 500
CHANNELS = ["Website", "Mobile App", "Facebook", "TikTok", "Marketplace", "Store"]
ORDER_STATUSES = [
    ("Pending", 5), ("Paid", 15), ("Fulfilled", 15), ("Shipped", 20),
    ("Delivered", 35), ("Cancelled", 7), ("Refunded", 3),
]


def random_order_timestamp(rng):
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 8, 28, tzinfo=timezone.utc)
    return start + timedelta(seconds=rng.randint(0, int((end - start).total_seconds())))


def choose_order_discount(rng, subtotal, customer_segment, channel):
    """Order-level promotion, after line-level promotions have been applied."""
    if subtotal < Decimal("300000"):
        return Decimal("0.00")
    if customer_segment == "VIP":
        rates, weights = [0, 0.03, 0.05, 0.10], [30, 35, 25, 10]
    elif channel == "Marketplace":
        rates, weights = [0, 0.03, 0.05], [45, 35, 20]
    else:
        rates, weights = [0, 0.03, 0.05], [65, 25, 10]
    return money(subtotal * Decimal(str(rng.choices(rates, weights=weights)[0])))


def calculate_shipping_fee(rng, subtotal, channel, order_status):
    """Shipping is business-derived: cancelled orders are not shipped."""
    if order_status == "Cancelled" or subtotal >= Decimal("1500000"):
        return Decimal("0.00")
    channel_base_fee = {
        "Website": 30000, "Mobile App": 25000, "Facebook": 35000,
        "TikTok": 35000, "Marketplace": 30000, "Store": 0,
    }[channel]
    return money(channel_base_fee + rng.choice([0, 5000, 10000, 15000]))


def load_reference_data(cur):
    cur.execute("""
        SELECT customer_id, customer_segment
        FROM customers WHERE status = 'Active' ORDER BY customer_id
    """)
    customers = [
        (row["customer_id"], row["customer_segment"])
        for row in cur.fetchall()
    ]
    cur.execute("""
        SELECT warehouse_id FROM warehouses
        WHERE status = 'Active' ORDER BY warehouse_id
    """)
    warehouses = [row["warehouse_id"] for row in cur.fetchall()]
    cur.execute("""
        SELECT product_id, unit_price, demand_class FROM products
        WHERE status = 'Active' ORDER BY product_id
    """)
    products = [
        (row["product_id"], row["unit_price"], row["demand_class"])
        for row in cur.fetchall()
    ]
    if not customers or not warehouses or not products:
        raise RuntimeError("Active customers, warehouses, and products are required.")
    return customers, warehouses, products


def assert_empty_order_domain(cur):
    """Refuse to append; regeneration must start from a clean derived domain."""
    cur.execute("SELECT COUNT(*) AS row_count FROM orders")
    order_count = cur.fetchone()["row_count"]
    cur.execute("SELECT COUNT(*) AS row_count FROM order_items")
    item_count = cur.fetchone()["row_count"]
    if order_count or item_count:
        raise RuntimeError(
            f"Order domain is not empty ({order_count} orders, {item_count} lines). "
            "Do not append or patch it. Rebuild this derived domain in a clean "
            "database, then rerun this generator before payments, inventory, and shipments."
        )


def validate_generated_orders(cur):
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE ABS(o.subtotal - COALESCE(x.items_subtotal, 0)) > 0.01) AS subtotal_mismatches,
            COUNT(*) FILTER (WHERE ABS(o.total_amount - (o.subtotal - o.discount_amount + o.shipping_fee)) > 0.01) AS total_mismatches,
            COUNT(*) FILTER (WHERE x.items_subtotal IS NULL) AS orders_without_items,
            COUNT(*) FILTER (WHERE o.discount_amount < 0 OR o.discount_amount > o.subtotal) AS discount_mismatches
        FROM orders AS o
        LEFT JOIN (
            SELECT order_id, SUM(item_total) AS items_subtotal
            FROM order_items GROUP BY order_id
        ) AS x ON x.order_id = o.order_id
    """)
    result = cur.fetchone()
    subtotal_failures = result["subtotal_mismatches"]
    total_failures = result["total_mismatches"]
    empty_orders = result["orders_without_items"]
    discount_failures = result["discount_mismatches"]
    failures = subtotal_failures + total_failures + empty_orders + discount_failures
    if failures:
        raise RuntimeError(
            "Order financial validation failed: "
            f"subtotal={subtotal_failures}, total={total_failures}, "
            f"empty={empty_orders}, discount={discount_failures}."
        )
    return {"subtotal_mismatches": 0, "total_mismatches": 0, "orders_without_items": 0}


def main():
    rng = random.Random(SEED + 6)
    inserted_items = 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            assert_empty_order_domain(cur)
            customers, warehouses, products = load_reference_data(cur)

            for _ in range(ORDER_COUNT):
                customer_id, customer_segment = rng.choice(customers)
                warehouse_id = rng.choice(warehouses)
                timestamp = random_order_timestamp(rng)
                channel = rng.choice(CHANNELS)
                status = rng.choices(
                    [status for status, _ in ORDER_STATUSES],
                    weights=[weight for _, weight in ORDER_STATUSES], k=1,
                )[0]
                lines = build_order_lines(rng, products, customer_segment)
                subtotal = money(sum((line[4] for line in lines), Decimal("0.00")))
                discount_amount = choose_order_discount(rng, subtotal, customer_segment, channel)
                shipping_fee = calculate_shipping_fee(rng, subtotal, channel, status)
                total_amount = money(subtotal - discount_amount + shipping_fee)

                cur.execute("""
                    INSERT INTO orders (
                        customer_id, warehouse_id, order_timestamp, channel, order_status,
                        subtotal, discount_amount, shipping_fee, total_amount, currency_code
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING order_id
                """, (customer_id, warehouse_id, timestamp, channel, status, subtotal,
                      discount_amount, shipping_fee, total_amount, "VND"))
                order_id = cur.fetchone()["order_id"]
                cur.executemany("""
                    INSERT INTO order_items (
                        order_id, product_id, quantity, unit_price, discount_amount, item_total
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, [(order_id, *line) for line in lines])
                inserted_items += len(lines)

            validation = validate_generated_orders(cur)
        conn.commit()

    print(f"Inserted {ORDER_COUNT} orders and {inserted_items} order items.")
    print(f"Financial validation passed: {validation}")


if __name__ == "__main__":
    main()
