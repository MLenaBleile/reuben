"""Corpus and session metrics computation.

Reference: SPEC.md Section 10.4; PROMPTS.md Prompt 12
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SessionMetrics:
    """Metrics for a single session."""

    session_id: Optional[str] = None
    sandwiches_made: int = 0
    foraging_attempts: int = 0
    sandwich_rate: float = 0.0
    mean_validity: float = 0.0
    total_cost: float = 0.0
    cost_per_sandwich: float = 0.0


@dataclass
class CorpusMetrics:
    """Metrics for the entire sandwich corpus."""

    total_sandwiches: int = 0
    unique_ingredients: int = 0
    ingredient_diversity: float = 0.0  # unique_ingredients / total_sandwiches
    structural_coverage: float = 0.0  # types_used / total_types
    mean_validity: float = 0.0
    mean_novelty: float = 0.0
    types_used: int = 0
    total_types: int = 10  # From the taxonomy


def compute_session_metrics(
    sandwiches: list[dict],
    foraging_attempts: int,
    llm_costs: float = 0.0,
) -> SessionMetrics:
    """Compute metrics for a session.

    Args:
        sandwiches: List of sandwich dicts with validity_score.
        foraging_attempts: Total foraging attempts in the session.
        llm_costs: Total LLM costs.

    Returns:
        Computed SessionMetrics.
    """
    metrics = SessionMetrics()
    metrics.sandwiches_made = len(sandwiches)
    metrics.foraging_attempts = foraging_attempts
    metrics.total_cost = llm_costs

    if foraging_attempts > 0:
        metrics.sandwich_rate = len(sandwiches) / foraging_attempts

    if sandwiches:
        scores = [s.get("validity_score", 0.0) for s in sandwiches]
        metrics.mean_validity = sum(scores) / len(scores)
        metrics.cost_per_sandwich = llm_costs / len(sandwiches) if llm_costs else 0.0

    return metrics


def compute_corpus_metrics(
    sandwiches: list[dict],
    unique_ingredient_count: int,
    types_used: set[str],
    total_types: int = 10,
) -> CorpusMetrics:
    """Compute metrics for the entire corpus.

    Args:
        sandwiches: List of sandwich dicts.
        unique_ingredient_count: Number of unique ingredients.
        types_used: Set of structural type names used.
        total_types: Total number of structural types in taxonomy.

    Returns:
        Computed CorpusMetrics.
    """
    metrics = CorpusMetrics()
    metrics.total_sandwiches = len(sandwiches)
    metrics.unique_ingredients = unique_ingredient_count
    metrics.types_used = len(types_used)
    metrics.total_types = total_types

    if sandwiches:
        metrics.ingredient_diversity = unique_ingredient_count / len(sandwiches)

        validity_scores = [s.get("validity_score", 0.0) for s in sandwiches]
        metrics.mean_validity = sum(validity_scores) / len(validity_scores)

        novelty_scores = [s.get("novelty_score", 0.0) for s in sandwiches if "novelty_score" in s]
        if novelty_scores:
            metrics.mean_novelty = sum(novelty_scores) / len(novelty_scores)

    if total_types > 0:
        metrics.structural_coverage = len(types_used) / total_types

    return metrics
