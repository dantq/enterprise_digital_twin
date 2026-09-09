from db import get_connection
from config import PAYMENT_METHODS, SEED

import random

random.seed(SEED + 6)

METHODS = [
    ("COD", "Internal", 0.025),
    ("Bank Transfer", "VietQR", 0.008),
    ("Credit Card", "Visa/Mastercard", 0.018),
    ("MoMo", "MoMo", 0.012),
    ("ZaloPay", "ZaloPay", 0.014),
    ("Installment", "Internal", 0.030),
]


def generate_payment_methods():
    rows = []

    for i in range(PAYMENT_METHODS):
        method_name, provider, baseline = METHODS[i]

        failure_rate = round(
            baseline * random.uniform(0.85, 1.15),
            4
        )

        rows.append(
            (
                method_name,
                provider,
                failure_rate,
                "Active",
            )
        )

    return rows


def main():
    rows = generate_payment_methods()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO payment_methods (
                    method_name,
                    provider,
                    failure_rate_baseline,
                    status
                )
                VALUES (%s, %s, %s, %s)
                """,
                rows,
            )

        conn.commit()

    print(f"Inserted payment methods: {len(rows)}")


if __name__ == "__main__":
    main()
