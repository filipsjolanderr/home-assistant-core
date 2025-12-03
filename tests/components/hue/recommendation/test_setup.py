"""Tests for recommendation setup."""

from datetime import timedelta
from unittest.mock import Mock

from homeassistant.components.hue.recommendation import async_setup_recommendation
from homeassistant.core import HomeAssistant


async def test_async_setup_recommendation_initialization(
    hass: HomeAssistant, mock_bridge_v2: Mock
) -> None:
    """Test async_setup_recommendation initializes coordinator correctly."""
    coordinator = await async_setup_recommendation(hass, mock_bridge_v2)

    assert coordinator is not None
    assert coordinator.bridge == mock_bridge_v2
    assert coordinator.update_interval == timedelta(seconds=15)
    # We currently expect two providers: sun, schedule and presence
    assert len(coordinator.providers) == 3
    provider_ids = {provider.provider_id for provider in coordinator.providers}
    assert "sun" in provider_ids
    assert "schedule" in provider_ids
    assert "presence" in provider_ids
    assert coordinator.policy_service is not None
    assert coordinator.scene_applier is not None


async def test_async_setup_recommendation_weights_configuration(
    hass: HomeAssistant, mock_bridge_v2: Mock
) -> None:
    """Test async_setup_recommendation configures weights correctly."""
    coordinator = await async_setup_recommendation(hass, mock_bridge_v2)

    weights = coordinator.policy_service.weights
    assert weights.strategy_weights["time_of_day"] == 0.5
    assert weights.strategy_weights["home_arrival"] == 2.0
    assert weights.inertia_boost == 0.0
    assert weights.switch_delta_min == 0.0
    assert weights.min_dwell_seconds == 0


async def test_async_setup_recommendation_strategies(
    hass: HomeAssistant, mock_bridge_v2: Mock
) -> None:
    """Test async_setup_recommendation configures strategies correctly."""
    coordinator = await async_setup_recommendation(hass, mock_bridge_v2)

    strategies = coordinator.policy_service.strategies
    strategy_ids = {strategy.strategy_id for strategy in strategies}
    # Both time_of_day and weekly_schedule strategies should be configured
    assert "time_of_day" in strategy_ids
    assert "weekly_schedule" in strategy_ids
    assert "home_arrival" in strategy_ids
