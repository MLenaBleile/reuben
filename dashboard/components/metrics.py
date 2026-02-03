"""Metric computation functions for the SANDWICH dashboard.

Queries the database or computes metrics from in-memory data structures
for display in the Streamlit dashboard.

Reference: PROMPTS.md Prompt 11
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SessionMetrics:
    """Metrics for the current or latest session."""

    session_id: Optional[str] = None
    status: str = "unknown"
    started_at: Optional[datetime] = None
    uptime_seconds: float = 0.0
    current_state: str = "idle"
    current_tier: int = 1
    patience_remaining: int = 5
    sandwiches_today: int = 0
    sandwich_rate: float = 0.0  # sandwiches per attempt
    mean_validity: float = 0.0
    cost_per_sandwich: float = 0.0
    total_cost: float = 0.0


@dataclass
class ErrorCounts:
    """Error counts by type."""

    content_errors: int = 0
    parse_errors: int = 0
    retryable_errors: int = 0
    fatal_errors: int = 0


@dataclass
class SandwichRow:
    """Summary row for the latest sandwiches table."""

    name: str
    structure_type: str
    validity_score: float
    recommendation: str
    created_at: Optional[datetime] = None


@dataclass
class CostBreakdown:
    """Cost breakdown by pipeline component."""

    forager: float = 0.0
    identifier: float = 0.0
    assembler: float = 0.0
    validator: float = 0.0


@dataclass
class ForagingStats:
    """Foraging statistics by tier and source."""

    tier_success_rates: dict[int, float] = field(default_factory=dict)
    source_counts: dict[str, int] = field(default_factory=dict)


def compute_session_metrics(
    session_data: dict,
    sandwiches: list[dict],
    foraging_attempts: int,
) -> SessionMetrics:
    """Compute session metrics from raw data.

    Args:
        session_data: Session metadata dict.
        sandwiches: List of sandwich dicts with validity_score.
        foraging_attempts: Total foraging attempts.

    Returns:
        Computed SessionMetrics.
    """
    metrics = SessionMetrics()

    metrics.session_id = session_data.get("session_id")
    metrics.status = session_data.get("status", "unknown")
    metrics.current_state = session_data.get("current_state", "idle")
    metrics.current_tier = session_data.get("current_tier", 1)
    metrics.patience_remaining = session_data.get("patience_remaining", 5)
    metrics.sandwiches_today = len(sandwiches)

    if foraging_attempts > 0:
        metrics.sandwich_rate = len(sandwiches) / foraging_attempts

    if sandwiches:
        scores = [s.get("validity_score", 0.0) for s in sandwiches]
        metrics.mean_validity = sum(scores) / len(scores)

    started = session_data.get("started_at")
    if started:
        metrics.started_at = started
        metrics.uptime_seconds = (datetime.now() - started).total_seconds()

    return metrics


def compute_validity_distribution(sandwiches: list[dict]) -> list[float]:
    """Extract validity scores for histogram display.

    Args:
        sandwiches: List of sandwich dicts.

    Returns:
        List of validity scores.
    """
    return [s.get("validity_score", 0.0) for s in sandwiches if "validity_score" in s]


def compute_cost_breakdown(llm_calls: list[dict]) -> CostBreakdown:
    """Compute cost breakdown by pipeline component.

    Args:
        llm_calls: List of LLM call log entries.

    Returns:
        CostBreakdown by component.
    """
    breakdown = CostBreakdown()

    component_map = {
        "curiosity": "forager",
        "identifier": "identifier",
        "assembler": "assembler",
        "validator": "validator",
        "raw": "validator",
    }

    for call in llm_calls:
        cost = call.get("cost", 0.0)
        component = call.get("component", "raw")
        attr = component_map.get(component, "validator")
        setattr(breakdown, attr, getattr(breakdown, attr) + cost)

    return breakdown
