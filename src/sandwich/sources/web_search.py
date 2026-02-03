"""Web search content source using DuckDuckGo.

Fetches search results and page content for sandwich ingredient discovery.
No API key required.

Reference: SPEC.md Section 3.2.1; PROMPTS.md Prompt 8
"""

import logging
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from sandwich.sources.base import ContentSource, RateLimiter, SourceResult

logger = logging.getLogger(__name__)

DUCKDUCKGO_HTML_URL = "https://html.duckduckgo.com/html/"


class WebSearchSource(ContentSource):
    """Web search source using DuckDuckGo HTML interface."""

    name = "web_search"
    tier = 2

    def __init__(self, max_per_minute: int = 10):
        self.rate_limiter = RateLimiter(max_per_minute)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; SANDWICH-Bot/1.0; research project)"
                    )
                },
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def fetch_random(self) -> SourceResult:
        """Fetch a random topic by searching for a random word.

        Uses a small set of seed words for serendipitous discovery.
        """
        import random

        seed_words = [
            "theorem", "paradox", "optimization", "constraint", "equilibrium",
            "convergence", "entropy", "symmetry", "recursion", "emergence",
            "bifurcation", "resonance", "topology", "duality", "invariant",
        ]
        query = random.choice(seed_words)
        return await self.fetch(query)

    async def fetch(self, query: Optional[str] = None) -> SourceResult:
        """Search the web and fetch the top result's content.

        Args:
            query: Search query string.

        Returns:
            SourceResult with page content.
        """
        if query is None:
            return await self.fetch_random()

        self.rate_limiter.wait_if_needed()
        client = await self._get_client()

        # Search DuckDuckGo
        try:
            resp = await client.post(
                DUCKDUCKGO_HTML_URL,
                data={"q": query},
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("DuckDuckGo search failed: %s", e)
            return SourceResult(
                content="",
                url=None,
                title=None,
                content_type="text",
                metadata={"query": query, "error": str(e)},
            )

        # Parse search results
        soup = BeautifulSoup(resp.text, "html.parser")
        results = soup.select("a.result__a")

        if not results:
            return SourceResult(
                content="",
                url=None,
                title=None,
                content_type="text",
                metadata={"query": query, "error": "no_results"},
            )

        # Get the first result URL
        first_result = results[0]
        href = first_result.get("href", "")
        title = first_result.get_text(strip=True)

        if not href:
            return SourceResult(
                content="",
                url=None,
                title=title,
                content_type="text",
                metadata={"query": query, "error": "no_href"},
            )

        # Fetch the actual page content
        return await self._fetch_page(href, title, query)

    async def _fetch_page(self, url: str, title: str, query: str) -> SourceResult:
        """Fetch and extract text content from a URL."""
        self.rate_limiter.wait_if_needed()
        client = await self._get_client()

        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("Failed to fetch page %s: %s", url, e)
            return SourceResult(
                content="",
                url=url,
                title=title,
                content_type="html",
                metadata={"query": query, "error": str(e)},
            )

        # Extract text content from HTML
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove script, style, nav elements
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)

        return SourceResult(
            content=text[:10000],  # Limit content size
            url=url,
            title=title,
            content_type="html",
            metadata={"query": query, "source": "web_search"},
        )
