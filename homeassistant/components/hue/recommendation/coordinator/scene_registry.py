"""Registry for Hue scenes per room.

This module keeps a mapping between room IDs and their available scenes,
including both the opaque scene ID and the human-readable scene name.

Strategies work on the scene *names* for better matching, while the
coordinator and scene applier continue to operate on the real scene IDs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SceneRef:
    """Reference to a Hue scene."""

    id: str
    """Opaque Hue scene identifier."""

    name: str
    """Human-readable scene name from Hue metadata."""


class SceneRegistry:
    """Registry for scenes per room/zone."""

    def __init__(self) -> None:
        """Initialize an empty scene registry."""
        self._by_room: dict[str, list[SceneRef]] = {}

    def set_room_scenes(self, room_id: str, scenes: list[SceneRef]) -> None:
        """Set the list of scenes for a room."""
        self._by_room[room_id] = scenes

    def get_room_scenes(self, room_id: str) -> list[SceneRef]:
        """Return all scenes registered for a room."""
        return self._by_room.get(room_id, [])

    def get_candidate_names(self, room_id: str) -> list[str]:
        """Return candidate scene names for a room.

        These names are what strategies should score and what the policy
        service will store in decisions.
        """
        return [scene.name for scene in self.get_room_scenes(room_id)]

    def resolve_id(self, room_id: str, scene_name: str) -> str | None:
        """Resolve a scene name to its ID for a given room.

        Matching is case-insensitive on the scene name.
        """
        scene_name_lower = scene_name.lower()
        for scene in self.get_room_scenes(room_id):
            if scene.name.lower() == scene_name_lower:
                return scene.id
        return None
