"""Ingredient analysis – find, create, and track ingredient reuse.

Wraps the corpus ingredient-matching logic for use by the analysis engine
and provides utilities for ingredient-level statistics.

Reference: SPEC.md Section 10.3; PROMPTS.md Prompt 12
"""

import logging
from typing import Optional
from uuid import UUID, uuid4

from sandwich.db.corpus import CorpusIngredient, SandwichCorpus

logger = logging.getLogger(__name__)


def find_or_create_ingredient(
    text: str,
    ingredient_type: str,
    embedding: Optional[list[float]],
    sandwich_id: UUID,
    corpus: SandwichCorpus,
    similarity_threshold: float = 0.92,
) -> CorpusIngredient:
    """Find an existing ingredient by text or embedding similarity, or create a new one.

    If a matching ingredient is found, its usage_count is incremented.
    Otherwise a new CorpusIngredient is created, added to the corpus, and returned.

    Args:
        text: The ingredient text (e.g. "Upper bound g(x)").
        ingredient_type: 'bread' or 'filling'.
        embedding: Optional embedding vector for fuzzy matching.
        sandwich_id: The sandwich this ingredient belongs to.
        corpus: The SandwichCorpus to search/update.
        similarity_threshold: Cosine similarity threshold for fuzzy match.

    Returns:
        The matched or newly created CorpusIngredient.
    """
    match = corpus.find_matching_ingredient(
        text=text,
        ingredient_type=ingredient_type,
        embedding=embedding,
        similarity_threshold=similarity_threshold,
    )

    if match is not None:
        match.usage_count += 1
        logger.debug(
            "Reused ingredient %s (usage_count=%d): %s",
            match.ingredient_id,
            match.usage_count,
            text[:60],
        )
        return match

    ingredient = CorpusIngredient(
        ingredient_id=uuid4(),
        text=text,
        ingredient_type=ingredient_type,
        embedding=embedding,
        usage_count=1,
    )
    corpus.add_ingredient(ingredient)
    logger.debug("Created new ingredient %s: %s", ingredient.ingredient_id, text[:60])
    return ingredient


def ingredient_reuse_stats(corpus: SandwichCorpus) -> dict:
    """Compute ingredient reuse statistics for the corpus.

    Returns:
        Dictionary with reuse metrics:
        - total_ingredients: Total unique ingredients tracked.
        - total_usages: Sum of all usage counts.
        - reuse_ratio: Average usage count per ingredient.
        - most_reused: The most-reused ingredient text (or None).
    """
    if not corpus.ingredients:
        return {
            "total_ingredients": 0,
            "total_usages": 0,
            "reuse_ratio": 0.0,
            "most_reused": None,
        }

    total_usages = sum(ing.usage_count for ing in corpus.ingredients)
    most_reused = max(corpus.ingredients, key=lambda i: i.usage_count)

    return {
        "total_ingredients": len(corpus.ingredients),
        "total_usages": total_usages,
        "reuse_ratio": total_usages / len(corpus.ingredients),
        "most_reused": most_reused.text,
    }
