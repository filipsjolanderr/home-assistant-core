"""Tests for recommendation coordinator."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from homeassistant.components.hue.recommendation.coordinator import (
    RecommendationCoordinator,
)
from homeassistant.components.hue.recommendation.context import HomeContext
from homeassistant.components.hue.recommendation.context.providers import (
    IContextProvider,
)
from homeassistant.components.hue.recommendation.policy import PolicyService
from homeassistant.components.hue.recommendation.policy.decision import Decision
from homeassistant.components.hue.recommendation.policy.last_decision import (
    LastDecisionStore,
)
from homeassistant.components.hue.recommendation.policy.weights import (
    WeightsAndParams,
)
from homeassistant.components.hue.recommendation.coordinator.scene_applier import SceneApplier
from homeassistant.core import HomeAssistant

from tests.components.hue.conftest import create_mock_bridge


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
def mock_scenes_controller() -> Mock:
    """Create mock scenes controller."""
    scenes_controller = Mock()
    scene1 = Mock()
    scene1.id = "scene1"
    scene2 = Mock()
    scene2.id = "scene2"

    def get_group(scene_id: str) -> Mock | None:
        """Mock get_group."""
        room = Mock()
        room.id = "test_room"
        return room

    scenes_controller.get_group = get_group
    scenes_controller.__iter__ = Mock(return_value=iter([scene1, scene2]))
    return scenes_controller


async def test_coordinator_update_data(
    hass: HomeAssistant,
    mock_bridge_v2: Mock,
    mock_scenes_controller: Mock,
) -> None:
    """Test coordinator updates data correctly."""
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
    weights = WeightsAndParams()
    last_decision = LastDecisionStore()

    coordinator = RecommendationCoordinator(
        hass=hass,
        bridge=mock_bridge_v2,
        room_id="test_room",
        providers=[provider],
        policy_service=policy_service,  # type: ignore[arg-type]
        scene_applier=scene_applier,
        update_interval=60,
    )

    result = await coordinator._async_update_data()

    assert result == decision
    assert policy_service.decide_called
    assert coordinator.current_context is not None
    assert coordinator.current_context.sun.elevation == 45.0


async def test_coordinator_enumerates_scenes(
    hass: HomeAssistant,
    mock_bridge_v2: Mock,
    mock_scenes_controller: Mock,
) -> None:
    """Test coordinator enumerates scenes for room."""
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
    weights = WeightsAndParams()
    last_decision = LastDecisionStore()

    coordinator = RecommendationCoordinator(
        hass=hass,
        bridge=mock_bridge_v2,
        room_id="test_room",
        providers=[provider],
        policy_service=policy_service,  # type: ignore[arg-type]
        scene_applier=scene_applier,
        update_interval=60,
    )

    await coordinator._async_update_data()

    assert coordinator.current_context is not None
    assert "scene1" in coordinator.current_context.lighting.available_scenes
    assert "scene2" in coordinator.current_context.lighting.available_scenes


async def test_coordinator_auto_apply_disabled(
    hass: HomeAssistant,
    mock_bridge_v2: Mock,
    mock_scenes_controller: Mock,
) -> None:
    """Test coordinator doesn't auto-apply when disabled."""
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
    weights = WeightsAndParams()
    last_decision = LastDecisionStore()

    coordinator = RecommendationCoordinator(
        hass=hass,
        bridge=mock_bridge_v2,
        room_id="test_room",
        providers=[provider],
        policy_service=policy_service,  # type: ignore[arg-type]
        scene_applier=scene_applier,
        update_interval=60,
    )
    coordinator.auto_apply_enabled = False

    await coordinator._async_update_data()

    # Should not have called scene applier
    mock_bridge_v2.async_request_call.assert_not_called()


async def test_coordinator_auto_apply_enabled(
    hass: HomeAssistant,
    mock_bridge_v2: Mock,
) -> None:
    """Test coordinator auto-applies when enabled."""
    # Create a mock scene that will be found
    scene1 = Mock()
    scene1.id = "scene1"

    # Create a fresh scenes controller mock that is properly iterable
    # Make it directly iterable by implementing __iter__ as a bound method
    scenes_controller = Mock()
    # Create a list to iterate over
    scenes_list = [scene1]
    # Make __iter__ return an iterator over the list (accepts self parameter)
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
            room.id = "test_room"
            return room
        return None
    scenes_controller.get_group = get_group

    # Replace the scenes controller (mock_bridge_v2 already has api.scenes from create_mock_bridge)
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

    # Create SceneApplier AFTER scenes controller is set up
    # SceneApplier stores bridge reference, so scenes must be ready
    scene_applier = SceneApplier(mock_bridge_v2)
    weights = WeightsAndParams()
    last_decision = LastDecisionStore()

    coordinator = RecommendationCoordinator(
        hass=hass,
        bridge=mock_bridge_v2,
        room_id="test_room",
        providers=[provider],
        policy_service=policy_service,  # type: ignore[arg-type]
        scene_applier=scene_applier,
        update_interval=60,
    )

    # Set auto_apply_enabled AFTER coordinator is created and scenes are set up
    # This avoids the refresh triggering before scenes are ready
    coordinator._auto_apply_enabled = True

    # Now manually trigger update to test auto-apply
    await coordinator._async_update_data()

    # Should have called scene applier
    assert mock_bridge_v2.async_request_call.called


async def test_coordinator_auto_apply_no_decision(
    hass: HomeAssistant,
    mock_bridge_v2: Mock,
    mock_scenes_controller: Mock,
) -> None:
    """Test coordinator doesn't auto-apply when no decision."""
    mock_bridge_v2.api.scenes = mock_scenes_controller
    mock_bridge_v2.async_request_call = AsyncMock()

    provider = MockProvider("test")
    policy_service = MockPolicyService(decision=None)
    scene_applier = SceneApplier(mock_bridge_v2)
    weights = WeightsAndParams()
    last_decision = LastDecisionStore()

    coordinator = RecommendationCoordinator(
        hass=hass,
        bridge=mock_bridge_v2,
        room_id="test_room",
        providers=[provider],
        policy_service=policy_service,  # type: ignore[arg-type]
        scene_applier=scene_applier,
        update_interval=60,
    )
    coordinator.auto_apply_enabled = True

    await coordinator._async_update_data()

    # Should not have called scene applier
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
    weights = WeightsAndParams()
    last_decision = LastDecisionStore()

    coordinator = RecommendationCoordinator(
        hass=hass,
        bridge=mock_bridge_v2,
        room_id="test_room",
        providers=[provider],
        policy_service=policy_service,  # type: ignore[arg-type]
        scene_applier=scene_applier,
        update_interval=60,
    )
    coordinator.data = decision

    await coordinator.apply_recommendation()

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
    weights = WeightsAndParams()
    last_decision = LastDecisionStore()

    coordinator = RecommendationCoordinator(
        hass=hass,
        bridge=mock_bridge_v2,
        room_id="test_room",
        providers=[provider],
        policy_service=policy_service,  # type: ignore[arg-type]
        scene_applier=scene_applier,
        update_interval=60,
    )
    coordinator.data = None

    with pytest.raises(ValueError, match="No recommendation available"):
        await coordinator.apply_recommendation()
