"""Scenario S003 Generator: Payment Gateway Outage (Suy giảm hệ thống thanh toán).

This module injects Scenario S003 into the Enterprise Digital Twin:
1. Operational Anomaly:
   - 35 orders attempted via MoMo on 2026-08-15 (08:00 to 16:00 UTC).
   - 30 payments fail due to GATEWAY_TIMEOUT, and the corresponding orders are Cancelled.
   - 5 payments succeed (intermittent availability), orders Paid.
   - 8 Customer Support Tickets filed complaining about MoMo payment errors.
2. Layer 5 (Incident Operational Metadata):
   - incidents: Surface incident registered with neutral summary.
   - incident_entities: Affected payment records and customer entities.
3. Layer 6 (Causal Ground Truth DAG):
   - causal_nodes: 5 nodes (RootCause, Mechanism, OperationalImpact x2, Outcome).
   - causal_links: 4 directed causal edges forming a strict DAG.
   - incident_causes: Primary root cause confirmed.
   - incident_evidence: Decisive log, metric, and record evidence.
   - incident_outcomes: Quantified revenue loss and SLA degradation.
4. Layer 7 (Benchmark & Evaluation):
   - benchmark_cases: Active test case with cutoff at 14:00 UTC.
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

# Ensure paths
DATA_GENERATOR_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATA_GENERATOR_DIR))

from db import get_connection
from config import SEED

S003_SEED = SEED + 3003
random.seed(S003_SEED)

SCENARIO_ID = "S003"
MOMO_METHOD_NAME = "MoMo"

INCIDENT_START = datetime(2026, 8, 15, 8, 0, 0, tzinfo=timezone.utc)
INCIDENT_DETECTED = datetime(2026, 8, 15, 9, 15, 0, tzinfo=timezone.utc)
INCIDENT_CUTOFF = datetime(2026, 8, 15, 14, 0, 0, tzinfo=timezone.utc)
INCIDENT_END = datetime(2026, 8, 15, 16, 0, 0, tzinfo=timezone.utc)


def money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def clean_existing_s003(conn):
    """Cleanly purge any previously injected S003 data for idempotency."""
    with conn.cursor() as cur:
        # Find existing incident_id for S003
        cur.execute("SELECT incident_id FROM incidents WHERE scenario_id = %s", (SCENARIO_ID,))
        row = cur.fetchone()
        if not row:
            return

        incident_id = row["incident_id"]
        print(f"Purging existing S003 data for incident {incident_id}...")

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

        # Operational records tagged by audit_log or specific S003 order IDs
        cur.execute("SELECT object_id FROM audit_log WHERE action_type = 'INJECT_S003_ORDER'")
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

        # Delete incident itself
        cur.execute("DELETE FROM incidents WHERE incident_id = %s", (incident_id,))
        cur.execute("DELETE FROM audit_log WHERE action_type LIKE 'INJECT_%' AND (metadata->>'scenario_id' = %s OR object_id = %s)", (SCENARIO_ID, incident_id))
        print("Previous S003 data successfully purged.")


def inject_s003():
    with get_connection() as conn:
        with conn.cursor() as cur:
            clean_existing_s003(conn)

            # 1. Fetch reference entities
            cur.execute("SELECT customer_id, customer_segment FROM customers WHERE status = 'Active'")
            customers = cur.fetchall()

            cur.execute("SELECT warehouse_id FROM warehouses WHERE status = 'Active'")
            warehouses = [r["warehouse_id"] for r in cur.fetchall()]

            cur.execute("SELECT product_id, unit_price, demand_class FROM products WHERE status = 'Active'")
            products = cur.fetchall()

            cur.execute("SELECT payment_method_id FROM payment_methods WHERE method_name = %s", (MOMO_METHOD_NAME,))
            momo_row = cur.fetchone()
            if not momo_row:
                raise RuntimeError(f"Payment method '{MOMO_METHOD_NAME}' not found in database.")
            momo_id = momo_row["payment_method_id"]

            print(f"Loaded {len(customers)} active customers, {len(warehouses)} warehouses, {len(products)} active products.")

            # 2. Generate 35 Operational Orders during incident window
            rng = random.Random(S003_SEED)
            total_orders = 35
            failed_count = 30
            success_count = total_orders - failed_count

            # Determine failure flags
            failure_flags = [True] * failed_count + [False] * success_count
            rng.shuffle(failure_flags)

            created_orders = []
            created_order_items = []
            created_order_history = []
            created_payments = []
            created_payment_history = []
            created_tickets = []

            total_failed_revenue = Decimal("0.00")

            channels = ["Website", "Mobile App", "Mobile App", "Website"]  # digital channels

            # Time distribution across 8 hours (08:00 to 16:00 UTC)
            window_seconds = int((INCIDENT_END - INCIDENT_START).total_seconds())

            for i, is_failed in enumerate(failure_flags):
                order_id = uuid.uuid4()
                cust = rng.choice(customers)
                customer_id = cust["customer_id"]
                customer_segment = cust["customer_segment"]
                warehouse_id = rng.choice(warehouses)
                channel = rng.choice(channels)

                # Spread timestamps realistically with higher density around peak hours (10:00 - 13:00)
                offset_sec = int(window_seconds * ((i + rng.uniform(0.1, 0.9)) / total_orders))
                order_time = INCIDENT_START + timedelta(seconds=offset_sec)

                # Order Items (1 to 3 items)
                item_count = rng.randint(1, 3)
                selected_prods = rng.sample(products, item_count)
                subtotal = Decimal("0.00")

                for p in selected_prods:
                    item_id = uuid.uuid4()
                    p_id = p["product_id"]
                    price = money(p["unit_price"])
                    qty = rng.choice([1, 2])
                    gross = money(Decimal(qty) * price)
                    disc = money(gross * Decimal("0.05")) if customer_segment == "VIP" else Decimal("0.00")
                    item_tot = money(gross - disc)
                    subtotal += item_tot

                    created_order_items.append((
                        item_id, order_id, p_id, Decimal(qty), price, disc, item_tot
                    ))

                # Order header totals
                order_discount = money(subtotal * Decimal("0.05")) if subtotal >= Decimal("500000") and customer_segment == "VIP" else Decimal("0.00")
                shipping_fee = Decimal("0.00") if is_failed else Decimal("30000.00")
                total_amount = money(subtotal - order_discount + shipping_fee)

                order_status = "Cancelled" if is_failed else "Paid"
                if is_failed:
                    total_failed_revenue += total_amount

                created_orders.append((
                    order_id, customer_id, warehouse_id, order_time,
                    channel, order_status, subtotal, order_discount,
                    shipping_fee, total_amount, "VND"
                ))

                # Order Status History
                hist_pending_id = uuid.uuid4()
                created_order_history.append((
                    hist_pending_id, order_id, "Pending", order_time, "System", "ORDER_PLACED"
                ))

                # Payment & Payment Status History
                payment_id = uuid.uuid4()
                payment_init_time = order_time + timedelta(minutes=rng.randint(1, 3))
                payment_status = "Failed" if is_failed else "Captured"
                payment_time = payment_init_time + timedelta(minutes=rng.randint(2, 4))
                tx_ref = f"MOMO-{order_time.strftime('%Y%m%d%H%M%S')}-{rng.randint(1000, 9999)}"

                created_payments.append((
                    payment_id, order_id, momo_id, payment_time,
                    total_amount, "VND", payment_status, tx_ref
                ))

                psh_init_id = uuid.uuid4()
                created_payment_history.append((
                    psh_init_id, payment_id, "Initiated", payment_init_time, None
                ))

                if is_failed:
                    psh_fail_id = uuid.uuid4()
                    created_payment_history.append((
                        psh_fail_id, payment_id, "Failed", payment_time, "GATEWAY_TIMEOUT"
                    ))
                    # Order cancelled after failed payment
                    hist_cancel_id = uuid.uuid4()
                    cancel_time = payment_time + timedelta(minutes=rng.randint(5, 10))
                    created_order_history.append((
                        hist_cancel_id, order_id, "Cancelled", cancel_time, "System", "PAYMENT_TIMEOUT"
                    ))

                    # Generate Customer Ticket for some failed orders (8 tickets total)
                    if len(created_tickets) < 8 and rng.random() < 0.35:
                        ticket_id = uuid.uuid4()
                        ticket_time = cancel_time + timedelta(minutes=rng.randint(10, 45))
                        created_tickets.append((
                            ticket_id, customer_id, order_id, ticket_time, None,
                            "Payment", "High" if rng.random() < 0.7 else "Critical",
                            "Open", None, None
                        ))
                else:
                    psh_cap_id = uuid.uuid4()
                    created_payment_history.append((
                        psh_cap_id, payment_id, "Captured", payment_time, None
                    ))
                    hist_paid_id = uuid.uuid4()
                    created_order_history.append((
                        hist_paid_id, order_id, "Paid", payment_time, "System", "PAYMENT_CONFIRMED"
                    ))

            # Batch insert operational records
            print(f"Inserting {len(created_orders)} orders, {len(created_order_items)} items...")
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
                INSERT INTO customer_tickets (
                    ticket_id, customer_id, order_id, created_at,
                    resolved_at, category, priority, status,
                    resolution_time_hours, satisfaction_score
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, created_tickets)

            print(f"Operational anomaly injected: {failed_count} failed orders ({total_failed_revenue:,.2f} VND loss), {len(created_tickets)} tickets.")

            # Record audit log for orders to enable idempotent cleanup
            for o in created_orders:
                cur.execute("""
                    INSERT INTO audit_log (
                        audit_log_id, event_timestamp, actor_role,
                        action_type, object_type, object_id, success, metadata
                    ) VALUES (
                        gen_random_uuid(), %s, 'edt_simulator',
                        'INJECT_S003_ORDER', 'Order', %s, true,
                        jsonb_build_object('scenario_id', 'S003')
                    )
                """, (o[3], o[0]))

            # 3. Layer 5 — Incident & Safe Observation
            incident_id = uuid.uuid4()
            neutral_summary = (
                "Hệ thống giám sát ghi nhận tỷ lệ thanh toán thất bại tăng vọt cục bộ trong ngày 15/08/2026, "
                "tập trung vào các giao dịch qua ví điện tử, dẫn đến số lượng đơn hàng không hoàn tất tăng cao "
                "kèm theo khiếu nại gia tăng từ khách hàng."
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
                "High", "Payment", "Closed", neutral_summary
            ))

            # Incident entities: PaymentMethod (MoMo) and sample failed payments
            cur.execute("""
                INSERT INTO incident_entities (
                    incident_entity_id, incident_id, entity_type, entity_id,
                    observed_at, impact_type, impact_severity
                ) VALUES (
                    gen_random_uuid(), %s, 'Payment', %s,
                    %s, 'GATEWAY_OUTAGE_SAMPLE', 0.9000
                )
            """, (incident_id, created_payments[0][0], INCIDENT_DETECTED))

            # 4. Layer 6 — Causal Ground Truth DAG
            node1_id = uuid.uuid4()  # RootCause
            node2_id = uuid.uuid4()  # Mechanism
            node3_id = uuid.uuid4()  # OperationalImpact (Sales)
            node4_id = uuid.uuid4()  # OperationalImpact (Customer)
            node5_id = uuid.uuid4()  # Outcome (Finance)

            nodes_data = [
                (
                    node1_id, incident_id, "RootCause", "Payment",
                    "PaymentMethod", momo_id, INCIDENT_START, INCIDENT_END,
                    "Suy giảm hệ thống cổng thanh toán MoMo (Gateway Timeout)",
                    "Cổng thanh toán MoMo gặp sự cố hạ tầng máy chủ và kết nối mạng từ phía đối tác cung cấp dịch vụ, dẫn đến mất khả năng xử lý giao dịch."
                ),
                (
                    node2_id, incident_id, "Mechanism", "Payment",
                    "PaymentMethod", momo_id, INCIDENT_START + timedelta(minutes=5), INCIDENT_END,
                    "Tỷ lệ giao dịch thanh toán thất bại tăng vọt",
                    "Giao dịch thanh toán qua MoMo bị timeout liên tục (mã GATEWAY_TIMEOUT), tỷ lệ thất bại tăng từ 1.35% lên 85.7%."
                ),
                (
                    node3_id, incident_id, "OperationalImpact", "Fulfillment",
                    None, None, INCIDENT_START + timedelta(minutes=15), INCIDENT_END + timedelta(minutes=30),
                    "Đơn hàng bị hủy hàng loạt do không hoàn tất thanh toán",
                    "Các đơn hàng chờ thanh toán qua MoMo không nhận được webhook xác nhận và bị hệ thống tự động hủy (Cancelled)."
                ),
                (
                    node4_id, incident_id, "OperationalImpact", "Customer",
                    None, None, INCIDENT_START + timedelta(minutes=35), INCIDENT_END + timedelta(hours=2),
                    "Gia tăng khiếu nại khách hàng về lỗi thanh toán",
                    "Khách hàng gặp lỗi giao dịch gửi nhiều yêu cầu hỗ trợ (tickets) phàn nàn về việc trừ tiền nhưng đơn hàng chưa xác nhận."
                ),
                (
                    node5_id, incident_id, "Outcome", "Finance",
                    None, None, INCIDENT_START, INCIDENT_END,
                    "Tổn thất doanh thu bán hàng trực tiếp",
                    f"Doanh thu bị thất thoát trực tiếp từ 30 đơn hàng bị hủy đạt tổng cộng {total_failed_revenue:,.2f} VND."
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
                (uuid.uuid4(), incident_id, node1_id, node2_id, "Causes", Decimal("0.0"), Decimal("0.9900")),
                (uuid.uuid4(), incident_id, node2_id, node3_id, "Causes", Decimal("15.0"), Decimal("0.9500")),
                (uuid.uuid4(), incident_id, node2_id, node4_id, "Amplifies", Decimal("30.0"), Decimal("0.8500")),
                (uuid.uuid4(), incident_id, node3_id, node5_id, "Causes", Decimal("60.0"), Decimal("0.9500")),
            ]

            cur.executemany("""
                INSERT INTO causal_links (
                    causal_link_id, incident_id, cause_node_id, effect_node_id,
                    relationship_type, lag_minutes, confidence
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, links_data)

            # Primary Root Cause
            cur.execute("""
                INSERT INTO incident_causes (
                    incident_cause_id, incident_id, node_id,
                    cause_rank, is_primary, confirmed_at
                ) VALUES (
                    gen_random_uuid(), %s, %s,
                    1, true, %s
                )
            """, (incident_id, node1_id, INCIDENT_END + timedelta(hours=1)))

            # Incident Evidence
            # Sample failed payment status history
            sample_psh = [h for h in created_payment_history if h[2] == "Failed"][0]
            sample_ticket = created_tickets[0]

            evidence_data = [
                (
                    uuid.uuid4(), incident_id, node2_id, "Log",
                    "payment_status_history", sample_psh[0], sample_psh[3],
                    "Mã lỗi GATEWAY_TIMEOUT xuất hiện dồn dập trong lịch sử trạng thái thanh toán của cổng MoMo.",
                    True
                ),
                (
                    uuid.uuid4(), incident_id, node2_id, "Metric",
                    None, None, INCIDENT_DETECTED,
                    "Tỷ lệ thất bại thanh toán của MoMo đạt 85.7% (so với baseline 1.35%), trong khi các cổng thanh toán khác vẫn bình thường (<3%).",
                    True
                ),
                (
                    uuid.uuid4(), incident_id, node4_id, "Record",
                    "customer_tickets", sample_ticket[0], sample_ticket[3],
                    "Khách hàng phản ánh giao dịch ví MoMo bị trừ tiền hoặc báo timeout nhưng không được xác nhận đơn hàng.",
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
                    uuid.uuid4(), incident_id, node5_id, "RevenueLoss",
                    INCIDENT_END + timedelta(hours=1), "failed_order_revenue_loss",
                    total_failed_revenue, total_failed_revenue, "VND"
                ),
                (
                    uuid.uuid4(), incident_id, node2_id, "SLADegradation",
                    INCIDENT_END + timedelta(hours=1), "momo_payment_success_rate",
                    Decimal("0.1429"), None, None
                ),
            ]

            cur.executemany("""
                INSERT INTO incident_outcomes (
                    incident_outcome_id, incident_id, node_id, outcome_type,
                    measured_at, metric_name, metric_value,
                    financial_impact, currency_code
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, outcomes_data)

            # 5. Layer 7 — Benchmark & Evaluation
            case_id = uuid.uuid4()
            case_name = "BENCHMARK-S003-PAYMENT-MOMO-20260815"

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
                datetime(2026, 8, 15, 0, 0, 0, tzinfo=timezone.utc),
                INCIDENT_CUTOFF
            ))

            # Benchmark Observations (Records observed up to cutoff time)
            observations_data = []
            for p in created_payments:
                if p[3] <= INCIDENT_CUTOFF:
                    observations_data.append((
                        uuid.uuid4(), case_id, "payments", p[0], p[3],
                        "Signal" if p[6] == "Failed" else "Context"
                    ))

            for t in created_tickets:
                if t[3] <= INCIDENT_CUTOFF:
                    observations_data.append((
                        uuid.uuid4(), case_id, "customer_tickets", t[0], t[3],
                        "Signal"
                    ))

            cur.executemany("""
                INSERT INTO benchmark_observations (
                    benchmark_observation_id, benchmark_case_id, source_table,
                    source_record_id, observed_at, observation_role
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, observations_data)

            # Evaluation Targets (Rubrics for AI Analyst Evaluation)
            targets_data = [
                (
                    uuid.uuid4(), case_id, "RootCause",
                    json.dumps({
                        "primary_root_cause": "PaymentGatewayDegradation",
                        "domain": "Payment",
                        "affected_channel_or_provider": "MoMo",
                        "expected_keywords": ["MoMo", "gateway", "cổng thanh toán", "timeout", "suy giảm", "lỗi kết nối", "dịch vụ thanh toán"]
                    }),
                    node1_id, Decimal("0.3000")
                ),
                (
                    uuid.uuid4(), case_id, "CausalPath",
                    json.dumps({
                        "required_nodes": ["RootCause", "Mechanism", "OperationalImpact", "Outcome"],
                        "causal_sequence": [
                            ["PaymentGatewayDegradation", "PaymentFailureSpike"],
                            ["PaymentFailureSpike", "OrderCancellationSpike"],
                            ["OrderCancellationSpike", "RevenueLoss"]
                        ]
                    }),
                    None, Decimal("0.2500")
                ),
                (
                    uuid.uuid4(), case_id, "AffectedEntity",
                    json.dumps({
                        "entity_type": "PaymentMethod",
                        "entity_name": "MoMo",
                        "entity_id": str(momo_id)
                    }),
                    node1_id, Decimal("0.1500")
                ),
                (
                    uuid.uuid4(), case_id, "Outcome",
                    json.dumps({
                        "metric_name": "failed_order_revenue_loss",
                        "expected_value": float(total_failed_revenue),
                        "tolerance_percent": 0.20,
                        "currency": "VND"
                    }),
                    node5_id, Decimal("0.1500")
                ),
                (
                    uuid.uuid4(), case_id, "RecommendedAction",
                    json.dumps({
                        "recommended_actions": [
                            "Tạm ẩn hoặc tắt cổng thanh toán MoMo trên trang thanh toán",
                            "Điều hướng khách hàng sang các phương thức thanh toán thay thế (VietQR / Chuyển khoản, Thẻ quốc tế, COD)",
                            "Liên hệ khẩn cấp đối tác MoMo để cập nhật tiến độ khắc phục sự cố kết nối",
                            "Gửi thông báo và voucher xin lỗi tới các khách hàng có giao dịch thất bại"
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

            # 6. Audit Log
            audit_meta = json.dumps({
                "scenario_id": "S003",
                "case_name": case_name,
                "total_orders": total_orders,
                "failed_orders": failed_count,
                "failed_revenue": float(total_failed_revenue),
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
        print("SCENARIO S003 INJECTION COMPLETED SUCCESSFULLY!")
        print(f"Incident ID: {incident_id}")
        print(f"Benchmark Case: {case_name}")
        print(f"Total Injected Orders: {total_orders} ({failed_count} failed, {success_count} succeeded)")
        print(f"Total Injected Tickets: {len(created_tickets)}")
        print(f"Total Unrealized Revenue Loss: {total_failed_revenue:,.2f} VND")
        print(f"Benchmark Pre-Cutoff Observations: {len(observations_data)}")
        print(f"Causal Nodes: {len(nodes_data)} | Links: {len(links_data)} | Targets: {len(targets_data)}")
        print("=" * 70)


if __name__ == "__main__":
    inject_s003()
