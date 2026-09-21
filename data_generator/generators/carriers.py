import random

from db import get_connection
from config import CARRIERS, SEED

random.seed(SEED + 5)

CARRIER_NAMES = [
    "Viettel Post",
    "VNPost",
    "GHN",
    "GHTK",
    "J&T Express",
    "Ninja Van",
    "Best Express",
    "Kerry Express",
    "DHL Vietnam",
    "FedEx Vietnam",
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

def generate_carriers():
    names = CARRIER_NAMES[:CARRIERS]

    rows = []

    for name in names:
        average_delivery_days = round(
            random.uniform(1.0, 5.0), 2
        )

        delivery_reliability = round(
            random.uniform(0.85, 0.99), 4
        )

        region = random.choice(REGIONS)

        status = random.choices(
            ["Active", "Suspended", "Inactive"],
            weights=[90, 5, 5],
        )[0]

        rows.append((
            name,
            average_delivery_days,
            delivery_reliability,
            region,
            status,
        ))

    return rows


def main():
    rows = generate_carriers()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO carriers (
                    carrier_name,
                    average_delivery_days,
                    delivery_reliability,
                    region,
                    status
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                rows,
            )

        conn.commit()

    print(f"Inserted carriers: {len(rows)}")


if __name__ == "__main__":
    main()
