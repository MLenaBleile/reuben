"""Tests for the identifier and selector modules.

Reference: PROMPTS.md Prompt 5
"""

import json
import math
import random
import textwrap
from unittest.mock import AsyncMock

import pytest

from sandwich.agent.identifier import (
    CandidateStructure,
    IdentificationResult,
    identify_ingredients,
    _parse_candidate,
)
from sandwich.agent.selector import (
    SelectionConfig,
    SelectedCandidate,
    select_candidate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_llm(response_json: dict) -> AsyncMock:
    """Create a mock SandwichLLM that returns the given JSON as a string."""
    llm = AsyncMock()
    llm.identify_ingredients = AsyncMock(return_value=json.dumps(response_json))
    llm.raw_call = AsyncMock(return_value=json.dumps(response_json))
    return llm


def _make_embedding(seed: int, dim: int = 32) -> list[float]:
    """Generate a deterministic unit-length pseudo-random vector."""
    rng = random.Random(seed)
    raw = [rng.gauss(0, 1) for _ in range(dim)]
    norm = math.sqrt(sum(x * x for x in raw))
    return [x / norm for x in raw]


def _make_similar_embedding(base: list[float], noise: float = 0.05) -> list[float]:
    """Create an embedding close to `base` by adding small noise."""
    rng = random.Random(42)
    perturbed = [x + rng.gauss(0, noise) for x in base]
    norm = math.sqrt(sum(x * x for x in perturbed))
    return [x / norm for x in perturbed]


SQUEEZE_THEOREM_CONTENT = textwrap.dedent("""\
    The squeeze theorem, also known as the sandwich theorem, is a fundamental
    result in mathematical analysis. It provides a method for evaluating the
    limit of a function by bounding it between two other functions whose limits
    are already known.

    Formally, suppose that for all x in some interval containing c (except
    possibly at c itself), we have g(x) <= f(x) <= h(x). If both g(x) and h(x)
    approach the same limit L as x approaches c, then f(x) must also approach L.

    This theorem is particularly useful in situations where direct computation of
    a limit is difficult or impossible. For example, consider the well-known limit
    of sin(x)/x as x approaches 0. By establishing appropriate upper and lower
    bounds using geometric arguments on the unit circle, we can show that this
    limit equals 1.

    The applications of the squeeze theorem extend beyond elementary calculus.
    In real analysis, it plays a crucial role in proving the convergence of
    sequences and series.
""")

RECIPE_CONTENT = textwrap.dedent("""\
    Classic Sourdough Bread Recipe

    This recipe takes approximately 24 hours from start to finish. Begin by
    mixing 500g of bread flour with 350g of water and 100g of active sourdough
    starter. Add 10g of salt and mix until a shaggy dough forms.

    The bulk fermentation phase lasts 4-6 hours at room temperature. During this
    time, perform a series of stretch and folds every 30 minutes for the first
    2 hours. The dough should increase in volume by roughly 50% and show signs
    of aeration.

    After bulk fermentation, shape the dough into a round or oval loaf. Place it
    in a banneton basket and refrigerate overnight for 12-16 hours. This cold
    retard develops flavor and makes scoring easier.

    The next morning, preheat your oven to 500F with a Dutch oven inside. Score
    the dough with a sharp blade, transfer it to the hot Dutch oven, and bake
    covered for 20 minutes. Remove the lid and continue baking at 450F for
    another 20-25 minutes until deeply golden brown.

    The internal temperature should reach at least 205F. Let the loaf cool
    completely on a wire rack before slicing, about 1-2 hours.
""")

GIBBERISH_CONTENT = textwrap.dedent("""\
    Flurp zazzle bimtop quorx fleen drabble snix wompus glarb. Tizzle
    frax nebulon sklort wimple doof. Grazzle plink snorf tooble baxen
    frizzle quonk spleem. Nux wibble draxon floop gumtree bazzle spork
    crumble ziff. Blonx trazzle fweep gumption snarfle wimzee drool
    plonk nixie gloob.

    Skizzle frump glarb tozzle breen waxle droof. Plim snazzle gorbix
    fleent troozle baxon gleep. Wumble frizzox glarb plonk treez snaff
    bix droon gumtop fleeze.
""")


# ===================================================================
# Identifier tests
# ===================================================================

class TestSqueezeTheoremIdentification:
    """Verify identifier finds bound-type structure in squeeze theorem content."""

    @pytest.mark.asyncio
    async def test_squeeze_theorem_identification(self):
        response = {
            "candidates": [
                {
                    "bread_top": "Upper bound function g(x) where g(x) >= f(x)",
                    "bread_bottom": "Lower bound function h(x) where h(x) <= f(x)",
                    "filling": "Target function f(x) whose limit we seek",
                    "structure_type": "bound",
                    "confidence": 0.95,
                    "rationale": "The squeeze theorem is a perfect sandwich: f(x) is bounded above and below.",
                }
            ],
            "no_sandwich_reason": None,
        }
        llm = _make_mock_llm(response)

        result = await identify_ingredients(SQUEEZE_THEOREM_CONTENT, llm)

        assert len(result.candidates) >= 1
        assert result.no_sandwich_reason is None

        # At least one candidate should be a bound type
        bound_candidates = [
            c for c in result.candidates if c.structure_type == "bound"
        ]
        assert len(bound_candidates) >= 1
        assert bound_candidates[0].confidence > 0.7


class TestRecipeIdentification:
    """Verify identifier finds structure in a cooking recipe."""

    @pytest.mark.asyncio
    async def test_recipe_identification(self):
        response = {
            "candidates": [
                {
                    "bread_top": "Raw ingredients (flour, water, starter)",
                    "bread_bottom": "Finished golden loaf at 205F internal temperature",
                    "filling": "The fermentation and transformation process",
                    "structure_type": "temporal",
                    "confidence": 0.80,
                    "rationale": "The bread-making process is bounded by start and end states.",
                },
                {
                    "bread_top": "Minimum baking temperature (450F)",
                    "bread_bottom": "Maximum baking temperature (500F)",
                    "filling": "Optimal baking conditions for crust development",
                    "structure_type": "bound",
                    "confidence": 0.60,
                    "rationale": "Temperature constraints bound the baking process.",
                },
            ],
            "no_sandwich_reason": None,
        }
        llm = _make_mock_llm(response)

        result = await identify_ingredients(RECIPE_CONTENT, llm)

        assert len(result.candidates) >= 1
        assert result.no_sandwich_reason is None

        # Should find temporal or bound structure
        types = {c.structure_type for c in result.candidates}
        assert types & {"temporal", "bound"}


class TestGibberishNoCandidates:
    """Verify identifier returns no candidates for gibberish."""

    @pytest.mark.asyncio
    async def test_gibberish_no_candidates(self):
        response = {
            "candidates": [],
            "no_sandwich_reason": "All filling, no structure. A soup of nonsense words. I make sandwiches, not word salad.",
        }
        llm = _make_mock_llm(response)

        result = await identify_ingredients(GIBBERISH_CONTENT, llm)

        assert len(result.candidates) == 0
        assert result.no_sandwich_reason is not None
        assert len(result.no_sandwich_reason) > 0


# ===================================================================
# Candidate parsing tests
# ===================================================================

class TestCandidateParsing:
    """Verify _parse_candidate handles edge cases."""

    def test_valid_candidate(self):
        raw = {
            "bread_top": "Upper bound",
            "bread_bottom": "Lower bound",
            "filling": "Target",
            "structure_type": "bound",
            "confidence": 0.9,
            "rationale": "Good structure",
        }
        cand = _parse_candidate(raw)
        assert cand is not None
        assert cand.bread_top == "Upper bound"
        assert cand.confidence == 0.9

    def test_missing_bread_returns_none(self):
        raw = {
            "bread_top": "",
            "bread_bottom": "Lower bound",
            "filling": "Target",
        }
        assert _parse_candidate(raw) is None

    def test_confidence_clamped(self):
        raw = {
            "bread_top": "A",
            "bread_bottom": "B",
            "filling": "C",
            "confidence": 1.5,
        }
        cand = _parse_candidate(raw)
        assert cand is not None
        assert cand.confidence == 1.0

    def test_confidence_clamped_negative(self):
        raw = {
            "bread_top": "A",
            "bread_bottom": "B",
            "filling": "C",
            "confidence": -0.5,
        }
        cand = _parse_candidate(raw)
        assert cand is not None
        assert cand.confidence == 0.0


# ===================================================================
# Selector tests
# ===================================================================

class TestSelectorRanking:
    """Verify selector picks highest-confidence candidate with empty corpus."""

    def test_selector_ranking(self):
        candidates = [
            CandidateStructure(
                bread_top="A", bread_bottom="B", filling="C",
                structure_type="bound", confidence=0.6, rationale="ok",
            ),
            CandidateStructure(
                bread_top="D", bread_bottom="E", filling="F",
                structure_type="temporal", confidence=0.9, rationale="great",
            ),
            CandidateStructure(
                bread_top="G", bread_bottom="H", filling="I",
                structure_type="dialectic", confidence=0.7, rationale="good",
            ),
        ]

        result = select_candidate(candidates)

        assert result is not None
        # With empty corpus, novelty and diversity bonuses are equal (1.0 each),
        # so highest confidence should win
        assert result.candidate.confidence == 0.9
        assert result.candidate.structure_type == "temporal"


class TestSelectorNoveltyBonus:
    """Verify novel candidate can beat higher-confidence similar candidate."""

    def test_selector_novelty_bonus(self):
        # Candidate A: high confidence but similar to corpus
        # Candidate B: lower confidence but novel
        cand_a = CandidateStructure(
            bread_top="Prior distribution",
            bread_bottom="Likelihood function",
            filling="Posterior distribution",
            structure_type="stochastic",
            confidence=0.85,
            rationale="Bayesian",
        )
        cand_b = CandidateStructure(
            bread_top="Opening position A",
            bread_bottom="Opening position B",
            filling="Compromise agreement",
            structure_type="negotiation",
            confidence=0.70,
            rationale="Diplomatic",
        )
        candidates = [cand_a, cand_b]

        # Corpus has one embedding very similar to candidate A
        corpus_base = _make_embedding(seed=100)
        corpus_embeddings = [corpus_base]

        # Candidate A embedding is very similar to corpus
        emb_a = _make_similar_embedding(corpus_base, noise=0.01)
        # Candidate B embedding is very different
        emb_b = _make_embedding(seed=999)
        candidate_embeddings = [emb_a, emb_b]

        # Use high novelty weight to ensure novel candidate wins
        cfg = SelectionConfig(
            min_confidence=0.4,
            novelty_weight=0.5,
            diversity_weight=0.0,
        )

        result = select_candidate(
            candidates,
            corpus_embeddings=corpus_embeddings,
            candidate_embeddings=candidate_embeddings,
            config=cfg,
        )

        assert result is not None
        # The novel candidate (B) should win despite lower confidence
        assert result.candidate.structure_type == "negotiation"
        assert result.novelty_bonus > 0.5


class TestSelectorThreshold:
    """Verify selector returns None when all candidates below min_confidence."""

    def test_selector_threshold(self):
        candidates = [
            CandidateStructure(
                bread_top="A", bread_bottom="B", filling="C",
                structure_type="bound", confidence=0.2, rationale="weak",
            ),
            CandidateStructure(
                bread_top="D", bread_bottom="E", filling="F",
                structure_type="temporal", confidence=0.3, rationale="poor",
            ),
        ]

        cfg = SelectionConfig(min_confidence=0.5)
        result = select_candidate(candidates, config=cfg)

        assert result is None


class TestSelectorDiversityBonus:
    """Verify diversity bonus favours underrepresented types."""

    def test_diversity_bonus_favours_rare_type(self):
        # Two candidates with same confidence
        cand_common = CandidateStructure(
            bread_top="A", bread_bottom="B", filling="C",
            structure_type="bound", confidence=0.7, rationale="common",
        )
        cand_rare = CandidateStructure(
            bread_top="D", bread_bottom="E", filling="F",
            structure_type="perspectival", confidence=0.7, rationale="rare",
        )
        candidates = [cand_common, cand_rare]

        type_frequencies = {
            "bound": 0.8,        # very common
            "perspectival": 0.1,  # rare
        }

        cfg = SelectionConfig(
            min_confidence=0.4,
            novelty_weight=0.0,
            diversity_weight=0.5,
        )

        result = select_candidate(
            candidates,
            type_frequencies=type_frequencies,
            config=cfg,
        )

        assert result is not None
        assert result.candidate.structure_type == "perspectival"
        assert result.diversity_bonus > 0.5


class TestSelectorEmptyCandidates:
    """Verify selector handles empty candidate list."""

    def test_empty_candidates(self):
        result = select_candidate([])
        assert result is None
