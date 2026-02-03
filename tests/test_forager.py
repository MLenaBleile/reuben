"""Tests for the forager, content sources, and tier transition logic.

Reference: PROMPTS.md Prompt 8
"""

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sandwich.agent.forager import Forager, ForagerConfig, ForagingResult
from sandwich.sources.base import ContentSource, RateLimiter, SourceResult
from sandwich.sources.wikipedia import WikipediaSource


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class MockContentSource(ContentSource):
    """A mock content source for testing."""

    def __init__(self, name: str, tier: int, content: str = "Mock content"):
        self.name = name
        self.tier = tier
        self.rate_limiter = None
        self._content = content
        self.fetch_count = 0
        self.fetch_random_count = 0

    async def fetch(self, query=None):
        self.fetch_count += 1
        return SourceResult(
            content=self._content,
            url=f"https://example.com/{query or 'random'}",
            title=f"Mock: {query or 'random'}",
            content_type="text",
            metadata={"source": self.name},
        )

    async def fetch_random(self):
        self.fetch_random_count += 1
        return SourceResult(
            content=self._content,
            url="https://example.com/random",
            title="Random Article",
            content_type="text",
            metadata={"source": self.name},
        )


class EmptyContentSource(ContentSource):
    """A source that always returns empty content."""

    def __init__(self, name: str = "empty", tier: int = 1):
        self.name = name
        self.tier = tier
        self.rate_limiter = None

    async def fetch(self, query=None):
        return SourceResult(content="", metadata={})

    async def fetch_random(self):
        return SourceResult(content="", metadata={})


# ===================================================================
# Wikipedia source tests (mocked HTTP)
# ===================================================================

def _make_http_response(json_data: dict):
    """Create a mock httpx response that behaves like a real one."""
    resp = MagicMock()
    resp.status_code = 200
    resp.is_success = True
    resp.raise_for_status = MagicMock(return_value=resp)
    resp.json.return_value = json_data
    return resp


class TestWikipediaRandom:
    """Verify WikipediaSource.fetch_random returns valid content."""

    @pytest.mark.asyncio
    async def test_wikipedia_random(self):
        wiki = WikipediaSource()

        mock_client = AsyncMock()
        mock_client.is_closed = False

        random_response = _make_http_response({
            "query": {
                "random": [{"title": "Squeeze theorem", "id": 12345}]
            }
        })

        summary_response = _make_http_response({
            "title": "Squeeze theorem",
            "extract": (
                "In calculus, the squeeze theorem, also known as the sandwich "
                "theorem, is a theorem regarding the limit of a function that "
                "is bounded between two other functions. The squeeze theorem is "
                "used in calculus and mathematical analysis, typically to "
                "confirm the limit of a function via comparison with two other "
                "functions whose limits are known. It was first used "
                "geometrically by the mathematicians Archimedes and Eudoxus in "
                "an effort to compute pi, and was formulated in modern terms "
                "by Carl Friedrich Gauss."
            ),
            "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Squeeze_theorem"}},
            "description": "theorem in calculus",
        })

        mock_client.get = AsyncMock(side_effect=[random_response, summary_response])
        wiki._client = mock_client

        result = await wiki.fetch_random()

        assert len(result.content) > 100
        assert result.url is not None
        assert result.title == "Squeeze theorem"


class TestWikipediaSearch:
    """Verify WikipediaSource.fetch(query) returns relevant content."""

    @pytest.mark.asyncio
    async def test_wikipedia_search(self):
        wiki = WikipediaSource()

        mock_client = AsyncMock()
        mock_client.is_closed = False

        search_response = _make_http_response({
            "query": {
                "search": [{"title": "Squeeze theorem", "snippet": "...squeeze..."}]
            }
        })

        summary_response = _make_http_response({
            "title": "Squeeze theorem",
            "extract": (
                "In calculus, the squeeze theorem, also known as the sandwich "
                "theorem, is a theorem regarding the limit of a function that "
                "is bounded between two other functions. The squeeze theorem is "
                "used in calculus and mathematical analysis, typically to "
                "confirm the limit of a function via comparison with two other "
                "functions whose limits are known."
            ),
            "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Squeeze_theorem"}},
            "description": "theorem in calculus",
        })

        mock_client.get = AsyncMock(side_effect=[search_response, summary_response])
        wiki._client = mock_client

        result = await wiki.fetch("squeeze theorem")

        assert len(result.content) > 100
        assert "squeeze" in result.content.lower() or "theorem" in result.content.lower()
        assert result.title == "Squeeze theorem"
        assert result.url is not None


# ===================================================================
# Tier transition tests
# ===================================================================

class TestTierTransitionDown:
    """Verify tier demotes after consecutive failures."""

    def test_tier_transition_down(self):
        source_t1 = MockContentSource("wiki", 1)
        source_t2 = MockContentSource("search", 2)
        llm = AsyncMock()

        forager = Forager(
            sources={1: [source_t1], 2: [source_t2]},
            llm=llm,
            config=ForagerConfig(failures_to_demote=3),
        )
        forager.current_tier = 2

        # Record 3 consecutive failures
        forager.record_failure()
        assert forager.current_tier == 2
        forager.record_failure()
        assert forager.current_tier == 2
        forager.record_failure()
        assert forager.current_tier == 1  # Demoted!

        # Counter should have reset
        assert forager.consecutive_failures == 0


class TestTierTransitionUp:
    """Verify tier promotes after consecutive successes."""

    def test_tier_transition_up(self):
        source_t1 = MockContentSource("wiki", 1)
        source_t2 = MockContentSource("search", 2)
        llm = AsyncMock()

        forager = Forager(
            sources={1: [source_t1], 2: [source_t2]},
            llm=llm,
            config=ForagerConfig(successes_to_promote=5),
        )
        assert forager.current_tier == 1

        # Record 5 consecutive successes
        for i in range(4):
            forager.record_success()
            assert forager.current_tier == 1

        forager.record_success()
        assert forager.current_tier == 2  # Promoted!

        # Counter should have reset
        assert forager.consecutive_successes == 0


class TestTierNoDemoteBelowOne:
    """Verify tier can't go below 1."""

    def test_no_demote_below_one(self):
        source_t1 = MockContentSource("wiki", 1)
        llm = AsyncMock()

        forager = Forager(
            sources={1: [source_t1]},
            llm=llm,
            config=ForagerConfig(failures_to_demote=2),
        )
        assert forager.current_tier == 1

        forager.record_failure()
        forager.record_failure()
        assert forager.current_tier == 1  # Can't go below 1


class TestTierNoPromoteAboveMax:
    """Verify tier can't exceed maximum available."""

    def test_no_promote_above_max(self):
        source_t1 = MockContentSource("wiki", 1)
        llm = AsyncMock()

        forager = Forager(
            sources={1: [source_t1]},
            llm=llm,
            config=ForagerConfig(successes_to_promote=2),
        )
        assert forager.current_tier == 1

        forager.record_success()
        forager.record_success()
        assert forager.current_tier == 1  # No tier 2 available


# ===================================================================
# Rate limiting tests
# ===================================================================

class TestRateLimiting:
    """Verify rate limiter delays rapid requests."""

    def test_rate_limiting(self):
        # 60 per minute = 1 per second
        limiter = RateLimiter(max_per_minute=60)

        # First request should not wait
        wait1 = limiter.wait_if_needed()
        assert wait1 == 0.0

        # Immediate second request should wait ~1 second
        # But we'll use a fast rate for testing: 6000/min = 10ms interval
        fast_limiter = RateLimiter(max_per_minute=6000)
        fast_limiter.wait_if_needed()
        start = time.monotonic()
        fast_limiter.wait_if_needed()
        elapsed = time.monotonic() - start

        # Should have waited approximately 0.01 seconds (10ms)
        assert elapsed >= 0.005, f"Expected >= 5ms wait, got {elapsed:.4f}s"


# ===================================================================
# Foraging tests
# ===================================================================

class TestForagingWithCuriosity:
    """Verify forager uses curiosity prompt for directed search."""

    @pytest.mark.asyncio
    async def test_foraging_with_curiosity(self):
        source = MockContentSource("wiki", 1, content="Squeeze theorem content here")
        llm = AsyncMock()

        forager = Forager(sources={1: [source]}, llm=llm)

        result = await forager.forage(curiosity="squeeze theorem")

        assert result is not None
        assert result.source_name == "wiki"
        assert result.curiosity_prompt == "squeeze theorem"
        assert source.fetch_count == 1


class TestForagingRandomWhenNoCuriosity:
    """Verify forager fetches random content when no curiosity given."""

    @pytest.mark.asyncio
    async def test_foraging_random(self):
        source = MockContentSource("wiki", 1, content="Random article content")
        llm = AsyncMock()

        forager = Forager(sources={1: [source]}, llm=llm)

        result = await forager.forage()

        assert result is not None
        assert source.fetch_random_count == 1


class TestForagingEmptyContent:
    """Verify forager returns None for empty content."""

    @pytest.mark.asyncio
    async def test_foraging_empty(self):
        source = EmptyContentSource()
        llm = AsyncMock()

        forager = Forager(sources={1: [source]}, llm=llm)

        result = await forager.forage(curiosity="anything")

        assert result is None


class TestSuccessResetsFailures:
    """Verify success resets the failure counter."""

    def test_success_resets_failures(self):
        llm = AsyncMock()
        source = MockContentSource("wiki", 1)
        forager = Forager(sources={1: [source]}, llm=llm)

        forager.record_failure()
        forager.record_failure()
        assert forager.consecutive_failures == 2

        forager.record_success()
        assert forager.consecutive_failures == 0
        assert forager.consecutive_successes == 1
