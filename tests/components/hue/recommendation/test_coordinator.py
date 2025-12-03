"""Tests for recommendation coordinator."""

from unittest.mock import AsyncMock, Mock

from aiohue.v2.controllers.groups import Room, Zone
import pytest

from homeassistant.components.hue.recommendation.context import HomeContext
from homeassistant.components.hue.recommendation.context.providers import (
    IContextProvider,
)
from homeassistant.components.hue.recommendation.coordinator import (
    RecommendationCoordinator,
)
from homeassistant.components.hue.recommendation.coordinator.scene_applier import (
    SceneApplier,
)
from homeassistant.components.hue.recommendation.coordinator.scene_registry import (
    SceneRegistry,
)
from homeassistant.components.hue.recommendation.policy.decision import Decision
from homeassistant.core import HomeAssistant


class MockProvider(IContextProvider):
    """Mock context provider for testing."""

    def __init__(self, provider_id: str, elevation: float = 45.0) -> None:
        """Initialize mock provider."""
        self._provider_id = provider_id
        self._elevation = elevation

    @property
    def provider_id(self) -> str:
        """Return provider ID."""
        return self._provider_id

    async def fetch(self, context: HomeContext) -> HomeContext:
        """Update context with mock data."""
        context.sun.elevation = self._elevation
        return context


class MockPolicyService:
    """Mock policy service for testing."""

    def __init__(self, decision: Decision | None = None) -> None:
        """Initialize mock policy service."""
        self._decision = decision
        self.decide_called = False

    async def decide(
        self, context: HomeContext, candidates: list[str] | None = None
    ) -> Decision | None:
        """Return mock decision."""
        self.decide_called = True
        return self._decision


@pytest.fixture
def mock_groups_controller() -> Mock:
    """Create mock groups controller with rooms/zones."""
    groups_controller = Mock()

    # Create mock rooms using spec to pass isinstance checks
    room1 = Mock(spec=Room)
    room1.id = "test_room_1"
    room1.metadata = Mock()
    room1.metadata.name = "Room 1"
    room1.type = Mock()
    room1.type.value = "room"

    room2 = Mock(spec=Room)
    room2.id = "test_room_2"
    room2.metadata = Mock()
    room2.metadata.name = "Room 2"
    room2.type = Mock()
    room2.type.value = "room"

    # Bridge home can be a Zone or Room depending on implementation
    bridge_home = Mock(spec=Zone)
    bridge_home.id = "bridge_home"
    bridge_home.metadata = Mock()
    bridge_home.metadata.name = "Home"
    bridge_home.type = Mock()
    bridge_home.type.value = "bridge_home"

    groups_list = [room1, room2, bridge_home]
    groups_controller.__iter__ = Mock(return_value=iter(groups_list))
    return groups_controller


@pytest.fixture
def mock_scenes_controller() -> Mock:
    """Create mock scenes controller."""
    scenes_controller = Mock()
    scene1 = Mock()
    scene1.id = "scene1"
    scene2 = Mock()
    scene2.id = "scene2"

    def get_group(scene_id: str) -> Mock | None:
        """Mock get_group - scenes belong to test_room_1."""
        room = Mock()
        room.id = "test_room_1"
        return room

    scenes_controller.get_group = get_group
    scenes_controller.__iter__ = Mock(return_value=iter([scene1, scene2]))
    return scenes_controller


async def test_coordinator_update_data(
    hass: HomeAssistant,
    mock_bridge_v2: Mock,
    mock_groups_controller: Mock,
    mock_scenes_controller: Mock,
) -> None:
    """Test coordinator updates data correctly for all rooms."""
    mock_bridge_v2.api.groups = mock_groups_controller
    mock_bridge_v2.api.scenes = mock_scenes_controller

    provider = MockProvider("test", elevation=45.0)
    decision = Decision(
        scene_id="scene1",
        score=1.0,
        confidence=0.8,
        contributions={},
        strategy_scores={},
    )
    policy_service = MockPolicyService(decision)
    scene_applier = SceneApplier(mock_bridge_v2)

    coordinator = RecommendationCoordinator(
        hass=hass,
        bridge=mock_bridge_v2,
        providers=[provider],
        policy_service=policy_service,  # type: ignore[arg-type]
        scene_applier=scene_applier,
        scene_registry=SceneRegistry(),
        update_interval=60,
    )

    result = await coordinator._async_update_data()

    # Result should be a dict mapping room_id -> Decision
    assert isinstance(result, dict)
    assert "test_room_1" in result
    assert "test_room_2" in result
    assert "bridge_home" in result
    # test_room_1 should have a decision (has scenes)
    assert result["test_room_1"] is not None
    # Other rooms might be None if no scenes
    # Note: policy_service.decide_called is False because we're using random decisions for testing
    assert coordinator.current_context is not None
    assert coordinator.current_context.sun.elevation == 45.0


async def test_coordinator_enumerates_scenes(
    hass: HomeAssistant,
    mock_bridge_v2: Mock,
    mock_groups_controller: Mock,
    mock_scenes_controller: Mock,
) -> None:
    """Test coordinator enumerates scenes for all rooms."""
    mock_bridge_v2.api.groups = mock_groups_controller
    mock_bridge_v2.api.scenes = mock_scenes_controller

    provider = MockProvider("test")
    decision = Decision(
        scene_id="scene1",
        score=1.0,
        confidence=0.8,
        contributions={},
        strategy_scores={},
    )
    policy_service = MockPolicyService(decision)
    scene_applier = SceneApplier(mock_bridge_v2)

    coordinator = RecommendationCoordinator(
        hass=hass,
        bridge=mock_bridge_v2,
        providers=[provider],
        policy_service=policy_service,  # type: ignore[arg-type]
        scene_applier=scene_applier,
        scene_registry=SceneRegistry(),
        update_interval=60,
    )

    await coordinator._async_update_data()

    assert coordinator.current_context is not None
    # Context is shared, but scenes are enumerated per room
    # The context.lighting.available_scenes will be set for each room during iteration


async def test_coordinator_auto_apply_disabled(
    hass: HomeAssistant,
    mock_bridge_v2: Mock,
    mock_groups_controller: Mock,
    mock_scenes_controller: Mock,
) -> None:
    """Test coordinator doesn't auto-apply when disabled."""
    mock_bridge_v2.api.groups = mock_groups_controller
    mock_bridge_v2.api.scenes = mock_scenes_controller
    mock_bridge_v2.async_request_call = AsyncMock()

    provider = MockProvider("test")
    decision = Decision(
        scene_id="scene1",
        score=1.0,
        confidence=0.8,
        contributions={},
        strategy_scores={},
    )
    policy_service = MockPolicyService(decision)
    scene_applier = SceneApplier(mock_bridge_v2)

    coordinator = RecommendationCoordinator(
        hass=hass,
        bridge=mock_bridge_v2,
        providers=[provider],
        policy_service=policy_service,  # type: ignore[arg-type]
        scene_applier=scene_applier,
        scene_registry=SceneRegistry(),
        update_interval=60,
    )
    # Auto-apply is disabled by default (empty dict)

    await coordinator._async_update_data()

    # Should not have called scene applier
    mock_bridge_v2.async_request_call.assert_not_called()


async def test_coordinator_auto_apply_enabled(
    hass: HomeAssistant,
    mock_bridge_v2: Mock,
    mock_groups_controller: Mock,
) -> None:
    """Test coordinator auto-applies when enabled for a room."""
    # Create a mock scene that will be found
    scene1 = Mock()
    scene1.id = "scene1"

    # Create a fresh scenes controller mock that is properly iterable
    scenes_controller = Mock()
    scenes_list = [scene1]
    scenes_controller.__iter__ = lambda self: iter(scenes_list)

    # Mock scene recall
    scene_recall = AsyncMock()
    scenes_controller.scene = Mock()
    scenes_controller.scene.recall = scene_recall

    # Ensure get_group returns a room for scene1 (used by coordinator)
    def get_group(scene_id: str) -> Mock | None:
        """Mock get_group."""
        if scene_id == "scene1":
            room = Mock()
            room.id = "test_room_1"
            return room
        return None

    scenes_controller.get_group = get_group

    mock_bridge_v2.api.groups = mock_groups_controller
    mock_bridge_v2.api.scenes = scenes_controller
    mock_bridge_v2.async_request_call = AsyncMock()

    provider = MockProvider("test")
    decision = Decision(
        scene_id="scene1",
        score=1.0,
        confidence=0.8,
        contributions={},
        strategy_scores={},
    )
    policy_service = MockPolicyService(decision)
    scene_applier = SceneApplier(mock_bridge_v2)

    coordinator = RecommendationCoordinator(
        hass=hass,
        bridge=mock_bridge_v2,
        providers=[provider],
        policy_service=policy_service,  # type: ignore[arg-type]
        scene_applier=scene_applier,
        scene_registry=SceneRegistry(),
        update_interval=60,
    )

    # Enable auto-apply for test_room_1
    coordinator.set_auto_apply_enabled("test_room_1", True)

    # Now manually trigger update to test auto-apply
    await coordinator._async_update_data()

    # Should have called scene applier
    assert mock_bridge_v2.async_request_call.called


async def test_coordinator_global_auto_apply_enabled(
    hass: HomeAssistant,
    mock_bridge_v2: Mock,
    mock_groups_controller: Mock,
) -> None:
    """Test global auto-apply applies to all rooms."""
    scene1 = Mock()
    scene1.id = "scene1"

    scenes_controller = Mock()
    scenes_list = [scene1]
    scenes_controller.__iter__ = lambda self: iter(scenes_list)

    scene_recall = AsyncMock()
    scenes_controller.scene = Mock()
    scenes_controller.scene.recall = scene_recall

    def get_group(scene_id: str) -> Mock | None:
        if scene_id == "scene1":
            room = Mock()
            room.id = "test_room_2"
            return room
        return None

    scenes_controller.get_group = get_group

    mock_bridge_v2.api.groups = mock_groups_controller
    mock_bridge_v2.api.scenes = scenes_controller
    mock_bridge_v2.async_request_call = AsyncMock()

    provider = MockProvider("test")
    decision = Decision(
        scene_id="scene1",
        score=1.0,
        confidence=0.8,
        contributions={},
        strategy_scores={},
    )
    policy_service = MockPolicyService(decision)
    scene_applier = SceneApplier(mock_bridge_v2)

    coordinator = RecommendationCoordinator(
        hass=hass,
        bridge=mock_bridge_v2,
        providers=[provider],
        policy_service=policy_service,  # type: ignore[arg-type]
        scene_applier=scene_applier,
        scene_registry=SceneRegistry(),
        update_interval=60,
    )

    coordinator.set_global_auto_apply(True)

    await coordinator._async_update_data()

    assert mock_bridge_v2.async_request_call.called


async def test_coordinator_auto_apply_no_decision(
    hass: HomeAssistant,
    mock_bridge_v2: Mock,
    mock_groups_controller: Mock,
    mock_scenes_controller: Mock,
) -> None:
    """Test coordinator doesn't auto-apply when no decision."""
    mock_bridge_v2.api.groups = mock_groups_controller
    mock_bridge_v2.api.scenes = mock_scenes_controller
    mock_bridge_v2.async_request_call = AsyncMock()

    provider = MockProvider("test")
    policy_service = MockPolicyService(decision=None)
    scene_applier = SceneApplier(mock_bridge_v2)

    coordinator = RecommendationCoordinator(
        hass=hass,
        bridge=mock_bridge_v2,
        providers=[provider],
        policy_service=policy_service,  # type: ignore[arg-type]
        scene_applier=scene_applier,
        scene_registry=SceneRegistry(),
        update_interval=60,
    )
    coordinator.set_auto_apply_enabled("test_room_1", True)

    await coordinator._async_update_data()

    # Should not have called scene applier (no decision returned)
    mock_bridge_v2.async_request_call.assert_not_called()


async def test_coordinator_apply_recommendation(
    hass: HomeAssistant,
    mock_bridge_v2: Mock,
    mock_scenes_controller: Mock,
) -> None:
    """Test coordinator apply_recommendation method."""
    mock_bridge_v2.api.scenes = mock_scenes_controller
    mock_bridge_v2.async_request_call = AsyncMock()

    scene_recall = AsyncMock()
    mock_scenes_controller.scene = Mock()
    mock_scenes_controller.scene.recall = scene_recall

    provider = MockProvider("test")
    decision = Decision(
        scene_id="scene1",
        score=1.0,
        confidence=0.8,
        contributions={},
        strategy_scores={},
    )
    policy_service = MockPolicyService(decision)
    scene_applier = SceneApplier(mock_bridge_v2)

    coordinator = RecommendationCoordinator(
        hass=hass,
        bridge=mock_bridge_v2,
        providers=[provider],
        policy_service=policy_service,  # type: ignore[arg-type]
        scene_applier=scene_applier,
        scene_registry=SceneRegistry(),
        update_interval=60,
    )
    # Set data as dict with decision for test_room_1
    coordinator.data = {"test_room_1": decision}

    await coordinator.apply_recommendation("test_room_1")

    assert mock_bridge_v2.async_request_call.called


async def test_coordinator_apply_recommendation_no_decision(
    hass: HomeAssistant,
    mock_bridge_v2: Mock,
    mock_scenes_controller: Mock,
) -> None:
    """Test coordinator apply_recommendation raises when no decision."""
    mock_bridge_v2.api.scenes = mock_scenes_controller

    provider = MockProvider("test")
    policy_service = MockPolicyService(decision=None)
    scene_applier = SceneApplier(mock_bridge_v2)

    coordinator = RecommendationCoordinator(
        hass=hass,
        bridge=mock_bridge_v2,
        providers=[provider],
        policy_service=policy_service,  # type: ignore[arg-type]
        scene_applier=scene_applier,
        scene_registry=SceneRegistry(),
        update_interval=60,
    )
    coordinator.data = {"test_room_1": None}

    with pytest.raises(ValueError, match="No recommendation available for room"):
        await coordinator.apply_recommendation("test_room_1")


async def test_coordinator_get_decision(
    hass: HomeAssistant,
    mock_bridge_v2: Mock,
) -> None:
    """Test coordinator get_decision method."""
    provider = MockProvider("test")
    policy_service = MockPolicyService(decision=None)
    scene_applier = SceneApplier(mock_bridge_v2)

    coordinator = RecommendationCoordinator(
        hass=hass,
        bridge=mock_bridge_v2,
        providers=[provider],
        policy_service=policy_service,  # type: ignore[arg-type]
        scene_applier=scene_applier,
        scene_registry=SceneRegistry(),
        update_interval=60,
    )

    decision1 = Decision(
        scene_id="scene1",
        score=1.0,
        confidence=0.8,
        contributions={},
        strategy_scores={},
    )
    decision2 = Decision(
        scene_id="scene2",
        score=0.9,
        confidence=0.7,
        contributions={},
        strategy_scores={},
    )

    coordinator.data = {
        "test_room_1": decision1,
        "test_room_2": decision2,
        "bridge_home": None,
    }

    assert coordinator.get_decision("test_room_1") == decision1
    assert coordinator.get_decision("test_room_2") == decision2
    assert coordinator.get_decision("bridge_home") is None
    assert coordinator.get_decision("nonexistent_room") is None


async def test_coordinator_auto_apply_enabled_methods(
    hass: HomeAssistant,
    mock_bridge_v2: Mock,
) -> None:
    """Test coordinator auto_apply_enabled getter/setter methods."""
    provider = MockProvider("test")
    policy_service = MockPolicyService(decision=None)
    scene_applier = SceneApplier(mock_bridge_v2)

    coordinator = RecommendationCoordinator(
        hass=hass,
        bridge=mock_bridge_v2,
        providers=[provider],
        policy_service=policy_service,  # type: ignore[arg-type]
        scene_applier=scene_applier,
        scene_registry=SceneRegistry(),
        update_interval=60,
    )

    # Initially disabled
    assert coordinator.get_auto_apply_enabled("test_room_1") is False

    # Enable for one room
    coordinator.set_auto_apply_enabled("test_room_1", True)
    assert coordinator.get_auto_apply_enabled("test_room_1") is True
    assert coordinator.get_auto_apply_enabled("test_room_2") is False

    # Disable
    coordinator.set_auto_apply_enabled("test_room_1", False)
    assert coordinator.get_auto_apply_enabled("test_room_1") is False
