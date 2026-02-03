"""Sandwich corpus – in-memory view of existing sandwiches for pipeline decisions.

Provides embedding similarity, type frequency, and ingredient lookups
without requiring direct DB queries from pipeline components.

Reference: PROMPTS.md Prompt 7
"""

import logging
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass
class CorpusIngredient:
    """A tracked ingredient in the corpus."""

    ingredient_id: UUID
    text: str
    ingredient_type: str  # 'bread' or 'filling'
    embedding: Optional[list[float]] = None
    usage_count: int = 1


@dataclass
class SandwichCorpus:
    """In-memory corpus of existing sandwiches for pipeline decisions.

    This is a lightweight abstraction that can be populated from the database
    or constructed manually for testing.
    """

    embeddings: list[list[float]] = field(default_factory=list)
    type_counts: dict[str, int] = field(default_factory=dict)
    ingredients: list[CorpusIngredient] = field(default_factory=list)
    total_sandwiches: int = 0

    def is_empty(self) -> bool:
        """Whether the corpus has any sandwiches."""
        return self.total_sandwiches == 0

    def get_all_embeddings(self) -> list[list[float]]:
        """Return all sandwich embeddings."""
        return self.embeddings

    def max_similarity(self, embedding: list[float]) -> float:
        """Return the maximum cosine similarity to any existing sandwich.

        Returns 0.0 if the corpus is empty.
        """
        if not self.embeddings:
            return 0.0
        return max(
            _cosine_similarity(embedding, corpus_emb)
            for corpus_emb in self.embeddings
        )

    def get_type_frequencies(self) -> dict[str, float]:
        """Return structure type frequencies as ratios (0-1).

        Returns empty dict if corpus is empty.
        """
        if self.total_sandwiches == 0:
            return {}
        return {
            t: count / self.total_sandwiches
            for t, count in self.type_counts.items()
        }

    def find_matching_ingredient(
        self,
        text: str,
        ingredient_type: str,
        embedding: Optional[list[float]] = None,
        similarity_threshold: float = 0.92,
    ) -> Optional[CorpusIngredient]:
        """Find an existing ingredient by exact text or embedding similarity.

        Args:
            text: The ingredient text.
            ingredient_type: 'bread' or 'filling'.
            embedding: Optional embedding for fuzzy matching.
            similarity_threshold: Cosine similarity threshold for fuzzy match.

        Returns:
            Matching CorpusIngredient or None.
        """
        text_lower = text.strip().lower()

        # Exact text match first
        for ing in self.ingredients:
            if ing.ingredient_type == ingredient_type and ing.text.strip().lower() == text_lower:
                return ing

        # Fuzzy embedding match
        if embedding is not None:
            best_match: Optional[CorpusIngredient] = None
            best_sim = 0.0
            for ing in self.ingredients:
                if ing.ingredient_type == ingredient_type and ing.embedding is not None:
                    sim = _cosine_similarity(embedding, ing.embedding)
                    if sim > best_sim:
                        best_sim = sim
                        best_match = ing
            if best_match and best_sim >= similarity_threshold:
                return best_match

        return None

    def add_sandwich(
        self,
        embedding: list[float],
        structure_type: str,
    ) -> None:
        """Record a new sandwich in the corpus."""
        self.embeddings.append(embedding)
        self.type_counts[structure_type] = self.type_counts.get(structure_type, 0) + 1
        self.total_sandwiches += 1

    def add_ingredient(self, ingredient: CorpusIngredient) -> None:
        """Add an ingredient to the corpus tracking."""
        self.ingredients.append(ingredient)
