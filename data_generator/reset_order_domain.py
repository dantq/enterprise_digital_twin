"""Safely clear only generated order-domain data before a full regeneration.

Run without arguments for a dry-run report.  ``--apply`` deletes only records
derived from existing orders and leaves master data and Ground Truth untouched.
"""

import argparse

from db import get_connection


KNOWN_FK_CHILDREN = {
    "orders": {
        "order_items", "order_status_history", "payments", "shipments",
        "customer_tickets", "reviews", "marketing_events", "financial_transactions",
    },
    "payments": {"payment_status_history", "financial_transactions"},
    "shipments": {"shipment_status_history", "financial_transactions"},
}

COUNT_TABLES = [
    "orders", "order_items", "order_status_history", "payments",
    "payment_status_history", "inventory_movements", "shipments",
    "shipment_status_history", "customer_tickets", "reviews",
    "marketing_events", "financial_transactions",
]


def table_exists(cur, table_name):
    cur.execute("SELECT to_regclass(%s) IS NOT NULL AS exists", (f"public.{table_name}",))
    return cur.fetchone()["exists"]


def discover_unknown_dependencies(cur):
    """Fail closed if the schema adds a relationship not covered by this reset."""
    unknown = []
    for parent, allowed_children in KNOWN_FK_CHILDREN.items():
        if not table_exists(cur, parent):
            continue
        cur.execute("""
            SELECT child.relname AS child_table
            FROM pg_constraint AS fk
            JOIN pg_class AS child ON child.oid = fk.conrelid
            JOIN pg_class AS parent ON parent.oid = fk.confrelid
            JOIN pg_namespace AS ns ON ns.oid = child.relnamespace
            WHERE fk.contype = 'f'
              AND ns.nspname = 'public'
              AND parent.relname = %s
        """, (parent,))
        for row in cur.fetchall():
            child = row["child_table"]
            if child not in allowed_children:
                unknown.append(f"{child} -> {parent}")
    if unknown:
        raise RuntimeError(
            "Reset refused because these dependencies are not explicitly scoped: "
            + ", ".join(sorted(set(unknown)))
        )


def counts(cur):
    result = {}
    for table_name in COUNT_TABLES:
        if table_exists(cur, table_name):
            cur.execute(f"SELECT COUNT(*) AS row_count FROM {table_name}")
            result[table_name] = cur.fetchone()["row_count"]
    return result


def delete_if_table_exists(cur, table_name, statement):
    if table_exists(cur, table_name):
        cur.execute(statement)
        return cur.rowcount
    return 0


def reset(cur):
    """Delete children before parents; every statement is scoped to current orders."""
    deleted = {}
    deleted["financial_transactions"] = delete_if_table_exists(cur, "financial_transactions", """
        DELETE FROM financial_transactions AS ft
        WHERE ft.order_id IN (SELECT order_id FROM orders)
           OR ft.payment_id IN (SELECT payment_id FROM payments)
           OR ft.shipment_id IN (SELECT shipment_id FROM shipments)
    """)
    deleted["marketing_events"] = delete_if_table_exists(cur, "marketing_events", """
        DELETE FROM marketing_events WHERE order_id IN (SELECT order_id FROM orders)
    """)
    deleted["reviews"] = delete_if_table_exists(cur, "reviews", """
        DELETE FROM reviews WHERE order_id IN (SELECT order_id FROM orders)
    """)
    deleted["customer_tickets"] = delete_if_table_exists(cur, "customer_tickets", """
        DELETE FROM customer_tickets WHERE order_id IN (SELECT order_id FROM orders)
    """)
    deleted["payment_status_history"] = delete_if_table_exists(cur, "payment_status_history", """
        DELETE FROM payment_status_history WHERE payment_id IN (SELECT payment_id FROM payments)
    """)
    deleted["shipment_status_history"] = delete_if_table_exists(cur, "shipment_status_history", """
        DELETE FROM shipment_status_history WHERE shipment_id IN (SELECT shipment_id FROM shipments)
    """)
    deleted["inventory_movements"] = delete_if_table_exists(cur, "inventory_movements", """
        DELETE FROM inventory_movements
        WHERE reference_entity_type = 'Order'
          AND reference_entity_id IN (SELECT order_id FROM orders)
    """)
    deleted["shipments"] = delete_if_table_exists(cur, "shipments", """
        DELETE FROM shipments WHERE order_id IN (SELECT order_id FROM orders)
    """)
    deleted["payments"] = delete_if_table_exists(cur, "payments", """
        DELETE FROM payments WHERE order_id IN (SELECT order_id FROM orders)
    """)
    deleted["order_status_history"] = delete_if_table_exists(cur, "order_status_history", """
        DELETE FROM order_status_history WHERE order_id IN (SELECT order_id FROM orders)
    """)
    deleted["order_items"] = delete_if_table_exists(cur, "order_items", "DELETE FROM order_items")
    deleted["orders"] = delete_if_table_exists(cur, "orders", "DELETE FROM orders")
    return deleted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="perform the reset after preflight")
    args = parser.parse_args()

    with get_connection() as conn:
        with conn.cursor() as cur:
            discover_unknown_dependencies(cur)
            before = counts(cur)
            print("Order-domain reset preflight:")
            for table_name, row_count in before.items():
                print(f"  {table_name}: {row_count}")
            if not args.apply:
                print("Dry run only. Re-run with --apply to delete the scoped derived data.")
                return
            deleted = reset(cur)
        conn.commit()

    print("Reset complete:")
    for table_name, row_count in deleted.items():
        print(f"  {table_name}: {row_count} deleted")


if __name__ == "__main__":
    main()
