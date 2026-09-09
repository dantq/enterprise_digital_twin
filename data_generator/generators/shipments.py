import os
import sys
import random
from datetime import timedelta

# Allow direct execution:
# python data_generator/generators/shipments.py
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_GENERATOR_DIR = os.path.dirname(CURRENT_DIR)

if DATA_GENERATOR_DIR not in sys.path:
    sys.path.insert(0, DATA_GENERATOR_DIR)

from db import get_connection


RANDOM_SEED = 20260829
random.seed(RANDOM_SEED)


ELIGIBLE_ORDER_STATUSES = {
    "Fulfilled",
    "Shipped",
    "Delivered",
    "Refunded",
}


def choose_carrier(carriers):
    """
    Weighted carrier selection.

    Higher reliability receives slightly higher probability.
    This preserves realistic variation while still respecting
    carrier operational quality.
    """
    weights = []

    for carrier in carriers:
        reliability = float(carrier["delivery_reliability"])

        # Keep selection probability positive.
        weight = max(0.1, reliability)
        weights.append(weight)

    return random.choices(carriers, weights=weights, k=1)[0]


def calculate_shipment_status(order_status):
    """
    Map the current order state to a shipment state.
    """
    if order_status == "Fulfilled":
        return "PickedUp"

    if order_status == "Shipped":
        return random.choices(
            ["PickedUp", "InTransit"],
            weights=[0.15, 0.85],
            k=1,
        )[0]

    if order_status == "Delivered":
        return "Delivered"

    if order_status == "Refunded":
        return random.choices(
            ["Returned", "Delivered"],
            weights=[0.75, 0.25],
            k=1,
        )[0]

    return "Created"


def build_shipment_timestamps(
    order_timestamp,
    carrier,
    shipment_status,
):
    """
    Create realistic shipment and delivery timestamps.
    """

    average_days = float(carrier["average_delivery_days"])

    pickup_delay_hours = random.uniform(2, 36)

    shipment_timestamp = order_timestamp + timedelta(
        hours=pickup_delay_hours
    )

    estimated_days = max(
        1,
        int(round(average_days + random.uniform(-0.75, 0.75)))
    )

    estimated_delivery_timestamp = (
        shipment_timestamp
        + timedelta(days=estimated_days)
    )

    delivered_timestamp = None

    if shipment_status == "Delivered":
        delivery_variation_hours = random.uniform(-12, 24)

        delivered_timestamp = (
            estimated_delivery_timestamp
            + timedelta(hours=delivery_variation_hours)
        )

        # Ensure delivery never occurs before shipment.
        if delivered_timestamp < shipment_timestamp:
            delivered_timestamp = (
                shipment_timestamp
                + timedelta(hours=random.uniform(12, 48))
            )

    return (
        shipment_timestamp,
        estimated_delivery_timestamp,
        delivered_timestamp,
    )


def generate_tracking_number(index):
    """
    Generate deterministic unique tracking numbers.
    """
    return f"VN{2026}{index:08d}"


def main():
    with get_connection() as conn:
        with conn.cursor() as cur:

            # ---------------------------------------------------------
            # Load eligible orders
            # ---------------------------------------------------------
            cur.execute(
                """
                SELECT
                    order_id,
                    warehouse_id,
                    order_timestamp,
                    order_status
                FROM orders
                WHERE order_status = ANY(%s)
                ORDER BY order_timestamp, order_id;
                """,
                (list(ELIGIBLE_ORDER_STATUSES),),
            )

            orders = cur.fetchall()

            # ---------------------------------------------------------
            # Load active carriers
            # ---------------------------------------------------------
            cur.execute(
                """
                SELECT
                    carrier_id,
                    carrier_name,
                    average_delivery_days,
                    delivery_reliability,
                    region,
                    status
                FROM carriers
                WHERE status = 'Active'
                ORDER BY carrier_name;
                """
            )

            carriers = cur.fetchall()

            if not orders:
                print("No eligible orders found.")
                return

            if not carriers:
                print("No active carriers found.")
                return

            print(f"Found {len(orders)} eligible orders.")
            print(f"Found {len(carriers)} active carriers.")

            # ---------------------------------------------------------
            # Generate shipments
            # ---------------------------------------------------------
            rows = []

            for index, order in enumerate(orders, start=1):

                carrier = choose_carrier(carriers)

                shipment_status = calculate_shipment_status(
                    order["order_status"]
                )

                (
                    shipment_timestamp,
                    estimated_delivery_timestamp,
                    delivered_timestamp,
                ) = build_shipment_timestamps(
                    order["order_timestamp"],
                    carrier,
                    shipment_status,
                )

                tracking_number = generate_tracking_number(index)

                rows.append(
                    (
                        order["order_id"],
                        order["warehouse_id"],
                        carrier["carrier_id"],
                        shipment_timestamp,
                        estimated_delivery_timestamp,
                        delivered_timestamp,
                        shipment_status,
                        tracking_number,
                    )
                )

            # ---------------------------------------------------------
            # Insert
            # ---------------------------------------------------------
            cur.executemany(
                """
                INSERT INTO shipments (
                    order_id,
                    warehouse_id,
                    carrier_id,
                    shipment_timestamp,
                    estimated_delivery_timestamp,
                    delivered_timestamp,
                    shipment_status,
                    tracking_number
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (tracking_number) DO NOTHING;
                """,
                rows,
            )

            conn.commit()
            print(f"Inserted shipments: {len(rows)}")


if __name__ == "__main__":
    main()