"""Base class and data types for content sources.

Reference: SPEC.md Section 3.2.1; PROMPTS.md Prompt 8
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SourceResult:
    """Result from a content source fetch."""

    content: str
    url: Optional[str] = None
    title: Optional[str] = None
    content_type: str = "text"
    metadata: dict = field(default_factory=dict)


class RateLimiter:
    """Simple token-bucket rate limiter.

    Args:
        max_per_minute: Maximum number of requests per minute.
    """

    def __init__(self, max_per_minute: int):
        self.max_per_minute = max_per_minute
        self.interval = 60.0 / max_per_minute
        self._last_request: float = 0.0

    def wait_if_needed(self) -> float:
        """Block until a request is allowed.

        Returns:
            The number of seconds waited (0.0 if no wait needed).
        """
        now = time.monotonic()
        elapsed = now - self._last_request
        if elapsed < self.interval:
            wait_time = self.interval - elapsed
            time.sleep(wait_time)
            self._last_request = time.monotonic()
            return wait_time
        self._last_request = now
        return 0.0


class ContentSource(ABC):
    """Abstract base class for content sources.

    Each source has a name, a tier (1=reliable, 2=moderate, 3=experimental),
    and an optional rate limit.
    """

    name: str
    tier: int
    rate_limiter: Optional[RateLimiter]

    @abstractmethod
    async def fetch(self, query: Optional[str] = None) -> SourceResult:
        """Fetch content matching a query.

        Args:
            query: Search query. If None, implementation may fetch random content.

        Returns:
            SourceResult with fetched content.
        """
        ...

    @abstractmethod
    async def fetch_random(self) -> SourceResult:
        """Fetch a random piece of content from this source.

        Returns:
            SourceResult with random content.
        """
        ...
