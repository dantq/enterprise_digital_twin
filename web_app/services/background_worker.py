"""Autonomous Sentinel Background Worker (24/7 Operational Guardian).

Features:
1. Automated Heartbeat Monitoring:
   - Scans operational enterprise databases continuously (default every 60s).
   - Detects real-time anomalies across Payment, Delivery, Supply, Marketing, Customer domains.
2. Self-Triggering Multi-Agent RCA Dispatch:
   - Automatically initiates 6-Agent investigation lifecycle (`MultiAgentOrchestrator`)
     when new or active anomalies are detected.
   - Saves certified Root Cause Analysis (RCA) reports to `reports/`.
3. Enterprise Audit Log & Control Center:
   - Maintains rolling audit trail of scans, alerts, and agent dispatches.
   - Provides thread-safe start, stop, pause/resume, and forced instant scan (`scan_now`).
"""

import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_analyst.anomaly_detector import BusinessHeartbeatDetector
from ai_analyst.orchestrator import MultiAgentOrchestrator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = PROJECT_ROOT / "reports"


class AutonomousSentinelWorker:
    """Thread-safe background daemon continuously guarding enterprise health."""

    _instance: Optional["AutonomousSentinelWorker"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self, interval_seconds: int = 60):
        if hasattr(self, "_initialized") and self._initialized:
            return

        self.interval_seconds = interval_seconds
        self.is_running = False
        self.is_paused = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self.detector = BusinessHeartbeatDetector()
        self.orchestrator = MultiAgentOrchestrator()

        self.start_time: Optional[datetime] = None
        self.last_scan_time: Optional[datetime] = None
        self.scan_count = 0
        self.total_anomalies_detected = 0
        self.investigations_triggered = 0

        # Ring buffer for audit logs (stores up to 100 recent entries)
        self.audit_logs: List[Dict[str, Any]] = []
        self._max_logs = 100

        # Track which incidents have already been investigated to prevent redundant RCA loops
        self._investigated_incident_ids: set = set()

        REPORTS_DIR.mkdir(exist_ok=True)
        self._initialized = True

    def _append_log(self, level: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Thread-safe append to audit log history."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "details": details or {},
        }
        with self._lock:
            self.audit_logs.insert(0, entry)
            if len(self.audit_logs) > self._max_logs:
                self.audit_logs.pop()

    def start(self):
        """Starts the background sentinel daemon thread."""
        with self._lock:
            if self.is_running:
                return

            self.is_running = True
            self.is_paused = False
            self._stop_event.clear()
            self.start_time = datetime.now()
            self._thread = threading.Thread(target=self._run_loop, name="AutonomousSentinelDaemon", daemon=True)
            self._thread.start()

        self._append_log("INFO", f"Autonomous Sentinel 24/7 worker started (interval: {self.interval_seconds}s).")
        print(f"[Sentinel Worker] Started daemon thread with {self.interval_seconds}s interval.")

    def stop(self):
        """Gracefully stops the background sentinel daemon."""
        with self._lock:
            if not self.is_running:
                return
            self.is_running = False
            self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

        self._append_log("WARNING", "Autonomous Sentinel worker stopped.")
        print("[Sentinel Worker] Stopped daemon thread.")

    def toggle(self) -> bool:
        """Toggles pause/resume state of automated scanning."""
        with self._lock:
            self.is_paused = not self.is_paused
            state = "PAUSED" if self.is_paused else "ACTIVE"
        self._append_log("INFO", f"Autonomous Sentinel state changed to: {state}.")
        return not self.is_paused

    def set_interval(self, seconds: int):
        """Updates scan interval frequency."""
        with self._lock:
            self.interval_seconds = max(10, min(seconds, 3600))
        self._append_log("INFO", f"Sentinel scan interval updated to {self.interval_seconds} seconds.")

    def _run_loop(self):
        """Core background loop executing scheduled scans."""
        # Initial brief sleep to let web server finish binding ports
        time.sleep(2.0)

        while not self._stop_event.is_set():
            if not self.is_paused:
                try:
                    self.execute_scan_cycle()
                except Exception as e:
                    self._append_log("ERROR", f"Error during Sentinel scan cycle: {str(e)}")
                    print(f"[Sentinel Worker Error] {e}")

            # Sleep in 1-second chunks to allow prompt shutdown
            for _ in range(self.interval_seconds):
                if self._stop_event.is_set():
                    break
                time.sleep(1.0)

    def execute_scan_cycle(self, force_rca: bool = False) -> Dict[str, Any]:
        """Performs a single complete scan cycle, detecting anomalies and dispatching RCA."""
        scan_time = datetime.now()
        with self._lock:
            self.scan_count += 1
            self.last_scan_time = scan_time

        # 1. Run Enterprise Heartbeat Pulse Scan
        scan_result = self.detector.run_full_scan()
        anomalies = scan_result.get("anomalies_detected", [])
        with self._lock:
            self.total_anomalies_detected += len(anomalies)

        dispatched_investigations = []

        if not anomalies:
            self._append_log("INFO", "Heartbeat Scan OK: Enterprise operations healthy across all domains.")
            return {
                "status": "SUCCESS",
                "healthy": True,
                "anomalies_count": 0,
                "dispatched_count": 0,
                "scan_timestamp": scan_time.isoformat(),
            }

        self._append_log(
            "WARNING",
            f"Heartbeat Scan: Detected {len(anomalies)} operational anomalies. Reviewing for RCA dispatch.",
            {"domains": scan_result.get("summary_by_domain")},
        )

        # 2. Review and Dispatch Multi-Agent Investigations for Unresolved/Critical Incidents
        for anom in anomalies:
            inc_id = anom.get("incident_id")
            domain = anom.get("domain")
            obs = anom.get("matched_observation")

            # Check if RCA report already exists on disk
            report_file = REPORTS_DIR / f"RCA_{domain}_{inc_id[:8]}.md" if inc_id else None
            needs_investigation = force_rca or (inc_id not in self._investigated_incident_ids and (not report_file or not report_file.exists()))

            if needs_investigation and obs:
                try:
                    self._append_log(
                        "DISPATCH",
                        f"Autonomous RCA Triggered: Dispatching 6-Agent investigation on incident #{inc_id[:8]} ({domain}).",
                    )
                    print(f"[Sentinel Dispatch] Starting 6-Agent investigation on [{domain}] #{inc_id[:8]}...")

                    # Trigger Multi-Agent Orchestrator
                    investigation = self.orchestrator.run_investigation_on_incident(obs, evaluate_benchmark=True)
                    rca = investigation.get("rca_report", {})

                    # Write RCA report markdown file
                    if report_file and rca.get("executive_summary"):
                        with open(report_file, "w", encoding="utf-8") as rf:
                            rf.write(rca["executive_summary"])

                    with self._lock:
                        self._investigated_incident_ids.add(inc_id)
                        self.investigations_triggered += 1

                    scorecard = investigation.get("benchmark_scorecard") or {}
                    total_score = scorecard.get("total_score", 0.0)

                    self._append_log(
                        "SUCCESS",
                        f"RCA Complete for #{inc_id[:8]} ({domain}): Root Cause identified as '{rca.get('primary_root_cause')}' (Score: {total_score:.1f}/100).",
                        {
                            "incident_id": inc_id,
                            "domain": domain,
                            "root_cause": rca.get("primary_root_cause"),
                            "benchmark_score": total_score,
                        },
                    )
                    dispatched_investigations.append({
                        "incident_id": inc_id,
                        "domain": domain,
                        "root_cause": rca.get("primary_root_cause"),
                        "benchmark_score": total_score,
                        "status": "COMPLETED",
                    })
                except Exception as ex:
                    self._append_log("ERROR", f"Multi-Agent investigation failed for #{inc_id[:8]}: {str(ex)}")
                    print(f"[Sentinel Error] Investigation failed: {ex}")

        return {
            "status": "SUCCESS",
            "healthy": False,
            "anomalies_count": len(anomalies),
            "dispatched_count": len(dispatched_investigations),
            "dispatched_investigations": dispatched_investigations,
            "scan_timestamp": scan_time.isoformat(),
            "scan_result": scan_result,
        }

    def scan_now(self, force_rca: bool = False) -> Dict[str, Any]:
        """Synchronously triggers an immediate scan cycle on demand."""
        self._append_log("ACTION", "Manual forced scan initiated via Executive Command.")
        return self.execute_scan_cycle(force_rca=force_rca)

    def get_status(self) -> Dict[str, Any]:
        """Returns comprehensive operational telemetry of the Sentinel Worker."""
        now = datetime.now()
        uptime_seconds = int((now - self.start_time).total_seconds()) if self.start_time else 0
        
        # Calculate seconds until next scheduled scan
        if self.last_scan_time:
            elapsed = (now - self.last_scan_time).total_seconds()
            next_in = max(0, int(self.interval_seconds - elapsed))
        else:
            next_in = self.interval_seconds

        return {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "state": "PAUSED" if self.is_paused else ("ACTIVE" if self.is_running else "STOPPED"),
            "interval_seconds": self.interval_seconds,
            "scan_count": self.scan_count,
            "total_anomalies_detected": self.total_anomalies_detected,
            "investigations_triggered": self.investigations_triggered,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "last_scan_time": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "next_scan_seconds": next_in if (self.is_running and not self.is_paused) else None,
            "uptime_seconds": uptime_seconds,
        }

    def get_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent audit logs."""
        with self._lock:
            return list(self.audit_logs[:limit])


# Global Singleton instance
sentinel_worker = AutonomousSentinelWorker()
