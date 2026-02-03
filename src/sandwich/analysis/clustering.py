"""Sandwich clustering – groups sandwiches by embedding similarity.

Uses HDBSCAN for density-based clustering on sandwich embeddings.

Reference: SPEC.md Section 10.1; PROMPTS.md Prompt 12
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ClusteringConfig:
    """Configuration for sandwich clustering."""

    min_cluster_size: int = 3
    min_samples: int = 2
    metric: str = "euclidean"


@dataclass
class ClusterResult:
    """Result of a clustering run."""

    labels: list[int]  # Cluster label per sandwich (-1 = noise)
    n_clusters: int
    n_noise: int
    cluster_sizes: dict[int, int] = field(default_factory=dict)


def run_clustering(
    embeddings: list[list[float]],
    config: Optional[ClusteringConfig] = None,
) -> ClusterResult:
    """Cluster sandwiches by embedding similarity using HDBSCAN.

    Args:
        embeddings: List of sandwich embedding vectors.
        config: Clustering configuration.

    Returns:
        ClusterResult with labels and statistics.
    """
    cfg = config or ClusteringConfig()

    if len(embeddings) < cfg.min_cluster_size:
        logger.info(
            "Too few sandwiches (%d) for clustering (need >= %d)",
            len(embeddings),
            cfg.min_cluster_size,
        )
        return ClusterResult(
            labels=[-1] * len(embeddings),
            n_clusters=0,
            n_noise=len(embeddings),
        )

    import hdbscan

    data = np.array(embeddings)

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=cfg.min_cluster_size,
        min_samples=cfg.min_samples,
        metric=cfg.metric,
    )
    labels = clusterer.fit_predict(data).tolist()

    unique_labels = set(labels)
    n_clusters = len(unique_labels - {-1})
    n_noise = labels.count(-1)

    cluster_sizes = {}
    for label in unique_labels:
        if label != -1:
            cluster_sizes[label] = labels.count(label)

    logger.info(
        "Clustering: %d clusters, %d noise points from %d sandwiches",
        n_clusters,
        n_noise,
        len(embeddings),
    )

    return ClusterResult(
        labels=labels,
        n_clusters=n_clusters,
        n_noise=n_noise,
        cluster_sizes=cluster_sizes,
    )
