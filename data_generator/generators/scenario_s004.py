"""Scenario S004 Generator: Marketing Inefficiency (Phân bổ marketing không hiệu quả).

This module injects Scenario S004 into the Enterprise Digital Twin:
1. Operational Baseline:
   - Populates 4 baseline marketing campaigns across Facebook, Google Search, Website, and Mobile App with healthy ROAS (2.5x - 4.0x) and normal CAC (80k - 150k VND).
2. Operational Anomaly:
   - Injects high-budget campaign 'Mega Summer Tech Expo 2026' on channel 'TikTok' (Budget: 500M VND, Actual Spend: 485M VND).
   - Massive impression volume (1,200,000) and click volume (65,000), but conversions collapse to only 28 conversions (0.04% conversion rate).
   - CAC skyrockets to 17.3M VND per customer.
   - Financial marketing spend outflows recorded in `financial_transactions`.
3. Layer 5 (Incident Operational Metadata):
   - incidents: Surface incident registered with neutral summary.
   - incident_entities: Affected campaign entity.
4. Layer 6 (Causal Ground Truth DAG):
   - causal_nodes: 5 nodes (RootCause, Mechanism, OperationalImpact x2, Outcome).
   - causal_links: 4 directed causal edges forming a strict DAG.
   - incident_causes: Primary root cause confirmed.
   - incident_evidence: Decisive spend logs and conversion records.
   - incident_outcomes: Quantified net marketing loss (~450,000,000 VND).
5. Layer 7 (Benchmark & Evaluation):
   - benchmark_cases: Active test case with cutoff at 2026-08-10.
   - benchmark_observations: Allowlisted pre-cutoff operational signals.
   - evaluation_targets: Ground truth rubrics for AI Analyst evaluation.
6. Infrastructure:
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

S004_SEED = SEED + 4004
random.seed(S004_SEED)

SCENARIO_ID = "S004"
CAMPAIGN_NAME = "Mega Summer Tech Expo 2026"
CHANNEL_NAME = "TikTok"

INCIDENT_START = datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc)      # 07:00 ICT
INCIDENT_DETECTED = datetime(2026, 8, 5, 3, 0, 0, tzinfo=timezone.utc)   # 10:00 ICT
INCIDENT_CUTOFF = datetime(2026, 8, 10, 0, 0, 0, tzinfo=timezone.utc)    # 07:00 ICT
INCIDENT_END = datetime(2026, 8, 14, 16, 59, 59, tzinfo=timezone.utc)   # 23:59 ICT


def money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def clean_existing_s004(conn):
    """Cleanly purge any previously injected S004 data for idempotency."""
    with conn.cursor() as cur:
        cur.execute("SELECT incident_id FROM incidents WHERE scenario_id = %s", (SCENARIO_ID,))
        row = cur.fetchone()
        if not row:
            return

        incident_id = row["incident_id"]
        print(f"Purging existing S004 data for incident {incident_id}...")

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
        cur.execute("SELECT object_id FROM audit_log WHERE action_type = 'INJECT_S004_CAMPAIGN'")
        injected_campaign_ids = [r["object_id"] for r in cur.fetchall()]

        if injected_campaign_ids:
            cur.execute("DELETE FROM financial_transactions WHERE campaign_id = ANY(%s)", (injected_campaign_ids,))
            cur.execute("DELETE FROM marketing_events WHERE campaign_id = ANY(%s)", (injected_campaign_ids,))
            cur.execute("DELETE FROM marketing_campaigns WHERE campaign_id = ANY(%s)", (injected_campaign_ids,))

        # Delete incident itself
        cur.execute("DELETE FROM incidents WHERE incident_id = %s", (incident_id,))
        cur.execute("DELETE FROM audit_log WHERE action_type LIKE 'INJECT_%%' AND (metadata->>'scenario_id' = %s OR object_id = %s)", (SCENARIO_ID, incident_id))
        print("Previous S004 data successfully purged.")


def ensure_marketing_baseline(cur):
    """Generates baseline marketing campaigns if none exist."""
    cur.execute("SELECT COUNT(*) AS count FROM marketing_campaigns")
    if cur.fetchone()["count"] > 0:
        return

    print("Generating baseline marketing campaigns...")
    baseline_campaigns = [
        (uuid.uuid4(), "Brand Awareness Q1 2026", "Facebook", datetime(2026, 1, 15, tzinfo=timezone.utc), datetime(2026, 3, 31, tzinfo=timezone.utc), Decimal("80000000.00"), "VND", "Completed"),
        (uuid.uuid4(), "Back to School Promotion", "Website", datetime(2026, 6, 1, tzinfo=timezone.utc), datetime(2026, 7, 31, tzinfo=timezone.utc), Decimal("120000000.00"), "VND", "Completed"),
        (uuid.uuid4(), "App First Order Discount", "Mobile App", datetime(2026, 5, 1, tzinfo=timezone.utc), datetime(2026, 8, 30, tzinfo=timezone.utc), Decimal("50000000.00"), "VND", "Active"),
        (uuid.uuid4(), "Google Search Tech Keywords", "Search", datetime(2026, 4, 1, tzinfo=timezone.utc), datetime(2026, 8, 31, tzinfo=timezone.utc), Decimal("90000000.00"), "VND", "Active"),
    ]

    cur.executemany("""
        INSERT INTO marketing_campaigns (
            campaign_id, campaign_name, channel, start_time,
            end_time, budget_amount, currency_code, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, baseline_campaigns)

    # Insert baseline events & spend
    for camp in baseline_campaigns:
        camp_id = camp[0]
        # Spend transaction
        cur.execute("""
            INSERT INTO financial_transactions (
                transaction_timestamp, transaction_type, amount,
                currency_code, campaign_id, reference_code
            ) VALUES (%s, 'MarketingSpend', %s, 'VND', %s, %s)
        """, (camp[3], -camp[5], camp_id, f"MKT-BASE-{str(camp_id)[:8]}"))

        # Impressions and clicks
        cur.execute("""
            INSERT INTO marketing_events (
                campaign_id, event_timestamp, event_type, metric_value, cost_amount
            ) VALUES 
            (%s, %s, 'Impression', 500000, 0),
            (%s, %s, 'Click', 25000, 0),
            (%s, %s, 'Conversion', 1250, 0)
        """, (camp_id, camp[3], camp_id, camp[3] + timedelta(days=1), camp_id, camp[3] + timedelta(days=2)))

    print(f"Generated {len(baseline_campaigns)} baseline marketing campaigns.")


def inject_s004():
    with get_connection() as conn:
        with conn.cursor() as cur:
            clean_existing_s004(conn)
            ensure_marketing_baseline(cur)

            # 1. Create S004 Anomalous Campaign
            campaign_id = uuid.uuid4()
            budget = Decimal("500000000.00")
            actual_spend = Decimal("485000000.00")
            generated_revenue = Decimal("35000000.00") # only 35M revenue generated
            net_loss = actual_spend - generated_revenue  # 450,000,000 VND

            cur.execute("""
                INSERT INTO marketing_campaigns (
                    campaign_id, campaign_name, channel, start_time,
                    end_time, budget_amount, currency_code, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                campaign_id, CAMPAIGN_NAME, CHANNEL_NAME,
                INCIDENT_START, INCIDENT_END, budget, "VND", "Completed"
            ))

            # 2. Financial spend transactions
            # 3 spend tranches during the campaign
            spend_tranches = [
                (INCIDENT_START + timedelta(days=1), Decimal("150000000.00")),
                (INCIDENT_START + timedelta(days=5), Decimal("200000000.00")),
                (INCIDENT_START + timedelta(days=9), Decimal("135000000.00")),
            ]

            created_fin_txns = []
            for idx, (ttime, amt) in enumerate(spend_tranches):
                created_fin_txns.append((
                    ttime, "MarketingSpend", -amt, "VND",
                    campaign_id, f"MKT-S004-TIKTOK-{idx:02d}"
                ))

            cur.executemany("""
                INSERT INTO financial_transactions (
                    transaction_timestamp, transaction_type, amount,
                    currency_code, campaign_id, reference_code
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, created_fin_txns)

            # 3. Marketing Events (Massive impressions/clicks, dismal conversions)
            events_data = [
                # Impressions: 1.2M
                (uuid.uuid4(), campaign_id, INCIDENT_START + timedelta(days=2), "Impression", Decimal("1200000"), None),
                # Clicks: 65k
                (uuid.uuid4(), campaign_id, INCIDENT_START + timedelta(days=3), "Click", Decimal("65000"), None),
                # Spend event: 485M
                (uuid.uuid4(), campaign_id, INCIDENT_START + timedelta(days=6), "Spend", Decimal("485000000"), actual_spend),
                # Conversions: only 28 orders!
                (uuid.uuid4(), campaign_id, INCIDENT_START + timedelta(days=7), "Conversion", Decimal("28"), None),
            ]

            cur.executemany("""
                INSERT INTO marketing_events (
                    marketing_event_id, campaign_id, event_timestamp,
                    event_type, metric_value, cost_amount
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, events_data)

            # Audit log
            cur.execute("""
                INSERT INTO audit_log (
                    audit_log_id, event_timestamp, actor_role,
                    action_type, object_type, object_id, success, metadata
                ) VALUES (
                    gen_random_uuid(), %s, 'edt_simulator',
                    'INJECT_S004_CAMPAIGN', 'Campaign', %s, true,
                    jsonb_build_object('scenario_id', 'S004')
                )
            """, (INCIDENT_START, campaign_id))

            # 4. Layer 5: Incidents
            incident_id = uuid.uuid4()
            neutral_summary = "Hệ thống ghi nhận chi phí quảng cáo (Ad Spend) trên kênh TikTok tăng đột biến trong nửa đầu tháng 08/2026 nhưng tỷ lệ chuyển đổi đơn hàng và doanh thu ghi nhận sụt giảm nghiêm trọng so với kỳ vọng ngân sách."

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
                "High", "Marketing", "Closed", neutral_summary
            ))

            cur.execute("""
                INSERT INTO incident_entities (
                    incident_entity_id, incident_id, entity_type,
                    entity_id, observed_at, impact_type, impact_severity
                ) VALUES (
                    gen_random_uuid(), %s, 'Campaign', %s,
                    %s, 'MARKETING_INEFFICIENCY_SAMPLE', 0.9000
                )
            """, (incident_id, campaign_id, INCIDENT_DETECTED))

            # 5. Layer 6: Causal Ground Truth DAG
            node1_id = uuid.uuid4()
            node2_id = uuid.uuid4()
            node3_id = uuid.uuid4()
            node4_id = uuid.uuid4()
            node5_id = uuid.uuid4()

            nodes_data = [
                (
                    node1_id, incident_id, "RootCause", "Marketing",
                    "Campaign", campaign_id, INCIDENT_START, INCIDENT_END,
                    "Phân bổ ngân sách marketing không hiệu quả (Audience Mismatch)",
                    "Chiến dịch Mega Summer Tech Expo trên TikTok bị sai lệch tệp khách hàng mục tiêu, tiếp cận lưu lượng rác không có nhu cầu mua hàng."
                ),
                (
                    node2_id, incident_id, "Mechanism", "Marketing",
                    "Campaign", campaign_id, INCIDENT_START + timedelta(days=1), INCIDENT_END,
                    "Tăng vọt chi phí quảng cáo (Ad Spend Surge)",
                    "Ngân sách quảng cáo giải ngân 485 triệu VND với hơn 1.2 triệu lượt hiển thị nhưng lưu lượng kém chất lượng."
                ),
                (
                    node3_id, incident_id, "OperationalImpact", "Marketing",
                    None, None, INCIDENT_START + timedelta(days=3), INCIDENT_END,
                    "Tỷ lệ chuyển đổi sụp đổ (Conversion Rate Plunge)",
                    "Tỷ lệ chuyển đổi từ click sang đơn hàng sụt giảm xuống còn 0.04% (so với baseline 2.8%), chỉ tạo ra 28 đơn hàng."
                ),
                (
                    node4_id, incident_id, "OperationalImpact", "Finance",
                    None, None, INCIDENT_START + timedelta(days=5), INCIDENT_END,
                    "Chi phí sở hữu khách hàng tăng phi mã (CAC Spike)",
                    "Chi phí sở hữu khách hàng (Customer Acquisition Cost) tăng vọt lên 17.3 triệu VND/khách hàng (gấp hơn 100 lần bình thường)."
                ),
                (
                    node5_id, incident_id, "Outcome", "Finance",
                    None, None, INCIDENT_START, INCIDENT_END,
                    "Tổn thất lợi nhuận và lãng phí ngân sách tiếp thị",
                    f"Thất thoát tài chính ròng từ ngân sách marketing không hoàn vốn đạt {net_loss:,.2f} VND."
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
                (uuid.uuid4(), incident_id, node3_id, node4_id, "Causes", Decimal("24.0"), Decimal("0.9200")),
                (uuid.uuid4(), incident_id, node4_id, node5_id, "Causes", Decimal("24.0"), Decimal("0.9500")),
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

            cur.execute("""
                INSERT INTO incident_evidence (
                    incident_evidence_id, incident_id, node_id, evidence_type,
                    source_table, source_record_id, evidence_timestamp,
                    evidence_summary, is_decisive
                ) VALUES 
                (%s, %s, %s, 'Log', 'financial_transactions', %s, %s, 'Bút toán chi tiêu marketing 485 triệu VND trên kênh TikTok.', true),
                (%s, %s, %s, 'Metric', 'marketing_events', %s, %s, 'Tỷ lệ chuyển đổi chỉ đạt 28 lượt trên 65,000 lượt click.', true)
            """, (
                ev1_id, incident_id, node2_id, created_fin_txns[0][4], created_fin_txns[0][0],
                ev2_id, incident_id, node3_id, events_data[3][0], events_data[3][2]
            ))

            outcomes_data = [
                (
                    uuid.uuid4(), incident_id, node5_id, "RevenueLoss",
                    INCIDENT_END + timedelta(hours=1), "net_marketing_loss",
                    net_loss, net_loss, "VND"
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
            case_name = "BENCHMARK-S004-MARKETING-TIKTOK-20260805"
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
            obs_rows = [
                (uuid.uuid4(), case_id, "marketing_campaigns", campaign_id, INCIDENT_START, "Signal"),
            ]
            for ev in events_data:
                if ev[2] <= INCIDENT_CUTOFF:
                    obs_rows.append((uuid.uuid4(), case_id, "marketing_events", ev[0], ev[2], "Context"))

            cur.executemany("""
                INSERT INTO benchmark_observations (
                    benchmark_observation_id, benchmark_case_id,
                    source_table, source_record_id, observed_at, observation_role
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (benchmark_case_id, source_table, source_record_id) DO NOTHING
            """, obs_rows)

            eval_targets = [
                (uuid.uuid4(), case_id, "RootCause", node1_id, Decimal("0.3000"), {
                    "domain": "Marketing",
                    "primary_root_cause": "MarketingInefficiency",
                    "affected_channel": CHANNEL_NAME,
                    "expected_keywords": ["marketing", "TikTok", "chi phí", "ngân sách", "chuyển đổi", "quảng cáo", "CAC", "hiệu quả"]
                }),
                (uuid.uuid4(), case_id, "CausalPath", None, Decimal("0.2500"), {
                    "required_nodes": ["RootCause", "Mechanism", "OperationalImpact", "Outcome"],
                    "causal_sequence": [
                        ["MarketingInefficiency", "AdSpendSurge"],
                        ["AdSpendSurge", "ConversionRatePlunge"],
                        ["ConversionRatePlunge", "CACSpike"],
                        ["CACSpike", "NetProfitErosion"]
                    ]
                }),
                (uuid.uuid4(), case_id, "AffectedEntity", node1_id, Decimal("0.1500"), {
                    "entity_id": str(campaign_id),
                    "entity_name": CAMPAIGN_NAME,
                    "entity_type": "Campaign"
                }),
                (uuid.uuid4(), case_id, "Outcome", node5_id, Decimal("0.1500"), {
                    "metric_name": "net_marketing_loss",
                    "expected_value": float(net_loss),
                    "currency": "VND",
                    "tolerance_percent": 0.20
                }),
                (uuid.uuid4(), case_id, "RecommendedAction", None, Decimal("0.1500"), {
                    "recommended_actions": [
                        "Tạm dừng ngay chiến dịch quảng cáo TikTok đang bị lãng phí ngân sách",
                        "Rà soát và tái cấu trúc tệp đối tượng nhắm mục tiêu (Targeting Audience & Pixels)",
                        "Điều chuyển ngân sách marketing chưa giải ngân sang các kênh có ROAS dương (Search, Facebook)",
                        "Kiểm tra và tối ưu hóa tỷ lệ chuyển đổi trên trang đích (Landing Page UX & Funnel)"
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
            print(f"[SUCCESS] Scenario S004 (Marketing Inefficiency) successfully injected.")
            print(f"  Incident ID    : {incident_id}")
            print(f"  Benchmark Case : {case_name}")
            print(f"  Campaign Name  : {CAMPAIGN_NAME} ({CHANNEL_NAME})")
            print(f"  Net Loss       : {net_loss:,.2f} VND")


if __name__ == "__main__":
    inject_s004()
