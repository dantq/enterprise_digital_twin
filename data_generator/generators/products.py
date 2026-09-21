import random
from datetime import date, timedelta

from db import get_connection
from config import PRODUCTS, SEED


random.seed(SEED + 7)


PRODUCT_PREFIXES = [
    "VietTech",
    "Nova",
    "Smart",
    "Pro",
    "Eco",
    "Digital",
    "Vision",
    "Future",
    "Ultra",
    "Power",
]

PRODUCT_TYPES = [
    "Laptop",
    "Smartphone",
    "Monitor",
    "Camera",
    "Keyboard",
    "Mouse",
    "Headphone",
    "Tablet",
    "Router",
    "SSD",
]


DEMAND_CLASSES = [
    ("High", 50),
    ("Medium", 30),
    ("Low", 20),
]


def random_launch_date():
    start = date(2022, 1, 1)
    end = date(2026, 6, 30)

    days = (end - start).days

    return start + timedelta(
        days=random.randint(0, days)
    )


def get_category_ids():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT category_id
                FROM categories
                WHERE status = 'Active'
                ORDER BY category_name
                """
            )

            return [row[0] for row in cur.fetchall()]


def generate_products(category_ids):
    rows = []

    for i in range(PRODUCTS):

        prefix = random.choice(PRODUCT_PREFIXES)
        product_type = random.choice(PRODUCT_TYPES)

        product_name = (
            f"{prefix} {product_type} "
            f"{i + 1:03d}"
        )

        category_id = random.choice(category_ids)

        unit_price = round(
            random.uniform(300000, 30000000),
            2,
        )

        margin_rate = round(
            random.uniform(0.08, 0.35),
            4,
        )

        unit_cost = round(
            unit_price * (1 - margin_rate),
            2,
        )

        demand_class = random.choices(
            [x[0] for x in DEMAND_CLASSES],
            weights=[x[1] for x in DEMAND_CLASSES],
            k=1,
        )[0]

        demand_volatility = round(
            random.uniform(0.05, 0.50),
            4,
        )

        launch_date = random_launch_date()

        rows.append(
            (
                category_id,
                product_name,
                unit_price,
                unit_cost,
                margin_rate,
                demand_class,
                demand_volatility,
                launch_date,
                "Active",
            )
        )

    return rows


def main():
    category_ids = get_category_ids()

    if not category_ids:
        raise RuntimeError(
            "No active categories found."
        )

    if len(category_ids) < PRODUCTS:
        print(
            f"Found {len(category_ids)} categories "
            f"for {PRODUCTS} products."
        )

    rows = generate_products(category_ids)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO products (
                    category_id,
                    product_name,
                    unit_price,
                    unit_cost,
                    margin_rate,
                    demand_class,
                    demand_volatility,
                    launch_date,
                    status
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                """,
                rows,
            )

        conn.commit()

    print(
        f"Inserted products: {len(rows)}"
    )


if __name__ == "__main__":
    main()

