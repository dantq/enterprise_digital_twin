import random

from db import get_connection
from config import (
    PRODUCTS,
    SUPPLIER_PRODUCTS_PER_PRODUCT_MIN,
    SUPPLIER_PRODUCTS_PER_PRODUCT_MAX,
    SEED,
)

random.seed(SEED + 5)


def load_products(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT product_id, unit_cost
            FROM products
            ORDER BY product_id
        """)
        return cur.fetchall()


def load_suppliers(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT supplier_id
            FROM suppliers
            WHERE status = 'Active'
            ORDER BY supplier_id
        """)
        return [row[0] for row in cur.fetchall()]


def generate_rows(products, suppliers):
    if not products:
        raise RuntimeError("No products found.")

    if not suppliers:
        raise RuntimeError("No active suppliers found.")

    rows = []

    for product_id, product_unit_cost in products:
        max_suppliers = min(
            SUPPLIER_PRODUCTS_PER_PRODUCT_MAX,
            len(suppliers),
        )

        min_suppliers = min(
            SUPPLIER_PRODUCTS_PER_PRODUCT_MIN,
            max_suppliers,
        )

        supplier_count = random.randint(
            min_suppliers,
            max_suppliers,
        )

        selected_suppliers = random.sample(
            suppliers,
            supplier_count,
        )

        primary_supplier = random.choice(selected_suppliers)

        for supplier_id in selected_suppliers:
            variation = random.uniform(0.90, 1.10)

            unit_cost = round(
                float(product_unit_cost) * variation,
                2,
            )

            rows.append(
                (
                    supplier_id,
                    product_id,
                    f"SUP-{str(product_id)[:8].upper()}",
                    unit_cost,
                    supplier_id == primary_supplier,
                    "Active",
                )
            )

    return rows


def main():
    with get_connection() as conn:
        products = load_products(conn)
        suppliers = load_suppliers(conn)

        print(
            f"Found {len(products)} products "
            f"and {len(suppliers)} active suppliers."
        )

        rows = generate_rows(products, suppliers)

        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO supplier_products (
                    supplier_id,
                    product_id,
                    supplier_sku,
                    unit_cost,
                    is_primary,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                rows,
            )

        conn.commit()

    print(f"Inserted supplier_products: {len(rows)}")


if __name__ == "__main__":
    main()
