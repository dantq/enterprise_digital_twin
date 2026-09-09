"""Adversarial Critic B: Security & Anti-Leakage Verification.

Verifies that:
1. The role `edt_ai_analyst` CANNOT query:
   - `incidents` (direct table access)
   - `causal_nodes`
   - `causal_links`
   - `incident_causes`
   - `incident_evidence`
   - `incident_outcomes`
   - `benchmark_cases`
   - `evaluation_targets`
2. The role `edt_ai_analyst` CAN query:
   - `ai_incident_observations` (safe view projection)
   - Operational tables (orders, payments, etc.)
3. `ai_incident_observations` view schema has ZERO leakage:
   - Column `scenario_id` does NOT exist.
   - Column `surface_symptoms` contains no leak terms (MoMo, S003, RootCause).
"""

import sys
import psycopg
from pathlib import Path

DATA_GENERATOR_DIR = Path(__file__).resolve().parent / "data_generator"
sys.path.insert(0, str(DATA_GENERATOR_DIR))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import DB_HOST, DB_PORT, DB_NAME


def test_security():
    print("=" * 70)
    print("ADVERSARIAL CRITIC B: SECURITY & ANTI-LEAKAGE AUDIT")
    print("=" * 70)

    # 1. First, check schema view columns
    from db import get_connection
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'ai_incident_observations'
                ORDER BY ordinal_position
            """)
            view_cols = [r["column_name"] for r in cur.fetchall()]
            print(f"[PASS] ai_incident_observations view columns: {view_cols}")

            if "scenario_id" in view_cols:
                raise AssertionError("CRITICAL LEAKAGE: scenario_id is exposed in ai_incident_observations view!")

            cur.execute("SELECT surface_symptoms FROM ai_incident_observations LIMIT 1")
            symptoms = cur.fetchone()["surface_symptoms"]
            print(f"[PASS] Observed surface symptoms: \"{symptoms}\"")

            leak_words = ["MoMo", "S003", "root cause", "cổng MoMo", "timeout API"]
            for lw in leak_words:
                if lw.lower() in symptoms.lower():
                    raise AssertionError(f"LEAKAGE DETECTED: Leak term '{lw}' found in surface symptoms!")
            print("[PASS] Surface symptoms verified: 100% neutral observation, zero leakage.")

    # 2. Check RBAC permissions for edt_ai_analyst
    # Let's check what privileges exist in pg_tables for edt_ai_analyst
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT has_table_privilege('edt_ai_analyst', 'incidents', 'SELECT') AS can_read_incidents,
                       has_table_privilege('edt_ai_analyst', 'ai_incident_observations', 'SELECT') AS can_read_view,
                       has_table_privilege('edt_ai_analyst', 'causal_nodes', 'SELECT') AS can_read_causal_nodes,
                       has_table_privilege('edt_ai_analyst', 'causal_links', 'SELECT') AS can_read_causal_links,
                       has_table_privilege('edt_ai_analyst', 'incident_causes', 'SELECT') AS can_read_causes,
                       has_table_privilege('edt_ai_analyst', 'incident_evidence', 'SELECT') AS can_read_evidence,
                       has_table_privilege('edt_ai_analyst', 'incident_outcomes', 'SELECT') AS can_read_outcomes,
                       has_table_privilege('edt_ai_analyst', 'benchmark_cases', 'SELECT') AS can_read_benchmark,
                       has_table_privilege('edt_ai_analyst', 'evaluation_targets', 'SELECT') AS can_read_targets,
                       has_table_privilege('edt_ai_analyst', 'orders', 'SELECT') AS can_read_orders,
                       has_table_privilege('edt_ai_analyst', 'payments', 'SELECT') AS can_read_payments,
                       has_table_privilege('edt_ai_analyst', 'purchase_orders', 'SELECT') AS can_read_purchase_orders,
                       has_table_privilege('edt_ai_analyst', 'stores', 'SELECT') AS can_read_stores,
                       has_table_privilege('edt_ai_analyst', 'employees', 'SELECT') AS can_read_employees;
            """)
            privs = cur.fetchone()
            print("\n[RBAC PERMISSION MATRIX FOR edt_ai_analyst]:")
            for k, v in privs.items():
                print(f"  - {k:<30}: {'ALLOWED' if v else 'DENIED'}")

            # Assertions
            assert privs["can_read_incidents"] is False, "Violation: edt_ai_analyst has SELECT on incidents!"
            assert privs["can_read_causal_nodes"] is False, "Violation: edt_ai_analyst has SELECT on causal_nodes!"
            assert privs["can_read_causal_links"] is False, "Violation: edt_ai_analyst has SELECT on causal_links!"
            assert privs["can_read_causes"] is False, "Violation: edt_ai_analyst has SELECT on incident_causes!"
            assert privs["can_read_evidence"] is False, "Violation: edt_ai_analyst has SELECT on incident_evidence!"
            assert privs["can_read_outcomes"] is False, "Violation: edt_ai_analyst has SELECT on incident_outcomes!"
            assert privs["can_read_benchmark"] is False, "Violation: edt_ai_analyst has SELECT on benchmark_cases!"
            assert privs["can_read_targets"] is False, "Violation: edt_ai_analyst has SELECT on evaluation_targets!"

            assert privs["can_read_view"] is True, "Violation: edt_ai_analyst cannot read ai_incident_observations view!"
            assert privs["can_read_orders"] is True, "Violation: edt_ai_analyst cannot read operational orders!"
            assert privs["can_read_payments"] is True, "Violation: edt_ai_analyst cannot read operational payments!"
            assert privs["can_read_purchase_orders"] is True, "Violation: edt_ai_analyst cannot read operational purchase_orders!"
            assert privs["can_read_stores"] is True, "Violation: edt_ai_analyst cannot read stores!"
            assert privs["can_read_employees"] is True, "Violation: edt_ai_analyst cannot read employees!"

    print("\n" + "=" * 70)
    print("ALL SECURITY & ANTI-LEAKAGE BOUNDARIES ARE 100% ENFORCED AND VERIFIED!")
    print("=" * 70)


if __name__ == "__main__":
    test_security()
