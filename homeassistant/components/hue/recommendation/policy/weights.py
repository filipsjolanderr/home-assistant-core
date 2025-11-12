"""Weights and parameters for policy service."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WeightsAndParams:
    """Weights and parameters for policy decisions."""

    strategy_weights: dict[str, float] = field(default_factory=dict)
    """Weights for each strategy (strategy_id -> weight)."""
    inertia_boost: float = 0.2
    """Boost score for previously selected scene (hysteresis)."""
    switch_delta_min: float = 0.1
    """Minimum score delta required to switch scenes."""
    min_dwell_seconds: int = 300
    """Minimum time (seconds) before allowing scene switch."""

    def get_strategy_weight(self, strategy_id: str) -> float:
        """Get weight for a strategy, defaulting to 1.0."""
        return self.strategy_weights.get(strategy_id, 1.0)
