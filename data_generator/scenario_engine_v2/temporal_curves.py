"""Temporal Curves Engine for Scenario Engine V2.

Models realistic multi-phase crisis intensity over time:
1. Incubation (Ủ mầm): 10% - 20%
2. Escalation (Leo thang): 20% - 80%
3. Peak Crisis (Đỉnh điểm): 80% - 100%
4. Decay & Recovery (Hạ nhiệt): Exponential decline back to baseline
"""

import math
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class CrisisPhase(str, Enum):
    INCUBATION = "INCUBATION"
    ESCALATION = "ESCALATION"
    PEAK_CRISIS = "PEAK_CRISIS"
    DECAY_RECOVERY = "DECAY_RECOVERY"


class CurveProfile(str, Enum):
    MULTI_PHASE_PIECEWISE = "MULTI_PHASE_PIECEWISE"
    SIGMOID_BURST = "SIGMOID_BURST"
    WEIBULL_ASYMMETRIC = "WEIBULL_ASYMMETRIC"


class TemporalCurveEngine:
    """Computes time-varying crisis intensity and active crisis phase."""

    def __init__(
        self,
        curve_type: CurveProfile = CurveProfile.MULTI_PHASE_PIECEWISE,
        peak_severity: float = 1.0,
        incubation_ratio: float = 0.20,
        escalation_ratio: float = 0.35,
        peak_ratio: float = 0.25,
        decay_ratio: float = 0.20,
    ):
        self.curve_type = curve_type
        self.peak_severity = max(0.0, min(1.0, peak_severity))

        total = incubation_ratio + escalation_ratio + peak_ratio + decay_ratio
        self.incubation_ratio = incubation_ratio / total
        self.escalation_ratio = escalation_ratio / total
        self.peak_ratio = peak_ratio / total
        self.decay_ratio = decay_ratio / total

    def evaluate_normalized(self, t_norm: float) -> Dict[str, Any]:
        """Evaluates intensity for normalized progress t_norm in [0.0, 1.0]."""
        t = max(0.0, min(1.0, float(t_norm)))

        if self.curve_type == CurveProfile.SIGMOID_BURST:
            intensity, phase = self._eval_sigmoid(t)
        elif self.curve_type == CurveProfile.WEIBULL_ASYMMETRIC:
            intensity, phase = self._eval_weibull(t)
        else:
            intensity, phase = self._eval_piecewise(t)

        scaled_intensity = round(intensity * self.peak_severity, 4)
        return {
            "t_normalized": t,
            "phase": phase.value,
            "raw_intensity": round(intensity, 4),
            "effective_severity": scaled_intensity,
            "curve_type": self.curve_type.value,
        }

    def evaluate_datetime(
        self,
        current_time: datetime,
        start_time: datetime,
        end_time: datetime,
    ) -> Dict[str, Any]:
        """Evaluates intensity for a specific datetime between start_time and end_time."""
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        total_seconds = (end_time - start_time).total_seconds()
        if total_seconds <= 0:
            return self.evaluate_normalized(1.0)

        elapsed_seconds = (current_time - start_time).total_seconds()
        t_norm = elapsed_seconds / total_seconds
        res = self.evaluate_normalized(t_norm)
        res["current_time"] = current_time.isoformat()
        return res

    def _eval_piecewise(self, t: float) -> tuple[float, CrisisPhase]:
        p1 = self.incubation_ratio
        p2 = p1 + self.escalation_ratio
        p3 = p2 + self.peak_ratio

        if t < p1:
            progress = t / max(p1, 1e-6)
            intensity = 0.10 + 0.10 * progress
            return intensity, CrisisPhase.INCUBATION
        elif t < p2:
            progress = (t - p1) / max(self.escalation_ratio, 1e-6)
            intensity = 0.20 + 0.65 * (progress ** 1.5)
            return intensity, CrisisPhase.ESCALATION
        elif t < p3:
            progress = (t - p2) / max(self.peak_ratio, 1e-6)
            intensity = 0.85 + 0.15 * math.sin(progress * math.pi)
            return min(1.0, intensity), CrisisPhase.PEAK_CRISIS
        else:
            progress = (t - p3) / max(self.decay_ratio, 1e-6)
            intensity = 0.85 * math.exp(-3.0 * progress)
            return max(0.05, intensity), CrisisPhase.DECAY_RECOVERY

    def _eval_sigmoid(self, t: float) -> tuple[float, CrisisPhase]:
        k = 10.0
        mid = 0.4
        val = 1.0 / (1.0 + math.exp(-k * (t - mid)))
        if t < 0.25:
            phase = CrisisPhase.INCUBATION
        elif t < 0.50:
            phase = CrisisPhase.ESCALATION
        elif t < 0.75:
            phase = CrisisPhase.PEAK_CRISIS
        else:
            phase = CrisisPhase.DECAY_RECOVERY
        return min(1.0, max(0.0, val)), phase

    def _eval_weibull(self, t: float) -> tuple[float, CrisisPhase]:
        k = 2.2
        lam = 0.45
        if t <= 0:
            return 0.05, CrisisPhase.INCUBATION
        val = (k / lam) * ((t / lam) ** (k - 1)) * math.exp(-((t / lam) ** k))
        norm_val = val / 1.7
        intensity = min(1.0, max(0.05, norm_val))
        if t < 0.2:
            phase = CrisisPhase.INCUBATION
        elif t < 0.45:
            phase = CrisisPhase.ESCALATION
        elif t < 0.70:
            phase = CrisisPhase.PEAK_CRISIS
        else:
            phase = CrisisPhase.DECAY_RECOVERY
        return intensity, phase
