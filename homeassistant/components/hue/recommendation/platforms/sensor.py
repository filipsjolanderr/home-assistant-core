"""Support for Hue recommendation sensor entity."""

from __future__ import annotations

from collections.abc import Callable

from aiohue.v2.controllers.events import EventType
from aiohue.v2.controllers.groups import Room, Zone
from aiohue.v2.models.resource import ResourceTypes

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from ...bridge import HueBridge, HueConfigEntry
from ...const import DOMAIN
from ...v2.entity import HueBaseEntity
from ..coordinator import RecommendationCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: HueConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Hue recommendation sensor entities."""
    bridge = config_entry.runtime_data

    if bridge.api_version == 1:
        return

    @callback
    def async_add_sensor(event_type: EventType, resource: Room | Zone) -> None:
        """Add sensor entity for Hue room or zone."""
        if resource.type in (
            ResourceTypes.ROOM,
            ResourceTypes.ZONE,
            ResourceTypes.BRIDGE_HOME,
        ):
            async_add_entities([HueRecommendationSensorEntity(bridge, resource)])

    # Add sensors for all groups (rooms, zones, and bridge home)
    # Check all groups to ensure bridge home is included
    for group in bridge.api.groups:
        if isinstance(group, (Room, Zone)):
            async_add_sensor(EventType.RESOURCE_ADDED, group)

    # Register listener for all groups (rooms, zones, and bridge home)
    @callback
    def async_add_group(event_type: EventType, resource) -> None:
        """Add sensor for any Room or Zone (including bridge home)."""
        if isinstance(resource, (Room, Zone)):
            async_add_sensor(event_type, resource)

    config_entry.async_on_unload(
        bridge.api.groups.subscribe(
            async_add_group,
            event_filter=EventType.RESOURCE_ADDED,
        )
    )


class HueRecommendationSensorEntity(HueBaseEntity, SensorEntity):
    """Representation of a Hue recommendation sensor."""

    _attr_has_entity_name = True

    entity_description = SensorEntityDescription(
        key="recommendation",
        translation_key="recommendation",
        name=None,
        has_entity_name=True,
    )

    def __init__(self, bridge: HueBridge, room: Room | Zone) -> None:
        """Initialize the recommendation sensor."""
        super().__init__(bridge, bridge.api.groups, room)
        self.room = room  # Can be Room or Zone
        self._attr_unique_id = f"{room.id}_recommendation"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, room.id)},
        )
        self._coordinator_unsub: Callable[[], None] | None = None

    @property
    def suggested_object_id(self) -> str | None:
        """Return suggested object ID for entity ID generation."""
        # Always return "recommendation" for proper entity ID generation
        return "recommendation"

    @property
    def _coordinator(self) -> RecommendationCoordinator | None:
        """Get the shared recommendation coordinator from bridge."""
        return self.bridge.recommendation_coordinator

    async def async_added_to_hass(self) -> None:
        """Call when entity is added."""
        await super().async_added_to_hass()

        # Ensure coordinator is initialized (may be set after platform setup)
        self._async_bind_coordinator_listener()

        # Subscribe to room updates
        self.async_on_remove(
            self.bridge.api.groups.subscribe(
                self._handle_event,
                self.room.id,
                EventType.RESOURCE_UPDATED,
            )
        )

        # Subscribe to scene updates to refresh recommendation
        self.async_on_remove(
            self.bridge.api.scenes.subscribe(
                self._handle_scene_event,
            )
        )

    def _async_bind_coordinator_listener(self) -> None:
        """Ensure we bind to the coordinator once it becomes available."""

        def _attach_listener() -> None:
            if self._coordinator_unsub or not self._coordinator:
                return
            self._coordinator_unsub = self._coordinator.async_add_listener(
                self._handle_coordinator_update
            )
            self.async_on_remove(self._coordinator_unsub)
            # Trigger initial state update now that coordinator is available
            self._handle_coordinator_update()

        if self.bridge.recommendation_ready.is_set():
            _attach_listener()
            return

        async def _wait_for_recommendation() -> None:
            await self.bridge.recommendation_ready.wait()
            _attach_listener()

        ready_task = self.hass.async_create_task(_wait_for_recommendation())
        self.async_on_remove(ready_task.cancel)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle coordinator updates."""
        self.async_write_ha_state()

    @callback
    def _handle_scene_event(self, event_type: EventType, resource) -> None:
        """Handle scene updates."""
        # Check if this scene belongs to our room
        try:
            scene_group = self.bridge.api.scenes.get_group(resource.id)
            if scene_group and scene_group.id == self.room.id:
                # Request coordinator refresh when scenes change
                if self._coordinator:
                    self._coordinator.async_request_refresh()
        except (AttributeError, KeyError):
            # Scene might not have a group yet, ignore
            pass

    def _get_recommended_scene(self) -> str | None:
        """Get the recommended scene name for this room."""
        coordinator = self._coordinator
        if not coordinator or not coordinator.data:
            return None

        # Get decision for this specific room
        decision = coordinator.get_decision(self.room.id)
        if not decision or not decision.scene_id:
            return None

        # Get scene name from the scene ID
        # Try using .get() method first (if available)
        try:
            scene = self.bridge.api.scenes.get(decision.scene_id)
            if scene:
                return scene.metadata.name
        except (AttributeError, KeyError):
            pass

        # Fallback: iterate through scenes to find matching ID
        try:
            for scene in self.bridge.api.scenes:
                if scene.id == decision.scene_id:
                    return scene.metadata.name
        except (AttributeError, KeyError):
            pass

        # Final fallback: return scene ID if name not available
        return decision.scene_id

    @property
    def native_value(self) -> str | None:
        """Return the recommended scene name for this room."""
        return self._get_recommended_scene()
