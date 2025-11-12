"""Recommendation engine for Hue integration."""

from .composition_root import CompositionRoot, ProviderRegistry, StrategyRegistry
from .coordinator import RecommendationCoordinator, SceneApplier
from .policy import Decision, PolicyService

__all__ = [
    "CompositionRoot",
    "Decision",
    "PolicyService",
    "ProviderRegistry",
    "RecommendationCoordinator",
    "SceneApplier",
    "StrategyRegistry",
]
