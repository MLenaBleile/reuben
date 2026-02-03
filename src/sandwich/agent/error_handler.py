"""Error handler – routes errors to appropriate state transitions.

Reference: SPEC.md Section 6.4; PROMPTS.md Prompt 9
"""

import logging

from sandwich.errors.exceptions import (
    ContentError,
    FatalError,
    ParseError,
    RetryableError,
    SandwichError,
)

logger = logging.getLogger(__name__)


def determine_recovery_event(error: SandwichError) -> str:
    """Determine the state machine event based on error type.

    Args:
        error: The error that occurred.

    Returns:
        Event string to trigger the appropriate state transition.
        "recovered" routes back to IDLE for retryable errors.
        "fatal" routes to SESSION_END for unrecoverable errors.
    """
    if isinstance(error, FatalError):
        logger.error("Fatal error: %s (reason=%s)", error, error.reason)
        return "fatal"

    if isinstance(error, ContentError):
        logger.warning("Content error: %s (reason=%s)", error, error.reason)
        return "recovered"

    if isinstance(error, ParseError):
        logger.warning("Parse error: %s", error)
        return "recovered"

    if isinstance(error, RetryableError):
        logger.warning(
            "Retryable error (after max retries): %s (reason=%s)",
            error,
            error.reason,
        )
        return "recovered"

    # Unknown SandwichError subclass — treat as recoverable
    logger.warning("Unknown error type %s: %s", type(error).__name__, error)
    return "recovered"
