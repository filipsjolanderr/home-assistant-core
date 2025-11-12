"""Support for Hue recommendation button entity."""

from __future__ import annotations

from aiohue.v2.controllers.events import EventType
from aiohue.v2.controllers.groups import Room, Zone
from aiohue.v2.models.resource import ResourceTypes

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from ...bridge import HueBridge, HueConfigEntry
from ...const import DOMAIN
from ...v2.entity import HueBaseEntity
from ..composition_root import CompositionRoot
from ..coordinator import RecommendationCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: HueConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Hue recommendation button entities."""
    bridge = config_entry.runtime_data

    if bridge.api_version == 1:
        return

    # Ensure composition root is initialized (may already be done by sensor setup)
    if bridge.recommendation_composition_root is None:
        bridge.recommendation_composition_root = CompositionRoot(hass, bridge)
        coordinator = bridge.recommendation_composition_root.get_coordinator()
        # Start the coordinator to begin periodic updates
        # Use async_request_refresh since we don't have config_entry in coordinator
        await coordinator.async_request_refresh()

    @callback
    def async_add_button(event_type: EventType, resource: Room | Zone) -> None:
        """Add button entity for Hue room or zone."""
        if resource.type in (ResourceTypes.ROOM, ResourceTypes.ZONE, ResourceTypes.BRIDGE_HOME):
            async_add_entities([HueRecommendationButtonEntity(bridge, resource)])

    # Add buttons for all groups (rooms, zones, and bridge home)
    # Check all groups to ensure bridge home is included
    for group in bridge.api.groups:
        if isinstance(group, (Room, Zone)):
            async_add_button(EventType.RESOURCE_ADDED, group)

    # Register listener for all groups (rooms, zones, and bridge home)
    @callback
    def async_add_group(event_type: EventType, resource) -> None:
        """Add button for any Room or Zone (including bridge home)."""
        if isinstance(resource, (Room, Zone)):
            async_add_button(event_type, resource)

    config_entry.async_on_unload(
        bridge.api.groups.subscribe(
            async_add_group,
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

    def __init__(self, bridge: HueBridge, room: Room | Zone) -> None:
        """Initialize the recommendation button."""
        super().__init__(bridge, bridge.api.groups, room)
        self.room = room  # Can be Room or Zone
        self._attr_unique_id = f"{room.id}_apply_recommendation"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, room.id)},
        )
    @property
    def suggested_object_id(self) -> str | None:
        """Return suggested object ID for entity ID generation."""
        # Always return "apply_recommendation" for proper entity ID generation
        return "apply_recommendation"

    @property
    def _coordinator(self) -> RecommendationCoordinator | None:
        """Get the shared recommendation coordinator from bridge."""
        if self.bridge.recommendation_composition_root is None:
            return None
        return self.bridge.recommendation_composition_root.get_coordinator()

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

    async def async_press(self) -> None:
        """Press the button to apply the recommended scene."""
        coordinator = self._coordinator
        if not coordinator:
            raise HomeAssistantError("Recommendation coordinator not available")

        # Use coordinator's apply_recommendation method
        try:
            await coordinator.apply_recommendation(self.room.id)
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
