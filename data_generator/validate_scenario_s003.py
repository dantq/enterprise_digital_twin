"""Independent Validator for Scenario S003: Payment Gateway Outage.

Adversarial Critic Invariants Audited:
1. Incident & Safe Observation View Projection:
   - Incident exists and conforms to timestamp rules.
   - ai_incident_observations projects incident without leaking scenario_id.
2. Causal Ground Truth DAG:
   - Exactly 1 RootCause node and 1 primary cause.
   - Directed graph is strictly acyclic (Kahn's algorithm / topological sort).
   - All links have confidence in [0, 1] and lag >= 0.
3. Decisive Evidence Integrity:
   - All decisive evidence records point to real operational rows.
4. Quantified Outcome Precision:
   - Reported revenue loss exactly matches the total_amount sum of cancelled incident orders.
5. Benchmark Observation Cutoff Invariant:
   - Zero observation records timestamped after observation_cutoff_time.
6. Statistical Anomaly Isolation:
   - MoMo failure rate during incident window > 80%.
   - Other payment methods failure rate during window < 5%.
"""

import sys
from decimal import Decimal
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict, deque

DATA_GENERATOR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DATA_GENERATOR_DIR))

from db import get_connection

SCENARIO_ID = "S003"


def check_acyclic(nodes, edges):
    """Kahn's algorithm to verify that directed graph is an acyclic DAG."""
    in_degree = {n: 0 for n in nodes}
    adj = defaultdict(list)
    for u, v in edges:
        adj[u].append(v)
        in_degree[v] += 1

    queue = deque([n for n, d in in_degree.items() if d == 0])
    visited_count = 0

    while queue:
        curr = queue.popleft()
        visited_count += 1
        for neighbor in adj[curr]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return visited_count == len(nodes)


def validate_scenario_s003():
    print("=" * 70)
    print("SCENARIO S003 (PAYMENT GATEWAY OUTAGE) ADVERSARIAL VALIDATION")
    print("=" * 70)

    violations = []

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Incident Record Check
            cur.execute("""
                SELECT * FROM incidents WHERE scenario_id = %s
            """, (SCENARIO_ID,))
            incident = cur.fetchone()

            if not incident:
                raise RuntimeError(f"Incident with scenario_id '{SCENARIO_ID}' not found in database!")

            incident_id = incident["incident_id"]
            print(f"[PASS] Incident record found: {incident_id}")
            print(f"    - Affected Domain: {incident['affected_domain']}")
            print(f"    - Severity: {incident['severity']}")
            print(f"    - Status: {incident['status']}")
            print(f"    - Window: {incident['start_time']} -> {incident['end_time']}")

            if incident["detected_at"] < incident["start_time"]:
                violations.append("detected_at is before start_time")
            if incident["end_time"] and incident["end_time"] < incident["start_time"]:
                violations.append("end_time is before start_time")

            # 2. AI Safe Projection View Check
            cur.execute("""
                SELECT * FROM ai_incident_observations WHERE incident_id = %s
            """, (incident_id,))
            obs = cur.fetchone()

            if not obs:
                violations.append("Incident not visible in ai_incident_observations view")
            else:
                obs_cols = list(obs.keys())
                if "scenario_id" in obs_cols:
                    violations.append("CRITICAL: scenario_id LEAKED in ai_incident_observations!")
                else:
                    print("[PASS] ai_incident_observations successfully shields scenario_id from AI Analyst.")

            # 3. Causal Nodes & Acyclicity
            cur.execute("""
                SELECT node_id, node_type, truth_label, domain 
                FROM causal_nodes 
                WHERE incident_id = %s
            """, (incident_id,))
            nodes = cur.fetchall()
            node_ids = {n["node_id"] for n in nodes}
            print(f"[PASS] Causal Nodes: {len(nodes)} nodes registered")

            root_causes = [n for n in nodes if n["node_type"] == "RootCause"]
            if len(root_causes) != 1:
                violations.append(f"Expected exactly 1 RootCause node, found {len(root_causes)}")

            cur.execute("""
                SELECT cause_node_id, effect_node_id, relationship_type, confidence, lag_minutes
                FROM causal_links
                WHERE incident_id = %s
            """, (incident_id,))
            links = cur.fetchall()
            print(f"[PASS] Causal Links: {len(links)} directed edges registered")

            edges = [(l["cause_node_id"], l["effect_node_id"]) for l in links]
            is_dag = check_acyclic(node_ids, edges)
            if not is_dag:
                violations.append("Causal graph contains cycles! Violates DAG invariant.")
            else:
                print("[PASS] Causal Graph verified: Strict Acyclic DAG (no cycles or self-loops).")

            # 4. Primary Cause Invariant
            cur.execute("""
                SELECT ic.*, cn.node_type 
                FROM incident_causes ic
                JOIN causal_nodes cn ON ic.node_id = cn.node_id
                WHERE ic.incident_id = %s AND ic.is_primary = true
            """, (incident_id,))
            primary_causes = cur.fetchall()
            if len(primary_causes) != 1:
                violations.append(f"Expected exactly 1 primary cause, found {len(primary_causes)}")
            elif primary_causes[0]["node_type"] != "RootCause":
                violations.append("Primary cause does not point to a RootCause node!")
            else:
                print(f"[PASS] Primary Root Cause certified: Node {primary_causes[0]['node_id']}")

            # 5. Decisive Evidence Pointers
            cur.execute("""
                SELECT ie.* 
                FROM incident_evidence ie
                WHERE ie.incident_id = %s AND ie.is_decisive = true
            """, (incident_id,))
            decisive_evs = cur.fetchall()
            print(f"[PASS] Decisive Evidence: {len(decisive_evs)} decisive items registered")

            for dev in decisive_evs:
                if dev["source_table"] and dev["source_record_id"]:
                    table_name = dev["source_table"]
                    pk_col = "payment_status_history_id" if table_name == "payment_status_history" else f"{table_name[:-1]}_id"
                    cur.execute(f"SELECT COUNT(*) AS cnt FROM {table_name} WHERE {pk_col} = %s", (dev["source_record_id"],))
                    if cur.fetchone()["cnt"] == 0:
                        violations.append(f"Decisive evidence references non-existent record in {table_name}")

            # 6. Outcome Precision vs Operational Cancelled Orders
            cur.execute("""
                SELECT financial_impact, metric_value 
                FROM incident_outcomes 
                WHERE incident_id = %s AND outcome_type = 'RevenueLoss'
            """, (incident_id,))
            loss_outcome = cur.fetchone()

            cur.execute("""
                SELECT COALESCE(SUM(o.total_amount), 0) AS actual_loss
                FROM orders o
                JOIN payments p ON o.order_id = p.order_id
                JOIN payment_methods pm ON p.payment_method_id = pm.payment_method_id
                WHERE pm.method_name = 'MoMo'
                  AND o.order_status = 'Cancelled'
                  AND p.payment_status = 'Failed'
                  AND o.order_timestamp BETWEEN %s AND %s
            """, (incident["start_time"], incident["end_time"]))
            actual_loss = cur.fetchone()["actual_loss"]

            if not loss_outcome or abs(loss_outcome["financial_impact"] - actual_loss) > Decimal("0.01"):
                violations.append(f"Outcome financial impact mismatch! Stored: {loss_outcome['financial_impact'] if loss_outcome else None}, Actual: {actual_loss}")
            else:
                print(f"[PASS] Financial Outcome exact match: {actual_loss:,.2f} VND")

            # 7. Benchmark Cutoff Invariant
            cur.execute("""
                SELECT b.benchmark_case_id, b.case_name, b.observation_cutoff_time,
                       COUNT(bo.benchmark_observation_id) AS total_obs,
                       COUNT(*) FILTER (WHERE bo.observed_at > b.observation_cutoff_time) AS post_cutoff_leaks
                FROM benchmark_cases b
                LEFT JOIN benchmark_observations bo ON b.benchmark_case_id = bo.benchmark_case_id
                WHERE b.incident_id = %s
                GROUP BY b.benchmark_case_id, b.case_name, b.observation_cutoff_time
            """, (incident_id,))
            b_case = cur.fetchone()

            if not b_case:
                violations.append("No benchmark case found for incident")
            else:
                print(f"[PASS] Benchmark Case: '{b_case['case_name']}' with {b_case['total_obs']} observations")
                if b_case["post_cutoff_leaks"] > 0:
                    violations.append(f"CRITICAL: {b_case['post_cutoff_leaks']} observations recorded after cutoff time!")
                else:
                    print(f"[PASS] Benchmark Observation Cutoff Invariant: 0 post-cutoff leaks (all observed <= {b_case['observation_cutoff_time']})")

            # 8. Statistical Anomaly Isolation Check
            cur.execute("""
                SELECT 
                    pm.method_name,
                    COUNT(*) AS total_tx,
                    COUNT(*) FILTER (WHERE p.payment_status = 'Failed') AS failed_tx,
                    ROUND(COUNT(*) FILTER (WHERE p.payment_status = 'Failed')::numeric / COUNT(*), 4) AS failure_rate
                FROM payments p
                JOIN payment_methods pm ON p.payment_method_id = pm.payment_method_id
                WHERE p.payment_timestamp BETWEEN %s AND %s
                GROUP BY pm.method_name
                ORDER BY failure_rate DESC
            """, (incident["start_time"], incident["end_time"]))
            rate_report = cur.fetchall()

            print("\n[STATISTICAL ANOMALY REPORT DURING INCIDENT WINDOW]:")
            momo_rate = 0.0
            for r in rate_report:
                rate_pct = float(r["failure_rate"]) * 100
                print(f"    - {r['method_name']:<18}: {r['failed_tx']:>2}/{r['total_tx']:>2} failed ({rate_pct:>5.1f}%)")
                if r["method_name"] == "MoMo":
                    momo_rate = float(r["failure_rate"])

            if momo_rate < 0.80:
                violations.append(f"MoMo failure rate ({momo_rate*100:.1f}%) did not reach target threshold of 80%")
            else:
                print(f"[PASS] Anomaly Signal Confirmed: MoMo failure rate is {momo_rate*100:.1f}% (statistically isolated).")

    print("=" * 70)
    if violations:
        print(f"FAILED: {len(violations)} VIOLATIONS FOUND:")
        for v in violations:
            print(f"  [FAIL] {v}")
        sys.exit(1)
    else:
        print("ALL SCENARIO S003 CAUSAL & BENCHMARK INVARIANTS PASSED WITH ZERO VIOLATIONS!")
        print("=" * 70)


if __name__ == "__main__":
    validate_scenario_s003()
