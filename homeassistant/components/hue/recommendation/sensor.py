"""Support for Hue recommendation sensor entity."""

from __future__ import annotations

from aiohue.v2.controllers.events import EventType
from aiohue.v2.controllers.groups import Room
from aiohue.v2.models.resource import ResourceTypes

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from ..bridge import HueBridge, HueConfigEntry
from ..const import DOMAIN
from ..v2.entity import HueBaseEntity


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
    def async_add_sensor(event_type: EventType, resource: Room) -> None:
        """Add sensor entity for Hue room."""
        if resource.type in (ResourceTypes.ROOM, ResourceTypes.BRIDGE_HOME):
            async_add_entities([HueRecommendationSensorEntity(bridge, resource)])

    # Add sensors for all current rooms (including bridge home)
    for room in bridge.api.groups.room:
        async_add_sensor(EventType.RESOURCE_ADDED, room)

    # Also check all groups for bridge home (it might not be in .room)
    for group in bridge.api.groups:
        if isinstance(group, Room) and group.type == ResourceTypes.BRIDGE_HOME:
            async_add_sensor(EventType.RESOURCE_ADDED, group)

    # Register listener for new rooms
    config_entry.async_on_unload(
        bridge.api.groups.room.subscribe(
            async_add_sensor, event_filter=EventType.RESOURCE_ADDED
        )
    )

    # Also listen to all groups for bridge home
    @callback
    def async_add_bridge_home(event_type: EventType, resource) -> None:
        """Add sensor for bridge home if it's a Room."""
        if isinstance(resource, Room) and resource.type == ResourceTypes.BRIDGE_HOME:
            async_add_sensor(event_type, resource)

    config_entry.async_on_unload(
        bridge.api.groups.subscribe(
            async_add_bridge_home,
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

    def __init__(self, bridge: HueBridge, room: Room) -> None:
        """Initialize the recommendation sensor."""
        super().__init__(bridge, bridge.api.groups, room)
        self.room = room
        self._attr_unique_id = f"{room.id}_recommendation"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, room.id)},
        )
        # Set suggested_object_id directly to ensure correct entity ID generation
        self._attr_suggested_object_id = self.entity_description.key

    @property
    def suggested_object_id(self) -> str | None:
        """Return suggested object ID for entity ID generation."""
        # Override to use the key directly instead of resolving translations
        if (
            hasattr(self, "_attr_suggested_object_id")
            and self._attr_suggested_object_id
        ):
            return self._attr_suggested_object_id
        return self.entity_description.key

    async def async_added_to_hass(self) -> None:
        """Call when entity is added."""
        await super().async_added_to_hass()

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

    @callback
    def _handle_scene_event(self, event_type: EventType, resource) -> None:
        """Handle scene updates."""
        # Check if this scene belongs to our room
        try:
            scene_group = self.bridge.api.scenes.get_group(resource.id)
            if scene_group and scene_group.id == self.room.id:
                self.async_write_ha_state()
        except (AttributeError, KeyError):
            # Scene might not have a group yet, ignore
            pass

    def _get_recommended_scene(self) -> str | None:
        """Get the recommended scene name for this room."""
        try:
            # Find all scenes for this room
            scenes_for_room = []
            for scene in self.bridge.api.scenes:
                try:
                    scene_group = self.bridge.api.scenes.get_group(scene.id)
                    if scene_group and scene_group.id == self.room.id:
                        scenes_for_room.append(scene)
                except (AttributeError, KeyError):
                    # Scene might not have a group, skip it
                    continue

            if not scenes_for_room:
                return None

            # Return the first scene's name (simple recommendation)
            # Could be enhanced with more sophisticated logic later
            return scenes_for_room[0].metadata.name
        except (AttributeError, KeyError):
            return None

    @property
    def native_value(self) -> str | None:
        """Return the recommended scene name for this room."""
        return self._get_recommended_scene()
