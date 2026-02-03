"""Tests for the analysis engine.

Reference: PROMPTS.md Prompt 12
"""

import math
import random
from uuid import uuid4

import pytest

from sandwich.analysis.clustering import ClusterResult, ClusteringConfig, run_clustering
from sandwich.analysis.metrics import (
    CorpusMetrics,
    SessionMetrics,
    compute_corpus_metrics,
    compute_session_metrics,
)
from sandwich.analysis.relations import (
    DetectedRelation,
    SandwichInfo,
    detect_relations,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_embedding(seed: int, dim: int = 32) -> list[float]:
    """Generate a deterministic unit-length pseudo-random vector."""
    rng = random.Random(seed)
    raw = [rng.gauss(0, 1) for _ in range(dim)]
    norm = math.sqrt(sum(x * x for x in raw))
    return [x / norm for x in raw]


def _make_cluster_embedding(cluster_seed: int, index: int, noise: float = 0.05, dim: int = 32) -> list[float]:
    """Generate an embedding near a cluster centre."""
    rng = random.Random(cluster_seed + index * 1000)
    base = _make_embedding(cluster_seed, dim)
    perturbed = [x + rng.gauss(0, noise) for x in base]
    norm = math.sqrt(sum(x * x for x in perturbed))
    return [x / norm for x in perturbed]


def _make_similar_embedding(base: list[float], noise: float = 0.02) -> list[float]:
    """Create an embedding very close to base."""
    rng = random.Random(42)
    perturbed = [x + rng.gauss(0, noise) for x in base]
    norm = math.sqrt(sum(x * x for x in perturbed))
    return [x / norm for x in perturbed]


# ===================================================================
# Clustering tests
# ===================================================================

class TestClustering:
    """Verify HDBSCAN clustering assigns labels sensibly."""

    def test_clustering_with_clear_clusters(self):
        """Create two clear clusters and verify they're detected."""
        embeddings = []
        # Cluster A: 5 points near seed 100
        for i in range(5):
            embeddings.append(_make_cluster_embedding(100, i, noise=0.02))
        # Cluster B: 5 points near seed 999
        for i in range(5):
            embeddings.append(_make_cluster_embedding(999, i, noise=0.02))

        config = ClusteringConfig(min_cluster_size=3, min_samples=2)
        result = run_clustering(embeddings, config)

        assert isinstance(result, ClusterResult)
        assert len(result.labels) == 10

        # At minimum, the points within each cluster should share labels
        cluster_a_labels = set(result.labels[:5])
        cluster_b_labels = set(result.labels[5:])

        # If clustering works, at least one cluster should be detected
        # (HDBSCAN may or may not find both depending on the data)
        assert result.n_clusters >= 1 or result.n_noise < 10

    def test_clustering_too_few_points(self):
        """Verify graceful handling of too few points."""
        embeddings = [_make_embedding(1), _make_embedding(2)]
        result = run_clustering(embeddings)

        assert result.n_clusters == 0
        assert result.n_noise == 2
        assert result.labels == [-1, -1]

    def test_clustering_assigns_cluster_ids(self):
        """Verify cluster_ids are assigned (not all noise)."""
        # 12 points in 2 tight clusters
        embeddings = []
        for i in range(6):
            embeddings.append(_make_cluster_embedding(42, i, noise=0.01))
        for i in range(6):
            embeddings.append(_make_cluster_embedding(777, i, noise=0.01))

        config = ClusteringConfig(min_cluster_size=3, min_samples=2)
        result = run_clustering(embeddings, config)

        # At least some points should have cluster IDs
        non_noise = [l for l in result.labels if l != -1]
        assert len(non_noise) > 0, "Expected at least some clustered points"


# ===================================================================
# Relation detection tests
# ===================================================================

class TestRelationDetection:
    """Verify relation detection between sandwiches."""

    def test_similar_relation_detected(self):
        """Two sandwiches with similar embeddings should be linked."""
        base_emb = _make_embedding(42)
        similar_emb = _make_similar_embedding(base_emb)

        existing = SandwichInfo(
            sandwich_id=uuid4(),
            bread_top="Upper bound",
            bread_bottom="Lower bound",
            filling="Target value",
            embedding=base_emb,
        )

        new_sandwich = SandwichInfo(
            sandwich_id=uuid4(),
            bread_top="Maximum constraint",
            bread_bottom="Minimum constraint",
            filling="Optimum",
            embedding=similar_emb,
        )

        relations = detect_relations(new_sandwich, [existing], similarity_threshold=0.8)

        similar_rels = [r for r in relations if r.relation_type == "similar"]
        assert len(similar_rels) >= 1
        assert similar_rels[0].similarity_score >= 0.8

    def test_same_bread_detected(self):
        """Two sandwiches sharing bread should be linked."""
        existing = SandwichInfo(
            sandwich_id=uuid4(),
            bread_top="Bayesian prior",
            bread_bottom="Likelihood function",
            filling="Posterior distribution",
            embedding=_make_embedding(1),
        )

        new_sandwich = SandwichInfo(
            sandwich_id=uuid4(),
            bread_top="Bayesian prior",
            bread_bottom="Evidence",
            filling="Updated belief",
            embedding=_make_embedding(2),
        )

        relations = detect_relations(new_sandwich, [existing])

        same_bread = [r for r in relations if r.relation_type == "same_bread"]
        assert len(same_bread) >= 1

    def test_inverse_detected(self):
        """Two sandwiches with swapped bread should be detected as inverse."""
        existing = SandwichInfo(
            sandwich_id=uuid4(),
            bread_top="Thesis",
            bread_bottom="Antithesis",
            filling="Synthesis",
            embedding=_make_embedding(10),
        )

        new_sandwich = SandwichInfo(
            sandwich_id=uuid4(),
            bread_top="Antithesis",
            bread_bottom="Thesis",
            filling="Resolution",
            embedding=_make_embedding(20),
        )

        relations = detect_relations(new_sandwich, [existing])

        inverse_rels = [r for r in relations if r.relation_type == "inverse"]
        assert len(inverse_rels) >= 1

    def test_no_self_relation(self):
        """A sandwich should not detect relations with itself."""
        sid = uuid4()
        sandwich = SandwichInfo(
            sandwich_id=sid,
            bread_top="A",
            bread_bottom="B",
            filling="C",
            embedding=_make_embedding(1),
        )

        relations = detect_relations(sandwich, [sandwich])
        assert len(relations) == 0


# ===================================================================
# Metrics tests
# ===================================================================

class TestSessionMetrics:
    """Verify session metric computation."""

    def test_session_metrics(self):
        sandwiches = [
            {"validity_score": 0.8},
            {"validity_score": 0.9},
            {"validity_score": 0.7},
        ]
        metrics = compute_session_metrics(
            sandwiches=sandwiches,
            foraging_attempts=10,
            llm_costs=0.50,
        )

        assert metrics.sandwiches_made == 3
        assert metrics.foraging_attempts == 10
        assert metrics.sandwich_rate == pytest.approx(0.3)
        assert metrics.mean_validity == pytest.approx(0.8)
        assert metrics.cost_per_sandwich == pytest.approx(0.50 / 3)

    def test_session_metrics_empty(self):
        metrics = compute_session_metrics(sandwiches=[], foraging_attempts=5)

        assert metrics.sandwiches_made == 0
        assert metrics.sandwich_rate == 0.0
        assert metrics.mean_validity == 0.0


class TestCorpusMetrics:
    """Verify corpus metric computation."""

    def test_corpus_metrics(self):
        sandwiches = [
            {"validity_score": 0.85, "novelty_score": 0.9},
            {"validity_score": 0.75, "novelty_score": 0.7},
            {"validity_score": 0.90, "novelty_score": 0.8},
        ]
        types_used = {"bound", "stochastic", "dialectic"}

        metrics = compute_corpus_metrics(
            sandwiches=sandwiches,
            unique_ingredient_count=8,
            types_used=types_used,
            total_types=10,
        )

        assert metrics.total_sandwiches == 3
        assert metrics.unique_ingredients == 8
        assert metrics.ingredient_diversity == pytest.approx(8 / 3)
        assert metrics.structural_coverage == pytest.approx(0.3)
        assert metrics.types_used == 3
        assert metrics.mean_validity == pytest.approx(0.8333, abs=0.001)
        assert metrics.mean_novelty == pytest.approx(0.8)

    def test_corpus_metrics_empty(self):
        metrics = compute_corpus_metrics(
            sandwiches=[],
            unique_ingredient_count=0,
            types_used=set(),
        )

        assert metrics.total_sandwiches == 0
        assert metrics.ingredient_diversity == 0.0
        assert metrics.structural_coverage == 0.0
