import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import random
from decimal import Decimal, ROUND_HALF_UP

from db import get_connection
from config import SEED


random.seed(SEED + 5)

MIN_ITEMS_PER_ORDER = 1
MAX_ITEMS_PER_ORDER = 5


def money(value):
    return Decimal(str(value)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def generate_quantity(rng, demand_class):
    if demand_class == "High":
        return rng.choices(
            [1, 2, 3, 4, 5],
            weights=[20, 30, 25, 15, 10],
        )[0]

    if demand_class == "Medium":
        return rng.choices(
            [1, 2, 3, 4],
            weights=[35, 35, 20, 10],
        )[0]

    return rng.choices(
        [1, 2, 3],
        weights=[50, 35, 15],
    )[0]


def generate_discount(rng, gross_amount, customer_segment):

    if customer_segment == "VIP":
        rate = rng.choices(
            [0, 0.05, 0.10],
            weights=[45, 40, 15],
        )[0]

    elif customer_segment == "At-Risk":
        rate = rng.choices(
            [0, 0.05, 0.10],
            weights=[40, 45, 15],
        )[0]

    elif customer_segment == "New":
        rate = rng.choices(
            [0, 0.05],
            weights=[70, 30],
        )[0]

    else:
        rate = rng.choices(
            [0, 0.05, 0.10],
            weights=[70, 25, 5],
        )[0]

    return money(gross_amount * Decimal(str(rate)))


def build_order_lines(rng, products, customer_segment):
    """Build unique product lines before the order header is persisted."""
    item_count = rng.randint(MIN_ITEMS_PER_ORDER, MAX_ITEMS_PER_ORDER)
    selected_products = rng.sample(products, min(item_count, len(products)))
    rows = []

    for product_id, unit_price, demand_class in selected_products:
        unit_price = money(unit_price)
        quantity = generate_quantity(rng, demand_class)
        gross_amount = money(Decimal(quantity) * unit_price)
        discount_amount = generate_discount(rng, gross_amount, customer_segment)
        item_total = money(gross_amount - discount_amount)
        rows.append((product_id, quantity, unit_price, discount_amount, item_total))

    return rows


def main():

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    order_id,
                    customer_id
                FROM orders
                ORDER BY order_timestamp, order_id
                """
            )

            orders = cur.fetchall()

            cur.execute(
                """
                SELECT
                    customer_id,
                    customer_segment
                FROM customers
                """
            )

            customers = {
                row[0]: row[1]
                for row in cur.fetchall()
            }

            cur.execute(
                """
                SELECT
                    product_id,
                    unit_price,
                    demand_class
                FROM products
                WHERE status = 'Active'
                """
            )

            products = cur.fetchall()

            print(
                f"Found {len(orders)} orders, "
                f"{len(products)} active products."
            )

            if not orders:
                raise RuntimeError(
                    "No orders found. Generate orders first."
                )

            if not products:
                raise RuntimeError(
                    "No active products found."
                )

            rows = []

            for order_id, customer_id in orders:

                customer_segment = customers.get(
                    customer_id,
                    "Regular",
                )

                item_count = random.randint(
                    MIN_ITEMS_PER_ORDER,
                    MAX_ITEMS_PER_ORDER,
                )

                selected_products = random.sample(
                    products,
                    min(item_count, len(products)),
                )

                for product_id, unit_price, demand_class in selected_products:

                    unit_price = money(unit_price)

                    quantity = generate_quantity(
                        random,
                        demand_class
                    )

                    gross_amount = money(
                        Decimal(quantity) * unit_price
                    )

                    discount_amount = generate_discount(
                        random,
                        gross_amount,
                        customer_segment,
                    )

                    item_total = money(
                        gross_amount - discount_amount
                    )

                    rows.append(
                        (
                            order_id,
                            product_id,
                            quantity,
                            unit_price,
                            discount_amount,
                            item_total,
                        )
                    )

            cur.executemany(
                """
                INSERT INTO order_items (
                    order_id,
                    product_id,
                    quantity,
                    unit_price,
                    discount_amount,
                    item_total
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                rows,
            )

        conn.commit()

    print(f"Inserted order_items: {len(rows)}")


if __name__ == "__main__":
    raise SystemExit(
        "order_items.py is a library. Run orders.py to generate orders and "
        "their items atomically."
    )
