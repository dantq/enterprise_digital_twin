"""Realistic Business Noise Engine for Enterprise Digital Twin V2.

Implements controlled enterprise ingestion noise:
1. POS_DELAYED_SYNC: Physical retail orders synced with 6-18h lag.
2. REVIEW_MISATTRIBUTION: 3-5% random 1-star reviews from misclicks.
3. TELEMETRY_JITTER: Metric measurement jitter (+/- 3-5%).
4. Statistical validation helpers (Z-score, confidence intervals).
"""

import math
import random
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone


class NoiseType(str, Enum):
    POS_DELAYED_SYNC = "POS_DELAYED_SYNC"
    REVIEW_MISATTRIBUTION = "REVIEW_MISATTRIBUTION"
    TELEMETRY_JITTER = "TELEMETRY_JITTER"


class NoiseProfile:
    """Configuration for enterprise business noise injection."""

    def __init__(
        self,
        pos_delay_rate: float = 0.12,
        pos_min_delay_hours: float = 6.0,
        pos_max_delay_hours: float = 18.0,
        review_misattribution_rate: float = 0.04,
        telemetry_jitter_pct: float = 0.04,
        seed: Optional[int] = 42,
    ):
        self.pos_delay_rate = pos_delay_rate
        self.pos_min_delay_hours = pos_min_delay_hours
        self.pos_max_delay_hours = pos_max_delay_hours
        self.review_misattribution_rate = review_misattribution_rate
        self.telemetry_jitter_pct = telemetry_jitter_pct
        self.random = random.Random(seed)


class BusinessNoiseEngine:
    """Injects and quantifies enterprise noise without breaking database integrity."""

    def __init__(self, profile: Optional[NoiseProfile] = None):
        self.profile = profile or NoiseProfile()

    def apply_pos_sync_delay(
        self,
        event_time: datetime,
        channel: str = "Store POS",
    ) -> tuple[datetime, bool]:
        """Calculates ingested_at timestamp for orders.

        Applies 6-18h delay for physical POS channel if selected.
        """
        if channel in ("Store POS", "POS", "Physical Store"):
            if self.profile.random.random() < self.profile.pos_delay_rate:
                delay_hours = self.profile.random.uniform(
                    self.profile.pos_min_delay_hours,
                    self.profile.pos_max_delay_hours,
                )
                ingested_at = event_time + timedelta(hours=delay_hours)
                return ingested_at, True
        return event_time, False

    def is_review_noisy(self) -> bool:
        """Determines if an individual review is an accidental misattribution."""
        return self.profile.random.random() < self.profile.review_misattribution_rate

    def apply_metric_jitter(self, base_value: float, metric_name: str = "") -> float:
        """Applies realistic measurement noise (+/- 3-5%) around a baseline metric."""
        max_pct = self.profile.telemetry_jitter_pct
        noise_factor = self.profile.random.uniform(-max_pct, max_pct)
        noisy_val = base_value * (1.0 + noise_factor)
        return round(noisy_val, 4)

    @staticmethod
    def compute_z_score(sample_value: float, baseline_mean: float, baseline_std: float) -> float:
        """Calculates standard Z-score distance from moving baseline."""
        if baseline_std <= 1e-6:
            return 0.0
        return (sample_value - baseline_mean) / baseline_std

    @staticmethod
    def is_statistically_significant(z_score: float, confidence_level: float = 0.99) -> bool:
        """Checks if anomaly exceeds critical threshold (Z > 2.58 for 99% confidence)."""
        threshold = 2.576 if confidence_level >= 0.99 else 1.960
        return abs(z_score) >= threshold
