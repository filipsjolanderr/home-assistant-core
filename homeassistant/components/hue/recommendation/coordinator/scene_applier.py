"""Scene applier for applying recommended scenes."""

from __future__ import annotations

from aiohue.v2.models.smart_scene import SmartScene

from ...bridge import HueBridge


class SceneApplier:
    """Applies scenes to Hue bridge."""

    def __init__(self, bridge: HueBridge) -> None:
        """Initialize scene applier."""
        self.bridge = bridge

    async def apply(self, scene_id: str) -> None:
        """Apply a scene by ID.

        Args:
            scene_id: ID of the scene to apply

        Raises:
            ValueError: If scene not found
        """
        scenes = self.bridge.api.scenes

        # Find the scene
        scene = None
        for s in scenes:
            if s.id == scene_id:
                scene = s
                break

        if scene is None:
            raise ValueError(f"Scene {scene_id} not found")

        # Apply the scene
        if isinstance(scene, SmartScene):
            await self.bridge.async_request_call(
                scenes.smart_scene.recall,
                scene_id,
            )
        else:
            await self.bridge.async_request_call(
                scenes.scene.recall,
                scene_id,
            )
