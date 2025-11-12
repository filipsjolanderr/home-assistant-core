"""Tests for composition root."""

from datetime import timedelta
from unittest.mock import Mock

from homeassistant.components.hue.recommendation.composition_root import (
    CompositionRoot,
    ProviderRegistry,
    StrategyRegistry,
)
from homeassistant.core import HomeAssistant


async def test_provider_registry_build(hass: HomeAssistant) -> None:
    """Test ProviderRegistry.build creates default providers."""
    registry = ProviderRegistry.build(hass)

    assert len(registry.providers) == 1
    assert registry.providers[0].provider_id == "sun"


async def test_strategy_registry_build() -> None:
    """Test StrategyRegistry.build creates default strategies."""
    registry = StrategyRegistry.build()

    assert len(registry.strategies) == 1
    assert registry.strategies[0].strategy_id == "time_of_day"


async def test_composition_root_initialization(
    hass: HomeAssistant, mock_bridge_v2: Mock
) -> None:
    """Test CompositionRoot initializes all components."""
    root = CompositionRoot(hass, mock_bridge_v2, "test_room")

    assert root.hass == hass
    assert root.bridge == mock_bridge_v2
    assert root.room_id == "test_room"
    assert root.provider_registry is not None
    assert root.strategy_registry is not None
    assert root.weights is not None
    assert root.last_decision_store is not None
    assert root.policy_service is not None
    assert root.scene_applier is not None
    assert root.coordinator is not None


async def test_composition_root_get_coordinator(
    hass: HomeAssistant, mock_bridge_v2: Mock
) -> None:
    """Test CompositionRoot.get_coordinator returns coordinator."""
    root = CompositionRoot(hass, mock_bridge_v2, "test_room")

    coordinator = root.get_coordinator()

    assert coordinator == root.coordinator
    assert coordinator.room_id == "test_room"


async def test_composition_root_weights_configuration(
    hass: HomeAssistant, mock_bridge_v2: Mock
) -> None:
    """Test CompositionRoot configures weights correctly."""
    root = CompositionRoot(hass, mock_bridge_v2, "test_room")

    assert root.weights.strategy_weights["time_of_day"] == 1.0
    assert root.weights.inertia_boost == 0.2
    assert root.weights.switch_delta_min == 0.1
    assert root.weights.min_dwell_seconds == 300


async def test_composition_root_coordinator_configuration(
    hass: HomeAssistant, mock_bridge_v2: Mock
) -> None:
    """Test CompositionRoot configures coordinator correctly."""
    root = CompositionRoot(hass, mock_bridge_v2, "test_room")

    coordinator = root.coordinator
    assert coordinator.bridge == mock_bridge_v2
    assert coordinator.room_id == "test_room"
    assert coordinator.update_interval == timedelta(seconds=60)
    assert len(coordinator.providers) == 1
    assert coordinator.policy_service == root.policy_service
    assert coordinator.scene_applier == root.scene_applier
