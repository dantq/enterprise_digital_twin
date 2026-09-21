"""Multi-Agent Orchestrator for Enterprise Digital Twin.

Coordinates the end-to-end 6-Agent investigation lifecycle:
1. Observation Intake: Reads safe surface symptoms from `ai_incident_observations`.
2. Domain Hypothesis Generation: Executes parallel investigation across 3 Specialists:
   - Sales & Finance Analyst
   - Supply Chain & Operations Analyst
   - Customer & Market Experience Analyst
3. Adversarial Critique & Verification:
   - Evidence Critic audits sample size, statistical significance, and correlation vs causation.
   - Causal Critic validates temporal order, DAG acyclicity, and eliminates confounders.
4. Synthesis & Decision:
   - Final Synthesizer reconciles approved findings and produces the RCA Report.
5. Ground Truth Benchmark Evaluation (Evaluation Engine):
   - Scores the RCA output against restricted Layer 7 Ground Truth.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ai_analyst.db_sandbox import get_incident_observations
from ai_analyst.domain_specialists import (
    SalesFinanceAnalyst,
    SupplyChainAnalyst,
    CustomerExperienceAnalyst,
)
from ai_analyst.critics import EvidenceCritic, CausalCritic
from ai_analyst.synthesizer import FinalSynthesizer
from ai_analyst.evaluation import BenchmarkEvaluator


class MultiAgentOrchestrator:
    """Master Orchestrator managing multi-agent investigation and scoring."""

    def __init__(self):
        self.sales_analyst = SalesFinanceAnalyst()
        self.supply_analyst = SupplyChainAnalyst()
        self.cx_analyst = CustomerExperienceAnalyst()
        self.evidence_critic = EvidenceCritic()
        self.causal_critic = CausalCritic()
        self.synthesizer = FinalSynthesizer()
        self.evaluator = BenchmarkEvaluator()

    def run_investigation_on_incident(
        self,
        observation: Dict[str, Any],
        evaluate_benchmark: bool = True,
        cutoff_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Conducts a complete multi-agent investigation for a single observed incident."""
        incident_id = str(observation["incident_id"])
        domain = observation["affected_domain"]
        effective_cutoff = cutoff_time or observation.get("detected_at")

        # 1. Domain Specialist Phase (3 Agents)
        specialist_results = {
            "SalesFinanceAnalyst": self.sales_analyst.investigate(observation, effective_cutoff),
            "SupplyChainAnalyst": self.supply_analyst.investigate(observation, effective_cutoff),
            "CustomerExperienceAnalyst": self.cx_analyst.investigate(observation, effective_cutoff),
        }

        # 2. Adversarial Critique Phase — Layer 1 (2 Agents critique Specialists)
        evidence_verdict = self.evidence_critic.critique(
            specialist_results,
            observation,
            effective_cutoff,
        )
        causal_verdict = self.causal_critic.critique(
            specialist_results,
            evidence_verdict,
            observation,
        )

        # 3. TANG BAT LOI THU HAI — Cross-Critic Audit Layer
        # EvidenceCritic audits CausalCritic's DAG for evidence-based flaws
        cross_audit_of_causal = self.evidence_critic.critique_causal_verdict(
            causal_verdict,
            specialist_results,
        )
        # CausalCritic audits EvidenceCritic's verdicts for causal logic flaws
        cross_audit_of_evidence = self.causal_critic.critique_evidence_verdict(
            evidence_verdict,
            specialist_results,
        )

        # Inject cross-audit results so FinalSynthesizer can apply Overrule Mechanism
        evidence_verdict["cross_audit_of_causal"] = cross_audit_of_causal
        causal_verdict["cross_audit_of_evidence"] = cross_audit_of_evidence

        # 4. Final Synthesis Phase (1 Judge Agent — applies Overrule + Accountability Log)
        rca_report = self.synthesizer.synthesize(
            observation,
            specialist_results,
            evidence_verdict,
            causal_verdict,
            window_end=observation.get("end_time"),
        )

        # 5. Benchmark Scoring Phase (Restricted Ground Truth Evaluator)
        scorecard = None
        if evaluate_benchmark:
            scorecard = self.evaluator.evaluate_rca(rca_report)

        return {
            "incident_id": incident_id,
            "domain": domain,
            "observation": observation,
            "specialist_results": specialist_results,
            "evidence_critique": evidence_verdict,
            "causal_critique": causal_verdict,
            "cross_critic_audit": {
                "evidence_audits_causal": cross_audit_of_causal,
                "causal_audits_evidence": cross_audit_of_evidence,
            },
            "rca_report": rca_report,
            "benchmark_scorecard": scorecard,
        }


    def run_all_active_investigations(self, evaluate_benchmark: bool = True) -> List[Dict[str, Any]]:
        """Discovers all open surface incidents and runs full multi-agent investigations."""
        observations = get_incident_observations()
        results = []
        for obs in observations:
            res = self.run_investigation_on_incident(obs, evaluate_benchmark=evaluate_benchmark)
            results.append(res)
        return results

    def run_pro_enterprise_audit(self) -> Dict[str, Any]:
        """Conducts full-spectrum 6-Agent enterprise-wide strategic audit (Bậc 1 & Bậc 2)."""
        # Phase 1: 3 PRO Specialists work independently
        pro_specialists = {
            "SalesFinanceAnalyst": self.sales_analyst.conduct_pro_audit(),
            "SupplyChainAnalyst": self.supply_analyst.conduct_pro_audit(),
            "CustomerExperienceAnalyst": self.cx_analyst.conduct_pro_audit(),
        }

        # Phase 2: 2 Adversarial Critics audit and catch errors
        evidence_verdict = self.evidence_critic.critique_pro_audit(pro_specialists)
        causal_verdict = self.causal_critic.critique_pro_audit(pro_specialists)

        # Phase 3: Final Synthesizer compiles accountability and breakthrough solutions
        synthesis = self.synthesizer.synthesize_pro_audit(
            pro_specialists,
            evidence_verdict,
            causal_verdict,
        )

        return {
            "timestamp": datetime.now().isoformat(),
            "audit_framework": "6-Agent Adversarial & Cognitive Consensus",
            "pro_specialists": pro_specialists,
            "evidence_critic": evidence_verdict,
            "causal_critic": causal_verdict,
            "final_synthesis": synthesis,
        }
