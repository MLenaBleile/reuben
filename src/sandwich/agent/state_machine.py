"""Agent state machine – manages transitions through the sandwich-making pipeline.

Enforces legal state transitions and records checkpoints for crash recovery.

Reference: SPEC.md Sections 5.1–5.3, 6.4; PROMPTS.md Prompt 9
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class AgentState(Enum):
    IDLE = "idle"
    FORAGING = "foraging"
    PREPROCESSING = "preprocessing"
    IDENTIFYING = "identifying"
    SELECTING = "selecting"
    ASSEMBLING = "assembling"
    VALIDATING = "validating"
    STORING = "storing"
    ERROR_RECOVERY = "error_recovery"
    SESSION_END = "session_end"


# Legal transitions: current_state → { event → next_state }
TRANSITIONS: dict[AgentState, dict[str, AgentState]] = {
    AgentState.IDLE: {
        "start_foraging": AgentState.FORAGING,
        "end_session": AgentState.SESSION_END,
    },
    AgentState.FORAGING: {
        "content_found": AgentState.PREPROCESSING,
        "forage_failed": AgentState.IDLE,
        "error": AgentState.ERROR_RECOVERY,
    },
    AgentState.PREPROCESSING: {
        "content_accepted": AgentState.IDENTIFYING,
        "content_rejected": AgentState.IDLE,
        "error": AgentState.ERROR_RECOVERY,
    },
    AgentState.IDENTIFYING: {
        "candidates_found": AgentState.SELECTING,
        "no_candidates": AgentState.IDLE,
        "error": AgentState.ERROR_RECOVERY,
    },
    AgentState.SELECTING: {
        "candidate_selected": AgentState.ASSEMBLING,
        "none_viable": AgentState.IDLE,
        "error": AgentState.ERROR_RECOVERY,
    },
    AgentState.ASSEMBLING: {
        "assembly_complete": AgentState.VALIDATING,
        "error": AgentState.ERROR_RECOVERY,
    },
    AgentState.VALIDATING: {
        "accepted": AgentState.STORING,
        "review": AgentState.STORING,
        "rejected": AgentState.IDLE,
        "error": AgentState.ERROR_RECOVERY,
    },
    AgentState.STORING: {
        "stored": AgentState.IDLE,
        "error": AgentState.ERROR_RECOVERY,
    },
    AgentState.ERROR_RECOVERY: {
        "recovered": AgentState.IDLE,
        "fatal": AgentState.SESSION_END,
    },
    AgentState.SESSION_END: {},  # Terminal state — no transitions
}


class InvalidTransitionError(Exception):
    """Raised when an illegal state transition is attempted."""

    def __init__(self, current_state: AgentState, event: str):
        self.current_state = current_state
        self.event = event
        super().__init__(
            f"Invalid transition: {current_state.value} + '{event}' "
            f"(valid events: {list(TRANSITIONS.get(current_state, {}).keys())})"
        )


@dataclass
class StateCheckpoint:
    """A snapshot of the state machine at a point in time."""

    checkpoint_id: UUID = field(default_factory=uuid4)
    session_id: UUID = field(default_factory=uuid4)
    state: AgentState = AgentState.IDLE
    timestamp: datetime = field(default_factory=datetime.now)
    data: dict[str, Any] = field(default_factory=dict)
    transition_reason: str = ""


class StateMachine:
    """Manages agent state transitions with checkpoint support.

    Enforces the transition table and records every transition as a
    StateCheckpoint for crash recovery.
    """

    def __init__(self, session_id: Optional[UUID] = None):
        self.session_id = session_id or uuid4()
        self.current_state = AgentState.IDLE
        self.checkpoints: list[StateCheckpoint] = []

    def can_transition(self, event: str) -> bool:
        """Check whether a transition is legal from the current state.

        Args:
            event: The event name.

        Returns:
            True if the transition is allowed.
        """
        return event in TRANSITIONS.get(self.current_state, {})

    def transition(self, event: str, data: Optional[dict] = None) -> AgentState:
        """Execute a state transition.

        Args:
            event: The event triggering the transition.
            data: Optional state-specific payload to store in the checkpoint.

        Returns:
            The new state after the transition.

        Raises:
            InvalidTransitionError: If the transition is not allowed.
        """
        if not self.can_transition(event):
            raise InvalidTransitionError(self.current_state, event)

        new_state = TRANSITIONS[self.current_state][event]
        old_state = self.current_state

        checkpoint = StateCheckpoint(
            session_id=self.session_id,
            state=new_state,
            data=data or {},
            transition_reason=f"{old_state.value} --[{event}]--> {new_state.value}",
        )
        self.checkpoints.append(checkpoint)
        self.current_state = new_state

        logger.info(
            "Transition: %s --[%s]--> %s",
            old_state.value,
            event,
            new_state.value,
        )

        return new_state

    def recover_from_checkpoint(self, checkpoint: StateCheckpoint) -> None:
        """Restore the state machine from a checkpoint.

        Args:
            checkpoint: The checkpoint to restore from.
        """
        self.current_state = checkpoint.state
        self.session_id = checkpoint.session_id
        self.checkpoints.append(checkpoint)

        logger.info(
            "Recovered to state %s from checkpoint %s",
            checkpoint.state.value,
            checkpoint.checkpoint_id,
        )

    def get_latest_checkpoint(self) -> Optional[StateCheckpoint]:
        """Return the most recent checkpoint, if any."""
        return self.checkpoints[-1] if self.checkpoints else None
