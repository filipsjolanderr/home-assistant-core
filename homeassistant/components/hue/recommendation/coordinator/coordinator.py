"""Coordinator for recommendation engine."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from aiohue.v2.controllers.groups import Room, Zone

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from ...bridge import HueBridge
from ..context import HomeContext
from ..context.providers import IContextProvider
from ..policy import Decision, PolicyService
from .scene_applier import SceneApplier
from .scene_registry import SceneRef, SceneRegistry

_LOGGER = logging.getLogger(__name__)


class RecommendationCoordinator(DataUpdateCoordinator[dict[str, Decision | None]]):
    """Coordinator for Hue recommendation engine.

    Manages recommendations for all rooms/zones on a bridge.
    Data is a dict mapping room_id -> Decision | None.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        bridge: HueBridge,
        providers: list[IContextProvider],
        policy_service: PolicyService,
        scene_applier: SceneApplier,
        scene_registry: SceneRegistry,
        update_interval: timedelta | int | None = None,
    ) -> None:
        """Initialize coordinator."""
        # Convert int to timedelta if needed
        if isinstance(update_interval, int):
            update_interval = timedelta(seconds=update_interval)
        elif update_interval is None:
            update_interval = timedelta(seconds=60)

        super().__init__(
            hass,
            _LOGGER,
            name="hue_recommendation",
            update_interval=update_interval,
            config_entry=bridge.config_entry,
        )
        self.bridge = bridge
        self.providers = providers
        self.policy_service = policy_service
        self.scene_applier = scene_applier
        self.scene_registry = scene_registry
        self._auto_apply_enabled: dict[str, bool] = {}  # room_id -> enabled
        self._global_auto_apply = False
        self._context: HomeContext | None = None

    def get_auto_apply_enabled(self, room_id: str) -> bool:
        """Return whether auto-apply is enabled for a room."""
        return self._auto_apply_enabled.get(room_id, False)

    def set_auto_apply_enabled(self, room_id: str, value: bool) -> None:
        """Set auto-apply enabled state for a room."""
        self._auto_apply_enabled[room_id] = value
        if value:
            # Trigger immediate update when enabled
            # Schedule refresh asynchronously
            self.hass.async_create_task(self.async_request_refresh())

    def set_global_auto_apply(self, value: bool) -> None:
        """Set global auto-apply state (bridge home)."""
        self._global_auto_apply = value
        if value:
            self.hass.async_create_task(self.async_request_refresh())

    def get_decision(self, room_id: str) -> Decision | None:
        """Get the recommendation decision for a specific room."""
        if not self.data:
            return None
        return self.data.get(room_id)

    @property
    def current_context(self) -> HomeContext | None:
        """Return current context snapshot."""
        return self._context

    async def _async_update_data(self) -> dict[str, Decision | None]:
        """Fetch data and make recommendations for all rooms."""
        try:
            # Build context by fetching from all providers.
            # We currently run providers sequentially so that each provider
            # can build on the context produced by the previous ones
            # (e.g. schedule, sun, presence all merged into one HomeContext).
            context = HomeContext()
            for provider in self.providers:
                context = await provider.fetch(context)

            # Store context snapshot
            self._context = context

            # Get all rooms and zones (including bridge home)
            rooms: dict[str, str] = {}  # room_id -> room_name
            for group in self.bridge.api.groups:
                if isinstance(group, (Room, Zone)):
                    rooms[group.id] = group.metadata.name

            # Build recommendations for each room
            recommendations: dict[str, Decision | None] = {}

            for room_id, room_name in rooms.items():
                # Enumerate available scenes for this room
                available_scenes: list[SceneRef] = []
                for scene in self.bridge.api.scenes:
                    try:
                        scene_group = self.bridge.api.scenes.get_group(scene.id)
                        if scene_group and scene_group.id == room_id:
                            # Prefer human-readable name from metadata; fall back to ID
                            scene_name = (
                                getattr(getattr(scene, "metadata", None), "name", None)
                                or scene.id
                            )
                            available_scenes.append(
                                SceneRef(
                                    id=scene.id,
                                    name=scene_name,
                                )
                            )
                    except (AttributeError, KeyError):
                        continue

                # Update scene registry and context candidates (scene names)
                self.scene_registry.set_room_scenes(room_id, available_scenes)
                context.lighting.available_scenes = [
                    scene.name for scene in available_scenes
                ]

                # Log context summary
                _LOGGER.debug(
                    "Context for room %s (%s): sun_elevation=%.1f, sun_state=%s, "
                    "available_scenes=%s, occupancy=%s",
                    room_id,
                    room_name,
                    context.sun.elevation if context.sun else None,
                    context.sun.state if context.sun else None,
                    context.lighting.available_scenes,
                    context.constraints.occupancy_detected
                    if context.constraints
                    else None,
                )

                # Make decision using policy service
                candidate_names = context.lighting.available_scenes
                if not candidate_names:
                    _LOGGER.debug(
                        "No available scenes for room %s (%s)", room_id, room_name
                    )
                    recommendations[room_id] = None
                    continue

                # Use policy service to make decision (strategies work on scene names)
                decision = await self.policy_service.decide(context, candidate_names)

                # Log decision with additional detail about why it changed or stayed
                if decision:
                    _LOGGER.info(
                        "Recommendation for room %s (%s): scene_id=%s, score=%.3f, "
                        "confidence=%.3f, strategies=%s",
                        room_id,
                        room_name,
                        decision.scene_id,
                        decision.score,
                        decision.confidence,
                        list(decision.strategy_scores.keys()),
                    )
                    _LOGGER.debug(
                        "Recommendation details for room %s (%s): scene_id=%s, "
                        "score=%.3f, confidence=%.3f, strategy_scores=%s, "
                        "contributions=%s",
                        room_id,
                        room_name,
                        decision.scene_id,
                        decision.score,
                        decision.confidence,
                        decision.strategy_scores,
                        decision.contributions,
                    )
                else:
                    _LOGGER.debug(
                        "No recommendation available for room %s (%s) "
                        "(strategies returned no valid winner)",
                        room_id,
                        room_name,
                    )

                # Auto-apply if enabled and decision is valid
                auto_apply_enabled = (
                    self._global_auto_apply
                    or self._auto_apply_enabled.get(room_id, False)
                )
                if auto_apply_enabled and decision and decision.scene_id:
                    # Resolve scene name via registry; fall back to using scene_id directly
                    resolved_id = (
                        self.scene_registry.resolve_id(room_id, decision.scene_id)
                        or decision.scene_id
                    )
                    try:
                        await self.scene_applier.apply(resolved_id)
                        _LOGGER.debug(
                            "Auto-applied scene %s for room %s (%s)",
                            resolved_id,
                            room_id,
                            room_name,
                        )
                    except Exception as err:
                        _LOGGER.warning(
                            "Failed to auto-apply scene %s for room %s: %s",
                            decision.scene_id,
                            room_id,
                            err,
                        )

                recommendations[room_id] = decision

            return recommendations

        except Exception as err:
            _LOGGER.error("Error updating recommendations: %s", err, exc_info=True)
            return {}

    async def apply_recommendation(self, room_id: str) -> None:
        """Manually apply the current recommendation for a room."""
        decision = self.get_decision(room_id)
        if not decision or not decision.scene_id:
            raise ValueError(f"No recommendation available for room {room_id}")

        # Resolve scene name via registry; fall back to using scene_id directly
        resolved_id = self.scene_registry.resolve_id(room_id, decision.scene_id) or (
            decision.scene_id
        )

        _LOGGER.info(
            "Manually applying recommendation for room %s: scene_id=%s",
            room_id,
            decision.scene_id,
        )
        await self.scene_applier.apply(resolved_id)
