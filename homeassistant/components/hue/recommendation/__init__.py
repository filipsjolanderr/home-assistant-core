"""Recommendation engine for Hue integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.core import HomeAssistant

from ..bridge import HueBridge
from ..const import (
    CONF_RECOMMENDATION_UPDATE_INTERVAL,
    CONF_RECOMMENDATION_WEIGHT_HOME_ARRIVAL,
    CONF_RECOMMENDATION_WEIGHT_TIME_OF_DAY,
    CONF_RECOMMENDATION_WEIGHT_WEEKLY_SCHEDULE,
    DEFAULT_RECOMMENDATION_STRATEGY_WEIGHT,
    DEFAULT_RECOMMENDATION_UPDATE_INTERVAL,
    DEFAULT_RECOMMENDATION_WEIGHT_HOME_ARRIVAL,
    DEFAULT_RECOMMENDATION_WEIGHT_TIME_OF_DAY,
    DEFAULT_RECOMMENDATION_WEIGHT_WEEKLY_SCHEDULE,
)
from .coordinator import scene_catalog
from .context.providers.presence_provider import PresenceProvider
from .context.providers.provider import IContextProvider
from .context.providers.schedule_provider import ScheduleProvider
from .context.providers.sun_provider import SunProvider
from .coordinator import RecommendationCoordinator, SceneApplier
from .coordinator.scene_registry import SceneRegistry
from .policy import Decision, PolicyService
from .policy.last_decision import LastDecisionStore
from .policy.strategies import (
    HomeArrivalStrategy,
    IStrategy,
    TimeOfDayStrategy,
    WeeklyScheduleStrategy,
)
from .policy.weights import WeightsAndParams

__all__ = [
    "Decision",
    "PolicyService",
    "RecommendationCoordinator",
    "SceneApplier",
    "async_setup_recommendation",
    "scene_catalog",
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
    providers: list[IContextProvider] = [
        SunProvider(hass),
        ScheduleProvider(hass),
        PresenceProvider(hass),
    ]

    # Build strategies
    strategies: list[IStrategy] = [
        TimeOfDayStrategy(),
        WeeklyScheduleStrategy(),
        HomeArrivalStrategy(),
    ]

    # Map strategy IDs to config option keys for user-configurable weights.
    strategy_option_keys: dict[str, str] = {
        "time_of_day": CONF_RECOMMENDATION_WEIGHT_TIME_OF_DAY,
        "weekly_schedule": CONF_RECOMMENDATION_WEIGHT_WEEKLY_SCHEDULE,
        "home_arrival": CONF_RECOMMENDATION_WEIGHT_HOME_ARRIVAL,
    }

    # Build weights and params - auto-populate strategy weights from registered
    # strategies, allowing user-configured overrides via config entry options.
    config_entry = getattr(bridge, "config_entry", None)
    config_options: dict[str, object] = (
        getattr(config_entry, "options", {}) if config_entry is not None else {}
    )

    strategy_weights: dict[str, float] = {}
    for strategy in strategies:
        option_key = strategy_option_keys.get(strategy.strategy_id)
        if option_key is not None and option_key in config_options:
            # Coerce to float but fall back to default on invalid data.
            try:
                strategy_weights[strategy.strategy_id] = float(
                    config_options[option_key]  # type: ignore[arg-type]
                )
            except (TypeError, ValueError):
                strategy_weights[strategy.strategy_id] = (
                    DEFAULT_RECOMMENDATION_STRATEGY_WEIGHT
                )
        else:
            if strategy.strategy_id == "time_of_day":
                default_weight = DEFAULT_RECOMMENDATION_WEIGHT_TIME_OF_DAY
            elif strategy.strategy_id == "weekly_schedule":
                default_weight = DEFAULT_RECOMMENDATION_WEIGHT_WEEKLY_SCHEDULE
            elif strategy.strategy_id == "home_arrival":
                default_weight = DEFAULT_RECOMMENDATION_WEIGHT_HOME_ARRIVAL
            else:
                default_weight = DEFAULT_RECOMMENDATION_STRATEGY_WEIGHT
            strategy_weights[strategy.strategy_id] = default_weight

    # Hysteresis parameters (inertia and dwell) are centrally defined
    # in WeightsAndParams and can be overridden via config entry options
    # in the future. For now we rely on WeightsAndParams defaults here.
    weights = WeightsAndParams(strategy_weights=strategy_weights)

    # Build last decision store
    last_decision_store = LastDecisionStore()

    # Build policy service
    policy_service = PolicyService(
        strategies=strategies,
        weights=weights,
        last_decision=last_decision_store,
    )

    # Build scene applier and scene registry
    scene_applier = SceneApplier(bridge)
    scene_registry = SceneRegistry()

    # Determine update interval
    try:
        update_interval_seconds = int(
            config_options.get(
                CONF_RECOMMENDATION_UPDATE_INTERVAL,
                DEFAULT_RECOMMENDATION_UPDATE_INTERVAL,
            )
        )
    except (TypeError, ValueError):
        update_interval_seconds = DEFAULT_RECOMMENDATION_UPDATE_INTERVAL
    else:
        update_interval_seconds = max(update_interval_seconds, 5)

    # Build coordinator (manages all rooms)
    coordinator = RecommendationCoordinator(
        hass=hass,
        bridge=bridge,
        providers=providers,
        policy_service=policy_service,
        scene_applier=scene_applier,
        scene_registry=scene_registry,
        update_interval=timedelta(seconds=update_interval_seconds),
    )

    # Start the coordinator
    if bridge.config_entry is not None:
        await coordinator.async_config_entry_first_refresh()
    else:
        await coordinator.async_request_refresh()

    return coordinator
