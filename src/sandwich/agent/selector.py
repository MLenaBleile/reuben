"""Candidate selector – picks the best sandwich candidate from identification results.

Scores candidates based on confidence, novelty relative to the existing corpus,
and diversity of structural types.

Reference: SPEC.md Section 3.2.4; PROMPTS.md Prompt 5
"""

import logging
from dataclasses import dataclass
from typing import Optional

from sandwich.agent.identifier import CandidateStructure

logger = logging.getLogger(__name__)


@dataclass
class SelectionConfig:
    """Tuneable parameters for candidate selection."""

    min_confidence: float = 0.4
    novelty_weight: float = 0.3
    diversity_weight: float = 0.2


@dataclass
class SelectedCandidate:
    """A candidate selected for assembly."""

    candidate: CandidateStructure
    final_score: float
    novelty_bonus: float
    diversity_bonus: float
    rationale: str


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def select_candidate(
    candidates: list[CandidateStructure],
    *,
    corpus_embeddings: Optional[list[list[float]]] = None,
    candidate_embeddings: Optional[list[list[float]]] = None,
    type_frequencies: Optional[dict[str, float]] = None,
    config: Optional[SelectionConfig] = None,
) -> Optional[SelectedCandidate]:
    """Select the best candidate for assembly.

    Scoring formula per candidate:
        final_score = confidence + novelty_weight * novelty_bonus + diversity_weight * diversity_bonus

    Args:
        candidates: Candidate structures from the identifier.
        corpus_embeddings: Existing sandwich embeddings for novelty computation.
            If None or empty, novelty bonus is 1.0 for all candidates.
        candidate_embeddings: Embeddings for each candidate (parallel to candidates list).
            Required for novelty computation when corpus_embeddings is provided.
            Each embedding represents the candidate's overall concept.
        type_frequencies: Map of structure_type → frequency ratio (0-1).
            Used for diversity bonus. If None, diversity bonus is 1.0.
        config: Selection configuration.

    Returns:
        SelectedCandidate with the highest final_score, or None if no candidates
        pass the minimum confidence threshold.
    """
    cfg = config or SelectionConfig()

    if not candidates:
        return None

    # Filter by minimum confidence
    viable = [c for c in candidates if c.confidence >= cfg.min_confidence]
    if not viable:
        logger.info(
            "All %d candidates below min_confidence=%.2f",
            len(candidates),
            cfg.min_confidence,
        )
        return None

    best: Optional[SelectedCandidate] = None

    for i, cand in enumerate(viable):
        # --- Novelty bonus ---
        if corpus_embeddings and candidate_embeddings:
            # Find the candidate's index in the original list
            orig_idx = candidates.index(cand)
            if orig_idx < len(candidate_embeddings):
                cand_emb = candidate_embeddings[orig_idx]
                max_sim = max(
                    _cosine_similarity(cand_emb, corpus_emb)
                    for corpus_emb in corpus_embeddings
                )
                novelty_bonus = 1.0 - max_sim
                novelty_bonus = max(0.0, min(1.0, novelty_bonus))
            else:
                novelty_bonus = 1.0
        else:
            novelty_bonus = 1.0

        # --- Diversity bonus ---
        if type_frequencies and cand.structure_type in type_frequencies:
            # Less common types get higher bonus
            freq = type_frequencies[cand.structure_type]
            diversity_bonus = 1.0 - freq
            diversity_bonus = max(0.0, min(1.0, diversity_bonus))
        else:
            # Unknown type or no frequency data → maximum diversity bonus
            diversity_bonus = 1.0

        # --- Final score ---
        final_score = (
            cand.confidence
            + cfg.novelty_weight * novelty_bonus
            + cfg.diversity_weight * diversity_bonus
        )

        rationale = (
            f"confidence={cand.confidence:.2f}, "
            f"novelty_bonus={novelty_bonus:.2f} (w={cfg.novelty_weight}), "
            f"diversity_bonus={diversity_bonus:.2f} (w={cfg.diversity_weight}), "
            f"final={final_score:.3f}"
        )

        logger.debug(
            "Candidate '%s/%s': %s",
            cand.bread_top[:30],
            cand.filling[:30],
            rationale,
        )

        if best is None or final_score > best.final_score:
            best = SelectedCandidate(
                candidate=cand,
                final_score=final_score,
                novelty_bonus=novelty_bonus,
                diversity_bonus=diversity_bonus,
                rationale=rationale,
            )

    if best:
        logger.info(
            "Selected candidate: type=%s, %s",
            best.candidate.structure_type,
            best.rationale,
        )

    return best
