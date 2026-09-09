"""Integration and Functional Test Suite for Continuous Live Streaming and Enterprise NL2SQL Copilot."""

import sys
import json
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from fastapi.testclient import TestClient
from web_app.server import app

client = TestClient(app)

def http_get(path):
    res = client.get(path)
    return res.status_code, res.json()

def http_post(path, payload):
    res = client.post(path, json=payload)
    return res.status_code, res.json()


def test_streaming_status_endpoint():
    """Verifies that the live streaming telemetry endpoint returns active metrics."""
    status, data = http_get("/api/stream/status")
    assert status == 200
    assert data["status"] == "SUCCESS"
    assert "stream" in data
    st = data["stream"]
    assert "total_events_ingested" in st
    assert "moving_baselines" in st
    assert "order_velocity_per_min" in st["moving_baselines"]
    print(f"  [PASSED] test_streaming_status_endpoint (Events: {st['total_events_ingested']}, Velocity: {st['moving_baselines']['order_velocity_per_min']['mean']}/min)")


def test_streaming_toggle_endpoint():
    """Verifies that the live streaming pipeline can be toggled pause/resume."""
    status1, data1 = http_post("/api/stream/toggle", {})
    assert status1 == 200
    assert data1["status"] == "SUCCESS"

    status2, data2 = http_post("/api/stream/toggle", {})
    assert status2 == 200
    assert data2["status"] == "SUCCESS"
    print("  [PASSED] test_streaming_toggle_endpoint")


def test_streaming_inject_event():
    """Verifies manual event injection updates the event buffer and recalculates baseline."""
    payload = {
        "domain": "Sales & Revenue",
        "event_type": "TEST_INJECTION",
        "summary": "Đơn hàng thử nghiệm tự động từ kiểm thử pytest (+5.000.000 ₫)",
        "details": {"amount": 5000000, "quantity": 1}
    }
    status, data = http_post("/api/stream/inject", payload)
    assert status == 200
    assert data["status"] == "SUCCESS"
    assert "event" in data
    assert data["event"]["domain"] == "Sales & Revenue"
    print("  [PASSED] test_streaming_inject_event")


def test_nl2sql_digital_interventions_roi():
    """Verifies C-Suite What-If Digital Intervention ROI query."""
    status, data = http_post("/api/ai/query", {
        "query": "Nếu thực hiện tất cả can thiệp số, lợi nhuận ròng sẽ phục hồi bao nhiêu?"
    })
    assert status == 200
    assert data["status"] == "SUCCESS"
    assert data["domain"] == "CrisisGovernance"
    assert "Tổng giá trị phục hồi" in data["answer"]
    assert len(data["data"]) >= 5
    print("  [PASSED] test_nl2sql_digital_interventions_roi")


def test_nl2sql_tiktok_campaign():
    """Verifies CMO query about TikTok marketing campaign CAC & CVR."""
    status, data = http_post("/api/ai/query", {
        "query": "Hiệu quả chiến dịch TikTok so với các kênh khác (CAC & CVR)?"
    })
    assert status == 200
    assert data["status"] == "SUCCESS"
    assert "TikTok" in data["answer"]
    assert len(data["data"]) > 0
    print("  [PASSED] test_nl2sql_tiktok_campaign")


def test_nl2sql_cashflow_query():
    """Verifies CFO query about Net Cash Flow."""
    status, data = http_post("/api/ai/query", {
        "query": "Lưu chuyển tiền thuần (Net Cash Flow) đang ở mức bao nhiêu?"
    })
    assert status == 200
    assert data["status"] == "SUCCESS"
    assert len(data["data"]) > 0
    print("  [PASSED] test_nl2sql_cashflow_query")


def test_nl2sql_security_guardrail_rejection():
    """Verifies that destructive SQL commands are rejected by security guardrails."""
    status, data = http_post("/api/ai/query", {
        "query": "DROP TABLE orders; SELECT * FROM customers;"
    })
    assert status == 200
    assert data["status"] == "SECURITY_REJECTED"
    assert data["sql_query"] == "-- BLOCKED BY SECURITY GUARDRAIL"
    print("  [PASSED] test_nl2sql_security_guardrail_rejection")


if __name__ == "__main__":
    print("Running Streaming & NL2SQL Enterprise Test Suite...")
    test_streaming_status_endpoint()
    test_streaming_toggle_endpoint()
    test_streaming_inject_event()
    test_nl2sql_digital_interventions_roi()
    test_nl2sql_tiktok_campaign()
    test_nl2sql_cashflow_query()
    test_nl2sql_security_guardrail_rejection()
    print(">>> ALL 7 STREAMING & NL2SQL TESTS PASSED 100%! <<<")
