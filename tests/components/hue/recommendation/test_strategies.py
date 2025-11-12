"""Tests for recommendation strategies."""

import pytest

from homeassistant.components.hue.recommendation.context import HomeContext, SunContext
from homeassistant.components.hue.recommendation.policy.strategies.time_of_day_strategy import (
    TimeOfDayStrategy,
)


async def test_time_of_day_strategy_id() -> None:
    """Test TimeOfDayStrategy has correct ID."""
    strategy = TimeOfDayStrategy()
    assert strategy.strategy_id == "time_of_day"


async def test_time_of_day_strategy_daytime() -> None:
    """Test TimeOfDayStrategy prefers day scenes during daytime."""
    strategy = TimeOfDayStrategy()
    context = HomeContext(sun=SunContext(elevation=45.0))
    candidates = ["morning_scene", "day_scene", "evening_scene"]

    result = await strategy.score(context, candidates)

    assert result.scene_scores["day_scene"] == 1.0
    assert result.scene_scores["morning_scene"] == 0.5
    assert result.scene_scores["evening_scene"] == 0.5
    assert result.metadata["elevation"] == 45.0
    assert result.metadata["preferred_type"] == "day"


async def test_time_of_day_strategy_morning() -> None:
    """Test TimeOfDayStrategy prefers morning scenes at dawn."""
    strategy = TimeOfDayStrategy()
    context = HomeContext(sun=SunContext(elevation=5.0))
    candidates = ["morning_scene", "day_scene", "evening_scene"]

    result = await strategy.score(context, candidates)

    assert result.scene_scores["morning_scene"] == 1.0
    assert result.scene_scores["day_scene"] == 0.5
    assert result.scene_scores["evening_scene"] == 0.5
    assert result.metadata["preferred_type"] == "morning"


async def test_time_of_day_strategy_evening() -> None:
    """Test TimeOfDayStrategy prefers evening scenes at night."""
    strategy = TimeOfDayStrategy()
    context = HomeContext(sun=SunContext(elevation=-10.0))
    candidates = ["morning_scene", "day_scene", "evening_scene"]

    result = await strategy.score(context, candidates)

    assert result.scene_scores["evening_scene"] == 1.0
    assert result.scene_scores["day_scene"] == 0.5
    assert result.scene_scores["morning_scene"] == 0.5
    assert result.metadata["preferred_type"] == "evening"


async def test_time_of_day_strategy_unknown_scenes() -> None:
    """Test TimeOfDayStrategy handles unknown scene names."""
    strategy = TimeOfDayStrategy()
    context = HomeContext(sun=SunContext(elevation=45.0))
    candidates = ["unknown_scene_1", "unknown_scene_2"]

    result = await strategy.score(context, candidates)

    # Unknown scenes get default score
    assert result.scene_scores["unknown_scene_1"] == 0.1
    assert result.scene_scores["unknown_scene_2"] == 0.1


async def test_time_of_day_strategy_case_insensitive() -> None:
    """Test TimeOfDayStrategy is case insensitive."""
    strategy = TimeOfDayStrategy()
    context = HomeContext(sun=SunContext(elevation=45.0))
    candidates = ["DAY_SCENE", "Morning_Scene", "EvEnInG_ScEnE"]

    result = await strategy.score(context, candidates)

    assert result.scene_scores["DAY_SCENE"] == 1.0
    assert result.scene_scores["Morning_Scene"] == 0.5
    assert result.scene_scores["EvEnInG_ScEnE"] == 0.5
