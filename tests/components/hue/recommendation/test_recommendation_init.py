"""Tests for recommendation setup."""

from datetime import timedelta
from unittest.mock import Mock

from homeassistant.components.hue.const import (
    CONF_RECOMMENDATION_WEIGHT_HOME_ARRIVAL,
    CONF_RECOMMENDATION_WEIGHT_TIME_OF_DAY,
    CONF_RECOMMENDATION_WEIGHT_WEEKLY_SCHEDULE,
)
from homeassistant.components.hue.recommendation import async_setup_recommendation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def test_async_setup_recommendation_initialization(
    hass: HomeAssistant, mock_bridge_v2: Mock
) -> None:
    """Test async_setup_recommendation initializes coordinator correctly."""
    coordinator = await async_setup_recommendation(hass, mock_bridge_v2)

    assert coordinator is not None
    assert coordinator.bridge == mock_bridge_v2
    assert coordinator.update_interval == timedelta(seconds=15)
    # We currently expect three providers: sun, schedule and presence
    assert len(coordinator.providers) == 3
    provider_ids = {provider.provider_id for provider in coordinator.providers}
    assert "sun" in provider_ids
    assert "schedule" in provider_ids
    assert "presence" in provider_ids
    assert coordinator.policy_service is not None
    assert coordinator.scene_applier is not None


async def test_async_setup_recommendation_weights_configuration_defaults(
    hass: HomeAssistant, mock_bridge_v2: Mock
) -> None:
    """Test async_setup_recommendation uses default weights when no options set."""
    coordinator = await async_setup_recommendation(hass, mock_bridge_v2)

    weights = coordinator.policy_service.weights
    assert weights.strategy_weights["time_of_day"] == 0.5
    assert weights.strategy_weights["weekly_schedule"] == 1.0
    assert weights.strategy_weights["home_arrival"] == 2.0
    assert weights.inertia_boost == 0.0
    assert weights.switch_delta_min == 0.0
    assert weights.min_dwell_seconds == 0


async def test_async_setup_recommendation_weights_from_options(
    hass: HomeAssistant, mock_bridge_v2: Mock
) -> None:
    """Test async_setup_recommendation reads strategy weights from entry options."""
    # Minimal fake config entry with options attribute used by recommendation.
    mock_entry = Mock(spec=ConfigEntry)
    mock_entry.options = {
        CONF_RECOMMENDATION_WEIGHT_TIME_OF_DAY: 2.0,
        CONF_RECOMMENDATION_WEIGHT_WEEKLY_SCHEDULE: 0.5,
        CONF_RECOMMENDATION_WEIGHT_HOME_ARRIVAL: 3.0,
    }
    # Attributes used by RecommendationCoordinator / DataUpdateCoordinator
    mock_entry.state = None
    mock_entry.entry_id = "test-entry-id"
    mock_entry.async_on_unload = Mock()
    mock_bridge_v2.config_entry = mock_entry

    coordinator = await async_setup_recommendation(hass, mock_bridge_v2)

    weights = coordinator.policy_service.weights
    assert weights.strategy_weights["time_of_day"] == 2.0
    assert weights.strategy_weights["weekly_schedule"] == 0.5
    assert weights.strategy_weights["home_arrival"] == 3.0


async def test_async_setup_recommendation_strategies(
    hass: HomeAssistant, mock_bridge_v2: Mock
) -> None:
    """Test async_setup_recommendation configures strategies correctly."""
    coordinator = await async_setup_recommendation(hass, mock_bridge_v2)

    strategies = coordinator.policy_service.strategies
    strategy_ids = {strategy.strategy_id for strategy in strategies}
    # time_of_day, weekly_schedule and home_arrival strategies should be configured
    assert "time_of_day" in strategy_ids
    assert "weekly_schedule" in strategy_ids
    assert "home_arrival" in strategy_ids
