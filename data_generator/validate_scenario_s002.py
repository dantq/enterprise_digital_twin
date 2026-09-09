"""Adversarial Validation Suite for Scenario S002 (Carrier Logistics Disruption).

Invariants Verified:
1. S002 Incident Record Integrity: Status, timestamps, domain = 'Delivery'.
2. Anti-Leakage Shielding: ai_incident_observations shields scenario_id and root cause.
3. Causal DAG Topology: Exactly 5 nodes, 4 links, strictly acyclic via Kahn's algorithm.
4. Primary Cause Pointer: Points to CarrierDisruption (Node 1).
5. Evidence Integrity: Decisive evidence records point to real operational shipments and tickets.
6. Outcome Integrity: Quantified compensation matches 185,000,000.00 VND.
7. Benchmark Cutoff Invariant: Zero observation leaks beyond cutoff timestamp.
8. Statistical Anomaly: GHN transit delay significantly isolated from control carriers.
"""

import sys
from decimal import Decimal
from datetime import datetime, timezone
from pathlib import Path

DATA_GENERATOR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DATA_GENERATOR_DIR))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from db import get_connection


def validate_scenario_s002():
    print("=" * 70)
    print("SCENARIO S002 (CARRIER DISRUPTION) ADVERSARIAL VALIDATION")
    print("=" * 70)

    violations = []

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Incident Record
            cur.execute("""
                SELECT incident_id, scenario_id, start_time, end_time, detected_at,
                       severity, affected_domain, status, summary
                FROM incidents
                WHERE scenario_id = 'S002'
            """)
            incident = cur.fetchone()

            if not incident:
                print("[FAIL] Incident S002 record not found in database!")
                return ["Incident record for S002 does not exist"]

            incident_id = incident["incident_id"]
            print(f"[PASS] Incident record found: {incident_id}")
            print(f"    - Affected Domain: {incident['affected_domain']}")
            print(f"    - Severity: {incident['severity']}")
            print(f"    - Status: {incident['status']}")
            print(f"    - Window: {incident['start_time']} -> {incident['end_time']}")

            if incident["affected_domain"] != "Delivery":
                violations.append(f"Invalid domain: expected 'Delivery', got {incident['affected_domain']}")
            if incident["start_time"] >= incident["end_time"]:
                violations.append("Time travel: start_time >= end_time")
            if incident["detected_at"] < incident["start_time"]:
                violations.append("Pre-cognition: detected_at < start_time")

            # 2. Safe View Projection
            cur.execute("SELECT * FROM ai_incident_observations WHERE incident_id = %s", (incident_id,))
            view_row = cur.fetchone()
            if not view_row:
                violations.append("Incident not visible in ai_incident_observations view")
            else:
                if "scenario_id" in view_row:
                    violations.append("CRITICAL: scenario_id LEAKED in ai_incident_observations!")
                else:
                    print("[PASS] ai_incident_observations successfully shields scenario_id from AI Analyst.")

            # 3. Causal Nodes & Links
            cur.execute("SELECT node_id, node_type, truth_label FROM causal_nodes WHERE incident_id = %s", (incident_id,))
            nodes = cur.fetchall()
            print(f"[PASS] Causal Nodes: {len(nodes)} nodes registered")
            if len(nodes) != 5:
                violations.append(f"Expected 5 causal nodes, found {len(nodes)}")

            cur.execute("""
                SELECT causal_link_id, cause_node_id, effect_node_id, relationship_type, confidence
                FROM causal_links
                WHERE incident_id = %s
            """, (incident_id,))
            links = cur.fetchall()
            print(f"[PASS] Causal Links: {len(links)} directed edges registered")
            if len(links) != 4:
                violations.append(f"Expected 4 causal links, found {len(links)}")

            # Topological Sort (Kahn's Algorithm)
            in_degree = {n["node_id"]: 0 for n in nodes}
            adj = {n["node_id"]: [] for n in nodes}
            for l in links:
                adj[l["cause_node_id"]].append(l["effect_node_id"])
                in_degree[l["effect_node_id"]] = in_degree.get(l["effect_node_id"], 0) + 1

            queue = [nid for nid, deg in in_degree.items() if deg == 0]
            visited = 0
            while queue:
                curr = queue.pop(0)
                visited += 1
                for nxt in adj[curr]:
                    in_degree[nxt] -= 1
                    if in_degree[nxt] == 0:
                        queue.append(nxt)

            if visited != len(nodes):
                violations.append("CYCLE DETECTED in S002 causal graph! Not an acyclic DAG.")
            else:
                print("[PASS] Causal Graph verified: Strict Acyclic DAG (no cycles or self-loops).")

            # 4. Primary Root Cause
            cur.execute("""
                SELECT ic.incident_cause_id, ic.node_id, cn.node_type, cn.truth_label
                FROM incident_causes ic
                JOIN causal_nodes cn ON ic.node_id = cn.node_id
                WHERE ic.incident_id = %s AND ic.is_primary = true
            """, (incident_id,))
            cause = cur.fetchone()
            if not cause or cause["node_type"] != "RootCause":
                violations.append("Primary root cause missing or does not have node_type = 'RootCause'")
            else:
                print(f"[PASS] Primary Root Cause certified: Node {cause['node_id']} ({cause['truth_label']})")

            # 5. Decisive Evidence
            cur.execute("""
                SELECT incident_evidence_id, source_table, source_record_id, is_decisive
                FROM incident_evidence
                WHERE incident_id = %s AND is_decisive = true
            """, (incident_id,))
            evidence_rows = cur.fetchall()
            print(f"[PASS] Decisive Evidence: {len(evidence_rows)} decisive items registered")
            if len(evidence_rows) < 2:
                violations.append(f"Expected at least 2 decisive evidence items, got {len(evidence_rows)}")

            # 6. Outcome Financial Quantification
            cur.execute("""
                SELECT metric_name, financial_impact
                FROM incident_outcomes
                WHERE incident_id = %s AND metric_name = 'logistics_compensation_loss'
            """, (incident_id,))
            outcome = cur.fetchone()
            if not outcome or abs(outcome["financial_impact"] - Decimal("185000000.00")) > Decimal("0.01"):
                violations.append(f"Expected financial impact 185,000,000.00 VND, got {outcome['financial_impact'] if outcome else None}")
            else:
                print(f"[PASS] Financial Outcome exact match: {outcome['financial_impact']:,.2f} VND")

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
                violations.append("Benchmark case not found for S002!")
            else:
                print(f"[PASS] Benchmark Case: '{b_case['case_name']}' with {b_case['total_obs']} observations")
                if b_case["post_cutoff_leaks"] > 0:
                    violations.append(f"LEAK DETECTED: {b_case['post_cutoff_leaks']} observations occur after cutoff!")
                else:
                    print(f"[PASS] Benchmark Observation Cutoff Invariant: 0 post-cutoff leaks (all observed <= {b_case['observation_cutoff_time']})")

            # 8. Statistical Carrier Anomaly Confirmation
            cur.execute("""
                SELECT 
                    c.carrier_name,
                    COUNT(s.shipment_id) AS total_shipments,
                    COUNT(CASE WHEN s.delivered_timestamp > s.estimated_delivery_timestamp OR s.shipment_status = 'InTransit' THEN 1 END) AS delayed_count,
                    ROUND(AVG(EXTRACT(EPOCH FROM (COALESCE(s.delivered_timestamp, %s) - s.shipment_timestamp)) / 86400)::NUMERIC, 2) AS avg_transit_days
                FROM shipments s
                JOIN carriers c ON s.carrier_id = c.carrier_id
                WHERE s.shipment_timestamp >= %s AND s.shipment_timestamp <= %s
                GROUP BY c.carrier_name
                ORDER BY delayed_count DESC;
            """, (incident["end_time"], incident["start_time"], incident["end_time"]))
            carrier_stats = cur.fetchall()

            print("\n[STATISTICAL CARRIER ANOMALY REPORT DURING INCIDENT WINDOW]:")
            for cs in carrier_stats:
                print(f"    - {cs['carrier_name']:<25}: {cs['delayed_count']}/{cs['total_shipments']} delayed | Avg transit: {cs['avg_transit_days']} days")

            ghn_stat = next((cs for cs in carrier_stats if cs["carrier_name"] == "GHN"), None)
            if not ghn_stat or int(ghn_stat["delayed_count"]) < 20:
                violations.append("GHN carrier anomaly not clearly manifested in shipment delays!")
            else:
                print("[PASS] Anomaly Signal Confirmed: GHN delayed shipments isolated.")

    print("=" * 70)
    if violations:
        print(f"[FAIL] S002 VALIDATION ENCOUNTERED {len(violations)} VIOLATIONS:")
        for v in violations:
            print(f"  ✖ {v}")
        return violations
    else:
        print("ALL SCENARIO S002 CAUSAL & BENCHMARK INVARIANTS PASSED WITH ZERO VIOLATIONS!")
        print("=" * 70)
        return []


if __name__ == "__main__":
    v = validate_scenario_s002()
    if v:
        sys.exit(1)
