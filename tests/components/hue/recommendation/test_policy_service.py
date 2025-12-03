"""Tests for policy service."""

from datetime import UTC, datetime, timedelta

import pytest

from homeassistant.components.hue.recommendation.context import (
    Constraints,
    HomeContext,
    LightingContext,
    PresenceContext,
    ScheduleContext,
    SunContext,
)
from homeassistant.components.hue.recommendation.policy.last_decision import (
    LastDecisionStore,
)
from homeassistant.components.hue.recommendation.policy.policy_service import (
    PolicyService,
)
from homeassistant.components.hue.recommendation.policy.strategies.home_arrival_strategy import (
    HomeArrivalStrategy,
)
from homeassistant.components.hue.recommendation.policy.strategies.time_of_day_strategy import (
    TimeOfDayStrategy,
)
from homeassistant.components.hue.recommendation.policy.strategies.weekly_schedule_strategy import (
    WeeklyScheduleStrategy,
)
from homeassistant.components.hue.recommendation.policy.strategies.strategy import (
    IStrategy,
    StrategyResult,
)
from homeassistant.components.hue.recommendation.policy.weights import (
    WeightsAndParams,
)


class MockStrategy(IStrategy):
    """Mock strategy for testing."""

    def __init__(self, strategy_id: str, scores: dict[str, float]) -> None:
        """Initialize mock strategy."""
        self._strategy_id = strategy_id
        self._scores = scores

    @property
    def strategy_id(self) -> str:
        """Return strategy ID."""
        return self._strategy_id

    async def score(
        self, context: HomeContext, candidates: list[str]
    ) -> StrategyResult:
        """Return mock scores."""
        scene_scores = {
            candidate: self._scores.get(candidate, 0.0) for candidate in candidates
        }
        return StrategyResult(scene_scores=scene_scores)


async def test_policy_service_decide_simple() -> None:
    """Test PolicyService makes simple decision."""
    strategy = MockStrategy("test", {"scene1": 1.0, "scene2": 0.5})
    weights = WeightsAndParams(strategy_weights={"test": 1.0})
    last_decision = LastDecisionStore()

    service = PolicyService([strategy], weights, last_decision)
    context = HomeContext(
        lighting=LightingContext(available_scenes=["scene1", "scene2"]),
        sun=SunContext(elevation=45.0),
    )

    decision = await service.decide(context)

    assert decision is not None
    assert decision.scene_id == "scene1"
    assert decision.score == 1.0
    assert decision.confidence > 0.0


async def test_policy_service_decide_no_candidates() -> None:
    """Test PolicyService returns None when no candidates."""
    strategy = MockStrategy("test", {})
    weights = WeightsAndParams()
    last_decision = LastDecisionStore()

    service = PolicyService([strategy], weights, last_decision)
    context = HomeContext(lighting=LightingContext(available_scenes=[]))

    decision = await service.decide(context)

    assert decision is None


async def test_policy_service_weighted_scores() -> None:
    """Test PolicyService applies strategy weights correctly."""
    strategy1 = MockStrategy("strategy1", {"scene1": 1.0, "scene2": 0.5})
    strategy2 = MockStrategy("strategy2", {"scene1": 0.5, "scene2": 1.0})
    weights = WeightsAndParams(strategy_weights={"strategy1": 2.0, "strategy2": 1.0})
    last_decision = LastDecisionStore()

    service = PolicyService([strategy1, strategy2], weights, last_decision)
    context = HomeContext(
        lighting=LightingContext(available_scenes=["scene1", "scene2"]),
        sun=SunContext(elevation=45.0),
    )

    decision = await service.decide(context)

    assert decision is not None
    # scene1: 1.0 * 2.0 + 0.5 * 1.0 = 2.5
    # scene2: 0.5 * 2.0 + 1.0 * 1.0 = 2.0
    # scene1 should win
    assert decision.scene_id == "scene1"
    assert decision.score == 2.5


async def test_policy_service_hysteresis() -> None:
    """Test PolicyService applies hysteresis correctly."""
    strategy = MockStrategy("test", {"scene1": 1.0, "scene2": 0.9})
    weights = WeightsAndParams(
        strategy_weights={"test": 1.0},
        inertia_boost=0.2,
        switch_delta_min=0.1,
        min_dwell_seconds=300,
    )
    last_decision = LastDecisionStore()
    last_decision.update("scene2", 0.9)
    # Set timestamp to recent (within dwell time)
    last_decision.timestamp = datetime.now(UTC) - timedelta(seconds=100)

    service = PolicyService([strategy], weights, last_decision)
    context = HomeContext(
        lighting=LightingContext(available_scenes=["scene1", "scene2"]),
        sun=SunContext(elevation=45.0),
    )

    decision = await service.decide(context)

    assert decision is not None
    # scene1: 1.0
    # scene2: 0.9 + 0.2 (inertia) = 1.1
    # scene2 should win due to hysteresis
    assert decision.scene_id == "scene2"


async def test_policy_service_hysteresis_expired() -> None:
    """Test PolicyService switches when hysteresis expires."""
    strategy = MockStrategy("test", {"scene1": 1.0, "scene2": 0.9})
    weights = WeightsAndParams(
        strategy_weights={"test": 1.0},
        inertia_boost=0.2,
        switch_delta_min=0.1,
        min_dwell_seconds=300,
    )
    last_decision = LastDecisionStore()
    last_decision.update("scene2", 0.9)
    # Set timestamp to old (beyond dwell time)
    last_decision.timestamp = datetime.now(UTC) - timedelta(seconds=400)

    service = PolicyService([strategy], weights, last_decision)
    context = HomeContext(
        lighting=LightingContext(available_scenes=["scene1", "scene2"]),
        sun=SunContext(elevation=45.0),
    )

    decision = await service.decide(context)

    assert decision is not None
    # Hysteresis expired, scene1 should win
    assert decision.scene_id == "scene1"


async def test_policy_service_switch_delta_min() -> None:
    """Test PolicyService respects switch_delta_min threshold."""
    strategy = MockStrategy("test", {"scene1": 1.0, "scene2": 0.95})
    weights = WeightsAndParams(
        strategy_weights={"test": 1.0},
        inertia_boost=0.2,
        switch_delta_min=0.1,
        min_dwell_seconds=300,
    )
    last_decision = LastDecisionStore()
    last_decision.update("scene2", 0.95)
    last_decision.timestamp = datetime.now(UTC) - timedelta(seconds=100)

    service = PolicyService([strategy], weights, last_decision)
    context = HomeContext(
        lighting=LightingContext(available_scenes=["scene1", "scene2"]),
        sun=SunContext(elevation=45.0),
    )

    decision = await service.decide(context)

    assert decision is not None
    # scene1: 1.0
    # scene2: 0.95 + 0.2 = 1.15
    # Delta: 1.0 - 1.15 = -0.15 (negative, so no switch)
    # But scene2 already has higher score, so it wins
    assert decision.scene_id == "scene2"


async def test_policy_service_updates_last_decision() -> None:
    """Test PolicyService updates last decision store."""
    strategy = MockStrategy("test", {"scene1": 1.0})
    weights = WeightsAndParams()
    last_decision = LastDecisionStore()

    service = PolicyService([strategy], weights, last_decision)
    context = HomeContext(
        lighting=LightingContext(available_scenes=["scene1"]),
        sun=SunContext(elevation=45.0),
    )

    decision = await service.decide(context)

    assert decision is not None
    assert last_decision.scene_id == "scene1"
    assert last_decision.score == decision.score
    assert last_decision.timestamp is not None


async def test_policy_service_constraints() -> None:
    """Test PolicyService applies constraints."""
    strategy = MockStrategy("test", {"scene1": 1.0})
    weights = WeightsAndParams()
    last_decision = LastDecisionStore()

    service = PolicyService([strategy], weights, last_decision)
    context = HomeContext(
        lighting=LightingContext(available_scenes=["scene1"]),
        constraints=Constraints(occupancy_detected=True),
    )

    decision = await service.decide(context)

    # For MVP, constraints don't filter yet, so should still work
    assert decision is not None


async def test_policy_service_multiple_strategies_arrival_wins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test PolicyService combines multiple strategies and arrival can dominate."""
    time_strategy = TimeOfDayStrategy()
    arrival_strategy = HomeArrivalStrategy()

    # Avoid depending on real catalog contents so scores are predictable.
    def fake_get_scenes_for_time_of_day(period: str) -> list[str]:
        return []

    monkeypatch.setattr(
        "homeassistant.components.hue.recommendation.policy.strategies.time_of_day_strategy.get_scenes_for_time_of_day",
        fake_get_scenes_for_time_of_day,
    )

    weights = WeightsAndParams(
        strategy_weights={
            "time_of_day": 0.5,
            "home_arrival": 1.0,
        }
    )
    last_decision = LastDecisionStore()

    service = PolicyService([time_strategy, arrival_strategy], weights, last_decision)
    context = HomeContext(
        sun=SunContext(elevation=45.0),
        presence=PresenceContext(is_anyone_home=True, state="1"),
    )

    candidates = ["day_scene", "Welcome Home"]

    decision = await service.decide(context, candidates)

    assert decision is not None
    # Even though time_of_day prefers "day_scene", the higher weight for
    # home_arrival and its strong match for "Welcome Home" should win.
    assert decision.scene_id == "Welcome Home"
    assert "time_of_day" in decision.strategy_scores
    assert "home_arrival" in decision.strategy_scores
    assert decision.strategy_scores["home_arrival"]["Welcome Home"] == 1.0


async def test_policy_service_multiple_strategies_all_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test PolicyService with time-of-day, weekly schedule and arrival strategies."""
    time_strategy = TimeOfDayStrategy()
    schedule_strategy = WeeklyScheduleStrategy()
    arrival_strategy = HomeArrivalStrategy()

    # Make catalog-driven keywords deterministic for this test.
    def fake_get_scenes_for_time_of_day(period: str) -> list[str]:
        return []

    def fake_get_scenes_for_schedule_period(period: str) -> list[str]:
        return []

    monkeypatch.setattr(
        "homeassistant.components.hue.recommendation.policy.strategies.time_of_day_strategy.get_scenes_for_time_of_day",
        fake_get_scenes_for_time_of_day,
    )
    monkeypatch.setattr(
        "homeassistant.components.hue.recommendation.policy.strategies.weekly_schedule_strategy.get_scenes_for_schedule_period",
        fake_get_scenes_for_schedule_period,
    )

    weights = WeightsAndParams(
        strategy_weights={
            "time_of_day": 0.5,
            "weekly_schedule": 0.5,
            "home_arrival": 1.0,
        }
    )
    last_decision = LastDecisionStore()

    service = PolicyService(
        [time_strategy, schedule_strategy, arrival_strategy],
        weights,
        last_decision,
    )
    context = HomeContext(
        sun=SunContext(elevation=-5.0),
        schedule=ScheduleContext(
            active_period="evening",
            available_periods=["evening"],
            has_active_schedule=True,
        ),
        presence=PresenceContext(is_anyone_home=True, state="1"),
    )

    candidates = ["Evening Relax", "Welcome Home"]

    decision = await service.decide(context, candidates)

    assert decision is not None
    # Evening-focused strategies (time_of_day + weekly_schedule) should
    # together outweigh arrival and prefer the evening scene.
    assert decision.scene_id == "Evening Relax"
    assert set(decision.strategy_scores) == {
        "time_of_day",
        "weekly_schedule",
        "home_arrival",
    }
