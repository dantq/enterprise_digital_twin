"""Comprehensive Test Suite for Scenario Engine V2.

Verifies:
1. Temporal curves: 4 phases (Incubation, Escalation, Peak, Decay) across piecewise, sigmoid, weibull.
2. Realistic business noise: POS delay distribution, metric jitter, and statistical significance.
3. Composite Causal DAGs: Multi-root structures, collider convergence, and Kahn's acyclicity.
4. Marginal Attribution: Zero double-counting (L_total = L1 + L2 - L_interaction).
5. AI Analyst V2: Noise resilience, Evidence Critic audit, Causal Critic collider audit, and Synthesizer report.
6. Web API Endpoints: /api/scenarios/v2/catalog, /api/scenarios/v2/inject, /api/scenarios/v2/attribution.
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from web_app.server import app

from data_generator.scenario_engine_v2.temporal_curves import (
    TemporalCurveEngine,
    CrisisPhase,
    CurveProfile,
)
from data_generator.scenario_engine_v2.business_noise import (
    BusinessNoiseEngine,
    NoiseProfile,
)
from data_generator.scenario_engine_v2.causal_ground_truth_v2 import (
    CompositeCausalGraph,
)
from data_generator.scenario_engine_v2.composite_scenarios import (
    CompositeScenarioOrchestrator,
    COMPOSITE_CATALOG,
)
from ai_analyst.critics.evidence_critic import EvidenceCritic
from ai_analyst.critics.causal_critic import CausalCritic
from ai_analyst.synthesizer.final_synthesizer import FinalSynthesizer
from ai_analyst.anomaly_detector import BusinessHeartbeatDetector

client = TestClient(app)


def test_temporal_curves():
    """1. Verifies 4 crisis phases and bounds across profiles."""
    engine = TemporalCurveEngine(curve_type=CurveProfile.MULTI_PHASE_PIECEWISE, peak_severity=0.9)

    # Incubation
    t01 = engine.evaluate_normalized(0.05)
    assert t01["phase"] == CrisisPhase.INCUBATION.value
    assert 0.05 <= t01["effective_severity"] <= 0.30

    # Escalation
    t03 = engine.evaluate_normalized(0.35)
    assert t03["phase"] == CrisisPhase.ESCALATION.value

    # Peak
    t06 = engine.evaluate_normalized(0.65)
    assert t06["phase"] == CrisisPhase.PEAK_CRISIS.value
    assert t06["effective_severity"] >= 0.70

    # Decay
    t09 = engine.evaluate_normalized(0.95)
    assert t09["phase"] == CrisisPhase.DECAY_RECOVERY.value

    # Datetime evaluation
    now = datetime.now(timezone.utc)
    t_dt = engine.evaluate_datetime(now, now - timedelta(days=5), now + timedelta(days=5))
    assert "current_time" in t_dt
    assert 0.0 <= t_dt["effective_severity"] <= 1.0

    print("  [PASSED] test_temporal_curves (All 4 phases & bounds verified)")


def test_business_noise_engine():
    """2. Verifies POS sync delay, jitter bounds, and statistical significance."""
    profile = NoiseProfile(seed=123, telemetry_jitter_pct=0.05, pos_delay_rate=1.0)
    noise_engine = BusinessNoiseEngine(profile)

    now = datetime(2026, 8, 15, 10, 0, 0, tzinfo=timezone.utc)

    # POS delay
    ingested_at, delayed = noise_engine.apply_pos_sync_delay(now, "Store POS")
    assert delayed is True
    assert ingested_at > now
    diff_hours = (ingested_at - now).total_seconds() / 3600.0
    assert 6.0 <= diff_hours <= 18.0

    # Non-POS channel should never be delayed
    web_time, web_delayed = noise_engine.apply_pos_sync_delay(now, "Website")
    assert web_delayed is False
    assert web_time == now

    # Metric jitter within +/- 5%
    base_val = 1000.0
    jittered = noise_engine.apply_metric_jitter(base_val)
    assert 950.0 <= jittered <= 1050.0

    # Statistical significance
    z_insig = noise_engine.compute_z_score(102.0, 100.0, 5.0)  # Z = 0.4
    assert noise_engine.is_statistically_significant(z_insig) is False

    z_sig = noise_engine.compute_z_score(125.0, 100.0, 5.0)  # Z = 5.0
    assert noise_engine.is_statistically_significant(z_sig) is True

    print("  [PASSED] test_business_noise_engine (POS lag, jitter & Z-scores verified)")


def test_composite_causal_dag_and_acyclicity():
    """3. Verifies multi-root DAG structure and Kahn's algorithm acyclicity."""
    orch = CompositeScenarioOrchestrator()

    # S006 DAG
    dag_s006 = orch.build_causal_dag_s006()
    assert dag_s006.verify_acyclicity() is True
    assert "RC_SUPPLY" in dag_s006.nodes
    assert "RC_PAYMENT" in dag_s006.nodes
    assert "COLLIDER_REVENUE" in dag_s006.nodes
    assert dag_s006.nodes["COLLIDER_REVENUE"].node_type == "Collider"

    # S007 DAG
    dag_s007 = orch.build_causal_dag_s007()
    assert dag_s007.verify_acyclicity() is True
    assert "RC_LOGISTICS" in dag_s007.nodes
    assert "RC_QUALITY" in dag_s007.nodes
    assert "COLLIDER_CHURN" in dag_s007.nodes

    print("  [PASSED] test_composite_causal_dag_and_acyclicity (Strict Kahn DAG verified)")


def test_marginal_attribution_zero_double_counting():
    """4. Verifies marginal attribution deduction of interaction offset."""
    orch = CompositeScenarioOrchestrator()
    dag = orch.build_causal_dag_s006()

    primary_losses = {
        "S001_Supplier": 1000000000.0,
        "S003_Payment": 600000000.0,
    }
    res = dag.calculate_marginal_attribution(primary_losses, interaction_rate=0.05)

    assert res.interaction_offset == 80000000.0  # 5% of 1.6B
    assert res.total_financial_loss == 1520000000.0  # 1.6B - 80M
    assert sum(res.attribution_shares.values()) == 1.0
    assert res.attribution_shares["S001_Supplier"] == 0.625
    assert res.attribution_shares["S003_Payment"] == 0.375

    print("  [PASSED] test_marginal_attribution_zero_double_counting (Zero double-counting verified)")


def test_ai_analyst_v2_critics_and_heartbeat():
    """5. Verifies AI Analyst V2 noise filtering and adversarial auditing."""
    # Anomaly detector noise evaluation
    detector = BusinessHeartbeatDetector()
    noisy_eval = detector.evaluate_noise_resilience(sample_value=105.0, baseline_mean=100.0, baseline_std=10.0, sample_size=5)
    assert noisy_eval["is_noise"] is True
    assert noisy_eval["verdict"] == "FILTERED_NOISE"

    crisis_eval = detector.evaluate_noise_resilience(sample_value=145.0, baseline_mean=100.0, baseline_std=10.0, sample_size=30)
    assert crisis_eval["is_noise"] is False
    assert crisis_eval["verdict"] == "CONFIRMED_ANOMALY"

    # Evidence Critic audit
    ev_critic = EvidenceCritic()
    ev_audit = ev_critic.audit_noise_and_sample_size(sample_count=4, p_value=0.12)
    assert ev_audit["is_noise"] is True
    assert "REJECTED_AS_NOISE" in ev_audit["verdict"]

    # Causal Critic collider audit
    causal_critic = CausalCritic()
    # Case A: Double counting
    bad_audit = causal_critic.audit_confounders_and_marginal_attribution(
        identified_causes=["S001", "S003"],
        claimed_loss_allocations={"S001": 1000.0, "S003": 800.0},
        total_observed_loss=1200.0,
    )
    assert bad_audit["has_double_counting"] is True
    assert bad_audit["is_valid"] is False

    # Case B: Correct marginal attribution
    good_audit = causal_critic.audit_confounders_and_marginal_attribution(
        identified_causes=["S001", "S003"],
        claimed_loss_allocations={"S001": 600.0, "S003": 400.0},
        total_observed_loss=1000.0,
    )
    assert good_audit["is_valid"] is True
    assert good_audit["verdict"] == "CERTIFIED_MARGINAL_ATTRIBUTION"

    # Synthesizer composite report
    synthesizer = FinalSynthesizer()
    rca = synthesizer.synthesize_composite_rca_report(
        composite_scenario_id="S006",
        title="Test Composite",
        sub_causes=[
            {"cause_id": "S001", "gross_loss": 600000000.0},
            {"cause_id": "S003", "gross_loss": 400000000.0},
        ],
        gross_loss=1000000000.0,
    )
    assert rca["report_type"] == "COMPOSITE_MULTI_ROOT_RCA"
    assert rca["concurrency_verified"] is True
    assert rca["marginal_attribution"]["shares"]["S001"] == 0.60
    assert rca["marginal_attribution"]["shares"]["S003"] == 0.40

    print("  [PASSED] test_ai_analyst_v2_critics_and_heartbeat (Critics & Synthesizer verified)")


def test_api_endpoints_v2():
    """6. Verifies FastAPI REST endpoints for Scenario Engine V2."""
    # GET /api/scenarios/v2/catalog
    res = client.get("/api/scenarios/v2/catalog")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["total_scenarios"] >= 2
    scen_ids = [s["scenario_id"] for s in data["catalog"]]
    assert "S006" in scen_ids
    assert "S007" in scen_ids

    # POST /api/scenarios/v2/inject (S006)
    res2 = client.post("/api/scenarios/v2/inject", json={
        "scenario_id": "S006",
        "progress_t": 0.70,
        "apply_noise": True,
        "noise_level": 0.04,
    })
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "SUCCESS"
    assert data2["scenario_id"] == "S006"
    assert "surface_observation" in data2
    assert "ground_truth_hidden" in data2
    assert "ai_synthesizer_rca" in data2
    assert data2["ai_synthesizer_rca"]["concurrency_verified"] is True

    # GET /api/scenarios/v2/attribution
    res3 = client.get("/api/scenarios/v2/attribution?scenario_id=S006")
    assert res3.status_code == 200
    data3 = res3.json()
    assert len(data3["comparison"]) == 2
    for comp in data3["comparison"]:
        assert comp["attribution_error_pct"] <= 5.0
        assert comp["verdict"] == "MATCH_EXCELLENT"

    print("  [PASSED] test_api_endpoints_v2 (Catalog, Inject & Attribution endpoints verified)")


if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING SCENARIO ENGINE V2 TEST SUITE (CONCURRENCY, NOISE & ATTRIBUTION)")
    print("=" * 70)
    test_temporal_curves()
    test_business_noise_engine()
    test_composite_causal_dag_and_acyclicity()
    test_marginal_attribution_zero_double_counting()
    test_ai_analyst_v2_critics_and_heartbeat()
    test_api_endpoints_v2()
    print("=" * 70)
    print("ALL SCENARIO ENGINE V2 TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 70)
