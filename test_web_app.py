"""Test suite for Web Application API and Services."""

import sys
from pathlib import Path
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from web_app.server import app

client = TestClient(app)


def test_serve_index_html():
    """Verify that GET / returns the frontend HTML page."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Enterprise Digital Twin" in response.text
    assert "app.js" in response.text
    assert "style.css" in response.text


def test_dashboard_overview_endpoint():
    """Verify GET /api/dashboard/overview returns expected structure."""
    response = client.get("/api/dashboard/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "kpis" in data
    assert "trends" in data
    assert "channels" in data
    assert "carriers" in data
    assert "incidents" in data

    # Verify KPI sub-fields
    financial = data["kpis"]["financial"]
    assert financial["recognized_revenue"] > 0
    assert financial["total_orders"] > 0
    assert len(data["carriers"]) > 0
    assert len(data["incidents"]) == 5


def test_financial_pnl_endpoint():
    """Verify GET /api/finance/pnl returns canonical P&L data."""
    response = client.get("/api/finance/pnl")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    pnl = data["pnl"]
    assert pnl["currency"] == "VND"
    assert pnl["revenue"]["net_revenue"] > 0
    assert pnl["cogs"]["total_cogs"] > 0
    assert pnl["gross_profit"]["amount"] > 0
    assert pnl["operating_expenses"]["total_opex"] > 0
    assert pnl["incident_impact"]["total_erosion"] > 0
    assert len(pnl["incident_impact"]["breakdown"]) == 5


def test_financial_cashflow_endpoint():
    """Verify GET /api/finance/cashflow returns direct cash flow data."""
    response = client.get("/api/finance/cashflow")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    cf = data["cash_flow"]
    assert cf["currency"] == "VND"
    assert cf["inflows"]["total_inflows"] > 0
    assert cf["outflows"]["total_outflows"] > 0
    assert "net_cash_flow" in cf


def test_financial_categories_endpoint():
    """Verify GET /api/finance/categories returns category margin data."""
    response = client.get("/api/finance/categories")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    categories = data["categories"]
    assert len(categories) > 0
    for cat in categories:
      assert "category_name" in cat
      assert "revenue" in cat
      assert "gross_profit" in cat
      assert "margin_pct" in cat


def test_incidents_endpoint():
    """Verify GET /api/incidents returns 5 active crisis scenarios."""
    response = client.get("/api/incidents")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    incidents = data["incidents"]
    assert len(incidents) == 5
    domains = {i["domain"] for i in incidents}
    assert domains == {"Supply", "Delivery", "Payment", "Marketing", "Customer"}


def test_ai_suggestions_endpoint():
    """Verify GET /api/ai/suggestions returns executive prompts."""
    response = client.get("/api/ai/suggestions")
    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
    assert len(data["suggestions"]) >= 5


def test_ai_natural_language_queries():
    """Verify POST /api/ai/query handles key business questions safely."""
    test_queries = [
        "Báo cáo kết quả kinh doanh P&L tháng này?",
        "Tỷ lệ giao trễ của hãng vận chuyển GHN là bao nhiêu?",
        "Chi phí tiếp thị TikTok và hiệu quả chuyển đổi?",
        "Nhà cung cấp Viet Electronics đang giao trễ những đơn nào?",
        "Tại sao đơn hàng Eco Laptop 072 bị đánh giá 1 sao và hoàn tiền?",
        "Top sản phẩm bán chạy nhất theo doanh thu?",
    ]

    for q in test_queries:
        res = client.post("/api/ai/query", json={"query": q})
        assert res.status_code == 200
        ans = res.json()
        assert ans["status"] in ["ANSWERED", "SUCCESS"]
        assert len(ans["answer"]) > 20
        assert ans["sql_query"] != ""
        assert "suggested_followups" in ans


def test_ai_security_anti_leakage_guardrails():
    """Verify POST /api/ai/query blocks malicious queries and shielded tables."""
    blocked_queries = [
        "DROP TABLE orders CASCADE;",
        "DELETE FROM shipments;",
        "SELECT * FROM evaluation_targets;",
        "SELECT * FROM benchmark_cases;",
    ]

    for q in blocked_queries:
        res = client.post("/api/ai/query", json={"query": q})
        assert res.status_code == 200
        ans = res.json()
        assert ans["status"] == "SECURITY_REJECTED"
        assert ans["sql_query"] == "-- BLOCKED BY SECURITY GUARDRAIL"


def test_supply_chain_endpoint():
    """Verify GET /api/dashboard/supply-chain returns warehouses and low stock alerts."""
    response = client.get("/api/dashboard/supply-chain")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "data" in data
    sc = data["data"]
    assert len(sc["warehouses"]) == 5
    assert len(sc["low_stock_alerts"]) > 0
    assert len(sc["suppliers"]) > 0
    assert sc["summary"]["total_units_in_stock"] > 0


def test_customer_marketing_endpoint():
    """Verify GET /api/dashboard/customer-marketing returns CRM segments and campaigns."""
    response = client.get("/api/dashboard/customer-marketing")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    cm = data["data"]
    assert len(cm["segments"]) == 5
    assert len(cm["ratings"]) == 5
    assert len(cm["tickets"]) > 0
    assert len(cm["campaigns"]) == 5


def test_causal_dag_endpoint():
    """Verify GET /api/simulation/causal-dag returns structured DAGs for 5 scenarios."""
    response = client.get("/api/simulation/causal-dag")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert len(data["dags"]) == 5
    s1 = data["dags"][0]
    assert s1["code"] == "S001"
    assert len(s1["nodes"]) >= 4
    assert len(s1["links"]) >= 3


def test_what_if_simulation_endpoint():
    """Verify POST /api/simulation/what-if returns calculated quantitative recovery."""
    payload = {
        "backup_supplier_active": True,
        "ghn_reroute_pct": 40.0,
        "momo_failover": True,
        "tiktok_realloc_pct": 60.0,
        "eco_ota_patch": True
    }
    response = client.post("/api/simulation/what-if", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "SUCCESS"
    assert res["projected"]["total_recovered"] > 1000000000.0  # > 1B VND recovered
    assert res["projected"]["new_logistics_sla_pct"] > 85.0
    assert len(res["breakdown"]) == 5


def test_timeframe_filtering():
    """Verify GET /api/dashboard/overview respects timeframe query param."""
    for tf in ["all", "pre_crisis", "peak_crisis", "recovery"]:
        response = client.get(f"/api/dashboard/overview?timeframe={tf}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["alerts"]) >= 1
        if tf == "peak_crisis":
            assert len(data["alerts"]) >= 5


def test_agent_debate_endpoint():
    """Verify GET /api/simulation/agent-debate returns 6-agent roster and 4-round transcripts."""
    # Test default/S001 scenario
    response = client.get("/api/simulation/agent-debate?scenario=S001")
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "SUCCESS"
    assert res["scenario"] == "S001"

    arena = res["data"]
    assert "agent_roster" in arena
    roster = arena["agent_roster"]
    assert len(roster) >= 6
    agent_ids = [a["id"] for a in roster]
    assert "agent_1_ops" in agent_ids
    assert "agent_4_evi" in agent_ids
    assert "agent_6_syn" in agent_ids

    debate = arena["debate"]
    assert debate["scenario_code"] == "S001"
    assert len(debate["round_1_hypotheses"]) == 3
    assert len(debate["round_2_evidence_critique"]) == 3
    assert debate["round_3_causal_critique"]["acyclicity_verified"] is True
    acc = debate["round_4_synthesizer_verdict"]["accountability"]
    assert "wrong_agent" in acc
    assert "critic_agent" in acc
    assert acc["ground_truth_score"] == 100.0

    # Test all other crisis scenarios (S002-S005)
    for sc in ["S002", "S003", "S004", "S005"]:
        resp = client.get(f"/api/simulation/agent-debate?scenario={sc}")
        assert resp.status_code == 200
        d = resp.json()["data"]["debate"]
        assert d["scenario_code"] == sc
        assert len(d["round_1_hypotheses"]) == 3
        assert len(d["round_2_evidence_critique"]) == 3
        assert d["round_4_synthesizer_verdict"]["accountability"]["ground_truth_score"] == 100.0


def test_sentinel_status_endpoint():
    """Verify GET /api/sentinel/status returns valid telemetry."""
    resp = client.get("/api/sentinel/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert "telemetry" in data
    telemetry = data["telemetry"]
    assert "is_running" in telemetry
    assert "interval_seconds" in telemetry
    assert "state" in telemetry


def test_sentinel_toggle_endpoint():
    """Verify POST /api/sentinel/toggle toggles active state."""
    resp = client.post("/api/sentinel/toggle")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert "is_active" in data
    assert "message" in data


def test_sentinel_scan_now_endpoint():
    """Verify POST /api/sentinel/scan-now runs on-demand heartbeat scan."""
    resp = client.post("/api/sentinel/scan-now?force_rca=false")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert "scan_result" in data
    assert "anomalies_count" in data["scan_result"]


def test_sentinel_logs_endpoint():
    """Verify GET /api/sentinel/logs returns audit trail."""
    resp = client.get("/api/sentinel/logs?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert "logs" in data
    assert isinstance(data["logs"], list)


if __name__ == "__main__":
    tests = [
        test_serve_index_html,
        test_dashboard_overview_endpoint,
        test_supply_chain_endpoint,
        test_customer_marketing_endpoint,
        test_causal_dag_endpoint,
        test_what_if_simulation_endpoint,
        test_timeframe_filtering,
        test_agent_debate_endpoint,
        test_financial_pnl_endpoint,
        test_financial_cashflow_endpoint,
        test_financial_categories_endpoint,
        test_incidents_endpoint,
        test_ai_suggestions_endpoint,
        test_ai_natural_language_queries,
        test_ai_security_anti_leakage_guardrails,
        test_sentinel_status_endpoint,
        test_sentinel_toggle_endpoint,
        test_sentinel_scan_now_endpoint,
        test_sentinel_logs_endpoint,
    ]
    passed = 0
    failed = 0
    print(f"Running {len(tests)} web application test suites...")
    for t in tests:
        try:
            print(f"  [RUNNING] {t.__name__}...", end="", flush=True)
            t()
            print(" [PASSED]")
            passed += 1
        except Exception as e:
            print(f" [FAILED]: {e}")
            failed += 1
    print(f"\nResults: {passed} passed, {failed} failed.")
    if failed > 0:
        sys.exit(1)
    print("ALL TESTS PASSED SUCCESSFULLY!")



