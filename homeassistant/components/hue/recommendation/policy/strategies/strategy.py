"""Strategy interface for recommendation engine."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ...context import HomeContext


@dataclass
class StrategyResult:
    """Result from a strategy scoring candidates."""

    scene_scores: dict[str, float]
    """Map of scene_id -> score (higher is better)."""
    metadata: dict[str, Any] | None = None
    """Optional metadata about the strategy's decision."""


class IStrategy(ABC):
    """Interface for recommendation strategies."""

    @property
    @abstractmethod
    def strategy_id(self) -> str:
        """Return unique identifier for this strategy."""

    @abstractmethod
    async def score(
        self, context: HomeContext, candidates: list[str]
    ) -> StrategyResult:
        """Score candidate scenes based on context.

        Args:
            context: Current home context
            candidates: List of scene IDs to score

        Returns:
            StrategyResult with scores for each candidate
        """
