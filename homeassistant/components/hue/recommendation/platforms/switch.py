"""Support for Hue recommendation switch entity."""

from __future__ import annotations

from typing import Any

from aiohue.v2.controllers.events import EventType
from aiohue.v2.controllers.groups import Room, Zone
from aiohue.v2.models.resource import ResourceTypes

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from ...bridge import HueBridge, HueConfigEntry
from ...const import DOMAIN
from ...v2.entity import HueBaseEntity
from ..coordinator import RecommendationCoordinator

CONF_RECOMMENDATION_AUTO_APPLY = "recommendation_auto_apply"
CONF_RECOMMENDATION_AUTO_APPLY_GLOBAL = "recommendation_auto_apply_global"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: HueConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Hue recommendation switch entities."""
    bridge = config_entry.runtime_data

    if bridge.api_version == 1:
        return

    @callback
    def async_add_switch(event_type: EventType, resource: Room | Zone) -> None:
        """Add switch entity for Hue room or zone."""
        if resource.type in (
            ResourceTypes.ROOM,
            ResourceTypes.ZONE,
            ResourceTypes.BRIDGE_HOME,
        ):
            async_add_entities([HueRecommendationSwitchEntity(bridge, resource)])

    # Add switches for all groups (rooms, zones, and bridge home)
    # Check all groups to ensure bridge home is included
    for group in bridge.api.groups:
        if isinstance(group, (Room, Zone)):
            async_add_switch(EventType.RESOURCE_ADDED, group)

    # Register listener for all groups (rooms, zones, and bridge home)
    @callback
    def async_add_group(event_type: EventType, resource) -> None:
        """Add switch for any Room or Zone (including bridge home)."""
        if isinstance(resource, (Room, Zone)):
            async_add_switch(event_type, resource)

    config_entry.async_on_unload(
        bridge.api.groups.subscribe(
            async_add_group,
            event_filter=EventType.RESOURCE_ADDED,
        )
    )


class HueRecommendationSwitchEntity(HueBaseEntity, SwitchEntity):
    """Representation of a Hue recommendation auto-apply switch."""

    _attr_has_entity_name = True

    entity_description = SwitchEntityDescription(
        key="auto_apply_recommendation",
        translation_key="auto_apply_recommendation",
        name=None,
        has_entity_name=True,
    )

    def __init__(self, bridge: HueBridge, room: Room | Zone) -> None:
        """Initialize the recommendation switch."""
        super().__init__(bridge, bridge.api.groups, room)
        self.room = room  # Can be Room or Zone
        self._attr_unique_id = f"{room.id}_auto_apply_recommendation"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, room.id)},
        )
        self._is_home_room = room.type == ResourceTypes.BRIDGE_HOME
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

    @property
    def _coordinator(self) -> RecommendationCoordinator | None:
        """Get the shared recommendation coordinator from bridge."""
        return self.bridge.recommendation_coordinator

    async def async_added_to_hass(self) -> None:
        """Call when entity is added."""
        await super().async_added_to_hass()

        # Sync coordinator state with config entry options
        coordinator = self._coordinator
        if coordinator:
            enabled = self.is_on
            coordinator.set_auto_apply_enabled(self.room.id, enabled)

        # Subscribe to room updates
        self.async_on_remove(
            self.bridge.api.groups.subscribe(
                self._handle_event,
                self.room.id,
                EventType.RESOURCE_UPDATED,
            )
        )

    @property
    def is_on(self) -> bool:
        """Return true if auto-apply is enabled."""
        options = self.bridge.config_entry.options
        auto_apply = options.get(CONF_RECOMMENDATION_AUTO_APPLY, {})

        if self._is_home_room:
            # Check global setting first, then per-room
            if CONF_RECOMMENDATION_AUTO_APPLY_GLOBAL in options:
                return options[CONF_RECOMMENDATION_AUTO_APPLY_GLOBAL]

        return auto_apply.get(self.room.id, False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on auto-apply."""
        await self._update_auto_apply(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off auto-apply."""
        await self._update_auto_apply(False)

    async def _update_auto_apply(self, enabled: bool) -> None:
        """Update auto-apply setting in config entry options and coordinator."""
        options = dict(self.bridge.config_entry.options or {})
        auto_apply = dict(options.get(CONF_RECOMMENDATION_AUTO_APPLY, {}))

        if self._is_home_room:
            # For home room, update global setting
            options[CONF_RECOMMENDATION_AUTO_APPLY_GLOBAL] = enabled
        else:
            # For regular rooms, update per-room setting
            auto_apply[self.room.id] = enabled
            options[CONF_RECOMMENDATION_AUTO_APPLY] = auto_apply

        # Update config entry
        self.hass.config_entries.async_update_entry(
            self.bridge.config_entry, options=options
        )

        # Update coordinator state
        coordinator = self._coordinator
        if coordinator:
            coordinator.set_auto_apply_enabled(self.room.id, enabled)
