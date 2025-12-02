"""Presence provider for detecting users home/away state."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from homeassistant.core import HomeAssistant

from ..home_context import HomeContext, PresenceContext
from .provider import IContextProvider

DEFAULT_RECENT_SECONDS = 300


class PresenceProvider(IContextProvider):
    """Provider that summarizes presence for configured or discovered persons.

    Behavior:
    - Treat only explicit state == 'home' as present. Any other state is away.
    - If `tracked_entities` is None, auto-discover `person.` entities.
    """

    def __init__(
        self, hass: HomeAssistant, tracked_entities: list[str] | None = None
    ) -> None:
        """Initialize presence provider."""
        self.hass = hass
        self._tracked = tracked_entities

    @property
    def provider_id(self) -> str:
        """Return provider identifier."""
        return "presence"

    async def fetch(self, context: HomeContext) -> HomeContext:
        """Fetch presence summary and update the HomeContext.

        This provider treats only state == 'home' as present. All other states
        (including zone names other than 'home' and 'not_home') are considered away.
        """

        # Discover tracked entities if none configured
        if self._tracked:
            tracked = list(self._tracked)
        else:
            tracked = [
                s.entity_id
                for s in self.hass.states.async_all()
                if s.entity_id.startswith("person.")
            ]

        present: list[str] = []
        absent: list[str] = []
        last_changed_map: dict[str, str] = {}

        now = datetime.now(UTC)
        recent_threshold = timedelta(seconds=DEFAULT_RECENT_SECONDS)

        for ent_id in tracked:
            state = self.hass.states.get(ent_id)
            if not state:
                absent.append(ent_id)
                continue

            # Only consider explicit 'home' as present, and only if the last_changed
            # timestamp is recent enough to avoid reacting to stale states.
            last_changed = getattr(state, "last_changed", None)
            is_recent = True
            if last_changed is None:
                is_recent = False
            else:
                is_recent = (now - last_changed) <= recent_threshold

            if state.state == "home" and is_recent:
                present.append(ent_id)
            else:
                absent.append(ent_id)

            if last_changed is not None:
                last_changed_map[ent_id] = last_changed.isoformat()

        is_anyone_home = len(present) > 0

        context.presence = PresenceContext(
            is_anyone_home=is_anyone_home,
            present_entities=present,
            absent_entities=absent,
            last_changed=last_changed_map,
        )

        # Update occupancy constraint for strategies/policy
        context.constraints.occupancy_detected = is_anyone_home

        # Add metadata for diagnostics
        context.metadata.setdefault("presence", {})
        context.metadata["presence"].update(
            {
                "is_anyone_home": is_anyone_home,
                "present_entities": present,
                "absent_entities": absent,
            }
        )

        return context
