"""Time of day strategy based on sun position."""

from __future__ import annotations

from ...context import HomeContext
from .strategy import IStrategy, StrategyResult


class TimeOfDayStrategy(IStrategy):
    """MVP strategy: recommends 3 scenes based on sun position.

    - Morning scene: sun elevation < 10 degrees (dawn/morning)
    - Day scene: sun elevation >= 10 degrees (daytime)
    - Evening scene: sun elevation < 0 degrees (dusk/night)
    """

    @property
    def strategy_id(self) -> str:
        """Return strategy identifier."""
        return "time_of_day"

    async def score(
        self, context: HomeContext, candidates: list[str]
    ) -> StrategyResult:
        """Score candidates based on sun elevation."""
        elevation = context.sun.elevation
        scene_scores: dict[str, float] = {}

        # Determine which scene type to prefer based on sun elevation
        if elevation < 0:
            # Night/evening - prefer evening scenes
            preferred_prefixes = ["evening", "night", "dusk"]
            fallback_prefixes = ["day", "morning"]
        elif elevation < 10:
            # Morning/dawn - prefer morning scenes
            preferred_prefixes = ["morning", "dawn", "wake"]
            fallback_prefixes = ["day", "evening"]
        else:
            # Daytime - prefer day scenes
            preferred_prefixes = ["day", "bright", "work"]
            fallback_prefixes = ["morning", "evening"]

        # Score candidates based on name matching
        for scene_id in candidates:
            score = 0.0
            scene_name_lower = scene_id.lower()

            # Check preferred prefixes (higher score)
            for prefix in preferred_prefixes:
                if prefix in scene_name_lower:
                    score = 1.0
                    break

            # Check fallback prefixes (lower score)
            if score == 0.0:
                for prefix in fallback_prefixes:
                    if prefix in scene_name_lower:
                        score = 0.5
                        break

            # Default score if no match
            if score == 0.0:
                score = 0.1

            scene_scores[scene_id] = score

        return StrategyResult(
            scene_scores=scene_scores,
            metadata={
                "elevation": elevation,
                "preferred_type": preferred_prefixes[0]
                if preferred_prefixes
                else "unknown",
            },
        )
