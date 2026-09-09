"""Scenario S001 Generator: Supplier Disruption (Gián đoạn nhà cung cấp).

This module implements Scenario S001 for the Enterprise Digital Twin:
1. Procurement Baseline & Incident:
   - Generates ~60 baseline Purchase Orders across suppliers and warehouses (2025-2026).
   - Injects delayed Purchase Orders for supplier 'Viet Electronics' at 'Kho TP Hồ Chí Minh' in July 2026.
2. Operational Stockout Anomaly:
   - Injects 25 retail customer orders cancelled due to STOCKOUT between 2026-07-20 and 2026-08-05.
   - Injects 6 customer support tickets regarding out-of-stock cancellations.
3. Layer 5 (Incident Operational Metadata):
   - Surface incident registered in `incidents` with neutral summary.
   - Affected entities linked in `incident_entities`.
4. Layer 6 (Causal Ground Truth DAG):
   - 6 nodes (RootCause: Supply, Mechanism: Supply, OperationalImpact: Inventory,
     OperationalImpact: Fulfillment, OperationalImpact: Customer, Outcome: Finance).
   - 5 directed edges forming a strict acyclic DAG.
   - Primary root cause confirmed in `incident_causes`.
   - Decisive evidence in `incident_evidence`.
   - Quantified revenue loss and stockout days in `incident_outcomes`.
5. Layer 7 (Benchmark & Evaluation):
   - Benchmark test case with cutoff at 2026-07-30 00:00:00 UTC.
   - Allowlisted pre-cutoff observations.
   - Evaluation target rubrics.
6. Audit Log:
   - Audit trail recorded in `audit_log`.
"""

import os
import sys
import uuid
import random
import json
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Setup paths
DATA_GENERATOR_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATA_GENERATOR_DIR))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from db import get_connection
from config import SEED

S001_SEED = SEED + 1001
random.seed(S001_SEED)

SCENARIO_ID = "S001"
TARGET_SUPPLIER_NAME = "Viet Electronics"
TARGET_WAREHOUSE_NAME = "Kho TP Hồ Chí Minh"

INCIDENT_START = datetime(2026, 7, 1, 0, 0, 0, tzinfo=timezone.utc)
PO_ORDER_TIME = datetime(2026, 7, 3, 9, 0, 0, tzinfo=timezone.utc)
PO_EXPECTED_TIME = datetime(2026, 7, 14, 17, 0, 0, tzinfo=timezone.utc)
STOCKOUT_START = datetime(2026, 7, 20, 0, 0, 0, tzinfo=timezone.utc)
INCIDENT_DETECTED = datetime(2026, 7, 24, 10, 0, 0, tzinfo=timezone.utc)
INCIDENT_CUTOFF = datetime(2026, 7, 30, 0, 0, 0, tzinfo=timezone.utc)
INCIDENT_END = datetime(2026, 8, 10, 18, 0, 0, tzinfo=timezone.utc)


def money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def clean_existing_s001(conn):
    """Purge any existing S001 data for idempotency without touching baseline POs or other scenarios."""
    with conn.cursor() as cur:
        cur.execute("SELECT incident_id FROM incidents WHERE scenario_id = %s", (SCENARIO_ID,))
        row = cur.fetchone()
        if not row:
            return

        incident_id = row["incident_id"]
        print(f"Purging existing S001 data for incident {incident_id}...")

        # Benchmark layer
        cur.execute("""
            DELETE FROM evaluation_targets 
            WHERE benchmark_case_id IN (SELECT benchmark_case_id FROM benchmark_cases WHERE incident_id = %s)
        """, (incident_id,))
        cur.execute("""
            DELETE FROM benchmark_observations 
            WHERE benchmark_case_id IN (SELECT benchmark_case_id FROM benchmark_cases WHERE incident_id = %s)
        """, (incident_id,))
        cur.execute("DELETE FROM benchmark_cases WHERE incident_id = %s", (incident_id,))

        # Causal Ground Truth layer
        cur.execute("DELETE FROM incident_outcomes WHERE incident_id = %s", (incident_id,))
        cur.execute("DELETE FROM incident_evidence WHERE incident_id = %s", (incident_id,))
        cur.execute("DELETE FROM incident_causes WHERE incident_id = %s", (incident_id,))
        cur.execute("DELETE FROM causal_links WHERE incident_id = %s", (incident_id,))
        cur.execute("DELETE FROM causal_nodes WHERE incident_id = %s", (incident_id,))

        # Incident entities
        cur.execute("DELETE FROM incident_entities WHERE incident_id = %s", (incident_id,))

        # S001 retail orders
        cur.execute("SELECT object_id FROM audit_log WHERE action_type = 'INJECT_S001_ORDER'")
        injected_order_ids = [r["object_id"] for r in cur.fetchall()]

        if injected_order_ids:
            cur.execute("DELETE FROM customer_tickets WHERE order_id = ANY(%s)", (injected_order_ids,))
            cur.execute("""
                DELETE FROM payment_status_history 
                WHERE payment_id IN (SELECT payment_id FROM payments WHERE order_id = ANY(%s))
            """, (injected_order_ids,))
            cur.execute("DELETE FROM payments WHERE order_id = ANY(%s)", (injected_order_ids,))
            cur.execute("DELETE FROM order_status_history WHERE order_id = ANY(%s)", (injected_order_ids,))
            cur.execute("DELETE FROM order_items WHERE order_id = ANY(%s)", (injected_order_ids,))
            cur.execute("DELETE FROM orders WHERE order_id = ANY(%s)", (injected_order_ids,))

        # S001 delayed POs
        cur.execute("SELECT object_id FROM audit_log WHERE action_type = 'INJECT_S001_PO'")
        injected_po_ids = [r["object_id"] for r in cur.fetchall()]

        if injected_po_ids:
            cur.execute("DELETE FROM purchase_order_items WHERE purchase_order_id = ANY(%s)", (injected_po_ids,))
            cur.execute("DELETE FROM purchase_orders WHERE purchase_order_id = ANY(%s)", (injected_po_ids,))

        # Incident record
        cur.execute("DELETE FROM incidents WHERE incident_id = %s", (incident_id,))
        cur.execute("DELETE FROM audit_log WHERE action_type LIKE 'INJECT_%' AND (metadata->>'scenario_id' = %s OR object_id = %s)", (SCENARIO_ID, incident_id))
        print("Previous S001 data successfully purged.")


def generate_baseline_pos(conn, rng):
    """Generate baseline Purchase Orders if none exist."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM purchase_orders")
        existing_pos = cur.fetchone()["cnt"]
        if existing_pos > 0:
            print(f"Procurement domain already contains {existing_pos} baseline POs. Skipping baseline generation.")
            return

        print("Generating 60 baseline Purchase Orders across 2025-2026...")
        cur.execute("SELECT supplier_id, average_lead_time_days FROM suppliers WHERE status = 'Active'")
        suppliers = cur.fetchall()

        cur.execute("SELECT warehouse_id FROM warehouses WHERE status = 'Active'")
        warehouses = [r["warehouse_id"] for r in cur.fetchall()]

        cur.execute("SELECT supplier_id, product_id, unit_cost FROM supplier_products WHERE status = 'Active'")
        sp_rows = cur.fetchall()
        supplier_prods = {}
        for sp in sp_rows:
            supplier_prods.setdefault(sp["supplier_id"], []).append(sp)

        start_date = datetime(2025, 1, 15, tzinfo=timezone.utc)
        end_date = datetime(2026, 7, 1, tzinfo=timezone.utc)
        time_span = int((end_date - start_date).total_seconds())

        po_records = []
        po_item_records = []

        for i in range(60):
            po_id = uuid.uuid4()
            sup = rng.choice(suppliers)
            sup_id = sup["supplier_id"]
            lead_days = float(sup["average_lead_time_days"])
            wh_id = rng.choice(warehouses)

            po_time = start_date + timedelta(seconds=rng.randint(0, time_span))
            exp_delivery = po_time + timedelta(days=lead_days * rng.uniform(0.9, 1.1))
            # Normal completed PO: delivered within minor variance
            rec_time = exp_delivery + timedelta(days=rng.uniform(-1.0, 1.5))
            po_status = "Received"

            prods = supplier_prods.get(sup_id, [])
            if not prods:
                continue

            item_count = rng.randint(2, min(4, len(prods)))
            selected_items = rng.sample(prods, item_count)

            po_total = Decimal("0.00")
            for sp in selected_items:
                poi_id = uuid.uuid4()
                p_id = sp["product_id"]
                cost = money(sp["unit_cost"])
                qty = Decimal(rng.randint(50, 200))
                line_total = money(qty * cost)
                po_total += line_total

                po_item_records.append((
                    poi_id, po_id, p_id, qty, qty, cost, line_total
                ))

            po_records.append((
                po_id, sup_id, wh_id, po_time, exp_delivery, rec_time,
                po_status, po_total, "VND"
            ))

        cur.executemany("""
            INSERT INTO purchase_orders (
                purchase_order_id, supplier_id, warehouse_id, order_timestamp,
                expected_delivery_timestamp, received_timestamp, po_status,
                total_amount, currency_code
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, po_records)

        cur.executemany("""
            INSERT INTO purchase_order_items (
                purchase_order_item_id, purchase_order_id, product_id,
                ordered_quantity, received_quantity, unit_cost, item_total
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, po_item_records)

        print(f"Generated {len(po_records)} baseline POs and {len(po_item_records)} line items.")


def inject_s001():
    with get_connection() as conn:
        with conn.cursor() as cur:
            clean_existing_s001(conn)

            rng = random.Random(S001_SEED)

            # Ensure baseline POs exist
            generate_baseline_pos(conn, rng)

            # 1. Fetch Target Entities
            cur.execute("SELECT supplier_id, average_lead_time_days FROM suppliers WHERE supplier_name = %s", (TARGET_SUPPLIER_NAME,))
            sup_row = cur.fetchone()
            if not sup_row:
                raise RuntimeError(f"Supplier '{TARGET_SUPPLIER_NAME}' not found.")
            supplier_id = sup_row["supplier_id"]

            cur.execute("SELECT warehouse_id FROM warehouses WHERE warehouse_name = %s", (TARGET_WAREHOUSE_NAME,))
            wh_row = cur.fetchone()
            if not wh_row:
                raise RuntimeError(f"Warehouse '{TARGET_WAREHOUSE_NAME}' not found.")
            warehouse_id = wh_row["warehouse_id"]

            # Fetch Viet Electronics products
            cur.execute("""
                SELECT sp.product_id, sp.unit_cost, p.unit_price, p.product_name 
                FROM supplier_products sp
                JOIN products p ON sp.product_id = p.product_id
                WHERE sp.supplier_id = %s
                ORDER BY p.product_name
            """, (supplier_id,))
            target_prods = cur.fetchall()

            # Select 3 key monitor SKUs
            monitor_prods = [p for p in target_prods if "Monitor" in p["product_name"]][:3]
            if not monitor_prods:
                monitor_prods = target_prods[:3]

            print(f"Target Supplier: {TARGET_SUPPLIER_NAME} ({supplier_id})")
            print(f"Target Warehouse: {TARGET_WAREHOUSE_NAME} ({warehouse_id})")
            print(f"Target Products: {[p['product_name'] for p in monitor_prods]}")

            # 2. Inject S001 Delayed Purchase Orders
            # PO 1: Placed 2026-07-03, Expected 2026-07-14, STILL 'Ordered' (overdue!)
            po1_id = uuid.uuid4()
            po1_items = []
            po1_total = Decimal("0.00")

            for p in monitor_prods:
                poi_id = uuid.uuid4()
                qty = Decimal("250.0")
                cost = money(p["unit_cost"])
                line_tot = money(qty * cost)
                po1_total += line_tot
                po1_items.append((
                    poi_id, po1_id, p["product_id"], qty, Decimal("0.0"), cost, line_tot
                ))

            # PO 2: Placed 2026-07-10, Expected 2026-07-21, STILL 'Ordered' (overdue!)
            po2_id = uuid.uuid4()
            po2_items = []
            po2_total = Decimal("0.00")

            for p in monitor_prods:
                poi_id = uuid.uuid4()
                qty = Decimal("200.0")
                cost = money(p["unit_cost"])
                line_tot = money(qty * cost)
                po2_total += line_tot
                po2_items.append((
                    poi_id, po2_id, p["product_id"], qty, Decimal("0.0"), cost, line_tot
                ))

            delayed_pos = [
                (po1_id, supplier_id, warehouse_id, PO_ORDER_TIME, PO_EXPECTED_TIME, None, "Ordered", po1_total, "VND"),
                (po2_id, supplier_id, warehouse_id, datetime(2026, 7, 10, 10, 0, 0, tzinfo=timezone.utc), datetime(2026, 7, 21, 17, 0, 0, tzinfo=timezone.utc), None, "Ordered", po2_total, "VND"),
            ]

            cur.executemany("""
                INSERT INTO purchase_orders (
                    purchase_order_id, supplier_id, warehouse_id, order_timestamp,
                    expected_delivery_timestamp, received_timestamp, po_status,
                    total_amount, currency_code
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, delayed_pos)

            cur.executemany("""
                INSERT INTO purchase_order_items (
                    purchase_order_item_id, purchase_order_id, product_id,
                    ordered_quantity, received_quantity, unit_cost, item_total
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, po1_items + po2_items)

            # Record audit log for POs
            for po in delayed_pos:
                cur.execute("""
                    INSERT INTO audit_log (
                        audit_log_id, event_timestamp, actor_role,
                        action_type, object_type, object_id, success, metadata
                    ) VALUES (
                        gen_random_uuid(), %s, 'edt_simulator',
                        'INJECT_S001_PO', 'PurchaseOrder', %s, true,
                        jsonb_build_object('scenario_id', 'S001')
                    )
                """, (po[3], po[0]))

            # 3. Inject Retail Anomaly (25 Cancelled Orders due to Stockout)
            cur.execute("SELECT customer_id, customer_segment FROM customers WHERE status = 'Active'")
            customers = cur.fetchall()

            cur.execute("SELECT payment_method_id FROM payment_methods WHERE status = 'Active'")
            payment_methods = [r["payment_method_id"] for r in cur.fetchall()]

            retail_orders = []
            retail_order_items = []
            retail_order_history = []
            retail_payments = []
            retail_payment_history = []
            retail_tickets = []

            total_stockout_revenue_loss = Decimal("0.00")

            stockout_span_sec = int((INCIDENT_END - STOCKOUT_START).total_seconds())

            for i in range(25):
                order_id = uuid.uuid4()
                cust = rng.choice(customers)
                customer_id = cust["customer_id"]
                cust_seg = cust["customer_segment"]
                pay_method_id = rng.choice(payment_methods)

                offset_sec = int(stockout_span_sec * ((i + rng.uniform(0.1, 0.9)) / 25))
                order_time = STOCKOUT_START + timedelta(seconds=offset_sec)

                # Order contains 1 of the out-of-stock monitor products
                p = rng.choice(monitor_prods)
                p_id = p["product_id"]
                price = money(p["unit_price"])
                qty = Decimal(rng.choice([1, 2]))
                gross = money(qty * price)
                disc = money(gross * Decimal("0.05")) if cust_seg == "VIP" else Decimal("0.00")
                item_tot = money(gross - disc)

                item_id = uuid.uuid4()
                retail_order_items.append((
                    item_id, order_id, p_id, qty, price, disc, item_tot
                ))

                order_discount = Decimal("0.00")
                shipping_fee = Decimal("0.00")  # cancelled orders have 0 shipping fee
                total_amount = item_tot
                total_stockout_revenue_loss += total_amount

                retail_orders.append((
                    order_id, customer_id, warehouse_id, order_time,
                    "Website", "Cancelled", item_tot, order_discount,
                    shipping_fee, total_amount, "VND"
                ))

                # Lifecycle: Pending -> Cancelled (STOCKOUT)
                hist_pending_id = uuid.uuid4()
                retail_order_history.append((
                    hist_pending_id, order_id, "Pending", order_time, "System", "ORDER_PLACED"
                ))

                cancel_time = order_time + timedelta(minutes=rng.randint(10, 30))
                hist_cancel_id = uuid.uuid4()
                retail_order_history.append((
                    hist_cancel_id, order_id, "Cancelled", cancel_time, "System", "OUT_OF_STOCK"
                ))

                # Payment: Initiated -> Failed
                payment_id = uuid.uuid4()
                pay_init_time = order_time + timedelta(minutes=2)
                pay_fail_time = cancel_time

                retail_payments.append((
                    payment_id, order_id, pay_method_id, pay_fail_time,
                    total_amount, "VND", "Failed", f"STK-CANCEL-{order_id}"
                ))

                psh_init_id = uuid.uuid4()
                retail_payment_history.append((
                    psh_init_id, payment_id, "Initiated", pay_init_time, None
                ))

                psh_fail_id = uuid.uuid4()
                retail_payment_history.append((
                    psh_fail_id, payment_id, "Failed", pay_fail_time, "ORDER_CANCELLED_STOCKOUT"
                ))

                # Customer Support Tickets (6 tickets)
                if len(retail_tickets) < 6 and rng.random() < 0.35:
                    ticket_id = uuid.uuid4()
                    ticket_time = cancel_time + timedelta(minutes=rng.randint(15, 60))
                    retail_tickets.append((
                        ticket_id, customer_id, order_id, ticket_time, None,
                        "Order", "High", "Open", None, None
                    ))

            # Batch insert retail records
            cur.executemany("""
                INSERT INTO orders (
                    order_id, customer_id, warehouse_id, order_timestamp,
                    channel, order_status, subtotal, discount_amount,
                    shipping_fee, total_amount, currency_code
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, retail_orders)

            cur.executemany("""
                INSERT INTO order_items (
                    order_item_id, order_id, product_id, quantity,
                    unit_price, discount_amount, item_total
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, retail_order_items)

            cur.executemany("""
                INSERT INTO order_status_history (
                    order_status_history_id, order_id, status,
                    status_timestamp, actor_type, reason_code
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, retail_order_history)

            cur.executemany("""
                INSERT INTO payments (
                    payment_id, order_id, payment_method_id, payment_timestamp,
                    amount, currency_code, payment_status, provider_transaction_ref
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, retail_payments)

            cur.executemany("""
                INSERT INTO payment_status_history (
                    payment_status_history_id, payment_id, status,
                    status_timestamp, failure_code
                ) VALUES (%s, %s, %s, %s, %s)
            """, retail_payment_history)

            cur.executemany("""
                INSERT INTO customer_tickets (
                    ticket_id, customer_id, order_id, created_at,
                    resolved_at, category, priority, status,
                    resolution_time_hours, satisfaction_score
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, retail_tickets)

            for o in retail_orders:
                cur.execute("""
                    INSERT INTO audit_log (
                        audit_log_id, event_timestamp, actor_role,
                        action_type, object_type, object_id, success, metadata
                    ) VALUES (
                        gen_random_uuid(), %s, 'edt_simulator',
                        'INJECT_S001_ORDER', 'Order', %s, true,
                        jsonb_build_object('scenario_id', 'S001')
                    )
                """, (o[3], o[0]))

            print(f"Injected 25 stockout cancelled orders ({total_stockout_revenue_loss:,.2f} VND loss), {len(retail_tickets)} tickets.")

            # 4. Layer 5 — Incident & Safe Observation
            incident_id = uuid.uuid4()
            neutral_summary = (
                "Hệ thống giám sát ghi nhận số lượng đơn hàng bị hủy do thiếu hàng tồn kho (Stockout) "
                "tăng đột biến tại Kho TP. Hồ Chí Minh trong tháng 07/2026 đối với các dòng thiết bị màn hình, "
                "đồng thời ghi nhận sự chậm trễ trong các lô hàng nhập kho từ chuỗi cung ứng."
            )

            cur.execute("""
                INSERT INTO incidents (
                    incident_id, scenario_id, detected_at, start_time, end_time,
                    severity, affected_domain, status, summary
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
            """, (
                incident_id, SCENARIO_ID, INCIDENT_DETECTED, INCIDENT_START, INCIDENT_END,
                "Critical", "Supply", "Closed", neutral_summary
            ))

            # Incident entities
            entities_data = [
                (uuid.uuid4(), incident_id, "Supplier", supplier_id, INCIDENT_DETECTED, "SUPPLIER_DISRUPTION_SOURCE", Decimal("1.0000")),
                (uuid.uuid4(), incident_id, "Warehouse", warehouse_id, INCIDENT_DETECTED, "STOCKOUT_FACILITY", Decimal("0.8500")),
                (uuid.uuid4(), incident_id, "PurchaseOrder", po1_id, INCIDENT_DETECTED, "OVERDUE_REPLENISHMENT_PO", Decimal("0.9500")),
            ]
            cur.executemany("""
                INSERT INTO incident_entities (
                    incident_entity_id, incident_id, entity_type, entity_id,
                    observed_at, impact_type, impact_severity
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, entities_data)

            # 5. Layer 6 — Causal Ground Truth DAG
            node1_id = uuid.uuid4()  # RootCause (Supply)
            node2_id = uuid.uuid4()  # Mechanism (Supply)
            node3_id = uuid.uuid4()  # OperationalImpact (Inventory)
            node4_id = uuid.uuid4()  # OperationalImpact (Fulfillment)
            node5_id = uuid.uuid4()  # OperationalImpact (Customer)
            node6_id = uuid.uuid4()  # Outcome (Finance)

            nodes_data = [
                (
                    node1_id, incident_id, "RootCause", "Supply",
                    "Supplier", supplier_id, INCIDENT_START, INCIDENT_END,
                    "Gián đoạn hoạt động nhà cung cấp Viet Electronics (Đình trệ sản xuất)",
                    "Nhà cung cấp Viet Electronics gặp sự cố đứt gãy nguồn cung linh kiện bán dẫn và đình trệ dây chuyền sản xuất thiết bị màn hình."
                ),
                (
                    node2_id, incident_id, "Mechanism", "Supply",
                    "PurchaseOrder", po1_id, PO_EXPECTED_TIME, INCIDENT_END,
                    "Đơn đặt hàng mua (Purchase Orders) bị trễ hạn giao hàng nghiêm trọng",
                    "Đơn đặt hàng bổ sung PO-1 và PO-2 cho Kho TP. Hồ Chí Minh không được giao đúng hạn cam kết (vượt lead time hợp đồng 11 ngày)."
                ),
                (
                    node3_id, incident_id, "OperationalImpact", "Inventory",
                    "Warehouse", warehouse_id, STOCKOUT_START, INCIDENT_END,
                    "Cạn kiệt tồn kho an toàn (Stockout) tại Kho TP. Hồ Chí Minh",
                    "Do không có hàng nhập kho bổ sung, mức tồn kho khả dụng của các dòng sản phẩm màn hình tại Kho TP. Hồ Chí Minh giảm về 0."
                ),
                (
                    node4_id, incident_id, "OperationalImpact", "Fulfillment",
                    None, None, STOCKOUT_START + timedelta(days=2), INCIDENT_END,
                    "Đơn hàng bán lẻ của khách hàng bị hủy tự động do hết hàng tồn kho",
                    "Hệ thống bán lẻ tự động hủy 25 đơn hàng của người tiêu dùng do không đủ tồn kho để đóng gói và vận chuyển."
                ),
                (
                    node5_id, incident_id, "OperationalImpact", "Customer",
                    None, None, STOCKOUT_START + timedelta(days=3), INCIDENT_END,
                    "Gia tăng khiếu nại của khách hàng về tình trạng hết hàng và hủy đơn",
                    "Khách hàng phàn nàn và gửi ticket yêu cầu giải thích về lý do đơn hàng màn hình bị hủy đơn phương sau khi đặt."
                ),
                (
                    node6_id, incident_id, "Outcome", "Finance",
                    None, None, INCIDENT_START, INCIDENT_END,
                    "Tổn thất doanh thu bán lẻ trực tiếp do thiếu hụt nguồn cung",
                    f"Doanh thu bị thất thoát trực tiếp từ 25 đơn hàng bán lẻ bị hủy đạt {total_stockout_revenue_loss:,.2f} VND."
                ),
            ]

            cur.executemany("""
                INSERT INTO causal_nodes (
                    node_id, incident_id, node_type, domain,
                    entity_type, entity_id, valid_from, valid_to,
                    truth_label, truth_description
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, nodes_data)

            # Causal Links (Acyclic DAG)
            links_data = [
                (uuid.uuid4(), incident_id, node1_id, node2_id, "Causes", Decimal("2880.0"), Decimal("0.9800")),
                (uuid.uuid4(), incident_id, node2_id, node3_id, "Causes", Decimal("7200.0"), Decimal("0.9500")),
                (uuid.uuid4(), incident_id, node3_id, node4_id, "Causes", Decimal("2880.0"), Decimal("0.9200")),
                (uuid.uuid4(), incident_id, node3_id, node5_id, "Amplifies", Decimal("4320.0"), Decimal("0.8500")),
                (uuid.uuid4(), incident_id, node4_id, node6_id, "Causes", Decimal("1440.0"), Decimal("0.9500")),
            ]

            cur.executemany("""
                INSERT INTO causal_links (
                    causal_link_id, incident_id, cause_node_id, effect_node_id,
                    relationship_type, lag_minutes, confidence
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, links_data)

            # Primary Cause
            cur.execute("""
                INSERT INTO incident_causes (
                    incident_cause_id, incident_id, node_id,
                    cause_rank, is_primary, confirmed_at
                ) VALUES (
                    gen_random_uuid(), %s, %s,
                    1, true, %s
                )
            """, (incident_id, node1_id, INCIDENT_END + timedelta(hours=1)))

            # Decisive Evidence
            evidence_data = [
                (
                    uuid.uuid4(), incident_id, node2_id, "Record",
                    "purchase_orders", po1_id, PO_EXPECTED_TIME + timedelta(days=2),
                    "Đơn đặt hàng PO với nhà cung cấp Viet Electronics quá hạn giao hàng dự kiến nhưng trạng thái vẫn là Ordered (chưa nhập kho).",
                    True
                ),
                (
                    uuid.uuid4(), incident_id, node3_id, "Metric",
                    None, None, STOCKOUT_START,
                    "Mức tồn kho khả dụng của các sản phẩm màn hình chính tại Kho TP. Hồ Chí Minh giảm về mức 0.",
                    True
                ),
                (
                    uuid.uuid4(), incident_id, node4_id, "Record",
                    "orders", retail_orders[0][0], retail_orders[0][3],
                    "Đơn hàng bán lẻ bị hủy với lý do OUT_OF_STOCK sau khi kho hết hàng.",
                    False
                ),
            ]

            cur.executemany("""
                INSERT INTO incident_evidence (
                    incident_evidence_id, incident_id, node_id, evidence_type,
                    source_table, source_record_id, evidence_timestamp,
                    evidence_summary, is_decisive
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, evidence_data)

            # Incident Outcomes
            outcomes_data = [
                (
                    uuid.uuid4(), incident_id, node6_id, "RevenueLoss",
                    INCIDENT_END + timedelta(hours=1), "stockout_revenue_loss",
                    total_stockout_revenue_loss, total_stockout_revenue_loss, "VND"
                ),
                (
                    uuid.uuid4(), incident_id, node3_id, "Stockout",
                    INCIDENT_END + timedelta(hours=1), "stockout_duration_days",
                    Decimal("16.0000"), None, None
                ),
            ]

            cur.executemany("""
                INSERT INTO incident_outcomes (
                    incident_outcome_id, incident_id, node_id, outcome_type,
                    measured_at, metric_name, metric_value,
                    financial_impact, currency_code
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, outcomes_data)

            # 6. Layer 7 — Benchmark & Evaluation
            case_id = uuid.uuid4()
            case_name = "BENCHMARK-S001-SUPPLIER-VIET-ELEC-20260724"

            cur.execute("""
                INSERT INTO benchmark_cases (
                    benchmark_case_id, incident_id, case_name, split,
                    observation_start_time, observation_cutoff_time,
                    created_at, status
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s,
                    CURRENT_TIMESTAMP, 'Active'
                )
            """, (
                case_id, incident_id, case_name, "Test",
                datetime(2026, 7, 1, 0, 0, 0, tzinfo=timezone.utc),
                INCIDENT_CUTOFF
            ))

            # Benchmark Observations (strictly before cutoff 2026-07-30)
            observations_data = []
            # Injected delayed POs
            for po in delayed_pos:
                if po[3] <= INCIDENT_CUTOFF:
                    observations_data.append((
                        uuid.uuid4(), case_id, "purchase_orders", po[0], po[3], "Signal"
                    ))

            # Cancelled retail orders before cutoff
            for o in retail_orders:
                if o[3] <= INCIDENT_CUTOFF:
                    observations_data.append((
                        uuid.uuid4(), case_id, "orders", o[0], o[3], "Signal"
                    ))

            for t in retail_tickets:
                if t[3] <= INCIDENT_CUTOFF:
                    observations_data.append((
                        uuid.uuid4(), case_id, "customer_tickets", t[0], t[3], "Context"
                    ))

            cur.executemany("""
                INSERT INTO benchmark_observations (
                    benchmark_observation_id, benchmark_case_id, source_table,
                    source_record_id, observed_at, observation_role
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, observations_data)

            # Evaluation Targets
            targets_data = [
                (
                    uuid.uuid4(), case_id, "RootCause",
                    json.dumps({
                        "primary_root_cause": "SupplierDisruption",
                        "domain": "Supply",
                        "affected_supplier": TARGET_SUPPLIER_NAME,
                        "expected_keywords": ["Viet Electronics", "supplier", "nhà cung cấp", "đứt gãy cung ứng", "chậm giao hàng", "sản xuất", "mua hàng"]
                    }),
                    node1_id, Decimal("0.3000")
                ),
                (
                    uuid.uuid4(), case_id, "CausalPath",
                    json.dumps({
                        "required_nodes": ["RootCause", "Mechanism", "OperationalImpact", "Outcome"],
                        "causal_sequence": [
                            ["SupplierDisruption", "PODeliveryDelay"],
                            ["PODeliveryDelay", "WarehouseStockout"],
                            ["WarehouseStockout", "OrderCancellation"],
                            ["OrderCancellation", "RevenueLoss"]
                        ]
                    }),
                    None, Decimal("0.2500")
                ),
                (
                    uuid.uuid4(), case_id, "AffectedEntity",
                    json.dumps({
                        "entity_type": "Supplier",
                        "entity_name": TARGET_SUPPLIER_NAME,
                        "entity_id": str(supplier_id)
                    }),
                    node1_id, Decimal("0.1500")
                ),
                (
                    uuid.uuid4(), case_id, "Outcome",
                    json.dumps({
                        "metric_name": "stockout_revenue_loss",
                        "expected_value": float(total_stockout_revenue_loss),
                        "tolerance_percent": 0.20,
                        "currency": "VND"
                    }),
                    node6_id, Decimal("0.1500")
                ),
                (
                    uuid.uuid4(), case_id, "RecommendedAction",
                    json.dumps({
                        "recommended_actions": [
                            "Kích hoạt nhà cung cấp dự phòng (Secondary Supplier) cho các sản phẩm màn hình",
                            "Điều chuyển hàng tồn kho từ Kho Hà Nội hoặc Kho Đà Nẵng về Kho TP. Hồ Chí Minh",
                            "Cập nhật tăng Lead Time cam kết của Viet Electronics trong hệ thống quản trị cung ứng",
                            "Gửi thông báo xin lỗi và phiếu giảm giá cho các khách hàng có đơn hàng bị hủy do hết hàng"
                        ]
                    }),
                    None, Decimal("0.1500")
                ),
            ]

            cur.executemany("""
                INSERT INTO evaluation_targets (
                    evaluation_target_id, benchmark_case_id, target_type,
                    target_value, causal_node_id, scoring_weight
                ) VALUES (%s, %s, %s, %s::jsonb, %s, %s)
            """, targets_data)

            # Audit log for scenario injection
            audit_meta = json.dumps({
                "scenario_id": SCENARIO_ID,
                "case_name": case_name,
                "delayed_pos": len(delayed_pos),
                "stockout_orders": len(retail_orders),
                "revenue_loss": float(total_stockout_revenue_loss),
            })
            cur.execute("""
                INSERT INTO audit_log (
                    audit_log_id, event_timestamp, actor_role,
                    action_type, object_type, object_id, success, metadata
                ) VALUES (
                    gen_random_uuid(), CURRENT_TIMESTAMP, 'edt_simulator',
                    'INJECT_INCIDENT', 'Incident', %s, true, %s::jsonb
                )
            """, (incident_id, audit_meta))

        conn.commit()
        print("=" * 70)
        print("SCENARIO S001 INJECTION COMPLETED SUCCESSFULLY!")
        print(f"Incident ID: {incident_id}")
        print(f"Benchmark Case: {case_name}")
        print(f"Delayed POs Injected: {len(delayed_pos)}")
        print(f"Stockout Retail Orders: {len(retail_orders)} (Loss: {total_stockout_revenue_loss:,.2f} VND)")
        print(f"Customer Tickets: {len(retail_tickets)}")
        print(f"Benchmark Observations: {len(observations_data)}")
        print(f"Causal Nodes: {len(nodes_data)} | Links: {len(links_data)} | Targets: {len(targets_data)}")
        print("=" * 70)


if __name__ == "__main__":
    inject_s001()
