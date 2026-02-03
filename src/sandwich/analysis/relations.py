"""Sandwich relation detection.

Finds and categorises relations between sandwiches:
- similar: high embedding similarity
- same_bread: shared bread ingredient text
- inverse: bread elements swapped

Reference: SPEC.md Section 10.2; PROMPTS.md Prompt 12
"""

import logging
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


@dataclass
class DetectedRelation:
    """A detected relation between two sandwiches."""

    relation_id: UUID = field(default_factory=uuid4)
    sandwich_a_id: UUID = field(default_factory=uuid4)
    sandwich_b_id: UUID = field(default_factory=uuid4)
    relation_type: str = "similar"
    similarity_score: float = 0.0
    rationale: str = ""


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass
class SandwichInfo:
    """Minimal sandwich info needed for relation detection."""

    sandwich_id: UUID
    bread_top: str
    bread_bottom: str
    filling: str
    embedding: list[float]


def detect_relations(
    new_sandwich: SandwichInfo,
    corpus: list[SandwichInfo],
    similarity_threshold: float = 0.8,
) -> list[DetectedRelation]:
    """Detect relations between a new sandwich and the existing corpus.

    Checks for:
      - similar: embedding cosine similarity > threshold
      - same_bread: either bread text matches exactly
      - inverse: bread_top/bread_bottom are swapped

    Args:
        new_sandwich: The newly created sandwich.
        corpus: Existing sandwiches to compare against.
        similarity_threshold: Cosine similarity threshold for 'similar' relation.

    Returns:
        List of detected relations.
    """
    relations: list[DetectedRelation] = []

    new_top = new_sandwich.bread_top.strip().lower()
    new_bottom = new_sandwich.bread_bottom.strip().lower()

    for existing in corpus:
        if existing.sandwich_id == new_sandwich.sandwich_id:
            continue

        ex_top = existing.bread_top.strip().lower()
        ex_bottom = existing.bread_bottom.strip().lower()

        # --- Similar ---
        sim = _cosine_similarity(new_sandwich.embedding, existing.embedding)
        if sim >= similarity_threshold:
            relations.append(DetectedRelation(
                sandwich_a_id=new_sandwich.sandwich_id,
                sandwich_b_id=existing.sandwich_id,
                relation_type="similar",
                similarity_score=sim,
                rationale=f"Embedding similarity {sim:.3f} >= {similarity_threshold}",
            ))

        # --- Same bread ---
        if (new_top == ex_top or new_top == ex_bottom
                or new_bottom == ex_top or new_bottom == ex_bottom):
            relations.append(DetectedRelation(
                sandwich_a_id=new_sandwich.sandwich_id,
                sandwich_b_id=existing.sandwich_id,
                relation_type="same_bread",
                similarity_score=sim,
                rationale="Shared bread concept",
            ))

        # --- Inverse ---
        if new_top == ex_bottom and new_bottom == ex_top:
            relations.append(DetectedRelation(
                sandwich_a_id=new_sandwich.sandwich_id,
                sandwich_b_id=existing.sandwich_id,
                relation_type="inverse",
                similarity_score=sim,
                rationale="Bread elements swapped",
            ))

    logger.info(
        "Detected %d relation(s) for sandwich %s",
        len(relations),
        new_sandwich.sandwich_id,
    )

    return relations
