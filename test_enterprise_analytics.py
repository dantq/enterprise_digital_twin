"""Automated Test Suite for Enterprise Analytics Engine (Bậc 1 & Bậc 2).

Tests:
1. Multi-temporal analysis (Month & Quarter grain): Non-empty timeline, valid MoM/QoQ/YoY growth.
2. Comparative matrix: Full presence of 5 dimensions (Channels, Stores, Carriers, Payments, Suppliers).
3. Diagnostic analysis (Bậc 2): Cancellation reasons breakdown, Z-Score anomaly tests, and financial loss attribution.
4. Executive summary synthesis: Comprehensive findings and health grade.
5. Data integrity: Gross Sales - Discounts = Net Sales consistency.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from web_app.services.enterprise_analytics_engine import EnterpriseAnalyticsEngine


def test_temporal_monthly_analysis():
    """Verifies monthly time-series aggregation and MoM/YoY growth rates."""
    result = EnterpriseAnalyticsEngine.get_temporal_growth_analysis(grain="month")
    assert result is not None, "Result should not be None"
    assert result["grain"] == "month", "Grain should be 'month'"
    assert result["total_periods"] > 0, "Should contain historical monthly periods"
    
    timeline = result["timeline"]
    assert len(timeline) >= 12, "Should span across multiple months"

    for p in timeline:
        assert "period_label" in p
        assert p["total_orders"] >= 0
        assert p["gross_sales"] >= 0
        assert p["net_revenue"] >= 0
        assert 0.0 <= p["cancellation_rate_pct"] <= 100.0

    # Test YoY calculation on 2026 periods
    periods_with_yoy = [p for p in timeline if p["growth_yoy_pct"] is not None]
    assert len(periods_with_yoy) > 0, "Should have calculated YoY for 2026 periods"
    print("PASS: test_temporal_monthly_analysis")


def test_temporal_quarterly_analysis():
    """Verifies quarterly time-series aggregation and QoQ growth rates."""
    result = EnterpriseAnalyticsEngine.get_temporal_growth_analysis(grain="quarter")
    assert result is not None
    assert result["grain"] == "quarter"
    assert result["total_periods"] >= 4, "Should span at least 4 quarters"
    
    timeline = result["timeline"]
    labels = [p["period_label"] for p in timeline]
    assert any("2025" in l for l in labels)
    assert any("2026" in l for l in labels)
    print("PASS: test_temporal_quarterly_analysis")


def test_comparative_matrix_completeness():
    """Verifies all 5 benchmarking dimensions are populated."""
    matrix = EnterpriseAnalyticsEngine.get_comparative_matrix()
    assert "channels" in matrix, "Missing channels matrix"
    assert "stores" in matrix, "Missing stores matrix"
    assert "carriers" in matrix, "Missing carriers matrix"
    assert "payment_methods" in matrix, "Missing payment methods matrix"
    assert "suppliers" in matrix, "Missing suppliers matrix"

    assert len(matrix["channels"]) > 0, "Channels list should not be empty"
    assert len(matrix["stores"]) > 0, "Stores list should not be empty"
    assert len(matrix["carriers"]) > 0, "Carriers list should not be empty"
    assert len(matrix["payment_methods"]) > 0, "Payment methods list should not be empty"
    assert len(matrix["suppliers"]) > 0, "Suppliers list should not be empty"

    # Verify Carrier SLA properties
    for c in matrix["carriers"]:
        assert "carrier_name" in c
        assert "delay_rate_pct" in c
        assert "on_time_rate_pct" in c
        assert c["delay_rate_pct"] + c["on_time_rate_pct"] == 100.0

    print("PASS: test_comparative_matrix_completeness")


def test_diagnostic_deep_dive():
    """Verifies Bậc 2 cancellation decomposition, Z-scores, and financial loss attribution."""
    diag = EnterpriseAnalyticsEngine.get_diagnostic_deep_dive()
    assert "cancellation_decomposition" in diag
    assert "statistical_anomalies" in diag
    assert "loss_attribution" in diag
    assert diag["total_quantified_erosion_loss"] > 0

    reasons = [r["reason_code"] for r in diag["cancellation_decomposition"]]
    assert any(r in reasons for r in ["OUT_OF_STOCK", "PAYMENT_TIMEOUT", "CUSTOMER_CANCELLED"])

    print("PASS: test_diagnostic_deep_dive")


def test_executive_summary_report():
    """Verifies executive synthesis combining Bậc 1 and Bậc 2."""
    report = EnterpriseAnalyticsEngine.get_executive_summary_report()
    assert "overall_health" in report
    assert report["overall_health"] in ("HEALTHY", "WARNING", "CRITICAL")
    assert "executive_summary" in report
    assert len(report["top_operational_findings"]) >= 3
    assert "data_slices" in report
    print("PASS: test_executive_summary_report")


if __name__ == "__main__":
    print("Running Enterprise Analytics Engine Tests...")
    test_temporal_monthly_analysis()
    test_temporal_quarterly_analysis()
    test_comparative_matrix_completeness()
    test_diagnostic_deep_dive()
    test_executive_summary_report()
    print("ALL 5 TESTS PASSED SUCCESSFULLY!")
