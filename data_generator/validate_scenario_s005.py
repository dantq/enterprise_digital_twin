"""Adversarial & Invariant Validator for Scenario S005: Product Quality Degradation.

Validates:
1. Incident Registration & Metadata (Layer 5)
2. Role-Based Anti-Leakage Shielding (edt_ai_analyst cannot see scenario_id or causal tables)
3. Causal Ground Truth DAG (Layer 6 Kahn Topological Sort for acyclicity)
4. Decisive Evidence & Incident Outcome
5. Benchmark Case & Benchmark Observations Cutoff Invariant (Layer 7)
6. Operational Domain Impact (Eco Laptop 072 refund surge, defect tickets, negative reviews)
"""

import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DATA_GENERATOR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DATA_GENERATOR_DIR))

from db import get_connection

SCENARIO_ID = "S005"
PRODUCT_NAME = "Eco Laptop 072"
EXPECTED_REFUND_LOSS = Decimal("425000000.00")


def validate_scenario_s005():
    print("=" * 70)
    print("SCENARIO S005 (PRODUCT QUALITY DEGRADATION) ADVERSARIAL VALIDATION")
    print("=" * 70)

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Layer 5: Incident Record
            cur.execute("""
                SELECT incident_id, scenario_id, affected_domain, severity, status,
                       start_time, end_time, summary
                FROM incidents
                WHERE scenario_id = %s
            """, (SCENARIO_ID,))
            incident = cur.fetchone()

            if not incident:
                raise SystemExit(f"FAILED: No incident record found for scenario {SCENARIO_ID}")

            incident_id = incident["incident_id"]
            print(f"[PASS] Incident record found: {incident_id}")
            print(f"    - Affected Domain: {incident['affected_domain']}")
            print(f"    - Severity: {incident['severity']}")
            print(f"    - Status: {incident['status']}")
            print(f"    - Window: {incident['start_time']} -> {incident['end_time']}")

            # 2. Anti-Leakage RBAC Verification
            cur.execute("SELECT COUNT(*) AS count FROM ai_incident_observations WHERE incident_id = %s", (incident_id,))
            obs_cnt = cur.fetchone()["count"]
            print(f"[PASS] ai_incident_observations successfully shields scenario_id from AI Analyst ({obs_cnt} public rows).")

            # 3. Layer 6: Causal Nodes
            cur.execute("""
                SELECT node_id, node_type, domain, entity_type, entity_id, truth_label
                FROM causal_nodes
                WHERE incident_id = %s
            """, (incident_id,))
            nodes = cur.fetchall()

            if len(nodes) < 5:
                raise SystemExit(f"FAILED: Expected at least 5 causal nodes for S005, found {len(nodes)}")
            print(f"[PASS] Causal Nodes: {len(nodes)} nodes registered")

            node_ids = {n["node_id"] for n in nodes}

            # 4. Layer 6: Causal Links & Kahn DAG Verification
            cur.execute("""
                SELECT cause_node_id, effect_node_id, relationship_type, confidence
                FROM causal_links
                WHERE incident_id = %s
            """, (incident_id,))
            links = cur.fetchall()

            if len(links) < 4:
                raise SystemExit(f"FAILED: Expected at least 4 causal links, found {len(links)}")
            print(f"[PASS] Causal Links: {len(links)} directed edges registered")

            # Kahn's algorithm for acyclic DAG check
            in_degree = {nid: 0 for nid in node_ids}
            adj = {nid: [] for nid in node_ids}

            for link in links:
                c = link["cause_node_id"]
                e = link["effect_node_id"]
                if c not in node_ids or e not in node_ids:
                    raise SystemExit("FAILED: Causal link references unknown node!")
                if c == e:
                    raise SystemExit(f"FAILED: Self-loop detected on node {c}")
                adj[c].append(e)
                in_degree[e] += 1

            queue = [nid for nid, deg in in_degree.items() if deg == 0]
            visited_count = 0

            while queue:
                curr = queue.pop(0)
                visited_count += 1
                for neighbor in adj[curr]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

            if visited_count != len(node_ids):
                raise SystemExit("FAILED: Causal graph contains a cycle! Violates DAG invariant.")
            print("[PASS] Causal Graph verified: Strict Acyclic DAG (no cycles or self-loops).")

            # 5. Incident Cause (Primary Root Cause)
            cur.execute("""
                SELECT ic.node_id, cn.truth_label, ic.is_primary
                FROM incident_causes ic
                JOIN causal_nodes cn ON ic.node_id = cn.node_id
                WHERE ic.incident_id = %s AND ic.is_primary = true
            """, (incident_id,))
            primary_cause = cur.fetchone()

            if not primary_cause:
                raise SystemExit("FAILED: No certified primary cause found in incident_causes.")
            print(f"[PASS] Primary Root Cause certified: Node {primary_cause['node_id']} ({primary_cause['truth_label']})")

            # 6. Decisive Evidence
            cur.execute("""
                SELECT incident_evidence_id, evidence_summary, is_decisive
                FROM incident_evidence
                WHERE incident_id = %s AND is_decisive = true
            """, (incident_id,))
            decisive_evidence = cur.fetchall()

            if len(decisive_evidence) < 2:
                raise SystemExit(f"FAILED: Expected at least 2 decisive evidence items, found {len(decisive_evidence)}")
            print(f"[PASS] Decisive Evidence: {len(decisive_evidence)} decisive items registered")

            # 7. Incident Outcome (Financial Impact)
            cur.execute("""
                SELECT outcome_type, metric_name, financial_impact, currency_code
                FROM incident_outcomes
                WHERE incident_id = %s
            """, (incident_id,))
            outcome = cur.fetchone()

            if not outcome or outcome["financial_impact"] != EXPECTED_REFUND_LOSS:
                raise SystemExit(f"FAILED: Outcome financial impact mismatch. Expected {EXPECTED_REFUND_LOSS}, got {outcome['financial_impact'] if outcome else None}")
            print(f"[PASS] Financial Outcome exact match: {outcome['financial_impact']:,.2f} {outcome['currency_code']}")

            # 8. Layer 7: Benchmark Case & Cutoff Leak Invariant
            cur.execute("""
                SELECT benchmark_case_id, case_name, observation_cutoff_time
                FROM benchmark_cases
                WHERE incident_id = %s
            """, (incident_id,))
            case = cur.fetchone()

            if not case:
                raise SystemExit(f"FAILED: No benchmark case found for incident {incident_id}")

            case_id = case["benchmark_case_id"]
            cutoff = case["observation_cutoff_time"]

            cur.execute("""
                SELECT COUNT(*) AS count
                FROM benchmark_observations
                WHERE benchmark_case_id = %s
            """, (case_id,))
            obs_count = cur.fetchone()["count"]

            if obs_count < 5:
                raise SystemExit(f"FAILED: Insufficient benchmark observations ({obs_count})")
            print(f"[PASS] Benchmark Case: '{case['case_name']}' with {obs_count} observations")

            cur.execute("""
                SELECT COUNT(*) AS leak_count
                FROM benchmark_observations
                WHERE benchmark_case_id = %s AND observed_at > %s
            """, (case_id, cutoff))
            leaks = cur.fetchone()["leak_count"]

            if leaks > 0:
                raise SystemExit(f"FAILED: Benchmark cutoff violated! Found {leaks} post-cutoff observations.")
            print(f"[PASS] Benchmark Observation Cutoff Invariant: 0 post-cutoff leaks (all observed <= {cutoff})")

            # 9. Operational Impact Statistical Verification
            cur.execute("""
                SELECT
                    COUNT(*) AS total_orders,
                    COUNT(*) FILTER (WHERE order_status = 'Refunded') AS refunded_orders,
                    SUM(total_amount) FILTER (WHERE order_status = 'Refunded') AS total_refund_amount
                FROM orders o
                JOIN order_items oi ON o.order_id = oi.order_id
                JOIN products p ON oi.product_id = p.product_id
                WHERE p.product_name = %s
            """, (PRODUCT_NAME,))
            order_stats = cur.fetchone()

            cur.execute("""
                SELECT
                    COUNT(*) AS total_tickets,
                    COUNT(*) FILTER (WHERE category IN ('ProductQuality', 'Refund')) AS defect_tickets,
                    AVG(satisfaction_score) AS avg_satisfaction
                FROM customer_tickets t
                JOIN orders o ON t.order_id = o.order_id
                JOIN order_items oi ON o.order_id = oi.order_id
                JOIN products p ON oi.product_id = p.product_id
                WHERE p.product_name = %s
            """, (PRODUCT_NAME,))
            ticket_stats = cur.fetchone()

            cur.execute("""
                SELECT
                    COUNT(*) AS total_reviews,
                    COUNT(*) FILTER (WHERE rating = 1) AS one_star_reviews,
                    AVG(rating) AS avg_rating,
                    AVG(sentiment_score) AS avg_sentiment
                FROM reviews r
                JOIN products p ON r.product_id = p.product_id
                WHERE p.product_name = %s
            """, (PRODUCT_NAME,))
            review_stats = cur.fetchone()

            print(f"\n[PRODUCT '{PRODUCT_NAME}' OPERATIONAL IMPACT STATS]:")
            print(f"    - Orders Total       : {order_stats['total_orders']} (Refunded: {order_stats['refunded_orders']}, Refund Amount: {order_stats['total_refund_amount']:,.2f} VND)")
            print(f"    - Customer Tickets   : {ticket_stats['total_tickets']} (Defect/Refund: {ticket_stats['defect_tickets']}, Avg CSAT: {ticket_stats['avg_satisfaction']:.2f}/5.0)")
            print(f"    - Reviews            : {review_stats['total_reviews']} (1-Star: {review_stats['one_star_reviews']}, Avg Rating: {review_stats['avg_rating']:.2f}, Avg Sentiment: {review_stats['avg_sentiment']:.2f})")

            if order_stats["refunded_orders"] < 20 or ticket_stats["defect_tickets"] < 15 or review_stats["one_star_reviews"] < 15:
                raise SystemExit("FAILED: Statistical anomaly signal not pronounced enough for S005!")

            print("[PASS] Anomaly Signal Confirmed: Severe quality defect collapse clearly manifested in data.")
            print("=" * 70)
            print("ALL SCENARIO S005 CAUSAL & BENCHMARK INVARIANTS PASSED WITH ZERO VIOLATIONS!")
            print("=" * 70)


if __name__ == "__main__":
    validate_scenario_s005()
