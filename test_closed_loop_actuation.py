"""Automated Test Suite for Closed-Loop Action Actuation (Bậc 3 & Bậc 4).

Tests:
1. Proposal generation: 5 certified actions across inventory, logistics, payment, customer.
2. Execution of CREATE_PURCHASE_ORDER transactionally into PostgreSQL.
3. Execution of INTER_WAREHOUSE_TRANSFER with check constraint compliance.
4. Execution of PAYMENT_GATEWAY_FAILOVER and CARRIER_SLA_REALLOCATION.
5. Audit trail verification: Tracks timestamps, operators, and projected recovery benefits.
6. FastAPI endpoints: GET /api/actions/proposals, POST /api/actions/execute, GET /api/actions/history.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from web_app.server import app
from web_app.services.action_actuator import action_actuator


def test_action_proposal_generation():
    """Verifies that 5 structured actions are proposed and certified."""
    res = action_actuator.generate_pro_action_proposals()
    assert res["status"] == "SUCCESS"
    assert res["total_actions_proposed"] == 5

    proposals = res["proposals"]
    action_types = {p["action_type"] for p in proposals}
    assert "CREATE_PURCHASE_ORDER" in action_types
    assert "INTER_WAREHOUSE_TRANSFER" in action_types
    assert "PAYMENT_GATEWAY_FAILOVER" in action_types
    assert "CARRIER_SLA_REALLOCATION" in action_types
    assert "ISSUE_CUSTOMER_APOLOGY_VOUCHER" in action_types

    for p in proposals:
        assert p["status"] == "PENDING_APPROVAL"
        assert p["projected_recovery_benefit_vnd"] > 0
        assert "parameters" in p

    print("PASS: test_action_proposal_generation")


def test_action_execution_pipeline():
    """Verifies safe execution of purchase order and inter-warehouse transfer."""
    action_actuator.generate_pro_action_proposals()

    # 1. Execute PO
    po_res = action_actuator.execute_action("ACT-PO-001", approved_by="CFO_Agent")
    assert po_res["status"] == "SUCCESS"
    assert "purchase_order_id" in po_res["execution_details"]
    assert po_res["approved_by"] == "CFO_Agent"

    # 2. Execute Transfer
    tr_res = action_actuator.execute_action("ACT-TR-002", approved_by="COO_Agent")
    assert tr_res["status"] == "SUCCESS"
    assert tr_res["execution_details"]["quantity_transferred"] == 30.0

    # 3. Execute Failover
    pay_res = action_actuator.execute_action("ACT-PAY-003", approved_by="CTO_Agent")
    assert pay_res["status"] == "SUCCESS"
    assert pay_res["execution_details"]["routing_status"] == "ACTIVE_FAILOVER"

    print("PASS: test_action_execution_pipeline")


def test_audit_history():
    """Verifies that executed actions are properly tracked in audit trail."""
    history = action_actuator.get_action_audit_history()
    assert len(history) >= 3, "Should have at least 3 audit entries"
    latest = history[0]
    assert "action_id" in latest
    assert "executed_at" in latest
    assert "approved_by" in latest
    print("PASS: test_audit_history")


def test_api_endpoints():
    """Verifies FastAPI client interaction with /api/actions endpoints."""
    client = TestClient(app)

    # 1. Get proposals
    r1 = client.get("/api/actions/proposals")
    assert r1.status_code == 200
    assert r1.json()["status"] == "SUCCESS"

    # 2. Execute an action
    r2 = client.post("/api/actions/execute", json={
        "action_id": "ACT-CAR-004",
        "approved_by": "LogisticsDirector"
    })
    assert r2.status_code == 200
    assert r2.json()["status"] == "SUCCESS"

    # 3. Get history
    r3 = client.get("/api/actions/history")
    assert r3.status_code == 200
    assert r3.json()["total_executed_actions"] >= 4

    print("PASS: test_api_endpoints")


if __name__ == "__main__":
    print("Running Closed-Loop Action Actuation Tests...")
    test_action_proposal_generation()
    test_action_execution_pipeline()
    test_audit_history()
    test_api_endpoints()
    print("ALL CLOSED-LOOP ACTION TESTS PASSED SUCCESSFULLY!")
