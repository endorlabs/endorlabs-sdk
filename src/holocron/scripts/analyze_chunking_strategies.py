#!/usr/bin/env python3
"""
Analyze different chunking strategies for content optimization.
Tests various approaches to determine optimal chunking across content types.
"""

import json
import random
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from .generic_chunking_framework import (
    ChunkingMetrics,
    ChunkingStrategy,
    ChunkingStrategyFactory,
)

# ChunkingMetrics and ChunkingStrategy are now imported from generic_chunking_framework


class SectionBasedChunking(ChunkingStrategy):
    """Current strategy: chunk by top-level sections."""

    def __init__(self):
        super().__init__("Section-Based (Current)")

    def chunk(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        chunks = []
        for section_name, section_content in data.items():
            if isinstance(section_content, dict):
                chunk_text = json.dumps({section_name: section_content}, indent=2)
                chunks.append(
                    {
                        "text": chunk_text,
                        "size": len(chunk_text),
                        "section": section_name,
                        "type": "section",
                    }
                )
        return chunks


class EndpointBasedChunking(ChunkingStrategy):
    """Chunk by individual API endpoints."""

    def __init__(self):
        super().__init__("Endpoint-Based")

    def chunk(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        chunks = []
        paths = data.get("paths", {})

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method in ["get", "post", "put", "patch", "delete"]:
                    # Create chunk for each operation
                    operation_data = {
                        "path": path,
                        "method": method.upper(),
                        "operation": operation,
                    }
                    chunk_text = json.dumps(operation_data, indent=2)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "size": len(chunk_text),
                            "path": path,
                            "method": method.upper(),
                            "operation_id": operation.get("operationId", ""),
                            "type": "endpoint",
                        }
                    )

        return chunks


class ServiceBasedChunking(ChunkingStrategy):
    """Chunk by service groups (using tags)."""

    def __init__(self):
        super().__init__("Service-Based")

    def chunk(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        chunks = []
        paths = data.get("paths", {})
        # tags = data.get("tags", [])  # Not used

        # Group operations by service
        service_operations = defaultdict(list)

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method in ["get", "post", "put", "patch", "delete"]:
                    service_tags = operation.get("tags", [])
                    for tag in service_tags:
                        service_operations[tag].append(
                            {
                                "path": path,
                                "method": method.upper(),
                                "operation": operation,
                            }
                        )

        # Create chunks for each service
        for service, operations in service_operations.items():
            service_data = {"service": service, "operations": operations}
            chunk_text = json.dumps(service_data, indent=2)
            chunks.append(
                {
                    "text": chunk_text,
                    "size": len(chunk_text),
                    "service": service,
                    "operation_count": len(operations),
                    "type": "service",
                }
            )

        return chunks


class ResourceBasedChunking(ChunkingStrategy):
    """Chunk by resource type (extracted from paths)."""

    def __init__(self):
        super().__init__("Resource-Based")

    def chunk(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        chunks = []
        paths = data.get("paths", {})

        # Group operations by resource
        resource_operations = defaultdict(list)

        for path, path_item in paths.items():
            # Extract resource name from path
            resource_match = re.search(
                r"/v1/namespaces/\{tenant_meta\.namespace\}/([^/]+)", path
            )
            if not resource_match:
                resource_match = re.search(
                    r"/v1/namespaces/\{object\.tenant_meta\.namespace\}/([^/]+)", path
                )

            if resource_match:
                resource = resource_match.group(1)

                for method, operation in path_item.items():
                    if method in ["get", "post", "put", "patch", "delete"]:
                        resource_operations[resource].append(
                            {
                                "path": path,
                                "method": method.upper(),
                                "operation": operation,
                            }
                        )

        # Create chunks for each resource
        for resource, operations in resource_operations.items():
            resource_data = {"resource": resource, "operations": operations}
            chunk_text = json.dumps(resource_data, indent=2)
            chunks.append(
                {
                    "text": chunk_text,
                    "size": len(chunk_text),
                    "resource": resource,
                    "operation_count": len(operations),
                    "type": "resource",
                }
            )

        return chunks


class HybridChunking(ChunkingStrategy):
    """Hybrid approach: chunk by service but limit size."""

    def __init__(self, max_chunk_size: int = 50000):
        super().__init__("Hybrid (Service + Size Limit)")
        self.max_chunk_size = max_chunk_size

    def chunk(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        chunks = []
        paths = data.get("paths", {})

        # Group operations by service
        service_operations = defaultdict(list)

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method in ["get", "post", "put", "patch", "delete"]:
                    service_tags = operation.get("tags", [])
                    for tag in service_tags:
                        service_operations[tag].append(
                            {
                                "path": path,
                                "method": method.upper(),
                                "operation": operation,
                            }
                        )

        # Create chunks for each service, splitting if too large
        for service, operations in service_operations.items():
            service_data = {"service": service, "operations": operations}
            chunk_text = json.dumps(service_data, indent=2)

            if len(chunk_text) <= self.max_chunk_size:
                # Single chunk
                chunks.append(
                    {
                        "text": chunk_text,
                        "size": len(chunk_text),
                        "service": service,
                        "operation_count": len(operations),
                        "type": "service",
                    }
                )
            else:
                # Split into multiple chunks
                chunk_size = len(operations) // 2
                for i in range(0, len(operations), chunk_size):
                    chunk_operations = operations[i : i + chunk_size]
                    chunk_data = {
                        "service": service,
                        "operations": chunk_operations,
                        "chunk_part": f"{i // chunk_size + 1}",
                    }
                    chunk_text = json.dumps(chunk_data, indent=2)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "size": len(chunk_text),
                            "service": service,
                            "operation_count": len(chunk_operations),
                            "type": "service_chunk",
                        }
                    )

        return chunks


class MonteCarloChunkingOptimizer:
    """Monte Carlo optimizer for finding optimal chunking parameters."""

    def __init__(self, content: str, content_type: str):
        self.content = content
        self.content_type = content_type
        self.best_strategy = None
        self.best_score = -float("inf")
        self.optimization_history = []

    def evaluate_strategy(self, strategy: ChunkingStrategy) -> ChunkingMetrics:
        """Evaluate a chunking strategy and return metrics."""
        try:
            chunks = strategy.chunk(self.content)

            if not chunks:
                return ChunkingMetrics(0, 0, 0, 0, 0, 0, 0, 0)

            chunk_sizes = [chunk["size"] for chunk in chunks]
            total_size = sum(chunk_sizes)
            avg_size = np.mean(chunk_sizes)
            max_size = np.max(chunk_sizes)
            min_size = np.min(chunk_sizes)
            size_std = np.std(chunk_sizes)

            # Calculate searchable ratio (chunks < 100KB)
            searchable_chunks = sum(1 for size in chunk_sizes if size < 100000)
            searchable_ratio = searchable_chunks / len(chunks) if chunks else 0

            # Calculate size distribution score (lower is better)
            if min_size > 0:
                size_ratio = max_size / min_size
                size_distribution_score = 1.0 / (1.0 + size_ratio)  # Higher is better
            else:
                size_distribution_score = 0.0

            return ChunkingMetrics(
                chunk_count=len(chunks),
                avg_size=avg_size,
                max_size=max_size,
                min_size=min_size,
                size_std=size_std,
                searchable_ratio=searchable_ratio,
                size_distribution_score=size_distribution_score,
                total_size=total_size,
            )

        except Exception as e:
            print(f"Error evaluating strategy {strategy.name}: {e}")
            return ChunkingMetrics(0, 0, 0, 0, 0, 0, 0, 0)

    def calculate_strategy_score(self, metrics: ChunkingMetrics) -> float:
        """Calculate overall score for a chunking strategy."""
        # Multi-objective optimization
        score = 0.0

        # Prefer more chunks (better granularity) - but not too many
        chunk_score = min(metrics.chunk_count / 100, 1.0) * 20
        score += chunk_score

        # Prefer smaller average size (better searchability)
        if metrics.avg_size > 0:
            size_score = max(0, 1.0 - (metrics.avg_size / 200000)) * 30
            score += size_score

        # Penalize very large chunks heavily
        if metrics.max_size > 200000:
            penalty = (metrics.max_size - 200000) / 10000
            score -= penalty

        # Reward good size distribution
        score += metrics.size_distribution_score * 20

        # Reward high searchable ratio
        score += metrics.searchable_ratio * 30

        # Penalize too many very small chunks (fragmentation)
        if metrics.avg_size < 1000:
            fragmentation_penalty = (1000 - metrics.avg_size) / 1000 * 10
            score -= fragmentation_penalty

        return score

    def monte_carlo_optimization(self, n_iterations: int = 1000) -> Dict[str, Any]:
        """Run Monte Carlo optimization to find best chunking strategy."""
        print(f"🎲 Running Monte Carlo optimization ({n_iterations} iterations)...")

        # Get available strategies for this content type
        available_strategies = ChunkingStrategyFactory.get_available_strategies(
            self.content_type
        )
        parameter_ranges = ChunkingStrategyFactory.get_parameter_ranges(
            self.content_type, "hybrid"
        )

        strategies_to_test = []

        # Generate random parameter combinations
        for _ in range(n_iterations):
            strategy_type = random.choice(available_strategies)

            # Generate random parameters based on content type
            params = {}
            for param_name, (min_val, max_val) in parameter_ranges.items():
                params[param_name] = random.randint(min_val, max_val)

            strategy = ChunkingStrategyFactory.create_strategy(
                self.content_type, strategy_type, **params
            )
            strategies_to_test.append(strategy)

        print(f"Testing {len(strategies_to_test)} strategy variations...")

        best_strategies = []

        for i, strategy in enumerate(strategies_to_test):
            if i % 100 == 0:
                print(f"  Progress: {i}/{len(strategies_to_test)}")

            metrics = self.evaluate_strategy(strategy)
            score = self.calculate_strategy_score(metrics)

            self.optimization_history.append(
                {"strategy": strategy.name, "score": score, "metrics": metrics}
            )

            if score > self.best_score:
                self.best_score = score
                self.best_strategy = strategy
                best_strategies.append((strategy, score, metrics))

        # Sort by score and return top strategies
        best_strategies.sort(key=lambda x: x[1], reverse=True)

        return {
            "best_strategy": self.best_strategy,
            "best_score": self.best_score,
            "top_strategies": best_strategies[:10],  # Top 10
            "optimization_history": self.optimization_history,
        }

    def genetic_algorithm_optimization(
        self, population_size: int = 50, generations: int = 20
    ) -> Dict[str, Any]:
        """Use genetic algorithm to evolve optimal chunking parameters."""
        print(
            f"🧬 Running Genetic Algorithm optimization ({population_size} pop, "
            f"{generations} gen)..."
        )

        # Get parameter ranges for this content type
        parameter_ranges = ChunkingStrategyFactory.get_parameter_ranges(
            self.content_type, "hybrid"
        )
        available_strategies = ChunkingStrategyFactory.get_available_strategies(
            self.content_type
        )

        # Initialize population with random parameters
        population = []
        for _ in range(population_size):
            strategy_type = random.choice(available_strategies)
            params = {}
            for param_name, (min_val, max_val) in parameter_ranges.items():
                params[param_name] = random.randint(min_val, max_val)

            strategy = ChunkingStrategyFactory.create_strategy(
                self.content_type, strategy_type, **params
            )
            metrics = self.evaluate_strategy(strategy)
            score = self.calculate_strategy_score(metrics)
            population.append((strategy, score, metrics))

        best_ever = max(population, key=lambda x: x[1])

        for generation in range(generations):
            # Sort by fitness
            population.sort(key=lambda x: x[1], reverse=True)

            # Keep top 50% and generate new offspring
            elite_size = population_size // 2
            elite = population[:elite_size]
            new_population = elite.copy()

            # Generate offspring through crossover and mutation
            while len(new_population) < population_size:
                parent1 = random.choice(elite)
                parent2 = random.choice(elite)

                # Crossover: average parameters
                child_params = {}
                for param_name in parameter_ranges.keys():
                    if hasattr(parent1[0], "parameters") and hasattr(
                        parent2[0], "parameters"
                    ):
                        p1_val = parent1[0].parameters.get(param_name, 0)
                        p2_val = parent2[0].parameters.get(param_name, 0)
                        child_params[param_name] = int((p1_val + p2_val) / 2)
                    else:
                        min_val, max_val = parameter_ranges[param_name]
                        child_params[param_name] = random.randint(min_val, max_val)

                # Mutation: add some randomness
                for param_name in child_params:
                    mutation_range = (
                        parameter_ranges[param_name][1]
                        - parameter_ranges[param_name][0]
                    ) // 10
                    mutation = random.randint(-mutation_range, mutation_range)
                    child_params[param_name] = max(
                        parameter_ranges[param_name][0],
                        min(
                            parameter_ranges[param_name][1],
                            child_params[param_name] + mutation,
                        ),
                    )

                strategy_type = random.choice(available_strategies)
                child_strategy = ChunkingStrategyFactory.create_strategy(
                    self.content_type, strategy_type, **child_params
                )
                child_metrics = self.evaluate_strategy(child_strategy)
                child_score = self.calculate_strategy_score(child_metrics)

                new_population.append((child_strategy, child_score, child_metrics))

            population = new_population
            current_best = max(population, key=lambda x: x[1])

            if current_best[1] > best_ever[1]:
                best_ever = current_best

            if generation % 5 == 0:
                print(f"  Generation {generation}: Best score = {current_best[1]:.2f}")

        return {
            "best_strategy": best_ever[0],
            "best_score": best_ever[1],
            "best_metrics": best_ever[2],
            "final_population": population[:10],  # Top 10 from final population
        }


def analyze_chunking_strategies(content: str, content_type: str):
    """Analyze different chunking strategies using Monte Carlo optimization."""

    print(
        f"🔍 Analyzing {content_type} chunking strategies with Monte Carlo "
        "optimization..."
    )

    # Initialize optimizer
    optimizer = MonteCarloChunkingOptimizer(content, content_type)

    print("\n📊 MONTE CARLO OPTIMIZATION")
    print("=" * 50)

    # Run Monte Carlo optimization
    mc_results = optimizer.monte_carlo_optimization(
        n_iterations=500
    )  # Reduced for speed

    print("\n🎯 MONTE CARLO RESULTS:")
    print(f"Best Strategy: {mc_results['best_strategy'].name}")
    print(f"Best Score: {mc_results['best_score']:.2f}")

    # Show top 5 strategies
    print("\n🏆 TOP 5 STRATEGIES:")
    for i, (strategy, score, metrics) in enumerate(mc_results["top_strategies"][:5], 1):
        print(f"  {i}. {strategy.name} (Score: {score:.2f})")
        print(f"     - Chunks: {metrics.chunk_count}")
        print(f"     - Avg Size: {metrics.avg_size:,.0f} chars")
        print(f"     - Max Size: {metrics.max_size:,.0f} chars")
        print(f"     - Searchable: {metrics.searchable_ratio * 100:.1f}%")

    # Run Genetic Algorithm for comparison
    print("\n🧬 GENETIC ALGORITHM OPTIMIZATION")
    print("=" * 40)

    ga_results = optimizer.genetic_algorithm_optimization(
        population_size=30, generations=15
    )

    print("\n🎯 GENETIC ALGORITHM RESULTS:")
    print(f"Best Strategy: {ga_results['best_strategy'].name}")
    print(f"Best Score: {ga_results['best_score']:.2f}")

    # Compare results
    print("\n📈 COMPARISON:")
    print(f"Monte Carlo Best: {mc_results['best_score']:.2f}")
    print(f"Genetic Algorithm Best: {ga_results['best_score']:.2f}")

    if ga_results["best_score"] > mc_results["best_score"]:
        print("🏆 Genetic Algorithm found better solution!")
        best_overall = ga_results
    else:
        print("🏆 Monte Carlo found better solution!")
        best_overall = mc_results

    # Final recommendations
    print("\n💡 FINAL RECOMMENDATIONS:")
    print("=" * 30)

    best_strategy = best_overall["best_strategy"]
    best_metrics = best_overall.get("best_metrics", None)

    if best_metrics:
        print(f"✅ Optimal Strategy: {best_strategy.name}")
        print(f"   - Chunk Count: {best_metrics.chunk_count}")
        print(f"   - Average Size: {best_metrics.avg_size:,.0f} chars")
        print(f"   - Max Size: {best_metrics.max_size:,.0f} chars")
        print(f"   - Searchable Ratio: {best_metrics.searchable_ratio * 100:.1f}%")
        print(
            f"   - Size Distribution Score: {best_metrics.size_distribution_score:.3f}"
        )

        # Implementation recommendations
        if hasattr(best_strategy, "max_chunk_size"):
            print("\n🔧 Implementation:")
            print(
                f"   - Use HybridChunking with "
                f"max_chunk_size={best_strategy.max_chunk_size}"
            )
            print(f"   - This creates {best_metrics.chunk_count} chunks")
            print(
                f"   - {best_metrics.searchable_ratio * 100:.1f}% are searchable "
                "(<100KB)"
            )

        if best_metrics.max_size < 100000:
            print("   ✅ All chunks are suitable for vector search")
        elif best_metrics.max_size < 200000:
            print("   ⚠️  Some chunks may be large for optimal search")
        else:
            print("   ❌ Some chunks are too large for effective search")

    # Save detailed results
    results_file = Path(".workspace/chunking_optimization_results.json")
    with open(results_file, "w") as f:
        json.dump(
            {
                "content_type": content_type,
                "monte_carlo": {
                    "best_strategy": best_strategy.name if best_strategy else None,
                    "best_score": mc_results["best_score"],
                    "top_strategies": [
                        {
                            "name": s.name,
                            "score": score,
                            "metrics": {
                                "chunk_count": int(m.chunk_count),
                                "avg_size": float(m.avg_size),
                                "max_size": float(m.max_size),
                                "searchable_ratio": float(m.searchable_ratio),
                            },
                        }
                        for s, score, m in mc_results["top_strategies"][:5]
                    ],
                },
                "genetic_algorithm": {
                    "best_strategy": ga_results["best_strategy"].name
                    if ga_results["best_strategy"]
                    else None,
                    "best_score": ga_results["best_score"],
                },
                "recommendations": {
                    "optimal_strategy": best_strategy.name if best_strategy else None,
                    "optimal_score": best_overall["best_score"],
                    "implementation_notes": (
                        "Use the recommended strategy parameters for optimal chunking"
                    ),
                },
            },
            f,
            indent=2,
        )

    print(f"\n💾 Detailed results saved to: {results_file}")

    return best_overall


if __name__ == "__main__":
    # For testing - load OpenAPI spec if available
    spec_file = Path(".workspace/downloads/openapi-swagger.json")
    if spec_file.exists():
        with open(spec_file, "r", encoding="utf-8") as f:
            spec_data = json.load(f)
        analyze_chunking_strategies(json.dumps(spec_data), "api_spec")
    else:
        print(
            "❌ OpenAPI spec file not found. Run 'uv run python -m holocron sync' "
            "first."
        )
