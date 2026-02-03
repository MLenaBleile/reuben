"""Content forager – explores information sources for sandwich ingredients.

Manages tiered sources with promotion/demotion logic based on consecutive
successes and failures.

Reference: SPEC.md Section 3.2.1; PROMPTS.md Prompt 8
"""

import logging
import random
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID, uuid4

from sandwich.llm.interface import SandwichLLM
from sandwich.sources.base import ContentSource, SourceResult

logger = logging.getLogger(__name__)


@dataclass
class ForagerConfig:
    """Configuration for the forager."""

    max_patience: int = 5
    tier_1_sources: list[str] = field(default_factory=lambda: ["wikipedia"])
    tier_2_sources: list[str] = field(default_factory=lambda: ["web_search"])
    tier_3_sources: list[str] = field(default_factory=list)
    successes_to_promote: int = 5
    failures_to_demote: int = 3


@dataclass
class ForagingResult:
    """Result from a foraging attempt."""

    source_result: SourceResult
    source_name: str
    curiosity_prompt: Optional[str] = None
    log_id: UUID = field(default_factory=uuid4)


class Forager:
    """Manages content exploration with tiered source selection.

    Sources are organized into tiers (1=most reliable, higher=experimental).
    The forager starts at tier 1 and promotes/demotes based on consecutive
    successes and failures.
    """

    def __init__(
        self,
        sources: dict[int, list[ContentSource]],
        llm: SandwichLLM,
        config: Optional[ForagerConfig] = None,
    ):
        self.sources = sources
        self.llm = llm
        self.config = config or ForagerConfig()
        self.current_tier: int = 1
        self.consecutive_failures: int = 0
        self.consecutive_successes: int = 0

    async def generate_curiosity(self, recent_topics: list[str]) -> str:
        """Generate a curiosity prompt using the LLM.

        Args:
            recent_topics: Topics recently explored, to avoid repetition.

        Returns:
            A single-sentence curiosity prompt.
        """
        return await self.llm.generate_curiosity(recent_topics)

    async def forage(
        self, curiosity: Optional[str] = None
    ) -> Optional[ForagingResult]:
        """Forage for content from the current tier's sources.

        If a curiosity prompt is provided, uses it as a search query.
        Otherwise fetches random content.

        Args:
            curiosity: Optional curiosity prompt to guide foraging.

        Returns:
            ForagingResult if content was found, None if all sources failed.
        """
        # Get sources for current tier, falling back to lower tiers
        tier_sources = self._get_tier_sources()
        if not tier_sources:
            logger.warning("No sources available for tier %d", self.current_tier)
            return None

        # Pick a random source from the tier
        source = random.choice(tier_sources)

        try:
            if curiosity:
                result = await source.fetch(curiosity)
            else:
                result = await source.fetch_random()
        except Exception as e:
            logger.warning(
                "Source '%s' failed: %s", source.name, e
            )
            return None

        if not result.content:
            logger.info(
                "Source '%s' returned empty content for query '%s'",
                source.name,
                curiosity,
            )
            return None

        return ForagingResult(
            source_result=result,
            source_name=source.name,
            curiosity_prompt=curiosity,
        )

    def record_success(self) -> None:
        """Record a successful sandwich creation.

        Resets failure counter, increments success counter.
        Promotes to higher tier after enough consecutive successes.
        """
        self.consecutive_failures = 0
        self.consecutive_successes += 1

        if self.consecutive_successes >= self.config.successes_to_promote:
            max_tier = max(self.sources.keys()) if self.sources else 1
            if self.current_tier < max_tier:
                old_tier = self.current_tier
                self.current_tier += 1
                self.consecutive_successes = 0
                logger.info(
                    "Tier promotion: %d → %d (after %d successes)",
                    old_tier,
                    self.current_tier,
                    self.config.successes_to_promote,
                )

    def record_failure(self) -> None:
        """Record a failed foraging/sandwich attempt.

        Resets success counter, increments failure counter.
        Demotes to lower tier after enough consecutive failures.
        """
        self.consecutive_successes = 0
        self.consecutive_failures += 1

        if self.consecutive_failures >= self.config.failures_to_demote:
            if self.current_tier > 1:
                old_tier = self.current_tier
                self.current_tier -= 1
                self.consecutive_failures = 0
                logger.info(
                    "Tier demotion: %d → %d (after %d failures)",
                    old_tier,
                    self.current_tier,
                    self.config.failures_to_demote,
                )

    def _get_tier_sources(self) -> list[ContentSource]:
        """Get sources for the current tier, falling back to lower tiers."""
        for tier in range(self.current_tier, 0, -1):
            if tier in self.sources and self.sources[tier]:
                return self.sources[tier]
        return []
