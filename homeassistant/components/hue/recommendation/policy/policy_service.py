"""Policy service for making recommendation decisions."""

from __future__ import annotations

import logging

from ..context import Constraints, HomeContext
from .candidate_scenes import CandidateScenes
from .decision import Decision
from .last_decision import LastDecisionStore
from .strategies import IStrategy
from .weights import WeightsAndParams

_LOGGER = logging.getLogger(__name__)


class PolicyService:
    """Service that makes recommendation decisions using strategies."""

    def __init__(
        self,
        strategies: list[IStrategy],
        weights: WeightsAndParams,
        last_decision: LastDecisionStore,
    ) -> None:
        """Initialize policy service."""
        self.strategies = strategies
        self.weights = weights
        self.last_decision = last_decision

    async def decide(
        self, context: HomeContext, candidates: list[str] | None = None
    ) -> Decision | None:
        """
        Make a recommendation decision.

        Args:
            context: Current home context
            candidates: Optional list of candidate scene IDs.
                       If None, will enumerate from context.

        Returns:
            Decision object, or None if no valid candidates
        """
        # Enumerate candidates if not provided
        if candidates is None:
            candidates = CandidateScenes.enumerate(context)

        if not candidates:
            _LOGGER.debug("No candidate scenes available")
            return None

        _LOGGER.debug("Candidate scenes: %s", candidates)

        # Apply constraints to filter candidates
        filtered_candidates = self._apply_constraints(context.constraints, candidates)

        if not filtered_candidates:
            _LOGGER.debug("All candidates filtered out by constraints")
            return None

        _LOGGER.debug("Filtered candidates: %s", filtered_candidates)

        # Get scores from all strategies
        strategy_results = {}
        for strategy in self.strategies:
            result = await strategy.score(context, filtered_candidates)
            strategy_results[strategy.strategy_id] = result

        # Calculate weighted scores
        weighted_scores: dict[str, float] = {}
        contributions: dict[str, float] = {}

        for scene_id in filtered_candidates:
            total_score = 0.0
            for strategy_id, result in strategy_results.items():
                strategy_score = result.scene_scores.get(scene_id, 0.0)
                weight = self.weights.get_strategy_weight(strategy_id)
                contribution = strategy_score * weight
                total_score += contribution
                contributions[f"{strategy_id}:{scene_id}"] = contribution

            # Apply hysteresis (inertia boost for previous scene)
            if (
                self.last_decision.scene_id == scene_id
                and self.last_decision.get_age_seconds()
                < self.weights.min_dwell_seconds
            ):
                total_score += self.weights.inertia_boost

            weighted_scores[scene_id] = total_score

        # Select best scene
        if not weighted_scores:
            return None

        # Sort by score (descending)
        sorted_scenes = sorted(
            weighted_scores.items(), key=lambda x: x[1], reverse=True
        )
        best_scene_id, best_score = sorted_scenes[0]

        # Check if we should switch (hysteresis check)
        if self.last_decision.scene_id:
            current_score = weighted_scores.get(self.last_decision.scene_id, 0.0)
            score_delta = best_score - current_score

            if (
                score_delta < self.weights.switch_delta_min
                and self.last_decision.get_age_seconds()
                < self.weights.min_dwell_seconds
            ):
                # Keep previous decision due to hysteresis
                _LOGGER.debug(
                    "Hysteresis applied: keeping previous scene %s (delta=%.3f < %.3f, age=%.1fs < %.1fs)",
                    self.last_decision.scene_id,
                    score_delta,
                    self.weights.switch_delta_min,
                    self.last_decision.get_age_seconds(),
                    self.weights.min_dwell_seconds,
                )
                best_scene_id = self.last_decision.scene_id
                best_score = current_score
            else:
                _LOGGER.debug(
                    "Scene switch allowed: delta=%.3f >= %.3f or age=%.1fs >= %.1fs",
                    score_delta,
                    self.weights.switch_delta_min,
                    self.last_decision.get_age_seconds(),
                    self.weights.min_dwell_seconds,
                )

        # Calculate confidence (normalized score)
        max_possible_score = (
            sum(
                self.weights.get_strategy_weight(s.strategy_id) for s in self.strategies
            )
            + self.weights.inertia_boost
        )
        confidence = min(
            best_score / max_possible_score if max_possible_score > 0 else 0.0, 1.0
        )

        # Build strategy scores dict
        strategy_scores = {
            strategy_id: result.scene_scores
            for strategy_id, result in strategy_results.items()
        }

        decision = Decision(
            scene_id=best_scene_id,
            score=best_score,
            confidence=confidence,
            contributions=contributions,
            strategy_scores=strategy_scores,
        )

        # Log decision details
        _LOGGER.info(
            "Decision made: scene_id=%s, score=%.3f, confidence=%.3f",
            best_scene_id,
            best_score,
            confidence,
        )
        _LOGGER.debug(
            "Decision details: scene_id=%s, score=%.3f, confidence=%.3f, "
            "strategy_scores=%s, contributions=%s",
            best_scene_id,
            best_score,
            confidence,
            strategy_scores,
            contributions,
        )

        # Update last decision store
        self.last_decision.update(best_scene_id, best_score)

        return decision

    def _apply_constraints(
        self, constraints: Constraints, candidates: list[str]
    ) -> list[str]:
        """Apply constraints to filter candidates."""
        # For MVP, we just check occupancy
        # In the future, we could filter based on do_not_disturb, sleep_mode, etc.
        if not constraints.occupancy_detected:
            # If no occupancy, we might want to return empty list or a specific "away" scene
            # For MVP, just return all candidates
            pass

        return candidates
