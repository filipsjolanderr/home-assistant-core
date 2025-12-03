"""Static Hue scene catalog loaded from JSON.

This module is the single place where concrete Hue scene *names* and
categories are defined. Other parts of the recommendation engine refer
to these helpers instead of hard-coding scene names.
"""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Final


def _load_static_scene_sets() -> dict[str, list[str]]:
    """Load static Hue scene sets from bundled JSON."""
    path = Path(__file__).with_name("coordinator").joinpath("hue_scenes.json")
    with path.open(encoding="utf-8") as fh:
        raw = json.load(fh)

    sets: dict[str, list[str]] = {}
    for item in raw.get("sets", []):
        name = item.get("name")
        scenes = item.get("scenes", [])
        if not isinstance(name, str) or not isinstance(scenes, list):
            continue
        sets[name] = [str(scene) for scene in scenes]
    return sets


#: Mapping from set/category name -> list of scene names.
STATIC_SCENE_SETS: Final[Mapping[str, list[str]]] = _load_static_scene_sets()


def _flatten_sets(set_names: list[str]) -> list[str]:
    """Return all scenes contained in the given set names."""
    scenes: list[str] = []
    for set_name in set_names:
        scenes.extend(STATIC_SCENE_SETS.get(set_name, ()))
    return scenes


# High-level mappings from "semantic periods" to scene sets from the JSON.
#
# These mappings intentionally only reference *set* names. The concrete
# scene names live exclusively in `hue_scenes.json`.
SCHEDULE_PERIOD_TO_SET_NAMES: Final[Mapping[str, list[str]]] = {
    # Gentle, bright scenes that work well to start the day
    "morning": ["Sunrise", "Pure"],
    # Neutral/active scenes suited for work or general daytime
    "work": ["Refreshing", "Futuristic", "Pure"],
    # Warm, cozy or dynamic evening scenes
    "evening": [
        "Cozy",
        "Dreamy",
        "Serenity",
        "Peaceful",
        "Lush",
        "Luxurious",
    ],
    # Darker, calmer scenes appropriate late at night
    "night": ["Serenity", "Peaceful", "Cozy"],
}

TIME_OF_DAY_TO_SET_NAMES: Final[Mapping[str, list[str]]] = {
    "morning": ["Sunrise", "Pure"],
    "day": ["Refreshing", "Futuristic", "Pure"],
    "evening": [
        "Cozy",
        "Dreamy",
        "Serenity",
        "Peaceful",
        "Lush",
        "Luxurious",
    ],
    "night": ["Serenity", "Peaceful", "Cozy"],
}

# Sets that work well as "arrival" / "welcome home" scenes. These are
# deliberately chosen from existing time-of-day buckets so that concrete
# scene names continue to live only in this JSON-driven catalog.
ARRIVAL_SET_NAMES: Final[list[str]] = [
    "Refreshing",
    "Pure",
    "Luxurious",
]


def get_scenes_for_arrival() -> list[str]:
    """Return scene names that are suitable for home arrival."""
    return _flatten_sets(ARRIVAL_SET_NAMES)


def get_scenes_for_schedule_period(period: str) -> list[str]:
    """Return scene names that are suitable for a schedule *period*."""
    return _flatten_sets(list(SCHEDULE_PERIOD_TO_SET_NAMES.get(period, ())))


def get_scenes_for_time_of_day(period: str) -> list[str]:
    """Return scene names suitable for a time-of-day bucket."""
    return _flatten_sets(list(TIME_OF_DAY_TO_SET_NAMES.get(period, ())))
