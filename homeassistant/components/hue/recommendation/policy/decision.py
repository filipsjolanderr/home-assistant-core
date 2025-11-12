"""Decision data structure."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Decision:
    """A recommendation decision."""

    scene_id: str
    """Selected scene ID."""
    score: float
    """Final weighted score."""
    confidence: float
    """Confidence level (0.0 to 1.0)."""
    contributions: dict[str, float]
    """Per-strategy contribution scores."""
    strategy_scores: dict[str, dict[str, float]]
    """Per-strategy scene scores."""
