"""Entry point for Reuben – the sandwich-making agent.

Usage:
    python -m sandwich.main --max-sandwiches 5
    python -m sandwich.main --max-duration 30

Reference: PROMPTS.md Prompt 10
"""

import argparse
import asyncio
import logging
from datetime import timedelta

from sandwich.agent.forager import Forager, ForagerConfig
from sandwich.agent.reuben import Reuben
from sandwich.config import SandwichConfig
from sandwich.db.corpus import SandwichCorpus
from sandwich.llm.anthropic import AnthropicSandwichLLM
from sandwich.llm.embeddings import OpenAIEmbeddingService
from sandwich.sources.web_search import WebSearchSource
from sandwich.sources.wikipedia import WikipediaSource

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def build_reuben(config: SandwichConfig) -> Reuben:
    """Construct a fully-wired Reuben agent."""
    llm = AnthropicSandwichLLM(config=config.llm)
    embeddings = OpenAIEmbeddingService()
    corpus = SandwichCorpus()

    sources = {}
    if config.foraging.wikipedia_enabled:
        sources.setdefault(1, []).append(WikipediaSource())
    if config.foraging.web_search_enabled:
        sources.setdefault(2, []).append(WebSearchSource())

    forager = Forager(
        sources=sources,
        llm=llm,
        config=ForagerConfig(max_patience=config.foraging.max_patience),
    )

    return Reuben(
        config=config,
        llm=llm,
        embeddings=embeddings,
        forager=forager,
        corpus=corpus,
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description="Reuben makes sandwiches")
    parser.add_argument(
        "--max-sandwiches", type=int, default=None,
        help="Stop after N sandwiches",
    )
    parser.add_argument(
        "--max-duration", type=int, default=None,
        help="Stop after N minutes",
    )
    args = parser.parse_args()

    config = SandwichConfig()
    reuben = build_reuben(config)

    session = await reuben.run(
        max_sandwiches=args.max_sandwiches,
        max_duration=timedelta(minutes=args.max_duration) if args.max_duration else None,
    )

    # Print summary
    print(f"\n--- Session Summary ---")
    print(f"Session ID: {session.session_id}")
    print(f"Duration: {session.ended_at - session.started_at}")
    print(f"Sandwiches made: {session.sandwiches_made}")
    print(f"Foraging attempts: {session.foraging_attempts}")
    if session.sandwiches:
        for s in session.sandwiches:
            print(f"  - {s.assembled.name} (validity: {s.validation.overall_score:.2f})")


if __name__ == "__main__":
    asyncio.run(main())
