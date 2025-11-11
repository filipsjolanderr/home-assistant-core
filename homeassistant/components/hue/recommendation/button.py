"""Support for Hue recommendation button entity."""

from __future__ import annotations

from aiohue.v2.controllers.events import EventType
from aiohue.v2.controllers.groups import Room
from aiohue.v2.models.resource import ResourceTypes
from aiohue.v2.models.smart_scene import SmartScene

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
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
    """Set up Hue recommendation button entities."""
    bridge = config_entry.runtime_data

    if bridge.api_version == 1:
        return

    @callback
    def async_add_button(event_type: EventType, resource: Room) -> None:
        """Add button entity for Hue room."""
        if resource.type in (ResourceTypes.ROOM, ResourceTypes.BRIDGE_HOME):
            async_add_entities([HueRecommendationButtonEntity(bridge, resource)])

    # Add buttons for all current rooms (including bridge home)
    for room in bridge.api.groups.room:
        async_add_button(EventType.RESOURCE_ADDED, room)

    # Also check all groups for bridge home (it might not be in .room)
    for group in bridge.api.groups:
        if isinstance(group, Room) and group.type == ResourceTypes.BRIDGE_HOME:
            async_add_button(EventType.RESOURCE_ADDED, group)

    # Register listener for new rooms
    config_entry.async_on_unload(
        bridge.api.groups.room.subscribe(
            async_add_button, event_filter=EventType.RESOURCE_ADDED
        )
    )

    # Also listen to all groups for bridge home
    @callback
    def async_add_bridge_home(event_type: EventType, resource) -> None:
        """Add button for bridge home if it's a Room."""
        if isinstance(resource, Room) and resource.type == ResourceTypes.BRIDGE_HOME:
            async_add_button(event_type, resource)

    config_entry.async_on_unload(
        bridge.api.groups.subscribe(
            async_add_bridge_home,
            event_filter=EventType.RESOURCE_ADDED,
        )
    )


class HueRecommendationButtonEntity(HueBaseEntity, ButtonEntity):
    """Representation of a Hue recommendation apply button."""

    _attr_has_entity_name = True

    entity_description = ButtonEntityDescription(
        key="apply_recommendation",
        translation_key="apply_recommendation",
        name=None,
        has_entity_name=True,
    )

    def __init__(self, bridge: HueBridge, room: Room) -> None:
        """Initialize the recommendation button."""
        super().__init__(bridge, bridge.api.groups, room)
        self.room = room
        self._attr_unique_id = f"{room.id}_apply_recommendation"
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

    def _get_recommended_scene(self):
        """Get the recommended scene for this room."""
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

            # Return the first scene (simple recommendation)
            return scenes_for_room[0]
        except (AttributeError, KeyError):
            return None

    async def async_press(self) -> None:
        """Press the button to apply the recommended scene."""
        scene = self._get_recommended_scene()
        if not scene:
            raise HomeAssistantError("No recommendation available for this room")

        # Check if it's a smart scene or regular scene
        if isinstance(scene, SmartScene):
            # Activate smart scene
            await self.bridge.async_request_call(
                self.bridge.api.scenes.smart_scene.recall,
                scene.id,
            )
        else:
            # Activate regular scene
            await self.bridge.async_request_call(
                self.bridge.api.scenes.scene.recall,
                scene.id,
            )
