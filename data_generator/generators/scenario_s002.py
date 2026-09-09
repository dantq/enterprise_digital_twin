"""Scenario S002 Generator: Logistics / Carrier Disruption (Gián đoạn vận chuyển).

This module injects Scenario S002 into the Enterprise Digital Twin:
1. Operational Anomaly:
   - Logistics partner 'GHN' suffers depot congestion and fleet bottleneck in Southern Hub.
   - 25 shipments handled by GHN during August 18-25, 2026 experience severe transit delays (average 9.5 days vs baseline 2.5 days).
   - 8 Customer Support Tickets created under category 'Delivery' with high priority.
   - 10 Customer Reviews with 1-star rating and negative sentiment citing late delivery.
   - Financial compensation transactions recorded.
2. Layer 5 (Incident Operational Metadata):
   - incidents: Surface incident registered with neutral summary.
   - incident_entities: Affected carrier entity (GHN).
3. Layer 6 (Causal Ground Truth DAG):
   - causal_nodes: 5 nodes (RootCause, Mechanism, OperationalImpact x2, Outcome).
   - causal_links: 4 directed causal edges forming a strict DAG.
   - incident_causes: Primary root cause confirmed.
   - incident_evidence: Decisive shipment delay records.
   - incident_outcomes: Quantified logistics compensation and customer retention loss.
4. Layer 7 (Benchmark & Evaluation):
   - benchmark_cases: Active test case with cutoff at 2026-08-23.
   - benchmark_observations: Allowlisted pre-cutoff operational signals.
   - evaluation_targets: Ground truth rubrics for AI Analyst evaluation.
5. Infrastructure:
   - audit_log: Injection audit trail.
"""

import os
import sys
import uuid
import random
import json
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA_GENERATOR_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATA_GENERATOR_DIR))

from db import get_connection
from config import SEED

S002_SEED = SEED + 2002
random.seed(S002_SEED)

SCENARIO_ID = "S002"
CARRIER_NAME = "GHN"

INCIDENT_START = datetime(2026, 8, 18, 1, 0, 0, tzinfo=timezone.utc)    # 08:00 ICT
INCIDENT_DETECTED = datetime(2026, 8, 20, 3, 0, 0, tzinfo=timezone.utc) # 10:00 ICT
INCIDENT_CUTOFF = datetime(2026, 8, 23, 0, 0, 0, tzinfo=timezone.utc)   # 07:00 ICT
INCIDENT_END = datetime(2026, 8, 25, 11, 0, 0, tzinfo=timezone.utc)     # 18:00 ICT


def money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def clean_existing_s002(conn):
    """Cleanly purge any previously injected S002 data for idempotency."""
    with conn.cursor() as cur:
        cur.execute("SELECT incident_id FROM incidents WHERE scenario_id = %s", (SCENARIO_ID,))
        row = cur.fetchone()
        if not row:
            return

        incident_id = row["incident_id"]
        print(f"Purging existing S002 data for incident {incident_id}...")

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

        # Operational records tagged by audit_log
        cur.execute("SELECT object_id FROM audit_log WHERE action_type = 'INJECT_S002_ORDER'")
        injected_order_ids = [r["object_id"] for r in cur.fetchall()]

        if injected_order_ids:
            cur.execute("DELETE FROM financial_transactions WHERE order_id = ANY(%s)", (injected_order_ids,))
            cur.execute("DELETE FROM reviews WHERE order_id = ANY(%s)", (injected_order_ids,))
            cur.execute("DELETE FROM customer_tickets WHERE order_id = ANY(%s)", (injected_order_ids,))
            cur.execute("""
                DELETE FROM shipment_status_history 
                WHERE shipment_id IN (SELECT shipment_id FROM shipments WHERE order_id = ANY(%s))
            """, (injected_order_ids,))
            cur.execute("DELETE FROM shipments WHERE order_id = ANY(%s)", (injected_order_ids,))
            cur.execute("""
                DELETE FROM payment_status_history 
                WHERE payment_id IN (SELECT payment_id FROM payments WHERE order_id = ANY(%s))
            """, (injected_order_ids,))
            cur.execute("DELETE FROM payments WHERE order_id = ANY(%s)", (injected_order_ids,))
            cur.execute("DELETE FROM order_status_history WHERE order_id = ANY(%s)", (injected_order_ids,))
            cur.execute("DELETE FROM order_items WHERE order_id = ANY(%s)", (injected_order_ids,))
            cur.execute("DELETE FROM orders WHERE order_id = ANY(%s)", (injected_order_ids,))

        # Delete incident itself
        cur.execute("DELETE FROM incidents WHERE incident_id = %s", (incident_id,))
        cur.execute("DELETE FROM audit_log WHERE action_type LIKE 'INJECT_%%' AND (metadata->>'scenario_id' = %s OR object_id = %s)", (SCENARIO_ID, incident_id))
        print("Previous S002 data successfully purged.")


def inject_s002():
    with get_connection() as conn:
        with conn.cursor() as cur:
            clean_existing_s002(conn)

            # 1. Fetch reference entities
            cur.execute("SELECT carrier_id, carrier_name FROM carriers WHERE carrier_name = %s", (CARRIER_NAME,))
            carrier = cur.fetchone()
            if not carrier:
                raise RuntimeError(f"Carrier '{CARRIER_NAME}' not found in database!")
            carrier_id = carrier["carrier_id"]

            cur.execute("SELECT warehouse_id FROM warehouses WHERE warehouse_name LIKE '%Hồ Chí Minh%' LIMIT 1")
            wh = cur.fetchone()
            warehouse_id = wh["warehouse_id"]

            cur.execute("SELECT customer_id FROM customers WHERE status = 'Active'")
            customers = [r["customer_id"] for r in cur.fetchall()]

            cur.execute("SELECT product_id, unit_price, unit_cost FROM products WHERE status = 'Active'")
            products = cur.fetchall()

            cur.execute("SELECT payment_method_id FROM payment_methods WHERE method_name = 'COD' LIMIT 1")
            pm_row = cur.fetchone()
            payment_method_id = pm_row["payment_method_id"]

            # 2. Generate 25 delayed shipments and orders for GHN
            created_orders = []
            created_order_items = []
            created_order_history = []
            created_payments = []
            created_payment_history = []
            created_shipments = []
            created_shipment_history = []
            created_tickets = []
            created_reviews = []
            created_fin_txns = []

            total_compensation_loss = Decimal("185000000.00")
            per_order_compensation = money(total_compensation_loss / Decimal("25"))

            rng = random.Random(S002_SEED)

            for i in range(25):
                order_id = uuid.uuid4()
                customer_id = rng.choice(customers)
                # Ensure orders and shipments fall evenly within the 7-day incident window
                hours_offset = (i * 6) + rng.randint(0, 8)
                order_time = INCIDENT_START + timedelta(hours=hours_offset)
                shipped_time = order_time + timedelta(hours=rng.randint(6, 14))

                subtotal = Decimal("0.00")
                selected_prods = rng.sample(products, rng.randint(1, 3))

                for p in selected_prods:
                    oi_id = uuid.uuid4()
                    qty = rng.randint(1, 2)
                    price = money(p["unit_price"])
                    itotal = money(price * qty)
                    subtotal += itotal
                    created_order_items.append((
                        oi_id, order_id, p["product_id"], qty, price, Decimal("0.00"), itotal
                    ))

                shipping_fee = Decimal("35000.00")
                total_amount = subtotal + shipping_fee

                # Delay transit: 8 to 12 days (severe delay compared to standard 2 days)
                transit_days = rng.randint(8, 12)
                deliv_time = shipped_time + timedelta(days=transit_days)
                is_delivered = deliv_time <= (INCIDENT_END + timedelta(days=5))
                order_status = "Delivered" if is_delivered else "Shipped"

                created_orders.append((
                    order_id, customer_id, warehouse_id, order_time,
                    "Mobile App", order_status, subtotal, Decimal("0.00"),
                    shipping_fee, total_amount, "VND"
                ))

                # Order history
                created_order_history.append((
                    uuid.uuid4(), order_id, "Pending", order_time, "Customer", None
                ))
                paid_time = order_time + timedelta(minutes=15)
                created_order_history.append((
                    uuid.uuid4(), order_id, "Paid", paid_time, "System", "PAYMENT_CONFIRMED"
                ))
                created_order_history.append((
                    uuid.uuid4(), order_id, "Shipped", shipped_time, "Staff", "PICKED_AND_PACKED"
                ))
                if is_delivered:
                    created_order_history.append((
                        uuid.uuid4(), order_id, "Delivered", deliv_time, "Carrier", "DELIVERED_LATE"
                    ))

                # Payment
                payment_id = uuid.uuid4()
                created_payments.append((
                    payment_id, order_id, payment_method_id, paid_time,
                    total_amount, "VND", "Captured", f"TXN-S002-{i:03d}"
                ))
                created_payment_history.append((
                    uuid.uuid4(), payment_id, "Captured", paid_time, None
                ))

                # Shipment
                shipment_id = uuid.uuid4()
                tracking_no = f"GHN-S002-{i:05d}"
                est_delivery = shipped_time + timedelta(days=2) # standard lead time is 2 days
                act_delivery = deliv_time if is_delivered else None
                shipment_status = "Delivered" if is_delivered else "InTransit"

                created_shipments.append((
                    shipment_id, order_id, warehouse_id, carrier_id,
                    shipped_time, est_delivery, act_delivery,
                    shipment_status, tracking_no
                ))

                # Shipment status history showing depot delay
                created_shipment_history.append((
                    uuid.uuid4(), shipment_id, "PickedUp", shipped_time, "Kho TP. Hồ Chí Minh", "Kiện hàng đã lấy"
                ))
                stuck_time = shipped_time + timedelta(hours=24)
                created_shipment_history.append((
                    uuid.uuid4(), shipment_id, "InTransit", stuck_time, "Bưu cục Trung tâm Miền Nam", "Tồn đọng bưu cục: Quá tải điều phối"
                ))
                if is_delivered:
                    created_shipment_history.append((
                        uuid.uuid4(), shipment_id, "Delivered", act_delivery, "Điểm giao nhận khách hàng", "Giao hàng hoàn tất trễ hạn"
                    ))

                # Customer Support Tickets (8 tickets)
                if len(created_tickets) < 8 and (i % 3 == 0):
                    ticket_id = uuid.uuid4()
                    ticket_time = est_delivery + timedelta(days=2, hours=rng.randint(1, 6))
                    created_tickets.append((
                        ticket_id, customer_id, order_id, ticket_time, None,
                        "Delivery", "High", "Open", None, Decimal(str(rng.choice([1.0, 1.5, 2.0])))
                    ))

                # Reviews (10 negative reviews)
                if len(created_reviews) < 10 and is_delivered and (i % 2 == 0):
                    review_id = uuid.uuid4()
                    rev_time = act_delivery + timedelta(hours=rng.randint(2, 24))
                    created_reviews.append((
                        customer_id, order_id, selected_prods[0]["product_id"],
                        rev_time, 1, Decimal("-0.8500"), "Delivery"
                    ))

                # Financial compensation transaction
                txn_id = uuid.uuid4()
                created_fin_txns.append((
                    shipped_time + timedelta(days=5),
                    "ShippingCost",
                    -per_order_compensation,
                    "VND",
                    order_id,
                    payment_id,
                    None,
                    shipment_id,
                    None,
                    f"COMP-GHN-{i:03d}"
                ))

            # 3. Batch insert operational data
            print(f"Inserting {len(created_orders)} orders, {len(created_shipments)} shipments, {len(created_tickets)} tickets...")

            cur.executemany("""
                INSERT INTO orders (
                    order_id, customer_id, warehouse_id, order_timestamp,
                    channel, order_status, subtotal, discount_amount,
                    shipping_fee, total_amount, currency_code
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, created_orders)

            cur.executemany("""
                INSERT INTO order_items (
                    order_item_id, order_id, product_id, quantity,
                    unit_price, discount_amount, item_total
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, created_order_items)

            cur.executemany("""
                INSERT INTO order_status_history (
                    order_status_history_id, order_id, status,
                    status_timestamp, actor_type, reason_code
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, created_order_history)

            cur.executemany("""
                INSERT INTO payments (
                    payment_id, order_id, payment_method_id, payment_timestamp,
                    amount, currency_code, payment_status, provider_transaction_ref
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, created_payments)

            cur.executemany("""
                INSERT INTO payment_status_history (
                    payment_status_history_id, payment_id, status,
                    status_timestamp, failure_code
                ) VALUES (%s, %s, %s, %s, %s)
            """, created_payment_history)

            cur.executemany("""
                INSERT INTO shipments (
                    shipment_id, order_id, warehouse_id, carrier_id,
                    shipment_timestamp, estimated_delivery_timestamp,
                    delivered_timestamp, shipment_status, tracking_number
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, created_shipments)

            cur.executemany("""
                INSERT INTO shipment_status_history (
                    shipment_status_history_id, shipment_id, status,
                    status_timestamp, location_region, exception_code
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, created_shipment_history)

            cur.executemany("""
                INSERT INTO customer_tickets (
                    ticket_id, customer_id, order_id, created_at,
                    resolved_at, category, priority, status,
                    resolution_time_hours, satisfaction_score
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, created_tickets)

            cur.executemany("""
                INSERT INTO reviews (
                    customer_id, order_id, product_id,
                    created_at, rating, sentiment_score, review_category
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (customer_id, order_id, product_id) DO NOTHING
            """, created_reviews)

            cur.executemany("""
                INSERT INTO financial_transactions (
                    transaction_timestamp, transaction_type, amount,
                    currency_code, order_id, payment_id, purchase_order_id,
                    shipment_id, campaign_id, reference_code
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, created_fin_txns)

            for o in created_orders:
                cur.execute("""
                    INSERT INTO audit_log (
                        audit_log_id, event_timestamp, actor_role,
                        action_type, object_type, object_id, success, metadata
                    ) VALUES (
                        gen_random_uuid(), %s, 'edt_simulator',
                        'INJECT_S002_ORDER', 'Order', %s, true,
                        jsonb_build_object('scenario_id', 'S002')
                    )
                """, (o[3], o[0]))

            # 4. Layer 5: Incidents
            incident_id = uuid.uuid4()
            neutral_summary = "Hệ thống giám sát vận đơn ghi nhận thời gian vận chuyển (Transit Duration) của các bưu kiện do đối tác GHN phụ trách tăng đột biến trong nửa cuối tháng 08/2026, dẫn đến tỷ lệ giao hàng trễ hạn cao kèm làn sóng khiếu nại giao vận từ khách hàng."

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
                "High", "Delivery", "Closed", neutral_summary
            ))

            cur.execute("""
                INSERT INTO incident_entities (
                    incident_entity_id, incident_id, entity_type,
                    entity_id, observed_at, impact_type, impact_severity
                ) VALUES (
                    gen_random_uuid(), %s, 'Shipment', %s,
                    %s, 'LOGISTICS_DISRUPTION_SAMPLE', 0.8500
                )
            """, (incident_id, created_shipments[0][0], INCIDENT_DETECTED))

            # 5. Layer 6: Causal Ground Truth DAG
            node1_id = uuid.uuid4()
            node2_id = uuid.uuid4()
            node3_id = uuid.uuid4()
            node4_id = uuid.uuid4()
            node5_id = uuid.uuid4()

            nodes_data = [
                (
                    node1_id, incident_id, "RootCause", "Delivery",
                    "Carrier", carrier_id, INCIDENT_START, INCIDENT_END,
                    "Gián đoạn vận chuyển bưu cục GHN (Depot Congestion)",
                    "Đối tác vận chuyển GHN gặp sự cố quá tải bưu cục trung tâm và điều phối giao nhận khu vực phía Nam."
                ),
                (
                    node2_id, incident_id, "Mechanism", "Delivery",
                    "Carrier", carrier_id, INCIDENT_START + timedelta(hours=12), INCIDENT_END,
                    "Thời gian vận chuyển bưu kiện tăng vọt và giao trễ hạn",
                    "Thời gian giao hàng trung bình của GHN tăng từ 2.5 ngày lên 9.5 ngày, nhiều bưu kiện lưu kho quá hạn."
                ),
                (
                    node3_id, incident_id, "OperationalImpact", "Customer",
                    None, None, INCIDENT_START + timedelta(days=2), INCIDENT_END + timedelta(days=1),
                    "Gia tăng khiếu nại khách hàng về giao hàng trễ",
                    "Khách hàng gửi yêu cầu hỗ trợ (tickets) phàn nàn về tình trạng đơn hàng giao chậm trễ quá ngày dự kiến."
                ),
                (
                    node4_id, incident_id, "OperationalImpact", "Customer",
                    None, None, INCIDENT_START + timedelta(days=3), INCIDENT_END + timedelta(days=2),
                    "Sụt giảm điểm đánh giá hài lòng và gia tăng đánh giá tiêu cực",
                    "Khách hàng chấm 1 sao kèm bình luận tiêu cực về chất lượng dịch vụ vận chuyển của đối tác."
                ),
                (
                    node5_id, incident_id, "Outcome", "Finance",
                    None, None, INCIDENT_START, INCIDENT_END,
                    "Chi phí đền bù giao trễ và phát hành voucher giữ chân",
                    f"Tổng thiệt hại tài chính phát sinh từ việc hoàn cước và bồi thường khách hàng đạt {total_compensation_loss:,.2f} VND."
                ),
            ]

            cur.executemany("""
                INSERT INTO causal_nodes (
                    node_id, incident_id, node_type, domain,
                    entity_type, entity_id, valid_from, valid_to,
                    truth_label, truth_description
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, nodes_data)

            links_data = [
                (uuid.uuid4(), incident_id, node1_id, node2_id, "Causes", Decimal("24.0"), Decimal("0.9800")),
                (uuid.uuid4(), incident_id, node2_id, node3_id, "Causes", Decimal("48.0"), Decimal("0.9500")),
                (uuid.uuid4(), incident_id, node3_id, node4_id, "Amplifies", Decimal("24.0"), Decimal("0.9000")),
                (uuid.uuid4(), incident_id, node4_id, node5_id, "Causes", Decimal("24.0"), Decimal("0.9200")),
            ]

            cur.executemany("""
                INSERT INTO causal_links (
                    causal_link_id, incident_id, cause_node_id, effect_node_id,
                    relationship_type, lag_minutes, confidence
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, links_data)

            cur.execute("""
                INSERT INTO incident_causes (
                    incident_cause_id, incident_id, node_id,
                    cause_rank, is_primary, confirmed_at
                ) VALUES (
                    gen_random_uuid(), %s, %s,
                    1, true, %s
                )
            """, (incident_id, node1_id, INCIDENT_END + timedelta(hours=1)))

            ev1_id = uuid.uuid4()
            ev2_id = uuid.uuid4()
            sample_shipment = created_shipments[0]
            sample_ticket = created_tickets[0]

            cur.execute("""
                INSERT INTO incident_evidence (
                    incident_evidence_id, incident_id, node_id, evidence_type,
                    source_table, source_record_id, evidence_timestamp,
                    evidence_summary, is_decisive
                ) VALUES 
                (%s, %s, %s, 'Record', 'shipments', %s, %s, 'Bưu kiện GHN giao trễ hạn nghiêm trọng so với cam kết.', true),
                (%s, %s, %s, 'Record', 'customer_tickets', %s, %s, 'Khiếu nại khách hàng phản ánh giao hàng chậm chạp.', true)
            """, (
                ev1_id, incident_id, node2_id, sample_shipment[0], sample_shipment[4],
                ev2_id, incident_id, node3_id, sample_ticket[0], sample_ticket[3]
            ))

            outcomes_data = [
                (
                    uuid.uuid4(), incident_id, node5_id, "RevenueLoss",
                    INCIDENT_END + timedelta(hours=1), "logistics_compensation_loss",
                    total_compensation_loss, total_compensation_loss, "VND"
                ),
            ]
            cur.executemany("""
                INSERT INTO incident_outcomes (
                    incident_outcome_id, incident_id, node_id, outcome_type,
                    measured_at, metric_name, metric_value,
                    financial_impact, currency_code
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, outcomes_data)

            # 6. Layer 7: Benchmark & Evaluation
            case_id = uuid.uuid4()
            case_name = "BENCHMARK-S002-LOGISTICS-GHN-20260820"
            cur.execute("""
                INSERT INTO benchmark_cases (
                    benchmark_case_id, incident_id, case_name, split,
                    observation_start_time, observation_cutoff_time, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                case_id, incident_id, case_name, "Test",
                INCIDENT_START, INCIDENT_CUTOFF, "Active"
            ))

            # Allowlisted observations before cutoff
            obs_rows = []
            for s in created_shipments:
                if s[4] <= INCIDENT_CUTOFF:
                    obs_rows.append((uuid.uuid4(), case_id, "shipments", s[0], s[4], "Signal"))
            for t in created_tickets:
                if t[3] <= INCIDENT_CUTOFF:
                    obs_rows.append((uuid.uuid4(), case_id, "customer_tickets", t[0], t[3], "Context"))

            cur.executemany("""
                INSERT INTO benchmark_observations (
                    benchmark_observation_id, benchmark_case_id,
                    source_table, source_record_id, observed_at, observation_role
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (benchmark_case_id, source_table, source_record_id) DO NOTHING
            """, obs_rows)

            eval_targets = [
                (uuid.uuid4(), case_id, "RootCause", node1_id, Decimal("0.3000"), {
                    "domain": "Logistics",
                    "primary_root_cause": "CarrierDisruption",
                    "affected_carrier": CARRIER_NAME,
                    "expected_keywords": ["GHN", "Giao Hàng Nhanh", "carrier", "vận chuyển", "logistics", "bưu cục", "chậm giao hàng", "tắc nghẽn"]
                }),
                (uuid.uuid4(), case_id, "CausalPath", None, Decimal("0.2500"), {
                    "required_nodes": ["RootCause", "Mechanism", "OperationalImpact", "Outcome"],
                    "causal_sequence": [
                        ["CarrierDisruption", "ShipmentDeliveryDelay"],
                        ["ShipmentDeliveryDelay", "DeliveryComplaintSpike"],
                        ["DeliveryComplaintSpike", "CustomerSatisfactionDrop"],
                        ["CustomerSatisfactionDrop", "LogisticsCompensationLoss"]
                    ]
                }),
                (uuid.uuid4(), case_id, "AffectedEntity", node1_id, Decimal("0.1500"), {
                    "entity_id": str(carrier_id),
                    "entity_name": CARRIER_NAME,
                    "entity_type": "Carrier"
                }),
                (uuid.uuid4(), case_id, "Outcome", node5_id, Decimal("0.1500"), {
                    "metric_name": "logistics_compensation_loss",
                    "expected_value": float(total_compensation_loss),
                    "currency": "VND",
                    "tolerance_percent": 0.20
                }),
                (uuid.uuid4(), case_id, "RecommendedAction", None, Decimal("0.1500"), {
                    "recommended_actions": [
                        "Tạm ngưng điều phối đơn hàng mới qua đối tác GHN tại khu vực phía Nam",
                        "Chuyển hướng luồng vận đơn sang các đơn vị vận chuyển dự phòng (Viettel Post, VNPost, J&T Express)",
                        "Làm việc khẩn cấp với đại diện GHN để giải tỏa các kiện hàng đang tắc nghẽn tại bưu cục",
                        "Chủ động gửi thông báo cập nhật tiến độ giao hàng và tặng voucher đền bù cho khách hàng"
                    ]
                })
            ]

            cur.executemany("""
                INSERT INTO evaluation_targets (
                    evaluation_target_id, benchmark_case_id, target_type,
                    causal_node_id, scoring_weight, target_value
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, [(t[0], t[1], t[2], t[3], t[4], json.dumps(t[5])) for t in eval_targets])

            conn.commit()
            print(f"[SUCCESS] Scenario S002 (Carrier Disruption) successfully injected.")
            print(f"  Incident ID    : {incident_id}")
            print(f"  Benchmark Case : {case_name}")
            print(f"  Delayed Parcels: {len(created_shipments)}")
            print(f"  Compensation   : {total_compensation_loss:,.2f} VND")


if __name__ == "__main__":
    inject_s002()
