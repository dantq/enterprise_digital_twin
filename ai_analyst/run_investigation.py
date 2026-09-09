"""CLI Executable Runner for Multi-Agent AI Analyst System.

Usage:
    python ai_analyst/run_investigation.py
    python ai_analyst/run_investigation.py --domain Supply
    python ai_analyst/run_investigation.py --domain Payment
"""

import argparse
import io
import os
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ai_analyst.orchestrator import MultiAgentOrchestrator
from ai_analyst.db_sandbox import get_incident_observations


def print_banner():
    print("=" * 80)
    print("       ENTERPRISE DIGITAL TWIN — MULTI-AGENT AI ANALYST SYSTEM")
    print("         6-Agent Autonomous Investigation & Benchmark Suite")
    print("=" * 80)


def format_currency(val: float) -> str:
    return f"{val:,.2f} VND"


def main():
    parser = argparse.ArgumentParser(description="Run AI Analyst Multi-Agent Investigation")
    parser.add_argument("--domain", type=str, default=None, help="Filter by affected domain (e.g. Payment, Supply)")
    parser.add_argument("--no-benchmark", action="store_true", help="Skip Ground Truth benchmark evaluation")
    args = parser.parse_args()

    print_banner()

    orchestrator = MultiAgentOrchestrator()
    observations = get_incident_observations()

    if args.domain:
        observations = [o for o in observations if o["affected_domain"].lower() == args.domain.lower()]

    if not observations:
        print(f"No incident observations found (filter: domain={args.domain}).")
        return

    print(f"\n[INFO] Discovered {len(observations)} active incident observation(s) from safe view.\n")

    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)

    for idx, obs in enumerate(observations, 1):
        domain = obs["affected_domain"]
        inc_id = str(obs["incident_id"])
        detected_at = obs["detected_at"]
        symptoms = obs["surface_symptoms"]

        print("━" * 80)
        print(f"INCIDENT #{idx}: [{domain.upper()}] — ID: {inc_id}")
        print(f"Detected At: {detected_at} | Severity: {obs['severity']} | Status: {obs['status']}")
        print(f"Surface Observation: \"{symptoms}\"")
        print("━" * 80)

        print("\n[PHASE 1] DEPLOYING 3 DOMAIN SPECIALISTS (RBAC: edt_ai_analyst)...")
        investigation = orchestrator.run_investigation_on_incident(
            obs,
            evaluate_benchmark=not args.no_benchmark,
        )

        spec = investigation["specialist_results"]
        for agent_name, sres in spec.items():
            print(f"  • {agent_name:<28}: {len(sres['findings'])} findings, {len(sres['hypotheses'])} hypotheses")
            for f in sres["findings"][:2]:
                print(f"      - {f}")

        print("\n[PHASE 2] ADVERSARIAL CRITIQUE & INVARIANT AUDIT...")
        ev = investigation["evidence_critique"]
        ca = investigation["causal_critique"]
        for crit in ev.get("critiques", []):
            print(f"  • EvidenceCritic [{crit['verdict']}]: {crit['rationale'][:110]}...")
        for temp in ca.get("temporal_checks", []):
            print(f"  • CausalCritic   [{'PASSED' if temp['valid'] else 'FAILED'}]: {temp['notes']}")
        print(f"  • Causal DAG Strict Acyclicity: {'PASSED (Kahn DAG verified)' if ca.get('acyclicity_verified') else 'FAILED'}")

        print("\n[PHASE 3] FINAL SYNTHESIS & RCA GENERATION...")
        rca = investigation["rca_report"]
        ent = rca.get("affected_entity") or {}
        outcome = rca.get("outcome") or {}
        print(f"  • Certified Root Cause : {rca['primary_root_cause']}")
        print(f"  • Responsible Entity   : {ent.get('entity_name')} ({ent.get('entity_type')}) [ID: {ent.get('entity_id')}]")
        print(f"  • Certified Causal DAG : {' -> '.join(ca['causal_graph'].get('nodes', []))}")
        print(f"  • Quantified Loss      : {format_currency(outcome.get('value', 0))}")
        print(f"  • Action Recommendations ({len(rca['recommended_actions'])} items):")
        for act in rca["recommended_actions"]:
            print(f"      ✔ {act}")

        # Save Markdown Report
        report_file = reports_dir / f"RCA_{domain}_{inc_id[:8]}.md"
        with open(report_file, "w", encoding="utf-8") as rf:
            rf.write(rca["executive_summary"])
        print(f"\n  [EXPORT] Executive summary written to: {report_file}")

        if not args.no_benchmark:
            print("\n[PHASE 4] GROUND TRUTH BENCHMARK EVALUATION (Layer 7 Rubric)...")
            scorecard = investigation.get("benchmark_scorecard")
            if scorecard and scorecard.get("status") != "ERROR":
                print(f"  • Benchmark Case: {scorecard['case_name']} (Split: {scorecard['split']})")
                print(f"  • Total Score   : {scorecard['total_score']} / 100.0  [{scorecard['grade']}]")
                print("  • Rubric Breakdown:")
                for tr in scorecard["target_results"]:
                    status_symbol = "✔" if tr["status"] == "PASSED" else "▲" if tr["status"] == "PARTIAL" else "✖"
                    print(f"      {status_symbol} {tr['target_type']:<18}: {tr['earned_points']:>5.1f}/{tr['max_points']:>5.1f} pt  ({tr['rationale'][:85]}...)")
            else:
                print(f"  • Benchmark error: {scorecard.get('error') if scorecard else 'No scorecard'}")

        print("\n" + "=" * 80 + "\n")

    print("[SUCCESS] ALL ACTIVE INCIDENT INVESTIGATIONS COMPLETED.")


if __name__ == "__main__":
    main()
