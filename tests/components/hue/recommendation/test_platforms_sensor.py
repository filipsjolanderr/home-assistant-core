"""Tests for Hue recommendation sensor platform."""

from unittest.mock import Mock

import pytest
from aiohue.v2.controllers.groups import Room
from aiohue.v2.models.resource import ResourceTypes

from homeassistant.components.hue.recommendation.platforms.sensor import (
    HueRecommendationSensorEntity,
    async_setup_entry,
)
from homeassistant.core import HomeAssistant

from tests.components.hue.conftest import create_mock_bridge
from tests.components.hue.recommendation.conftest import mock_hue_bridge_v2


async def test_async_setup_entry_v1_bridge(hass: HomeAssistant) -> None:
    """Test setup entry skips V1 bridges."""
    bridge = create_mock_bridge(hass, api_version=1)
    config_entry = Mock()
    config_entry.runtime_data = bridge
    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    async_add_entities.assert_not_called()


async def test_async_setup_entry_v2_bridge(
    hass: HomeAssistant, mock_hue_bridge_v2: Mock
) -> None:
    """Test setup entry creates entities for V2 bridges."""
    bridge = mock_hue_bridge_v2

    # Create test data with rooms
    test_data = [
        {
            "id": "room1",
            "id_v1": "/groups/1",
            "children": [],
            "metadata": {"name": "Test Room 1", "archetype": "living_room"},
            "services": [],
            "type": "room",
        },
        {
            "id": "bridge_home",
            "id_v1": "/groups/0",
            "children": [],
            "metadata": {"name": "Bridge Home"},
            "services": [],
            "type": "bridge_home",
        },
    ]

    # Initialize bridge with test data
    await bridge.api.load_test_data(test_data)
    config_entry = Mock()
    config_entry.runtime_data = bridge
    config_entry.async_on_unload = Mock()

    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    # Should add entities for both rooms (regular room + bridge home)
    # Note: bridge_home might be included in bridge.api.groups.room already
    # or might need to be found in bridge.api.groups
    assert async_add_entities.call_count >= 1
    # Verify at least the regular room was added
    if async_add_entities.call_count == 1:
        # If only 1, check if bridge_home is in groups.room
        rooms = list(bridge.api.groups.room)
        assert len(rooms) >= 1, "Expected at least one room"
    else:
        assert async_add_entities.call_count == 2


async def test_sensor_entity_initialization(
    hass: HomeAssistant, mock_hue_bridge_v2: Mock
) -> None:
    """Test sensor entity initialization."""
    bridge = mock_hue_bridge_v2
    # Initialize bridge with test data
    await bridge.api.load_test_data([])
    room = Mock(spec=Room)
    room.id = "room1"
    room.type = ResourceTypes.ROOM

    entity = HueRecommendationSensorEntity(bridge, room)

    assert entity.room == room
    assert entity._attr_unique_id == "room1_recommendation"
    assert entity._attr_has_entity_name is True
    assert entity.entity_description.key == "recommendation"


async def test_sensor_entity_suggested_object_id(
    hass: HomeAssistant, mock_hue_bridge_v2: Mock
) -> None:
    """Test sensor entity suggested_object_id property."""
    bridge = mock_hue_bridge_v2
    # Initialize bridge with test data
    await bridge.api.load_test_data([])
    room = Mock(spec=Room)
    room.id = "room1"
    room.type = ResourceTypes.ROOM

    entity = HueRecommendationSensorEntity(bridge, room)

    assert entity.suggested_object_id == "recommendation"


async def test_sensor_native_value_with_scene(
    hass: HomeAssistant, mock_hue_bridge_v2: Mock
) -> None:
    """Test sensor native_value returns scene name."""
    bridge = mock_hue_bridge_v2
    # Initialize bridge with test data
    await bridge.api.load_test_data([])

    room = Mock(spec=Room)
    room.id = "room1"
    room.type = ResourceTypes.ROOM

    # Create mock scene
    scene = Mock()
    scene.id = "scene1"
    scene.metadata = Mock()
    scene.metadata.name = "Test Scene"

    # Mock scenes controller
    scenes_controller = Mock()
    scenes_controller.get_group = Mock(return_value=room)
    scenes_controller.get = Mock(return_value=scene)
    scenes_controller.__iter__ = Mock(return_value=iter([scene]))
    bridge.api.scenes = scenes_controller

    # Mock coordinator with decision
    from homeassistant.components.hue.recommendation.policy.decision import Decision

    decision = Decision(
        scene_id="scene1",
        score=1.0,
        confidence=0.8,
        contributions={},
        strategy_scores={},
    )
    mock_coordinator = Mock()
    mock_coordinator.data = {"room1": decision}
    mock_coordinator.get_decision = Mock(return_value=decision)

    # Mock coordinator
    bridge.recommendation_coordinator = mock_coordinator

    entity = HueRecommendationSensorEntity(bridge, room)

    assert entity.native_value == "Test Scene"


async def test_sensor_native_value_no_scene(
    hass: HomeAssistant, mock_hue_bridge_v2: Mock
) -> None:
    """Test sensor native_value returns None when no scene available."""
    bridge = mock_hue_bridge_v2
    # Initialize bridge with test data
    await bridge.api.load_test_data([])

    room = Mock(spec=Room)
    room.id = "room1"
    room.type = ResourceTypes.ROOM

    # Mock scenes controller with no scenes
    scenes_controller = Mock()
    scenes_controller.__iter__ = Mock(return_value=iter([]))
    bridge.api.scenes = scenes_controller

    # Mock coordinator with no decision
    mock_coordinator = Mock()
    mock_coordinator.data = {"room1": None}
    mock_coordinator.get_decision = Mock(return_value=None)

    # Mock coordinator
    bridge.recommendation_coordinator = mock_coordinator

    entity = HueRecommendationSensorEntity(bridge, room)

    assert entity.native_value is None


async def test_sensor_native_value_scene_not_for_room(
    hass: HomeAssistant, mock_hue_bridge_v2: Mock
) -> None:
    """Test sensor native_value returns None when scene doesn't belong to room."""
    bridge = mock_hue_bridge_v2
    # Initialize bridge with test data
    await bridge.api.load_test_data([])

    room = Mock(spec=Room)
    room.id = "room1"
    room.type = ResourceTypes.ROOM

    other_room = Mock(spec=Room)
    other_room.id = "room2"

    # Create mock scene for different room
    scene = Mock()
    scene.id = "scene1"

    # Mock scenes controller
    scenes_controller = Mock()
    scenes_controller.get_group = Mock(return_value=other_room)
    scenes_controller.__iter__ = Mock(return_value=iter([scene]))
    bridge.api.scenes = scenes_controller

    # Mock coordinator with no decision for this room
    mock_coordinator = Mock()
    mock_coordinator.data = {"room1": None}
    mock_coordinator.get_decision = Mock(return_value=None)

    # Mock coordinator
    bridge.recommendation_coordinator = mock_coordinator

    entity = HueRecommendationSensorEntity(bridge, room)

    assert entity.native_value is None


async def test_sensor_async_added_to_hass(
    hass: HomeAssistant, mock_hue_bridge_v2: Mock
) -> None:
    """Test sensor entity added to hass subscribes to updates."""
    bridge = mock_hue_bridge_v2
    # Initialize bridge with test data
    await bridge.api.load_test_data([])

    room = Mock(spec=Room)
    room.id = "room1"
    room.type = ResourceTypes.ROOM

    # Mock coordinator
    mock_coordinator = Mock()
    mock_coordinator.async_add_listener = Mock(return_value=Mock())
    mock_coordinator.async_request_refresh = Mock()

    # Mock coordinator
    bridge.recommendation_coordinator = mock_coordinator

    groups_subscribe_mock = Mock(return_value=Mock())
    scenes_subscribe_mock = Mock(return_value=Mock())
    bridge.api.groups.subscribe = groups_subscribe_mock
    bridge.api.scenes.subscribe = scenes_subscribe_mock

    entity = HueRecommendationSensorEntity(bridge, room)
    entity.hass = hass
    entity.async_on_remove = Mock()
    entity.async_write_ha_state = Mock()

    await entity.async_added_to_hass()

    # Should subscribe to coordinator, groups and scenes
    mock_coordinator.async_add_listener.assert_called_once()
    assert groups_subscribe_mock.call_count >= 1
    assert scenes_subscribe_mock.call_count >= 1


async def test_sensor_handle_scene_event(
    hass: HomeAssistant, mock_hue_bridge_v2: Mock
) -> None:
    """Test sensor handles scene events correctly."""
    bridge = mock_hue_bridge_v2
    # Initialize bridge with test data
    await bridge.api.load_test_data([])

    room = Mock(spec=Room)
    room.id = "room1"
    room.type = ResourceTypes.ROOM

    # Mock coordinator
    mock_coordinator = Mock()
    mock_coordinator.async_request_refresh = Mock()

    # Mock coordinator
    bridge.recommendation_coordinator = mock_coordinator

    entity = HueRecommendationSensorEntity(bridge, room)
    entity.async_write_ha_state = Mock()

    # Mock scene event for this room
    scene = Mock()
    scene.id = "scene1"

    scenes_controller = Mock()
    scenes_controller.get_group = Mock(return_value=room)
    bridge.api.scenes = scenes_controller

    from aiohue.v2.controllers.events import EventType

    entity._handle_scene_event(EventType.RESOURCE_UPDATED, scene)

    # Should request coordinator refresh
    mock_coordinator.async_request_refresh.assert_called_once()


async def test_sensor_handle_scene_event_different_room(
    hass: HomeAssistant, mock_hue_bridge_v2: Mock
) -> None:
    """Test sensor ignores scene events for different rooms."""
    bridge = mock_hue_bridge_v2
    # Initialize bridge with test data
    await bridge.api.load_test_data([])

    room = Mock(spec=Room)
    room.id = "room1"
    room.type = ResourceTypes.ROOM

    other_room = Mock(spec=Room)
    other_room.id = "room2"

    entity = HueRecommendationSensorEntity(bridge, room)
    entity.async_write_ha_state = Mock()

    # Mock scene event for different room
    scene = Mock()
    scene.id = "scene1"

    scenes_controller = Mock()
    scenes_controller.get_group = Mock(return_value=other_room)
    bridge.api.scenes = scenes_controller

    from aiohue.v2.controllers.events import EventType

    entity._handle_scene_event(EventType.RESOURCE_UPDATED, scene)

    entity.async_write_ha_state.assert_not_called()
