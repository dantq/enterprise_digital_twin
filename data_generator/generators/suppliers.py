import random

from db import get_connection
from config import SUPPLIERS, SEED


SUPPLIER_NAMES = [
    "TechViet Distribution",
    "Saigon Digital Supply",
    "Viet Electronics",
    "Hanoi Technology",
    "Binh Duong Components",
    "Dong Nai Industrial Supply",
    "Mekong Electronics",
    "Central Tech Trading",
    "VietSmart Distribution",
    "Nova Technology",
    "An Phat Digital",
    "Minh Long Trading",
    "Thanh Cong Electronics",
    "Global Tech Vietnam",
    "Asia Digital Supply",
    "Phuoc Long Components",
    "Tan Viet Technology",
    "Hoang Gia Distribution",
    "Nam Viet Electronics",
    "Pacific Technology Supply",
]

REGIONS = [
    "Hà Nội",
    "TP Hồ Chí Minh",
    "Đà Nẵng",
    "Hải Phòng",
    "Bình Dương",
    "Đồng Nai",
    "Cần Thơ",
]


def generate_suppliers():
    random.seed(SEED + 3)

    rows = []

    for i in range(SUPPLIERS):

        supplier_name = SUPPLIER_NAMES[i]

        region = random.choices(
            REGIONS,
            weights=[20, 30, 10, 8, 15, 12, 5],
            k=1,
        )[0]

        reliability_score = round(
            random.uniform(0.75, 0.99),
            4,
        )

        average_lead_time_days = round(
            random.uniform(2.0, 14.0),
            2,
        )

        lead_time_std_days = round(
            random.uniform(0.3, 3.0),
            2,
        )

        rows.append(
            (
                supplier_name,
                reliability_score,
                average_lead_time_days,
                lead_time_std_days,
                region,
            )
        )

    return rows


def main():
    rows = generate_suppliers()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO suppliers (
                    supplier_name,
                    reliability_score,
                    average_lead_time_days,
                    lead_time_std_days,
                    region
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                rows,
            )

        conn.commit()

    print(f"Inserted suppliers: {len(rows)}")


if __name__ == "__main__":
    main()
