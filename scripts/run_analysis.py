#!/usr/bin/env python3
"""Run corpus analysis – clustering, relation detection, and metrics.

Can be executed as a one-shot script or scheduled as a cron job.

Usage:
    python scripts/run_analysis.py [--min-cluster-size N] [--similarity-threshold T]

Reference: PROMPTS.md Prompt 12
"""

import argparse
import logging
import sys

from sandwich.analysis.clustering import ClusteringConfig, run_clustering
from sandwich.analysis.ingredients import ingredient_reuse_stats
from sandwich.analysis.metrics import compute_corpus_metrics
from sandwich.analysis.relations import SandwichInfo, detect_relations
from sandwich.db.corpus import SandwichCorpus

logger = logging.getLogger("sandwich.analysis")


def _print_section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def run(
    corpus: SandwichCorpus,
    sandwich_infos: list[SandwichInfo],
    min_cluster_size: int = 3,
    similarity_threshold: float = 0.8,
) -> None:
    """Run the full analysis pipeline on a corpus.

    Args:
        corpus: The populated SandwichCorpus.
        sandwich_infos: List of SandwichInfo for relation detection.
        min_cluster_size: Minimum cluster size for HDBSCAN.
        similarity_threshold: Cosine similarity threshold for relations.
    """
    # --- Clustering ---
    _print_section("Clustering")
    embeddings = corpus.get_all_embeddings()
    if len(embeddings) >= min_cluster_size:
        config = ClusteringConfig(min_cluster_size=min_cluster_size)
        result = run_clustering(embeddings, config)
        print(f"  Sandwiches:  {len(embeddings)}")
        print(f"  Clusters:    {result.n_clusters}")
        print(f"  Noise:       {result.n_noise}")
        for cid, size in sorted(result.cluster_sizes.items()):
            print(f"    Cluster {cid}: {size} sandwiches")
    else:
        print(f"  Too few sandwiches ({len(embeddings)}) for clustering.")

    # --- Relation Detection ---
    _print_section("Relation Detection")
    total_relations = 0
    for info in sandwich_infos:
        others = [s for s in sandwich_infos if s.sandwich_id != info.sandwich_id]
        relations = detect_relations(info, others, similarity_threshold=similarity_threshold)
        if relations:
            total_relations += len(relations)
            for rel in relations:
                print(f"  {rel.relation_type}: {rel.source_id} <-> {rel.target_id} "
                      f"(score={rel.similarity_score:.3f})")
    if total_relations == 0:
        print("  No relations detected.")
    else:
        print(f"  Total relations: {total_relations}")

    # --- Ingredient Reuse ---
    _print_section("Ingredient Reuse")
    stats = ingredient_reuse_stats(corpus)
    print(f"  Unique ingredients: {stats['total_ingredients']}")
    print(f"  Total usages:       {stats['total_usages']}")
    print(f"  Reuse ratio:        {stats['reuse_ratio']:.2f}")
    if stats["most_reused"]:
        print(f"  Most reused:        {stats['most_reused']}")

    # --- Corpus Metrics ---
    _print_section("Corpus Metrics")
    sandwiches_for_metrics = [
        {"validity_score": 0.0, "novelty_score": 0.0}
    ] * corpus.total_sandwiches  # placeholder scores
    types_used = set(corpus.type_counts.keys())
    metrics = compute_corpus_metrics(
        sandwiches=sandwiches_for_metrics,
        unique_ingredient_count=len(corpus.ingredients),
        types_used=types_used,
    )
    print(f"  Total sandwiches:       {metrics.total_sandwiches}")
    print(f"  Unique ingredients:     {metrics.unique_ingredients}")
    print(f"  Ingredient diversity:   {metrics.ingredient_diversity:.2f}")
    print(f"  Structural coverage:    {metrics.structural_coverage:.1%}")
    print(f"  Types used:             {metrics.types_used}")

    print(f"\n{'=' * 60}")
    print("  Analysis complete.")
    print(f"{'=' * 60}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SANDWICH corpus analysis")
    parser.add_argument(
        "--min-cluster-size", type=int, default=3,
        help="Minimum cluster size for HDBSCAN (default: 3)",
    )
    parser.add_argument(
        "--similarity-threshold", type=float, default=0.8,
        help="Cosine similarity threshold for relation detection (default: 0.8)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # In production this would load from the database.
    # For now, print a message indicating how to populate the corpus.
    print("SANDWICH Analysis Engine")
    print("-" * 40)
    print("Note: This script requires a populated corpus.")
    print("Run `python -m sandwich.main --max-sandwiches 20` first to generate sandwiches.")
    print("Then this script can be connected to the database for live analysis.")
    print()
    print("Running with empty corpus for demonstration...")

    corpus = SandwichCorpus()
    run(
        corpus=corpus,
        sandwich_infos=[],
        min_cluster_size=args.min_cluster_size,
        similarity_threshold=args.similarity_threshold,
    )


if __name__ == "__main__":
    main()
