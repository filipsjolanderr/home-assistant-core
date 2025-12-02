"""Recommendation engine for Hue integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.core import HomeAssistant

from ..bridge import HueBridge
from .context.providers.provider import IContextProvider
from .context.providers.schedule_provider import ScheduleProvider
from .context.providers.sun_provider import SunProvider
from .coordinator import RecommendationCoordinator, SceneApplier
from .policy import Decision, PolicyService
from .policy.last_decision import LastDecisionStore
from .policy.strategies import IStrategy, TimeOfDayStrategy, WeeklyScheduleStrategy
from .policy.weights import WeightsAndParams

# Default weights and parameters for recommendation engine
DEFAULT_STRATEGY_WEIGHT = 1.0
"""Default weight for a strategy."""
DEFAULT_INERTIA_BOOST = 0.2
"""Default boost score for previously selected scene (hysteresis)."""
DEFAULT_SWITCH_DELTA_MIN = 0.1
"""Default minimum score delta required to switch scenes."""
DEFAULT_MIN_DWELL_SECONDS = 300
"""Default minimum time (seconds) before allowing scene switch."""

__all__ = [
    "Decision",
    "PolicyService",
    "RecommendationCoordinator",
    "SceneApplier",
    "async_setup_recommendation",
]


async def async_setup_recommendation(
    hass: HomeAssistant, bridge: HueBridge
) -> RecommendationCoordinator:
    """Set up recommendation engine for a bridge.

    Builds and wires together all components of the recommendation engine.
    One instance per bridge, manages recommendations for all rooms/zones.

    Args:
        hass: Home Assistant instance
        bridge: Hue bridge instance

    Returns:
        Initialized recommendation coordinator
    """
    # Build context providers
    providers: list[IContextProvider] = [SunProvider(hass), ScheduleProvider(hass)]

    # Build strategies
    strategies: list[IStrategy] = [TimeOfDayStrategy(), WeeklyScheduleStrategy()]

    # Build weights and params - auto-populate strategy weights from registered strategies
    strategy_weights = {
        strategy.strategy_id: DEFAULT_STRATEGY_WEIGHT for strategy in strategies
    }
    weights = WeightsAndParams(
        strategy_weights=strategy_weights,
        inertia_boost=DEFAULT_INERTIA_BOOST,
        switch_delta_min=DEFAULT_SWITCH_DELTA_MIN,
        min_dwell_seconds=DEFAULT_MIN_DWELL_SECONDS,
    )

    # Build last decision store
    last_decision_store = LastDecisionStore()

    # Build policy service
    policy_service = PolicyService(
        strategies=strategies,
        weights=weights,
        last_decision=last_decision_store,
    )

    # Build scene applier
    scene_applier = SceneApplier(bridge)

    # Build coordinator (manages all rooms)
    coordinator = RecommendationCoordinator(
        hass=hass,
        bridge=bridge,
        providers=providers,
        policy_service=policy_service,
        scene_applier=scene_applier,
        update_interval=timedelta(seconds=60),
    )

    # Start the coordinator
    if bridge.config_entry is not None:
        await coordinator.async_config_entry_first_refresh()
    else:
        await coordinator.async_request_refresh()

    return coordinator
