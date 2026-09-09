"""Automated Test Suite for PRO Domain Specialists & 6-Agent Adversarial Consensus.

Tests:
1. Each of the 3 PRO Specialists produces <= 5 concise findings.
2. EvidenceCritic captures empirical and statistical fallacies.
3. CausalCritic captures temporal precedence violations and reverse causal errors.
4. FinalSynthesizer compiles complete accountability report detailing who erred and who caught it.
5. FinalSynthesizer proposes exactly 5 breakthrough actionable solutions.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from ai_analyst.orchestrator import MultiAgentOrchestrator
from ai_analyst.domain_specialists import (
    SalesFinanceAnalyst,
    SupplyChainAnalyst,
    CustomerExperienceAnalyst,
)


def test_pro_specialists_scope_limit():
    """Verifies that each PRO specialist stays strictly within the limit of <= 5 findings."""
    sales_analyst = SalesFinanceAnalyst()
    supply_analyst = SupplyChainAnalyst()
    cx_analyst = CustomerExperienceAnalyst()

    res_sales = sales_analyst.conduct_pro_audit()
    res_supply = supply_analyst.conduct_pro_audit()
    res_cx = cx_analyst.conduct_pro_audit()

    assert res_sales["findings_count"] <= 5, "Sales findings must be <= 5"
    assert res_supply["findings_count"] <= 5, "Supply findings must be <= 5"
    assert res_cx["findings_count"] <= 5, "Customer findings must be <= 5"

    assert len(res_sales["hypotheses"]) > 0
    assert len(res_supply["hypotheses"]) > 0
    assert len(res_cx["hypotheses"]) > 0
    print("PASS: test_pro_specialists_scope_limit")


def test_adversarial_critics_and_accountability():
    """Verifies that 2 Critics audit findings and FinalSynthesizer reports accountability."""
    orch = MultiAgentOrchestrator()
    audit = orch.run_pro_enterprise_audit()

    assert "pro_specialists" in audit
    assert "evidence_critic" in audit
    assert "causal_critic" in audit
    assert "final_synthesis" in audit

    ev = audit["evidence_critic"]
    cv = audit["causal_critic"]
    fs = audit["final_synthesis"]

    # Check that both critics caught errors
    assert ev["captured_errors_count"] >= 2, "Evidence Critic should catch empirical errors"
    assert cv["captured_errors_count"] >= 2, "Causal Critic should catch temporal/causal errors"

    # Check Accountability Report
    acct = fs["accountability_report"]
    assert acct["total_errors_detected"] >= 4, "Total errors detected should be >= 4"
    
    matrix = acct["accountability_matrix"]
    faulty_agents = {item["faulty_agent"] for item in matrix}
    detectors = {item["detected_by"] for item in matrix}

    assert "SalesFinanceAnalyst" in faulty_agents
    assert "SupplyChainAnalyst" in faulty_agents
    assert "CustomerExperienceAnalyst" in faulty_agents

    assert any("EvidenceCritic" in d for d in detectors)
    assert any("CausalCritic" in d for d in detectors)

    # Check Breakthrough Solutions
    solutions = fs["breakthrough_solutions"]
    assert len(solutions) == 5, f"Expected exactly 5 breakthrough solutions, got {len(solutions)}"

    print("PASS: test_adversarial_critics_and_accountability")


if __name__ == "__main__":
    print("Running PRO Specialists & 6-Agent Adversarial Consensus Tests...")
    test_pro_specialists_scope_limit()
    test_adversarial_critics_and_accountability()
    print("ALL PRO SPECIALIST TESTS PASSED SUCCESSFULLY!")
