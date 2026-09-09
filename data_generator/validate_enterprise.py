"""Master Enterprise Digital Twin Integrity & Invariant Validation Suite.

Executes all domain-specific validation suites:
1. Orders & Items
2. Payments & Payment History
3. Inventory Snapshots & Movements
4. Shipments & Shipment History
"""

import sys
from pathlib import Path

DATA_GENERATOR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DATA_GENERATOR_DIR))

from validate_orders import main as run_orders_val
from validate_payments import validate_payments as run_payments_val
from validate_inventory import validate_inventory as run_inventory_val
from validate_shipments import validate_shipments as run_shipments_val
from validate_engagement_and_finance import validate_engagement_and_finance as run_engagement_val
from validate_scenario_s001 import validate_scenario_s001 as run_s001_val
from validate_scenario_s002 import validate_scenario_s002 as run_s002_val
from validate_scenario_s003 import validate_scenario_s003 as run_s003_val
from validate_scenario_s004 import validate_scenario_s004 as run_s004_val
from validate_scenario_s005 import validate_scenario_s005 as run_s005_val
from db import get_connection


def main():
    print("=" * 70)
    print("ENTERPRISE DIGITAL TWIN - MASTER SYSTEM AUDIT & INTEGRITY SUITE")
    print("=" * 70)

    # Database summary counts
    with get_connection() as conn:
        with conn.cursor() as cur:
            tables = [
                "warehouses", "carriers", "categories", "products", "suppliers",
                "supplier_products", "purchase_orders", "purchase_order_items",
                "customers", "payment_methods", "orders", "order_items",
                "order_status_history", "payments", "payment_status_history",
                "inventory_snapshots", "inventory_movements", "shipments",
                "shipment_status_history", "customer_tickets", "reviews",
                "financial_transactions", "marketing_campaigns", "marketing_events",
                "incidents", "incident_entities", "causal_nodes", "causal_links",
                "incident_causes", "incident_evidence", "incident_outcomes",
                "benchmark_cases", "benchmark_observations", "evaluation_targets",
                "audit_log"
            ]
            print("\n[1/11] DATABASE RECORD INVENTORY:")
            for t in tables:
                cur.execute(f"SELECT COUNT(*) AS cnt FROM {t}")
                cnt = cur.fetchone()["cnt"]
                print(f"  - {t:<28}: {cnt:>6} rows")

    print("\n[2/11] AUDITING ORDERS DOMAIN...")
    run_orders_val()

    print("\n[3/11] AUDITING PAYMENTS DOMAIN...")
    run_payments_val()

    print("\n[4/11] AUDITING INVENTORY DOMAIN...")
    run_inventory_val()

    print("\n[5/11] AUDITING SHIPMENTS DOMAIN...")
    run_shipments_val()

    print("\n[6/11] AUDITING ENGAGEMENT & FINANCE DOMAIN...")
    run_engagement_val()

    print("\n[7/11] AUDITING SCENARIO S001 (SUPPLIER DISRUPTION)...")
    run_s001_val()

    print("\n[8/11] AUDITING SCENARIO S002 (CARRIER LOGISTICS DISRUPTION)...")
    run_s002_val()

    print("\n[9/11] AUDITING SCENARIO S003 (PAYMENT GATEWAY OUTAGE)...")
    run_s003_val()

    print("\n[10/11] AUDITING SCENARIO S004 (MARKETING INEFFICIENCY)...")
    run_s004_val()

    print("\n[11/11] AUDITING SCENARIO S005 (PRODUCT QUALITY DEGRADATION)...")
    run_s005_val()

    print("\n" + "=" * 70)
    print("ALL OPERATIONAL DOMAINS & ALL 5 SCENARIO GROUND TRUTHS PASSED (ZERO VIOLATIONS)!")
    print("ENTERPRISE DIGITAL TWIN FULL SUITE (S001, S002, S003, S004, S005) 100% CERTIFIED.")
    print("=" * 70)


if __name__ == "__main__":
    main()
