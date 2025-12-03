"""Tests for recommendation strategies."""

import pytest

from homeassistant.components.hue.recommendation.context import (
    HomeContext,
    PresenceContext,
    ScheduleContext,
    SunContext,
)
from homeassistant.components.hue.recommendation.policy.strategies.time_of_day_strategy import (
    TimeOfDayStrategy,
)
from homeassistant.components.hue.recommendation.policy.strategies.weekly_schedule_strategy import (
    WeeklyScheduleStrategy,
)
from homeassistant.components.hue.recommendation.policy.strategies.home_arrival_strategy import (
    HomeArrivalStrategy,
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

    assert result.metadata is not None
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

    assert result.metadata is not None
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

    assert result.metadata is not None
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


async def test_weekly_schedule_uses_scene_catalog(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WeeklyScheduleStrategy should use scene names from scene_catalog."""
    strategy = WeeklyScheduleStrategy()

    # Provide a controlled catalog for the "morning" period so we do not
    # depend on the actual JSON contents beyond API shape.
    def fake_get_scenes_for_schedule_period(period: str) -> list[str]:
        if period == "morning":
            return ["Blossom"]
        return []

    monkeypatch.setattr(
        "homeassistant.components.hue.recommendation.policy.strategies.weekly_schedule_strategy.get_scenes_for_schedule_period",
        fake_get_scenes_for_schedule_period,
    )

    context = HomeContext(
        schedule=ScheduleContext(
            active_period="morning",
            available_periods=["morning", "work", "evening", "night"],
            has_active_schedule=True,
        )
    )

    candidates = ["Blossom", "work_scene"]

    result = await strategy.score(context, candidates)

    # Blossom should receive the top score because it comes from the
    # catalog for the active period, even though the name is not part
    # of the generic PERIOD_KEYWORDS list.
    assert result.scene_scores["Blossom"] == 1.0
    assert result.scene_scores["work_scene"] <= 1.0


async def test_weekly_schedule_no_active_period() -> None:
    """WeeklyScheduleStrategy should return neutral scores when no period is active."""
    strategy = WeeklyScheduleStrategy()
    context = HomeContext(
        schedule=ScheduleContext(
            active_period=None,
            available_periods=[],
            has_active_schedule=False,
        )
    )
    candidates = ["scene1", "scene2"]

    result = await strategy.score(context, candidates)

    assert result.metadata is not None
    assert result.scene_scores == {"scene1": 0.5, "scene2": 0.5}
    assert result.metadata["active_period"] is None
    assert result.metadata["has_active_schedule"] is False
    assert result.metadata["available_periods"] == []


async def test_weekly_schedule_keyword_matching() -> None:
    """WeeklyScheduleStrategy should favor scenes matching active period keywords."""
    strategy = WeeklyScheduleStrategy()
    context = HomeContext(
        schedule=ScheduleContext(
            active_period="evening",
            available_periods=["evening"],
            has_active_schedule=True,
        )
    )
    candidates = ["Evening Relax", "Work Focus", "Unknown"]

    result = await strategy.score(context, candidates)

    # Exact / direct period keyword match should get the highest score
    assert result.scene_scores["Evening Relax"] == 1.0
    # Other period keyword should get a lower but non-default score
    assert result.scene_scores["Work Focus"] == 0.3
    # No keyword match should fall back to the default score
    assert result.scene_scores["Unknown"] == 0.1


async def test_home_arrival_strategy_id() -> None:
    """Test HomeArrivalStrategy has correct ID."""
    strategy = HomeArrivalStrategy()

    assert strategy.strategy_id == "home_arrival"


async def test_home_arrival_strategy_anyone_home_keywords() -> None:
    """HomeArrivalStrategy should prefer arrival-style scenes when anyone is home."""
    strategy = HomeArrivalStrategy()
    context = HomeContext(
        presence=PresenceContext(
            is_anyone_home=True,
            state="1",
        )
    )
    candidates = [
        "Welcome Home",
        "Arrival Scene",
        "Arrive Party",
        "Generic Scene",
    ]

    result = await strategy.score(context, candidates)

    assert result.metadata is not None
    assert result.scene_scores["Welcome Home"] == 1.0
    assert result.scene_scores["Arrival Scene"] == 1.0
    assert result.scene_scores["Arrive Party"] == 1.0
    # Non-keyword scenes get a lower, neutral score
    assert result.scene_scores["Generic Scene"] == 0.2
    assert result.metadata["is_anyone_home"] is True


async def test_home_arrival_strategy_anyone_home_case_insensitive() -> None:
    """HomeArrivalStrategy matching should be case insensitive."""
    strategy = HomeArrivalStrategy()
    context = HomeContext(
        presence=PresenceContext(
            is_anyone_home=True,
            state="1",
        )
    )
    candidates = ["WELCOME", "HoMe Arrival", "normal"]

    result = await strategy.score(context, candidates)

    assert result.scene_scores["WELCOME"] == 1.0
    assert result.scene_scores["HoMe Arrival"] == 1.0
    assert result.scene_scores["normal"] == 0.2


async def test_home_arrival_strategy_no_one_home_neutral() -> None:
    """HomeArrivalStrategy should be neutral when no one is home."""
    strategy = HomeArrivalStrategy()
    context = HomeContext(
        presence=PresenceContext(
            is_anyone_home=False,
            state="0",
        )
    )
    candidates = ["Welcome Home", "Generic Scene"]

    result = await strategy.score(context, candidates)

    # When no one is home, all scores are neutral (0.0) so other strategies can decide
    assert result.metadata is not None
    assert result.scene_scores["Welcome Home"] == 0.0
    assert result.scene_scores["Generic Scene"] == 0.0
    assert result.metadata["is_anyone_home"] is False
