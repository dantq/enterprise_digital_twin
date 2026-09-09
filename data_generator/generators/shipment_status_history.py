import os
import sys
import random
from datetime import timedelta

# Cho phép import db.py khi chạy trực tiếp file
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_GENERATOR_DIR = os.path.dirname(CURRENT_DIR)

if DATA_GENERATOR_DIR not in sys.path:
    sys.path.insert(0, DATA_GENERATOR_DIR)

from db import get_connection


STATUS_SEQUENCE = {
    "PickedUp": ["Created", "PickedUp"],
    "InTransit": ["Created", "PickedUp", "InTransit"],
    "Delivered": ["Created", "PickedUp", "InTransit", "Delivered"],
    "Returned": ["Created", "PickedUp", "InTransit", "Delivered", "Returned"],
    "Failed": ["Created", "PickedUp", "InTransit", "Failed"],
}


REGIONS = [
    "Miền Bắc",
    "Miền Trung",
    "Miền Nam",
]


EXCEPTION_CODES = [
    "CUSTOMER_NOT_AVAILABLE",
    "ADDRESS_ISSUE",
    "WEATHER_DELAY",
    "TRAFFIC_DELAY",
    "SORTING_DELAY",
]


def generate_history():
    conn = get_connection()

    try:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT
                    shipment_id,
                    shipment_timestamp,
                    shipment_status
                FROM shipments
                ORDER BY shipment_timestamp, shipment_id;
            """)

            shipments = cur.fetchall()

            print(f"Found {len(shipments)} shipments.")

            inserted = 0

            for shipment in shipments:
                shipment_id = shipment["shipment_id"]
                shipment_timestamp = shipment["shipment_timestamp"]
                final_status = shipment["shipment_status"]

                statuses = STATUS_SEQUENCE.get(final_status)

                if not statuses:
                    print(
                        f"Skipping shipment {shipment_id}: "
                        f"unsupported status {final_status}"
                    )
                    continue

                current_timestamp = shipment_timestamp

                for index, status in enumerate(statuses):

                    # Các trạng thái sau Created xảy ra cách nhau
                    # từ vài phút đến vài giờ.
                    if index > 0:
                        current_timestamp += timedelta(
                            minutes=random.randint(30, 360)
                        )

                    location_region = random.choice(REGIONS)

                    exception_code = None

                    # Chỉ một số trạng thái có exception
                    # để dữ liệu vẫn tự nhiên.
                    if status in ["InTransit", "Failed", "Returned"]:
                        if random.random() < 0.08:
                            exception_code = random.choice(
                                EXCEPTION_CODES
                            )

                    cur.execute("""
                        INSERT INTO shipment_status_history (
                            shipment_id,
                            status,
                            status_timestamp,
                            location_region,
                            exception_code
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (shipment_id, status_timestamp)
                        DO NOTHING;
                    """, (
                        shipment_id,
                        status,
                        current_timestamp,
                        location_region,
                        exception_code,
                    ))

                    inserted += cur.rowcount

            conn.commit()

            print(f"Inserted history rows: {inserted}")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    generate_history()