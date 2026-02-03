"""Tests for the state machine and error handler.

Reference: PROMPTS.md Prompt 9
"""

from uuid import uuid4

import pytest

from sandwich.agent.error_handler import determine_recovery_event
from sandwich.agent.state_machine import (
    AgentState,
    InvalidTransitionError,
    StateCheckpoint,
    StateMachine,
)
from sandwich.errors.exceptions import (
    ContentError,
    FatalError,
    ParseError,
    RetryableError,
)


# ===================================================================
# test_valid_transitions
# ===================================================================

class TestValidTransitions:
    """Verify the happy-path transition sequence through the full pipeline."""

    def test_full_pipeline_transitions(self):
        sm = StateMachine()
        assert sm.current_state == AgentState.IDLE

        sm.transition("start_foraging")
        assert sm.current_state == AgentState.FORAGING

        sm.transition("content_found")
        assert sm.current_state == AgentState.PREPROCESSING

        sm.transition("content_accepted")
        assert sm.current_state == AgentState.IDENTIFYING

        sm.transition("candidates_found")
        assert sm.current_state == AgentState.SELECTING

        sm.transition("candidate_selected")
        assert sm.current_state == AgentState.ASSEMBLING

        sm.transition("assembly_complete")
        assert sm.current_state == AgentState.VALIDATING

        sm.transition("accepted")
        assert sm.current_state == AgentState.STORING

        sm.transition("stored")
        assert sm.current_state == AgentState.IDLE

        # Verify all transitions were recorded
        assert len(sm.checkpoints) == 8


# ===================================================================
# test_invalid_transition
# ===================================================================

class TestInvalidTransition:
    """Verify illegal transitions raise InvalidTransitionError."""

    def test_idle_to_validating(self):
        sm = StateMachine()
        assert sm.current_state == AgentState.IDLE

        with pytest.raises(InvalidTransitionError) as exc_info:
            sm.transition("accepted")

        assert exc_info.value.current_state == AgentState.IDLE
        assert exc_info.value.event == "accepted"

    def test_can_transition_false(self):
        sm = StateMachine()
        assert not sm.can_transition("accepted")
        assert sm.can_transition("start_foraging")


# ===================================================================
# test_checkpoint_persistence
# ===================================================================

class TestCheckpointPersistence:
    """Verify checkpoints are saved and queryable."""

    def test_checkpoints_saved(self):
        sm = StateMachine()

        sm.transition("start_foraging", data={"curiosity": "squeeze theorem"})
        sm.transition("content_found", data={"url": "https://example.com"})
        sm.transition("content_accepted")

        assert len(sm.checkpoints) == 3

        # First checkpoint should be FORAGING with curiosity data
        cp0 = sm.checkpoints[0]
        assert cp0.state == AgentState.FORAGING
        assert cp0.data["curiosity"] == "squeeze theorem"
        assert cp0.session_id == sm.session_id

        # Latest checkpoint
        latest = sm.get_latest_checkpoint()
        assert latest is not None
        assert latest.state == AgentState.IDENTIFYING


# ===================================================================
# test_crash_recovery
# ===================================================================

class TestCrashRecovery:
    """Verify state can be restored from a checkpoint."""

    def test_crash_recovery(self):
        # Original session — transition to ASSEMBLING
        sm1 = StateMachine()
        sm1.transition("start_foraging")
        sm1.transition("content_found")
        sm1.transition("content_accepted")
        sm1.transition("candidates_found")
        sm1.transition("candidate_selected", data={
            "bread_top": "Upper bound g(x)",
            "bread_bottom": "Lower bound h(x)",
            "filling": "Target function f(x)",
        })

        assert sm1.current_state == AgentState.ASSEMBLING
        checkpoint = sm1.get_latest_checkpoint()

        # Simulate crash: create new state machine and recover
        sm2 = StateMachine()
        assert sm2.current_state == AgentState.IDLE  # Fresh state

        sm2.recover_from_checkpoint(checkpoint)
        assert sm2.current_state == AgentState.ASSEMBLING
        assert sm2.session_id == sm1.session_id

        # Verify data payload is available
        latest = sm2.get_latest_checkpoint()
        assert latest.data["bread_top"] == "Upper bound g(x)"
        assert latest.data["filling"] == "Target function f(x)"

        # Can continue from recovered state
        sm2.transition("assembly_complete")
        assert sm2.current_state == AgentState.VALIDATING


# ===================================================================
# test_error_routing
# ===================================================================

class TestErrorRouting:
    """Verify errors are routed to the correct recovery events."""

    def test_content_error_recovered(self):
        event = determine_recovery_event(
            ContentError("Bad content", reason="too_short")
        )
        assert event == "recovered"

    def test_retryable_error_recovered(self):
        event = determine_recovery_event(
            RetryableError("Rate limit hit", reason="rate_limit")
        )
        assert event == "recovered"

    def test_parse_error_recovered(self):
        event = determine_recovery_event(
            ParseError("Bad JSON", raw_output="{invalid}")
        )
        assert event == "recovered"

    def test_fatal_error_fatal(self):
        event = determine_recovery_event(
            FatalError("Database down", reason="database_down")
        )
        assert event == "fatal"

    def test_error_routing_with_state_machine(self):
        """Verify error events work with state machine transitions."""
        sm = StateMachine()
        sm.transition("start_foraging")
        sm.transition("content_found")
        sm.transition("content_accepted")
        assert sm.current_state == AgentState.IDENTIFYING

        # Simulate an error
        sm.transition("error")
        assert sm.current_state == AgentState.ERROR_RECOVERY

        # ContentError → recovered → IDLE
        event = determine_recovery_event(
            ContentError("Bad content", reason="low_quality")
        )
        sm.transition(event)
        assert sm.current_state == AgentState.IDLE

    def test_fatal_error_ends_session(self):
        """Verify fatal error transitions to SESSION_END."""
        sm = StateMachine()
        sm.transition("start_foraging")
        sm.transition("error")
        assert sm.current_state == AgentState.ERROR_RECOVERY

        event = determine_recovery_event(
            FatalError("Auth failed", reason="auth_error")
        )
        sm.transition(event)
        assert sm.current_state == AgentState.SESSION_END


# ===================================================================
# test_session_end_terminal
# ===================================================================

class TestSessionEndTerminal:
    """Verify SESSION_END is a terminal state with no further transitions."""

    def test_session_end_terminal(self):
        sm = StateMachine()
        sm.transition("end_session")
        assert sm.current_state == AgentState.SESSION_END

        # No transitions should be possible
        assert not sm.can_transition("start_foraging")
        assert not sm.can_transition("end_session")
        assert not sm.can_transition("error")

        with pytest.raises(InvalidTransitionError):
            sm.transition("start_foraging")


# ===================================================================
# test_rejection_loops_back
# ===================================================================

class TestRejectionLoop:
    """Verify rejected content loops back to IDLE for retry."""

    def test_preprocessor_rejection(self):
        sm = StateMachine()
        sm.transition("start_foraging")
        sm.transition("content_found")
        sm.transition("content_rejected")
        assert sm.current_state == AgentState.IDLE

    def test_validator_rejection(self):
        sm = StateMachine()
        sm.transition("start_foraging")
        sm.transition("content_found")
        sm.transition("content_accepted")
        sm.transition("candidates_found")
        sm.transition("candidate_selected")
        sm.transition("assembly_complete")
        sm.transition("rejected")
        assert sm.current_state == AgentState.IDLE
