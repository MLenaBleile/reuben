"""Reusable chart components for the SANDWICH dashboard.

Reference: PROMPTS.md Prompt 11
"""

from typing import Optional

import plotly.express as px
import plotly.graph_objects as go


def validity_histogram(scores: list[float], title: str = "Validity Score Distribution"):
    """Create a histogram of validity scores.

    Args:
        scores: List of validity scores (0-1).
        title: Chart title.

    Returns:
        Plotly figure.
    """
    fig = px.histogram(
        x=scores,
        nbins=20,
        range_x=[0, 1],
        labels={"x": "Validity Score", "y": "Count"},
        title=title,
    )
    fig.update_layout(
        xaxis_title="Validity Score",
        yaxis_title="Count",
        bargap=0.05,
    )
    return fig


def sandwiches_over_time(timestamps: list, counts: list[int], title: str = "Sandwiches Over Time"):
    """Create a line chart of cumulative sandwiches over time.

    Args:
        timestamps: List of datetime objects.
        counts: Cumulative sandwich counts.
        title: Chart title.

    Returns:
        Plotly figure.
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=counts,
        mode="lines+markers",
        name="Sandwiches",
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title="Cumulative Sandwiches",
    )
    return fig


def cost_pie_chart(breakdown: dict[str, float], title: str = "Cost by Component"):
    """Create a pie chart of cost breakdown.

    Args:
        breakdown: Dict of component name → cost.
        title: Chart title.

    Returns:
        Plotly figure.
    """
    labels = list(breakdown.keys())
    values = list(breakdown.values())

    fig = px.pie(
        names=labels,
        values=values,
        title=title,
    )
    return fig


def tier_success_chart(tier_rates: dict[int, float], title: str = "Success Rate by Tier"):
    """Create a bar chart of success rates by tier.

    Args:
        tier_rates: Dict of tier number → success rate (0-1).
        title: Chart title.

    Returns:
        Plotly figure.
    """
    tiers = [f"Tier {t}" for t in sorted(tier_rates.keys())]
    rates = [tier_rates[t] * 100 for t in sorted(tier_rates.keys())]

    fig = px.bar(
        x=tiers,
        y=rates,
        labels={"x": "Tier", "y": "Success Rate (%)"},
        title=title,
    )
    fig.update_layout(yaxis_range=[0, 100])
    return fig
