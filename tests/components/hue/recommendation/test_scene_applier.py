"""Tests for scene applier."""

from unittest.mock import AsyncMock, Mock

import pytest

from homeassistant.components.hue.recommendation.coordinator.scene_applier import SceneApplier


async def test_scene_applier_apply_regular_scene() -> None:
    """Test SceneApplier applies regular scene."""
    bridge = Mock()
    bridge.async_request_call = AsyncMock()

    scene = Mock()
    scene.id = "scene1"

    scenes_controller = Mock()
    scenes_controller.scene = Mock()
    scenes_controller.scene.recall = AsyncMock()

    def get_scene(scene_id: str) -> Mock | None:
        """Mock get scene."""
        if scene_id == "scene1":
            return scene
        return None

    scenes_controller.__iter__ = Mock(return_value=iter([scene]))
    bridge.api = Mock()
    bridge.api.scenes = scenes_controller

    applier = SceneApplier(bridge)
    await applier.apply("scene1")

    assert bridge.async_request_call.called
    call_args = bridge.async_request_call.call_args
    assert call_args[0][0] == scenes_controller.scene.recall
    assert call_args[0][1] == "scene1"


async def test_scene_applier_apply_smart_scene() -> None:
    """Test SceneApplier applies smart scene."""
    from aiohue.v2.models.smart_scene import SmartScene

    bridge = Mock()
    bridge.async_request_call = AsyncMock()

    smart_scene = Mock(spec=SmartScene)
    smart_scene.id = "smart_scene1"

    scenes_controller = Mock()
    scenes_controller.smart_scene = Mock()
    scenes_controller.smart_scene.recall = AsyncMock()

    def get_scene(scene_id: str) -> Mock | None:
        """Mock get scene."""
        if scene_id == "smart_scene1":
            return smart_scene
        return None

    scenes_controller.__iter__ = Mock(return_value=iter([smart_scene]))
    bridge.api = Mock()
    bridge.api.scenes = scenes_controller

    applier = SceneApplier(bridge)
    await applier.apply("smart_scene1")

    assert bridge.async_request_call.called
    call_args = bridge.async_request_call.call_args
    assert call_args[0][0] == scenes_controller.smart_scene.recall
    assert call_args[0][1] == "smart_scene1"


async def test_scene_applier_apply_scene_not_found() -> None:
    """Test SceneApplier raises when scene not found."""
    bridge = Mock()
    scenes_controller = Mock()
    scenes_controller.__iter__ = Mock(return_value=iter([]))
    bridge.api = Mock()
    bridge.api.scenes = scenes_controller

    applier = SceneApplier(bridge)

    with pytest.raises(ValueError, match="Scene scene_not_found not found"):
        await applier.apply("scene_not_found")
