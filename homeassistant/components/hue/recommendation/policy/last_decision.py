"""Last decision store for hysteresis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class LastDecisionStore:
    """Stores the last decision made by the policy."""

    scene_id: str | None = None
    """Last selected scene ID."""
    score: float = 0.0
    """Score of the last decision."""
    timestamp: datetime | None = None
    """When the decision was made."""

    def update(self, scene_id: str, score: float) -> None:
        """Update the last decision."""
        self.scene_id = scene_id
        self.score = score
        self.timestamp = datetime.now(timezone.utc)

    def get_age_seconds(self) -> float:
        """Get age of last decision in seconds."""
        if self.timestamp is None:
            return float("inf")
        return (datetime.now(timezone.utc) - self.timestamp).total_seconds()
