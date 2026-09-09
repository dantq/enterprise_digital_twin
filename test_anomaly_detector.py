"""Test suite for BusinessHeartbeatDetector in ai_analyst/anomaly_detector.py."""

import io
import sys
from pathlib import Path

# Ensure UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from ai_analyst.anomaly_detector import BusinessHeartbeatDetector


def test_heartbeat_detector():
    print("=" * 70)
    print("RUNNING BUSINESS HEARTBEAT DETECTOR TEST")
    print("=" * 70)

    detector = BusinessHeartbeatDetector()
    scan_result = detector.run_full_scan()

    print(f"Timestamp       : {scan_result['scan_timestamp']}")
    print(f"Total Anomalies : {scan_result['total_anomalies']}")
    print(f"Domains Scanned : {', '.join(scan_result['domains_scanned'])}")
    print(f"Summary by Domain: {scan_result['summary_by_domain']}")
    print("-" * 70)

    assert scan_result["total_anomalies"] > 0, "Detector should detect anomalies in the digital twin."
    assert "Payment" in scan_result["summary_by_domain"]
    assert "Delivery" in scan_result["summary_by_domain"]
    assert "Supply" in scan_result["summary_by_domain"]

    for idx, anom in enumerate(scan_result["anomalies_detected"], 1):
        print(f"[{idx}] [{anom['severity']}] {anom['domain']}: {anom['entity_name']}")
        print(f"    Metric: {anom['metric_name']} = {anom['metric_value']} {anom['unit']} (Threshold: {anom['threshold']} {anom['unit']})")
        print(f"    Symptom: {anom['description'][:90]}...")
        print(f"    Matched Incident ID: {anom['incident_id']}")

    print("\n[SUCCESS] BusinessHeartbeatDetector test PASSED flawlessly!")


if __name__ == "__main__":
    test_heartbeat_detector()
