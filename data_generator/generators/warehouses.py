from db import get_connection
from config import WAREHOUSES, SEED

import random

random.seed(SEED + 4)

WAREHOUSE_NAMES = [
    "Kho Hà Nội",
    "Kho TP Hồ Chí Minh",
    "Kho Đà Nẵng",
    "Kho Bình Dương",
    "Kho Cần Thơ",
]

REGIONS = [
    "Hà Nội",
    "TP Hồ Chí Minh",
    "Đà Nẵng",
    "Bình Dương",
    "Cần Thơ",
]


def generate_warehouses():
    rows = []

    for i in range(WAREHOUSES):
        capacity = random.randint(5000, 30000)
        daily_processing_capacity = random.randint(500, 3000)

        rows.append(
            (
                WAREHOUSE_NAMES[i],
                REGIONS[i],
                capacity,
                daily_processing_capacity,
            )
        )

    return rows


def main():
    rows = generate_warehouses()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO warehouses (
                    warehouse_name,
                    region,
                    capacity,
                    daily_processing_capacity
                )
                VALUES (%s, %s, %s, %s)
                """,
                rows,
            )

        conn.commit()

    print(f"Inserted warehouses: {len(rows)}")


if __name__ == "__main__":
    main()
