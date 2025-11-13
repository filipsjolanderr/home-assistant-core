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
    assert coordinator.update_interval == timedelta(seconds=60)
    assert len(coordinator.providers) == 1
    assert coordinator.providers[0].provider_id == "sun"
    assert coordinator.policy_service is not None
    assert coordinator.scene_applier is not None


async def test_async_setup_recommendation_weights_configuration(
    hass: HomeAssistant, mock_bridge_v2: Mock
) -> None:
    """Test async_setup_recommendation configures weights correctly."""
    coordinator = await async_setup_recommendation(hass, mock_bridge_v2)

    weights = coordinator.policy_service.weights
    assert weights.strategy_weights["time_of_day"] == 1.0
    assert weights.inertia_boost == 0.2
    assert weights.switch_delta_min == 0.1
    assert weights.min_dwell_seconds == 300


async def test_async_setup_recommendation_strategies(
    hass: HomeAssistant, mock_bridge_v2: Mock
) -> None:
    """Test async_setup_recommendation configures strategies correctly."""
    coordinator = await async_setup_recommendation(hass, mock_bridge_v2)

    strategies = coordinator.policy_service.strategies
    assert len(strategies) == 1
    assert strategies[0].strategy_id == "time_of_day"
