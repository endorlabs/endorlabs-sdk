#!/usr/bin/env python3
"""
Unified analysis command for Holocron collections.
Analyzes content across different collections using pyproject.toml configuration.
"""

import json
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import load_config
from ..content_types import ContentTypeRegistry
from ..scripts.analyze_chunking_strategies import analyze_chunking_strategies


@dataclass
class AnalysisMetrics:
    """Metrics for analysis results."""

    collection_name: str
    files_analyzed: int
    total_size: int
    avg_size: float
    max_size: int
    min_size: int
    size_std: float
    chunk_count: int
    searchable_ratio: float
    recommendations: List[str]


@dataclass
class CollectionAnalysis:
    """Analysis results for a collection."""

    collection_name: str
    config: Dict[str, Any]
    metrics: AnalysisMetrics
    file_analysis: List[Dict[str, Any]]
    chunk_analysis: List[Dict[str, Any]]
    optimization: Optional[Dict[str, Any]] = None


class HolocronAnalyzer:
    """Unified analyzer for Holocron collections."""

    def __init__(self, config_path: str = "pyproject.toml"):
        """Initialize analyzer with configuration."""
        self.config = load_config(config_path)
        self.content_registry = ContentTypeRegistry(
            content_types=self.config.content_types,
            collection_mapping=self.config.collection_mapping,
            collections=self.config.collections,
        )

    def analyze_collection(
        self, collection_name: str, verbose: bool = False
    ) -> CollectionAnalysis:
        """Analyze a specific collection."""
        if collection_name not in self.config.collections:
            raise ValueError(
                f"Collection '{collection_name}' not found in configuration"
            )

        collection_config = self.config.collections[collection_name]

        if verbose:
            print(f"🔍 Analyzing collection: {collection_name}")
            print(f"   Config: {collection_config}")

        # Get files for this collection
        files = self._get_collection_files(collection_name)

        if not files:
            print(f"⚠️  No files found for collection '{collection_name}'")
            return CollectionAnalysis(
                collection_name=collection_name,
                config=asdict(collection_config),
                metrics=AnalysisMetrics(
                    collection_name=collection_name,
                    files_analyzed=0,
                    total_size=0,
                    avg_size=0,
                    max_size=0,
                    min_size=0,
                    size_std=0,
                    chunk_count=0,
                    searchable_ratio=0,
                    recommendations=["No files found to analyze"],
                ),
                file_analysis=[],
                chunk_analysis=[],
            )

        # Analyze files
        file_analysis = []
        all_sizes = []
        total_size = 0

        for file_path in files:
            file_metrics = self._analyze_file(file_path, collection_name)
            file_analysis.append(file_metrics)
            all_sizes.append(file_metrics["size"])
            total_size += file_metrics["size"]

        # Calculate statistics
        if all_sizes:
            avg_size = statistics.mean(all_sizes)
            max_size = max(all_sizes)
            min_size = min(all_sizes)
            size_std = statistics.stdev(all_sizes) if len(all_sizes) > 1 else 0
        else:
            avg_size = max_size = min_size = size_std = 0

        # Analyze chunks
        chunk_analysis = self._analyze_chunks(files, collection_name)
        chunk_count = sum(chunk["count"] for chunk in chunk_analysis)

        # Calculate searchable ratio (chunks < 100KB)
        searchable_chunks = sum(
            chunk["count"] for chunk in chunk_analysis if chunk["avg_size"] < 100000
        )
        searchable_ratio = searchable_chunks / chunk_count if chunk_count > 0 else 0

        # Generate recommendations
        recommendations = self._generate_recommendations(
            collection_name, avg_size, chunk_count, searchable_ratio
        )

        metrics = AnalysisMetrics(
            collection_name=collection_name,
            files_analyzed=len(files),
            total_size=total_size,
            avg_size=avg_size,
            max_size=max_size,
            min_size=min_size,
            size_std=size_std,
            chunk_count=chunk_count,
            searchable_ratio=searchable_ratio,
            recommendations=recommendations,
        )

        return CollectionAnalysis(
            collection_name=collection_name,
            config=asdict(collection_config),
            metrics=metrics,
            file_analysis=file_analysis,
            chunk_analysis=chunk_analysis,
        )

    def analyze_all_collections(
        self, verbose: bool = False
    ) -> Dict[str, CollectionAnalysis]:
        """Analyze all collections."""
        results = {}
        for collection_name in self.config.collections:
            try:
                result = self.analyze_collection(collection_name, verbose)
                results[collection_name] = result
            except Exception as e:
                print(f"⚠️  Error analyzing {collection_name}: {e}")
                continue
        return results

    def _get_collection_files(self, collection_name: str) -> List[str]:
        """Get files for a collection."""
        collection_config = self.config.collections[collection_name]
        files = []

        for include_path in collection_config.include_paths:
            path = Path(include_path)
            if path.exists():
                if path.is_file():
                    files.append(str(path))
                elif path.is_dir():
                    for file_path in path.rglob("*"):
                        if file_path.is_file() and self._is_text_file(str(file_path)):
                            files.append(str(file_path))

        return files

    def _is_text_file(self, file_path: str) -> bool:
        """Check if file is a text file."""
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(1024)
                return b"\0" not in chunk
        except Exception:
            return False

    def _analyze_file(self, file_path: str, collection_name: str) -> Dict[str, Any]:
        """Analyze a single file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            return {
                "file_path": file_path,
                "size": len(content),
                "lines": len(content.splitlines()),
                "content_type": self.content_registry.detect_content_type(file_path),
            }
        except Exception as e:
            return {
                "file_path": file_path,
                "size": 0,
                "lines": 0,
                "content_type": "unknown",
                "error": str(e),
            }

    def _analyze_chunks(
        self, files: List[str], collection_name: str
    ) -> List[Dict[str, Any]]:
        """Analyze chunks for files."""
        chunk_analysis = []

        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                content_type = self.content_registry.detect_content_type(file_path)
                if content_type:
                    source = self.content_registry.get_source(content_type)
                    if source:
                        chunks = source.chunk_content(content, file_path)
                        chunk_sizes = [len(chunk.text) for chunk in chunks]

                        chunk_analysis.append(
                            {
                                "file_path": file_path,
                                "content_type": content_type,
                                "count": len(chunks),
                                "avg_size": (
                                    statistics.mean(chunk_sizes) if chunk_sizes else 0
                                ),
                                "max_size": max(chunk_sizes) if chunk_sizes else 0,
                                "min_size": min(chunk_sizes) if chunk_sizes else 0,
                            }
                        )
            except Exception as e:
                chunk_analysis.append(
                    {
                        "file_path": file_path,
                        "content_type": "unknown",
                        "count": 0,
                        "avg_size": 0,
                        "max_size": 0,
                        "min_size": 0,
                        "error": str(e),
                    }
                )

        return chunk_analysis

    def _generate_recommendations(
        self,
        collection_name: str,
        avg_size: float,
        chunk_count: int,
        searchable_ratio: float,
    ) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []

        if avg_size > 50000:
            recommendations.append("Consider splitting large files for better chunking")

        if chunk_count == 0:
            recommendations.append("No chunks generated - check content type detection")

        if searchable_ratio < 0.8:
            recommendations.append("Many chunks are too large for optimal search")

        if not recommendations:
            recommendations.append("Collection appears well-optimized")

        return recommendations

    def _run_optimization(
        self,
        collection_name: str,
        content: str,
        iterations: int = 500,
        method: str = "both",
    ) -> Dict[str, Any]:
        """Run optimization for a collection."""
        try:
            return analyze_chunking_strategies(
                content=content,
                content_type=collection_name,
                iterations=iterations,
                method=method,
            )
        except Exception as e:
            print(f"❌ Error running optimization for {collection_name}: {e}")
            return {"collection": collection_name, "error": str(e)}


def analyze_command(args):
    """Execute the analyze command using command pattern."""
    from .analysis_commands import AnalysisCommandFactory

    analyzer = HolocronAnalyzer(args.config)
    command = AnalysisCommandFactory.create_command(args.collection)

    return command.execute(analyzer, args)


def print_analysis_result(
    result: CollectionAnalysis, output_file: Optional[str] = None
):
    """Print analysis results."""
    metrics = result.metrics

    print(f"\n📊 Analysis Results for {result.collection_name}")
    print("=" * 50)
    print(f"Files analyzed: {metrics.files_analyzed}")
    print(f"Total size: {metrics.total_size:,} bytes")
    print(f"Average file size: {metrics.avg_size:,.0f} bytes")
    print(f"Chunks generated: {metrics.chunk_count}")
    print(f"Searchable ratio: {metrics.searchable_ratio * 100:.1f}%")

    print("\n📋 Recommendations:")
    for rec in metrics.recommendations:
        print(f"  • {rec}")

    if output_file:
        with open(output_file, "w") as f:
            json.dump(asdict(result), f, indent=2, default=str)
        print(f"\n💾 Results saved to {output_file}")


def print_optimization_results(optimization_results: Dict[str, Any]):
    """Print optimization results."""
    if "error" in optimization_results:
        print(f"❌ Optimization failed: {optimization_results['error']}")
        return

    if "best_strategy" in optimization_results:
        best_strategy = optimization_results["best_strategy"]
        best_metrics = optimization_results["best_metrics"]

        print("\n🎯 Optimal Strategy Found:")
        print(f"   Strategy: {best_strategy.strategy_type}")
        print(f"   Max chunk size: {best_strategy.max_chunk_size}")
        print(f"   Overlap: {best_strategy.overlap}")
        print(f"   Searchable ratio: {best_metrics.searchable_ratio * 100:.1f}%")

        print("\n📝 Implementation:")
        content_type = optimization_results["content_type"]
        print(f"   [tool.holocron.content_types.{content_type}]")
        print(f"   chunk_size = {best_strategy.max_chunk_size}")
        print(f"   overlap = {best_strategy.overlap}")
    else:
        print("⚠️  No optimal strategy found")


def add_analyze_parser(subparsers):
    """Add analyze command parser."""
    parser = subparsers.add_parser(
        "analyze", help="Analyze Holocron collections and content"
    )

    parser.add_argument(
        "--collection",
        "-c",
        help="Analyze specific collection (default: all collections)",
    )

    parser.add_argument(
        "--config",
        default="pyproject.toml",
        help="Configuration file path (default: pyproject.toml)",
    )

    parser.add_argument("--output", "-o", help="Output file for detailed results")

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    # Optimization flags
    parser.add_argument(
        "--optimize",
        action="store_true",
        help="Run Monte Carlo optimization to find optimal chunking parameters",
    )

    parser.add_argument(
        "--optimizer-iterations",
        type=int,
        default=500,
        help="Number of Monte Carlo iterations (default: 500)",
    )

    parser.add_argument(
        "--optimizer-method",
        choices=["monte_carlo", "genetic", "both"],
        default="both",
        help="Optimization method to use (default: both)",
    )

    parser.set_defaults(func=analyze_command)
