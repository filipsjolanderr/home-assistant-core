"""Strategy that prefers arrival scenes when someone arrives home."""

from __future__ import annotations

from ...context import HomeContext
from .strategy import IStrategy, StrategyResult


class HomeArrivalStrategy(IStrategy):
    """Prefer arrival scenes on away->home transition."""

    @property
    def strategy_id(self) -> str:
        """Return strategy identifier."""
        return "home_arrival"

    async def score(
        self, context: HomeContext, candidates: list[str]
    ) -> StrategyResult:
        """Score candidates based on arrival transition.

        Detect an arrival when previous presence reported no one home and the
        current presence reports at least one entity in state 'home'.
        """
        prev = context.metadata.get("previous_presence", {})
        prev_any_home = prev.get("is_anyone_home", False)
        curr_any_home = context.presence.is_anyone_home

        scene_scores: dict[str, float] = {}

        # If transition away->home, prefer scenes that look like 'arrival' or 'welcome'
        if not prev_any_home and curr_any_home:
            # TODO: Look up the relevant scene names from Hue
            preferred_keywords = ["arrival", "welcome", "home", "arrive"]
            for scene_id in candidates:
                lowered = scene_id.lower()
                score = 0.0
                for kw in preferred_keywords:
                    if kw in lowered:
                        score = 1.0
                        break
                if score == 0.0:
                    score = 0.2
                scene_scores[scene_id] = score
        else:
            # Neutral scoring so other strategies decide
            for scene_id in candidates:
                scene_scores[scene_id] = 0.0

        return StrategyResult(
            scene_scores=scene_scores,
            metadata={"prev_any_home": prev_any_home, "curr_any_home": curr_any_home},
        )
