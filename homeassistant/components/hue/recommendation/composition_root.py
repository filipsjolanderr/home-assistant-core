"""Composition Root (DI) for recommendation engine."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..bridge import HueBridge
from .context.providers import IContextProvider
from .context.providers.sun_provider import SunProvider
from .coordinator import RecommendationCoordinator
from .coordinator.scene_applier import SceneApplier
from .policy import PolicyService
from .policy.last_decision import LastDecisionStore
from .policy.strategies import IStrategy, TimeOfDayStrategy
from .policy.weights import WeightsAndParams


class ProviderRegistry:
    """Registry for context providers."""

    def __init__(self, providers: list[IContextProvider]) -> None:
        """Initialize provider registry."""
        self.providers = providers

    @classmethod
    def build(cls, hass: HomeAssistant) -> ProviderRegistry:
        """Build provider registry with default providers."""
        providers: list[IContextProvider] = [
            SunProvider(hass),
        ]
        return cls(providers)


class StrategyRegistry:
    """Registry for recommendation strategies."""

    def __init__(self, strategies: list[IStrategy]) -> None:
        """Initialize strategy registry."""
        self.strategies = strategies

    @classmethod
    def build(cls) -> StrategyRegistry:
        """Build strategy registry with default strategies."""
        strategies: list[IStrategy] = [
            TimeOfDayStrategy(),
        ]
        return cls(strategies)


class CompositionRoot:
    """Composition Root (Dependency Injection container).

    Builds and wires together all components of the recommendation engine.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        bridge: HueBridge,
        room_id: str,
    ) -> None:
        """Initialize composition root."""
        self.hass = hass
        self.bridge = bridge
        self.room_id = room_id

        # Build registries
        self.provider_registry = ProviderRegistry.build(hass)
        self.strategy_registry = StrategyRegistry.build()

        # Build weights and params
        self.weights = WeightsAndParams(
            strategy_weights={
                "time_of_day": 1.0,
            },
            inertia_boost=0.2,
            switch_delta_min=0.1,
            min_dwell_seconds=300,
        )

        # Build last decision store
        self.last_decision_store = LastDecisionStore()

        # Build policy service
        self.policy_service = PolicyService(
            strategies=self.strategy_registry.strategies,
            weights=self.weights,
            last_decision=self.last_decision_store,
        )

        # Build scene applier
        self.scene_applier = SceneApplier(bridge)

        # Build coordinator
        self.coordinator = RecommendationCoordinator(
            hass=hass,
            bridge=bridge,
            room_id=room_id,
            providers=self.provider_registry.providers,
            policy_service=self.policy_service,
            scene_applier=self.scene_applier,
            update_interval=60,  # Update every 60 seconds (will be converted to timedelta)
        )

    def get_coordinator(self) -> RecommendationCoordinator:
        """Get the recommendation coordinator."""
        return self.coordinator
