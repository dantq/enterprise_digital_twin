import random
from datetime import date, timedelta

from db import get_connection
from config import CUSTOMERS, SEED


# Các giá trị PHẢI khớp với CHECK constraint của database.
CUSTOMER_SEGMENTS = [
    "New",
    "Regular",
    "VIP",
    "At-Risk",
    "Churned",
]

ACQUISITION_CHANNELS = [
    "Organic",
    "Facebook",
    "Google",
    "TikTok",
    "Referral",
    "Marketplace",
]

REGIONS = [
    "Hà Nội",
    "TP Hồ Chí Minh",
    "Đà Nẵng",
    "Hải Phòng",
    "Cần Thơ",
    "Bình Dương",
    "Đồng Nai",
]

AGE_GROUPS = [
    "18-24",
    "25-34",
    "35-44",
    "45-54",
    "55+",
]


def random_registration_date():
    start = date(2022, 1, 1)
    end = date(2026, 8, 28)

    days = (end - start).days

    return start + timedelta(
        days=random.randint(0, days)
    )


def generate_customers():
    rows = []

    for _ in range(CUSTOMERS):

        segment = random.choices(
            CUSTOMER_SEGMENTS,
            weights=[25, 50, 10, 10, 5],
            k=1,
        )[0]

        channel = random.choices(
            ACQUISITION_CHANNELS,
            weights=[30, 20, 15, 10, 15, 10],
            k=1,
        )[0]

        region = random.choices(
            REGIONS,
            weights=[20, 30, 10, 8, 7, 15, 10],
            k=1,
        )[0]

        age_group = random.choices(
            AGE_GROUPS,
            weights=[15, 35, 25, 15, 10],
            k=1,
        )[0]

        registration_date = random_registration_date()

        rows.append(
            (
                segment,
                channel,
                registration_date,
                region,
                age_group,
            )
        )

    return rows


def main():
    random.seed(SEED + 2)

    rows = generate_customers()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO customers (
                    customer_segment,
                    acquisition_channel,
                    registration_date,
                    region,
                    age_group
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                rows,
            )

        conn.commit()

    print(f"Inserted customers: {len(rows)}")


if __name__ == "__main__":
    main()
