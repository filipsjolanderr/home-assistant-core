"""Tests for static Hue scene catalog."""

from __future__ import annotations

from homeassistant.components.hue.recommendation.scene_catalog import (
    STATIC_SCENE_SETS,
    get_scenes_for_schedule_period,
    get_scenes_for_time_of_day,
)


async def test_static_scene_sets_loaded_from_json() -> None:
    """Scene catalog exposes sets and scenes from JSON."""
    # Basic sanity: at least one known set and scene is present.
    assert "Defaults" in STATIC_SCENE_SETS
    assert "Relax" in STATIC_SCENE_SETS["Defaults"]


async def test_get_scenes_for_schedule_period_uses_sets() -> None:
    """Schedule period helper flattens configured sets."""
    morning_scenes = get_scenes_for_schedule_period("morning")

    # Morning period should include all scenes from the Sunrise and Pure sets.
    expected = list(
        STATIC_SCENE_SETS.get("Sunrise", [])
    ) + list(STATIC_SCENE_SETS.get("Pure", []))

    for scene in expected:
        assert scene in morning_scenes


async def test_get_scenes_for_time_of_day_uses_sets() -> None:
    """Time-of-day helper flattens configured sets."""
    day_scenes = get_scenes_for_time_of_day("day")

    expected = list(
        STATIC_SCENE_SETS.get("Refreshing", [])
    ) + list(STATIC_SCENE_SETS.get("Futuristic", [])) + list(
        STATIC_SCENE_SETS.get("Pure", [])
    )

    for scene in expected:
        assert scene in day_scenes
