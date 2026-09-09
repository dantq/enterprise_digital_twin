"""Scenario S005 Generator: Product Quality Degradation (Suy giảm chất lượng sản phẩm).

This module injects Scenario S005 into the Enterprise Digital Twin:
1. Operational Anomaly:
   - Defective manufacturing batch for high-value SKU 'Eco Laptop 072' (unit price 17,000,000 VND).
   - 25 customer orders in early August 2026 suffer severe hardware failure (screen flickering, motherboard failure).
   - Orders transition to 'Refunded'.
   - 18 high-priority customer support tickets (category 'ProductQuality' / 'Refund').
   - 20 1-star reviews citing product hardware failure.
   - 25 refund financial transactions totaling -425,000,000 VND.
2. Layer 5 (Incident Operational Metadata):
   - incidents: Surface incident registered with domain 'Customer', severity 'High'.
   - incident_entities: Affected product entity.
3. Layer 6 (Causal Ground Truth DAG):
   - causal_nodes: 5 nodes (RootCause, Mechanism, OperationalImpact x2, Outcome).
   - causal_links: 5 directed causal edges forming a strict acyclic DAG.
   - incident_causes: Primary root cause confirmed.
   - incident_evidence: Decisive refund logs and defect review records.
   - incident_outcomes: Quantified refund financial impact (425,000,000 VND).
4. Layer 7 (Benchmark & Evaluation):
   - benchmark_cases: Active test case with cutoff at 2026-08-15.
   - benchmark_observations: Pre-cutoff operational records.
   - evaluation_targets: Ground truth scoring rubrics for AI Analyst.
5. Infrastructure:
   - audit_log: Tracking all injected records with 'INJECT_S005_PRODUCT_DEFECT'.
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

S005_SEED = SEED + 5005
random.seed(S005_SEED)

SCENARIO_ID = "S005"
PRODUCT_ID = uuid.UUID("50c3ee2e-fdb3-472b-ba13-93f812ea7e7f")
PRODUCT_NAME = "Eco Laptop 072"
UNIT_PRICE = Decimal("17000000.00")
ORDER_COUNT = 25
TOTAL_REFUND_LOSS = UNIT_PRICE * ORDER_COUNT  # 425,000,000.00 VND

INCIDENT_START = datetime(2026, 8, 5, 0, 0, 0, tzinfo=timezone.utc)      # 07:00 ICT
INCIDENT_DETECTED = datetime(2026, 8, 12, 3, 0, 0, tzinfo=timezone.utc)   # 10:00 ICT
INCIDENT_CUTOFF = datetime(2026, 8, 15, 0, 0, 0, tzinfo=timezone.utc)    # 07:00 ICT
INCIDENT_END = datetime(2026, 8, 25, 16, 59, 59, tzinfo=timezone.utc)   # 23:59 ICT


def clean_existing_s005(conn):
    """Cleanly purge any previously injected S005 data for idempotency."""
    with conn.cursor() as cur:
        cur.execute("SELECT incident_id FROM incidents WHERE scenario_id = %s", (SCENARIO_ID,))
        row = cur.fetchone()
        if not row:
            # Check for leftover audit log items
            cur.execute("SELECT object_id FROM audit_log WHERE action_type = 'INJECT_S005_PRODUCT_DEFECT' AND object_type = 'Order'")
            order_ids = [r["object_id"] for r in cur.fetchall()]
            if order_ids:
                purge_operational_orders(cur, order_ids)
            return

        incident_id = row["incident_id"]
        print(f"Purging existing S005 data for incident {incident_id}...")

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
        cur.execute("SELECT object_id FROM audit_log WHERE action_type = 'INJECT_S005_PRODUCT_DEFECT' AND object_type = 'Order'")
        order_ids = [r["object_id"] for r in cur.fetchall()]
        if order_ids:
            purge_operational_orders(cur, order_ids)

        # Delete incident itself
        cur.execute("DELETE FROM incidents WHERE incident_id = %s", (incident_id,))
        cur.execute("DELETE FROM audit_log WHERE action_type LIKE 'INJECT_%%' AND (metadata->>'scenario_id' = %s OR object_id = %s)", (SCENARIO_ID, incident_id))
        print("Previous S005 data successfully purged.")


def purge_operational_orders(cur, order_ids):
    """Safely delete all associated order records."""
    cur.execute("DELETE FROM financial_transactions WHERE order_id = ANY(%s)", (order_ids,))
    cur.execute("DELETE FROM customer_tickets WHERE order_id = ANY(%s)", (order_ids,))
    cur.execute("DELETE FROM reviews WHERE order_id = ANY(%s)", (order_ids,))
    cur.execute("DELETE FROM shipment_status_history WHERE shipment_id IN (SELECT shipment_id FROM shipments WHERE order_id = ANY(%s))", (order_ids,))
    cur.execute("DELETE FROM shipments WHERE order_id = ANY(%s)", (order_ids,))
    cur.execute("DELETE FROM payment_status_history WHERE payment_id IN (SELECT payment_id FROM payments WHERE order_id = ANY(%s))", (order_ids,))
    cur.execute("DELETE FROM payments WHERE order_id = ANY(%s)", (order_ids,))
    cur.execute("DELETE FROM order_status_history WHERE order_id = ANY(%s)", (order_ids,))
    cur.execute("DELETE FROM order_items WHERE order_id = ANY(%s)", (order_ids,))
    cur.execute("DELETE FROM orders WHERE order_id = ANY(%s)", (order_ids,))


def inject_s005():
    with get_connection() as conn:
        with conn.cursor() as cur:
            clean_existing_s005(conn)

            # Fetch reference resources
            cur.execute("SELECT customer_id FROM customers LIMIT %s", (ORDER_COUNT * 2,))
            customer_ids = [r["customer_id"] for r in cur.fetchall()]
            random.shuffle(customer_ids)

            cur.execute("SELECT warehouse_id FROM warehouses LIMIT 1")
            warehouse_id = cur.fetchone()["warehouse_id"]

            cur.execute("SELECT carrier_id FROM carriers LIMIT 1")
            carrier_id = cur.fetchone()["carrier_id"]

            cur.execute("SELECT payment_method_id FROM payment_methods LIMIT 1")
            payment_method_id = cur.fetchone()["payment_method_id"]

            # 1. Operational Injections: 25 defective orders
            created_orders = []
            created_payments = []
            created_shipments = []
            created_fin_txns = []
            created_tickets = []
            created_reviews = []
            order_ids = []

            for i in range(ORDER_COUNT):
                order_id = uuid.uuid4()
                order_ids.append(order_id)
                customer_id = customer_ids[i]

                # Order placed between Aug 5 and Aug 9
                day_offset = (i % 5)
                hour_offset = (i * 3) % 18
                order_time = INCIDENT_START + timedelta(days=day_offset, hours=hour_offset)
                paid_time = order_time + timedelta(minutes=5)
                fulfilled_time = order_time + timedelta(hours=2)
                shipped_time = order_time + timedelta(hours=6)
                delivered_time = order_time + timedelta(hours=28)
                defect_discovered_time = delivered_time + timedelta(hours=14)
                refund_time = defect_discovered_time + timedelta(hours=24)

                # Order master
                cur.execute("""
                    INSERT INTO orders (
                        order_id, customer_id, warehouse_id, order_timestamp,
                        channel, order_status, subtotal, discount_amount,
                        shipping_fee, total_amount, currency_code
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    order_id, customer_id, warehouse_id, order_time,
                    "Website", "Refunded", UNIT_PRICE, Decimal("0.00"),
                    Decimal("0.00"), UNIT_PRICE, "VND"
                ))

                # Order item
                cur.execute("""
                    INSERT INTO order_items (
                        order_item_id, order_id, product_id, quantity,
                        unit_price, discount_amount, item_total
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    uuid.uuid4(), order_id, PRODUCT_ID, 1,
                    UNIT_PRICE, Decimal("0.00"), UNIT_PRICE
                ))

                # Order status history (monotonically non-decreasing)
                order_history = [
                    (uuid.uuid4(), order_id, "Pending", order_time, "System"),
                    (uuid.uuid4(), order_id, "Paid", paid_time, "System"),
                    (uuid.uuid4(), order_id, "Fulfilled", fulfilled_time, "Staff"),
                    (uuid.uuid4(), order_id, "Shipped", shipped_time, "Carrier"),
                    (uuid.uuid4(), order_id, "Delivered", delivered_time, "Carrier"),
                    (uuid.uuid4(), order_id, "Refunded", refund_time, "Staff"),
                ]
                cur.executemany("""
                    INSERT INTO order_status_history (
                        order_status_history_id, order_id, status, status_timestamp, actor_type
                    ) VALUES (%s, %s, %s, %s, %s)
                """, order_history)

                # Payment
                payment_id = uuid.uuid4()
                cur.execute("""
                    INSERT INTO payments (
                        payment_id, order_id, payment_method_id, payment_timestamp,
                        amount, currency_code, payment_status, provider_transaction_ref
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    payment_id, order_id, payment_method_id, paid_time,
                    UNIT_PRICE, "VND", "Refunded", f"PAY-S005-{i:04d}"
                ))

                # Payment status history
                payment_history = [
                    (uuid.uuid4(), payment_id, "Initiated", order_time, None),
                    (uuid.uuid4(), payment_id, "Authorized", order_time + timedelta(minutes=1), None),
                    (uuid.uuid4(), payment_id, "Captured", paid_time, None),
                    (uuid.uuid4(), payment_id, "Refunded", refund_time, None),
                ]
                cur.executemany("""
                    INSERT INTO payment_status_history (
                        payment_status_history_id, payment_id, status, status_timestamp, failure_code
                    ) VALUES (%s, %s, %s, %s, %s)
                """, payment_history)

                # Shipment
                shipment_id = uuid.uuid4()
                cur.execute("""
                    INSERT INTO shipments (
                        shipment_id, order_id, warehouse_id, carrier_id,
                        shipment_timestamp, estimated_delivery_timestamp,
                        delivered_timestamp, shipment_status, tracking_number
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    shipment_id, order_id, warehouse_id, carrier_id,
                    shipped_time, order_time + timedelta(hours=48),
                    delivered_time, "Delivered", f"VN-S005-{i:04d}"
                ))

                # Shipment status history
                shipment_history = [
                    (uuid.uuid4(), shipment_id, "Created", fulfilled_time, "Hanoi Hub", None),
                    (uuid.uuid4(), shipment_id, "PickedUp", shipped_time, "Hanoi Hub", None),
                    (uuid.uuid4(), shipment_id, "InTransit", shipped_time + timedelta(hours=10), "Transit Hub", None),
                    (uuid.uuid4(), shipment_id, "Delivered", delivered_time, "Customer Location", None),
                ]
                cur.executemany("""
                    INSERT INTO shipment_status_history (
                        shipment_status_history_id, shipment_id, status,
                        status_timestamp, location_region, exception_code
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, shipment_history)

                # Financial transactions (Revenue and Refund)
                # Revenue: positive
                rev_txn_id = uuid.uuid4()
                cur.execute("""
                    INSERT INTO financial_transactions (
                        financial_transaction_id, transaction_timestamp, transaction_type,
                        amount, currency_code, order_id, payment_id, reference_code
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    rev_txn_id, paid_time, "Revenue",
                    UNIT_PRICE, "VND", order_id, payment_id, f"REV-S005-{i:04d}"
                ))

                # Refund: negative (< 0 as per invariant)
                ref_txn_id = uuid.uuid4()
                cur.execute("""
                    INSERT INTO financial_transactions (
                        financial_transaction_id, transaction_timestamp, transaction_type,
                        amount, currency_code, order_id, payment_id, reference_code
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    ref_txn_id, refund_time, "Refund",
                    -UNIT_PRICE, "VND", order_id, payment_id, f"REFUND-S005-{i:04d}"
                ))
                created_fin_txns.append((ref_txn_id, refund_time, -UNIT_PRICE))

                # Customer ticket (18 tickets out of 25)
                if i < 18:
                    ticket_id = uuid.uuid4()
                    cat = "ProductQuality" if i < 12 else "Refund"
                    prio = "Critical" if i < 8 else "High"
                    cur.execute("""
                        INSERT INTO customer_tickets (
                            ticket_id, customer_id, order_id, created_at, resolved_at,
                            category, priority, status, resolution_time_hours, satisfaction_score
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        ticket_id, customer_id, order_id, defect_discovered_time,
                        refund_time, cat, prio, "Closed",
                        Decimal("24.0"), Decimal("1.0")
                    ))
                    created_tickets.append((ticket_id, defect_discovered_time))

                # Product review (20 reviews out of 25)
                if i < 20:
                    review_id = uuid.uuid4()
                    review_time = defect_discovered_time + timedelta(hours=random.randint(1, 10))
                    cur.execute("""
                        INSERT INTO reviews (
                            review_id, customer_id, order_id, product_id,
                            created_at, rating, sentiment_score, review_category
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        review_id, customer_id, order_id, PRODUCT_ID,
                        review_time, 1, Decimal("-0.95"), "ProductQuality"
                    ))
                    created_reviews.append((review_id, review_time))

                # Audit log entry for each injected order
                cur.execute("""
                    INSERT INTO audit_log (
                        audit_log_id, event_timestamp, actor_role,
                        action_type, object_type, object_id, success, metadata
                    ) VALUES (
                        gen_random_uuid(), %s, 'edt_simulator',
                        'INJECT_S005_PRODUCT_DEFECT', 'Order', %s, true, %s::jsonb
                    )
                """, (order_time, order_id, json.dumps({'scenario_id': 'S005', 'product_id': str(PRODUCT_ID)})))

            print(f"Generated {ORDER_COUNT} refunded defect orders, 18 tickets, 20 negative reviews, 50 financial transactions.")

            # 2. Layer 5: Incident registration
            incident_id = uuid.uuid4()
            neutral_summary = "Hệ thống ghi nhận tỷ lệ đổi trả và hoàn tiền (Return & Refund) đối với sản phẩm Eco Laptop 072 tăng vọt bất thường trong nửa đầu tháng 08/2026, đi kèm sự gia tăng đột biến của các khiếu nại chất lượng sản phẩm và đánh giá 1 sao từ khách hàng."

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
                "High", "Customer", "Closed", neutral_summary
            ))

            cur.execute("""
                INSERT INTO incident_entities (
                    incident_entity_id, incident_id, entity_type,
                    entity_id, observed_at, impact_type, impact_severity
                ) VALUES (
                    gen_random_uuid(), %s, 'Product', %s,
                    %s, 'PRODUCT_QUALITY_DEGRADATION', 0.9500
                )
            """, (incident_id, PRODUCT_ID, INCIDENT_DETECTED))

            # 3. Layer 6: Causal Ground Truth DAG
            node1_id = uuid.uuid4()
            node2_id = uuid.uuid4()
            node3_id = uuid.uuid4()
            node4_id = uuid.uuid4()
            node5_id = uuid.uuid4()

            nodes_data = [
                (
                    node1_id, incident_id, "RootCause", "Customer",
                    "Product", PRODUCT_ID, INCIDENT_START, INCIDENT_END,
                    "Lô linh kiện màn hình và bo mạch chủ bị lỗi sản xuất (Defective Hardware Batch)",
                    "Lô linh kiện màn hình hiển thị và mạch nguồn bị lỗi từ khâu kiểm định nhà máy khiến thiết bị sập nguồn và cháy linh kiện sau 24h hoạt động."
                ),
                (
                    node2_id, incident_id, "Mechanism", "Customer",
                    "Product", PRODUCT_ID, INCIDENT_START + timedelta(days=1), INCIDENT_END,
                    "Tỷ lệ lỗi phần cứng nghiêm trọng sau bàn giao (Hardware Failure Rate Surge)",
                    "Toàn bộ máy tính xách tay Eco Laptop 072 thuộc lô sản xuất tháng 08/2026 đều xuất hiện hiện tượng sọc màn hình, liệt bàn phím và không nhận sạc."
                ),
                (
                    node3_id, incident_id, "OperationalImpact", "Customer",
                    "Product", PRODUCT_ID, INCIDENT_START + timedelta(days=3), INCIDENT_END,
                    "Làn sóng yêu cầu trả hàng và hoàn tiền hàng loạt (Wave of Return and Refund Requests)",
                    "Khách hàng đồng loạt yêu cầu hoàn tiền 100%, tỷ lệ hoàn trả của dòng sản phẩm tăng từ 0.5% lên 92%."
                ),
                (
                    node4_id, incident_id, "OperationalImpact", "Customer",
                    None, None, INCIDENT_START + timedelta(days=4), INCIDENT_END,
                    "Bùng nổ khiếu nại chất lượng và khủng hoảng đánh giá 1 sao (Quality Complaints & 1-Star Review Crisis)",
                    "Hàng loạt phiếu hỗ trợ khẩn cấp category ProductQuality và đánh giá 1 sao với điểm cảm xúc cực kỳ tiêu cực (-0.95)."
                ),
                (
                    node5_id, incident_id, "Outcome", "Finance",
                    None, None, INCIDENT_START, INCIDENT_END,
                    "Thiệt hại hoàn tiền trực tiếp và sụt giảm uy tín thương hiệu",
                    f"Tổng dòng tiền xuất quỹ bồi hoàn trực tiếp cho 25 đơn hàng bị lỗi đạt {TOTAL_REFUND_LOSS:,.2f} VND kèm nguy cơ churn khách hàng cao."
                ),
            ]

            cur.executemany("""
                INSERT INTO causal_nodes (
                    node_id, incident_id, node_type, domain,
                    entity_type, entity_id, valid_from, valid_to,
                    truth_label, truth_description
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, nodes_data)

            # Strict Acyclic Directed Causal DAG
            links_data = [
                (uuid.uuid4(), incident_id, node1_id, node2_id, "Causes", Decimal("24.0"), Decimal("0.9800")),
                (uuid.uuid4(), incident_id, node2_id, node3_id, "Causes", Decimal("48.0"), Decimal("0.9600")),
                (uuid.uuid4(), incident_id, node2_id, node4_id, "Causes", Decimal("36.0"), Decimal("0.9400")),
                (uuid.uuid4(), incident_id, node3_id, node5_id, "Causes", Decimal("24.0"), Decimal("0.9500")),
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

            # Decisive evidence
            cur.execute("""
                INSERT INTO incident_evidence (
                    incident_evidence_id, incident_id, node_id, evidence_type,
                    source_table, source_record_id, evidence_timestamp,
                    evidence_summary, is_decisive
                ) VALUES 
                (%s, %s, %s, 'Record', 'customer_tickets', %s, %s, 'Chuỗi khiếu nại ProductQuality phản ánh lỗi bo mạch và màn hình Eco Laptop 072.', true),
                (%s, %s, %s, 'Metric', 'financial_transactions', %s, %s, 'Tổng chi trả hoàn tiền 425 triệu VND cho 25 đơn hàng bị trả lại.', true)
            """, (
                uuid.uuid4(), incident_id, node4_id, created_tickets[0][0], created_tickets[0][1],
                uuid.uuid4(), incident_id, node5_id, created_fin_txns[0][0], created_fin_txns[0][1]
            ))

            outcomes_data = [
                (
                    uuid.uuid4(), incident_id, node5_id, "RefundIncrease",
                    INCIDENT_END + timedelta(hours=1), "total_defect_refund_amount",
                    TOTAL_REFUND_LOSS, TOTAL_REFUND_LOSS, "VND"
                ),
            ]
            cur.executemany("""
                INSERT INTO incident_outcomes (
                    incident_outcome_id, incident_id, node_id, outcome_type,
                    measured_at, metric_name, metric_value,
                    financial_impact, currency_code
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, outcomes_data)

            # 4. Layer 7: Benchmark & Evaluation Case
            case_id = uuid.uuid4()
            case_name = "BENCHMARK-S005-PRODUCT-QUALITY-20260815"
            cur.execute("""
                INSERT INTO benchmark_cases (
                    benchmark_case_id, incident_id, case_name, split,
                    observation_start_time, observation_cutoff_time, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                case_id, incident_id, case_name, "Test",
                INCIDENT_START, INCIDENT_CUTOFF, "Active"
            ))

            # Allowlisted observations pre-cutoff
            obs_rows = [
                (uuid.uuid4(), case_id, "products", PRODUCT_ID, INCIDENT_START, "Signal"),
            ]
            for t_id, t_time in created_tickets:
                if t_time <= INCIDENT_CUTOFF:
                    obs_rows.append((uuid.uuid4(), case_id, "customer_tickets", t_id, t_time, "Signal"))
            for r_id, r_time in created_reviews:
                if r_time <= INCIDENT_CUTOFF:
                    obs_rows.append((uuid.uuid4(), case_id, "reviews", r_id, r_time, "Signal"))
            for txn_id, txn_time, _ in created_fin_txns:
                if txn_time <= INCIDENT_CUTOFF:
                    obs_rows.append((uuid.uuid4(), case_id, "financial_transactions", txn_id, txn_time, "Context"))

            cur.executemany("""
                INSERT INTO benchmark_observations (
                    benchmark_observation_id, benchmark_case_id,
                    source_table, source_record_id, observed_at, observation_role
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (benchmark_case_id, source_table, source_record_id) DO NOTHING
            """, obs_rows)

            eval_targets = [
                (uuid.uuid4(), case_id, "RootCause", node1_id, Decimal("0.3000"), {
                    "domain": "Customer",
                    "primary_root_cause": "ProductQualityDegradation",
                    "affected_product": PRODUCT_NAME,
                    "expected_keywords": ["chất lượng", "sản phẩm", "linh kiện", "lỗi", "Eco Laptop 072", "màn hình", "bo mạch", "hoàn tiền", "1 sao", "đổi trả"]
                }),
                (uuid.uuid4(), case_id, "CausalPath", None, Decimal("0.2500"), {
                    "required_nodes": ["RootCause", "Mechanism", "OperationalImpact", "Outcome"],
                    "causal_sequence": [
                        ["ProductQualityDegradation", "HardwareFailureSurge"],
                        ["HardwareFailureSurge", "ReturnRefundWave"],
                        ["ReturnRefundWave", "QualityComplaintsSpike"],
                        ["QualityComplaintsSpike", "DirectRefundLoss"]
                    ]
                }),
                (uuid.uuid4(), case_id, "AffectedEntity", node1_id, Decimal("0.1500"), {
                    "entity_id": str(PRODUCT_ID),
                    "entity_name": PRODUCT_NAME,
                    "entity_type": "Product"
                }),
                (uuid.uuid4(), case_id, "Outcome", node5_id, Decimal("0.1500"), {
                    "metric_name": "total_defect_refund_amount",
                    "expected_value": float(TOTAL_REFUND_LOSS),
                    "currency": "VND",
                    "tolerance_percent": 0.20
                }),
                (uuid.uuid4(), case_id, "RecommendedAction", None, Decimal("0.1500"), {
                    "recommended_actions": [
                        "Thu hồi khẩn cấp toàn bộ lô hàng Eco Laptop 072 gặp sự cố phần cứng",
                        "Tạm ngưng phân phối và gỡ sản phẩm Eco Laptop 072 khỏi các kênh bán hàng",
                        "Kiểm tra chất lượng (QA/QC) với đối tác cung ứng bo mạch và màn hình",
                        "Chủ động liên hệ bồi hoàn, hỗ trợ đổi mới hoặc voucher giữ chân khách hàng bị ảnh hưởng"
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
            print(f"[SUCCESS] Scenario S005 (Product Quality Degradation) successfully injected.")
            print(f"  Incident ID    : {incident_id}")
            print(f"  Benchmark Case : {case_name}")
            print(f"  Product        : {PRODUCT_NAME} ({PRODUCT_ID})")
            print(f"  Total Refund   : {TOTAL_REFUND_LOSS:,.2f} VND")


if __name__ == "__main__":
    inject_s005()
