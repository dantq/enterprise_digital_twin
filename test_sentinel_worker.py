"""Test suite for AutonomousSentinelWorker in web_app/services/background_worker.py."""

import io
import sys
import time
from pathlib import Path

# Ensure UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from web_app.services.background_worker import AutonomousSentinelWorker, sentinel_worker


def test_sentinel_worker():
    print("=" * 70)
    print("RUNNING AUTONOMOUS SENTINEL WORKER TEST")
    print("=" * 70)

    # 1. Test Initial Status
    status = sentinel_worker.get_status()
    print("Initial Status:", status)
    assert not status["is_running"], "Worker should not be running before start()"

    # 2. Test Manual Instant Scan
    print("\nExecuting manual forced scan (scan_now)...")
    scan_res = sentinel_worker.scan_now(force_rca=False)
    print("Scan status       :", scan_res["status"])
    print("Anomalies found   :", scan_res["anomalies_count"])
    print("Investigations run:", scan_res["dispatched_count"])
    assert scan_res["status"] == "SUCCESS"

    # 3. Test Audit Logs
    logs = sentinel_worker.get_logs(limit=10)
    print(f"\nAudit Logs recorded ({len(logs)} entries):")
    for l in logs[:3]:
        print(f"  [{l['level']}] {l['timestamp']} - {l['message']}")
    assert len(logs) > 0, "Audit logs should contain entries from the scan"

    # 4. Test Start / Toggle / Stop Cycle
    print("\nTesting daemon thread lifecycle...")
    sentinel_worker.start()
    time.sleep(1.0)
    status_running = sentinel_worker.get_status()
    print("Running Status:", status_running["state"])
    assert status_running["is_running"] is True

    # Toggle Pause
    is_active = sentinel_worker.toggle()
    print("Toggled active state:", is_active)
    assert sentinel_worker.get_status()["state"] == "PAUSED"

    # Toggle Resume
    is_active = sentinel_worker.toggle()
    print("Toggled resume state:", is_active)
    assert sentinel_worker.get_status()["state"] == "ACTIVE"

    # Stop Daemon
    sentinel_worker.stop()
    status_stopped = sentinel_worker.get_status()
    print("Stopped Status:", status_stopped["state"])
    assert status_stopped["is_running"] is False

    print("\n[SUCCESS] AutonomousSentinelWorker test PASSED flawlessly!")


if __name__ == "__main__":
    test_sentinel_worker()
