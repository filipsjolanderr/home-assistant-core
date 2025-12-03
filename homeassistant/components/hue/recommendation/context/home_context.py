"""Home context data structure for recommendation engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LightingContext:
    """Lighting-related context."""

    available_scenes: list[str] = field(default_factory=list)
    """List of available scene IDs for the room."""


@dataclass
class Constraints:
    """Constraints that affect scene selection."""

    do_not_disturb: bool = False
    """Whether do-not-disturb mode is active."""
    sleep_mode: bool = False
    """Whether sleep mode is active."""
    occupancy_detected: bool = True
    """Whether occupancy is detected in the room."""


@dataclass
class SunContext:
    """Sun position and time context."""

    elevation: float = 0.0
    """Solar elevation angle in degrees."""
    azimuth: float = 0.0
    """Solar azimuth angle in degrees."""
    state: str = "below_horizon"
    """Sun state: 'above_horizon' or 'below_horizon'."""


@dataclass
class PresenceContext:
    """Presence and occupancy context."""

    is_anyone_home: bool = False
    """True if at least one is in the home zone."""
    state: str = "0"
    """Presence state: 0 if no one detected in zone.home, else > 0"""


@dataclass
class HomeContext:
    """Complete home context for recommendation decisions."""

    lighting: LightingContext = field(default_factory=LightingContext)
    """Lighting context."""
    sun: SunContext = field(default_factory=SunContext)
    """Sun context."""
    constraints: Constraints = field(default_factory=Constraints)
    """Constraints affecting scene selection."""
    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata from providers."""
    presence: PresenceContext = field(default_factory=PresenceContext)
    """Presence context."""
