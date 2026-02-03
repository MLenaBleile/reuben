"""SANDWICH Observability Dashboard.

A Streamlit dashboard for monitoring Reuben's sandwich-making operations.
Run with: streamlit run dashboard/app.py

Reference: SPEC.md Section 8.3; PROMPTS.md Prompt 11
"""

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from dashboard.components.charts import (
    cost_pie_chart,
    sandwiches_over_time,
    tier_success_chart,
    validity_histogram,
)
from dashboard.components.metrics import (
    CostBreakdown,
    ErrorCounts,
    SandwichRow,
    SessionMetrics,
    compute_session_metrics,
    compute_validity_distribution,
)

st.set_page_config(page_title="SANDWICH Operations", layout="wide")

# Auto-refresh every 5 seconds
st_autorefresh(interval=5000, key="dashboard_refresh")

st.title("SANDWICH Operations Dashboard")
st.caption("Monitoring Reuben's autonomous sandwich-making")

# ---------------------------------------------------------------------------
# NOTE: This dashboard is designed to connect to a live database.
# For now it displays placeholder data. When connected, replace the
# placeholder sections with queries to the PostgreSQL database.
# ---------------------------------------------------------------------------

# --- Header: Session status ---
st.subheader("Current Session")

# Placeholder metrics (replace with DB queries in production)
metrics = SessionMetrics(
    session_id="(no active session)",
    status="idle",
    current_state="idle",
    current_tier=1,
    patience_remaining=5,
    sandwiches_today=0,
    sandwich_rate=0.0,
    mean_validity=0.0,
)

header_cols = st.columns(6)
header_cols[0].metric("Session", str(metrics.session_id)[:8] if metrics.session_id else "N/A")
header_cols[1].metric("Status", metrics.status)
header_cols[2].metric("State", metrics.current_state)
header_cols[3].metric("Tier", metrics.current_tier)
header_cols[4].metric("Patience", metrics.patience_remaining)
header_cols[5].metric("Uptime", f"{metrics.uptime_seconds / 60:.1f}m")

# --- Row 1: Key metrics ---
st.subheader("Key Metrics")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Sandwiches Today", metrics.sandwiches_today)
m2.metric("Sandwich Rate", f"{metrics.sandwich_rate:.1%}")
m3.metric("Mean Validity", f"{metrics.mean_validity:.3f}")
m4.metric("Cost/Sandwich", f"${metrics.cost_per_sandwich:.4f}")

# --- Row 2: Charts ---
st.subheader("Visualizations")
chart1, chart2 = st.columns(2)

with chart1:
    # Validity distribution
    scores = compute_validity_distribution([])
    if scores:
        fig = validity_histogram(scores)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No sandwiches yet. Validity distribution will appear here.")

with chart2:
    # Sandwiches over time
    st.info("Sandwich timeline will appear here when data is available.")

# --- Row 3: Tables ---
st.subheader("Details")
tab1, tab2 = st.columns(2)

with tab1:
    st.markdown("**Latest Sandwiches**")
    st.info("Sandwich table will populate as Reuben makes sandwiches.")

with tab2:
    st.markdown("**Error Counts**")
    errors = ErrorCounts()
    st.table({
        "Type": ["Content", "Parse", "Retryable", "Fatal"],
        "Count": [
            errors.content_errors,
            errors.parse_errors,
            errors.retryable_errors,
            errors.fatal_errors,
        ],
    })

# --- Row 4: Cost breakdown ---
st.subheader("Cost Breakdown")
breakdown = CostBreakdown()
total = breakdown.forager + breakdown.identifier + breakdown.assembler + breakdown.validator
if total > 0:
    fig = cost_pie_chart({
        "Forager": breakdown.forager,
        "Identifier": breakdown.identifier,
        "Assembler": breakdown.assembler,
        "Validator": breakdown.validator,
    })
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Cost breakdown will appear once LLM calls are made.")

# --- Row 5: Foraging stats ---
st.subheader("Foraging Statistics")
st.info("Foraging statistics by tier and source will appear here.")
