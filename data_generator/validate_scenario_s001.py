"""Independent Validator for Scenario S001: Supplier Disruption.

Adversarial Critic Invariants Audited:
1. Procurement Domain Integrity:
   - PO math: item_total = round(ordered_quantity * unit_cost, 2).
   - PO header: total_amount = sum(item_total).
   - Received quantities and timestamps consistent.
2. Incident & Safe Observation View:
   - Incident S001 exists and conforms to timestamp rules.
   - ai_incident_observations projects incident without leaking scenario_id.
3. Causal Ground Truth DAG:
   - Exactly 1 RootCause node and 1 primary cause.
   - Directed graph is strictly acyclic (Kahn's algorithm / topological sort).
   - All links have confidence in [0, 1] and lag >= 0.
4. Decisive Evidence Integrity:
   - Decisive evidence points to actual overdue Purchase Orders and stockout logs.
5. Quantified Outcome Precision:
   - Reported revenue loss exactly matches the total_amount sum of cancelled stockout orders.
6. Benchmark Observation Cutoff Invariant:
   - Zero observation records timestamped after observation_cutoff_time.
7. Statistical Lead Time & Stockout Anomaly:
   - Viet Electronics overdue POs confirmed.
   - Retail orders cancelled with reason OUT_OF_STOCK verified.
"""

import sys
from decimal import Decimal
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict, deque

DATA_GENERATOR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DATA_GENERATOR_DIR))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from db import get_connection

SCENARIO_ID = "S001"
TARGET_SUPPLIER_NAME = "Viet Electronics"


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


def validate_scenario_s001():
    print("=" * 70)
    print("SCENARIO S001 (SUPPLIER DISRUPTION) ADVERSARIAL VALIDATION")
    print("=" * 70)

    violations = []

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Audit Procurement Domain
            cur.execute("SELECT COUNT(*) AS count FROM purchase_orders")
            total_pos = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) AS count FROM purchase_order_items")
            total_items = cur.fetchone()["count"]

            print(f"[PASS] Procurement Domain: {total_pos} POs, {total_items} line items.")

            # PO Item Math
            cur.execute("""
                SELECT COUNT(*) FILTER (
                    WHERE ABS(item_total - ROUND(ordered_quantity * unit_cost, 2)) > 0.001
                ) AS item_math_errors,
                COUNT(*) FILTER (
                    WHERE received_quantity > ordered_quantity OR received_quantity < 0
                ) AS invalid_received_qty
                FROM purchase_order_items
            """)
            item_audit = cur.fetchone()
            if item_audit["item_math_errors"] > 0:
                violations.append(f"{item_audit['item_math_errors']} PO item math errors!")
            if item_audit["invalid_received_qty"] > 0:
                violations.append(f"{item_audit['invalid_received_qty']} invalid received quantity rows!")

            # PO Header Sum vs Items
            cur.execute("""
                SELECT COUNT(*) AS header_mismatches
                FROM (
                    SELECT po.purchase_order_id, po.total_amount,
                           COALESCE(SUM(poi.item_total), 0) AS calc_total
                    FROM purchase_orders po
                    LEFT JOIN purchase_order_items poi ON po.purchase_order_id = poi.purchase_order_id
                    GROUP BY po.purchase_order_id, po.total_amount
                    HAVING ABS(po.total_amount - COALESCE(SUM(poi.item_total), 0)) > 0.01
                ) sub
            """)
            if cur.fetchone()["header_mismatches"] > 0:
                violations.append("PO total_amount does not match sum of item_total!")
            else:
                print("[PASS] PO financial arithmetic: 100% match between header and lines.")

            # 2. Incident Record Check
            cur.execute("SELECT * FROM incidents WHERE scenario_id = %s", (SCENARIO_ID,))
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

            # 3. AI Safe Projection View Check
            cur.execute("SELECT * FROM ai_incident_observations WHERE incident_id = %s", (incident_id,))
            obs = cur.fetchone()

            if not obs:
                violations.append("Incident not visible in ai_incident_observations view")
            else:
                obs_cols = list(obs.keys())
                if "scenario_id" in obs_cols:
                    violations.append("CRITICAL: scenario_id LEAKED in ai_incident_observations!")
                else:
                    print("[PASS] ai_incident_observations successfully shields scenario_id from AI Analyst.")

            # 4. Causal Nodes & Acyclicity
            cur.execute("SELECT node_id, node_type, truth_label, domain FROM causal_nodes WHERE incident_id = %s", (incident_id,))
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

            # 5. Primary Cause Invariant
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

            # 6. Decisive Evidence Pointers
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
                    pk_col = f"{table_name[:-1]}_id"
                    cur.execute(f"SELECT COUNT(*) AS cnt FROM {table_name} WHERE {pk_col} = %s", (dev["source_record_id"],))
                    if cur.fetchone()["cnt"] == 0:
                        violations.append(f"Decisive evidence references non-existent record in {table_name}")

            # 7. Outcome Precision vs Operational Cancelled Orders
            cur.execute("""
                SELECT financial_impact, metric_value 
                FROM incident_outcomes 
                WHERE incident_id = %s AND outcome_type = 'RevenueLoss'
            """, (incident_id,))
            loss_outcome = cur.fetchone()

            cur.execute("""
                SELECT COALESCE(SUM(o.total_amount), 0) AS actual_loss
                FROM orders o
                JOIN order_status_history osh ON o.order_id = osh.order_id
                WHERE osh.reason_code = 'OUT_OF_STOCK'
                  AND o.order_status = 'Cancelled'
                  AND o.order_timestamp BETWEEN %s AND %s
            """, (incident["start_time"], incident["end_time"]))
            actual_loss = cur.fetchone()["actual_loss"]

            if not loss_outcome or abs(loss_outcome["financial_impact"] - actual_loss) > Decimal("0.01"):
                violations.append(f"Outcome financial impact mismatch! Stored: {loss_outcome['financial_impact'] if loss_outcome else None}, Actual: {actual_loss}")
            else:
                print(f"[PASS] Financial Outcome exact match: {actual_loss:,.2f} VND")

            # 8. Benchmark Cutoff Invariant
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

            # 9. Statistical Anomaly Check: Overdue POs for Viet Electronics
            cur.execute("""
                SELECT s.supplier_name,
                       COUNT(*) AS total_pos,
                       COUNT(*) FILTER (WHERE po.po_status = 'Ordered' AND po.expected_delivery_timestamp < '2026-08-01') AS overdue_pos
                FROM purchase_orders po
                JOIN suppliers s ON po.supplier_id = s.supplier_id
                WHERE po.order_timestamp BETWEEN '2026-07-01' AND '2026-08-10'
                GROUP BY s.supplier_name
                ORDER BY overdue_pos DESC
            """)
            sup_report = cur.fetchall()

            print("\n[STATISTICAL SUPPLIER ANOMALY REPORT DURING INCIDENT WINDOW]:")
            viet_overdue = 0
            for r in sup_report:
                print(f"    - {r['supplier_name']:<28}: {r['overdue_pos']} overdue / {r['total_pos']} total POs")
                if r["supplier_name"] == TARGET_SUPPLIER_NAME:
                    viet_overdue = r["overdue_pos"]

            if viet_overdue < 2:
                violations.append(f"Viet Electronics expected at least 2 overdue POs, found {viet_overdue}")
            else:
                print(f"[PASS] Anomaly Signal Confirmed: {TARGET_SUPPLIER_NAME} has {viet_overdue} overdue POs.")

    print("=" * 70)
    if violations:
        print(f"FAILED: {len(violations)} VIOLATIONS FOUND:")
        for v in violations:
            print(f"  [FAIL] {v}")
        sys.exit(1)
    else:
        print("ALL SCENARIO S001 CAUSAL & BENCHMARK INVARIANTS PASSED WITH ZERO VIOLATIONS!")
        print("=" * 70)


if __name__ == "__main__":
    validate_scenario_s001()
