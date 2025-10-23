"""
Analysis Command Pattern for Holocron.

Extracts complex analysis logic from analyze_command() to reduce complexity.
"""

from abc import ABC, abstractmethod
from typing import Optional

from ..commands.analyze import (
    HolocronAnalyzer,
    print_analysis_result,
    print_optimization_results,
)


class AnalysisCommand(ABC):
    """Abstract base class for analysis commands."""

    @abstractmethod
    def execute(self, analyzer: HolocronAnalyzer, args) -> None:
        """Execute the analysis command."""
        pass


class SingleCollectionAnalysisCommand(AnalysisCommand):
    """Command for analyzing a single collection."""

    def execute(self, analyzer: HolocronAnalyzer, args) -> None:
        """Analyze a single collection with optional optimization."""
        try:
            result = analyzer.analyze_collection(args.collection, args.verbose)

            # Run optimization if requested
            if args.optimize:
                print(f"\n🎲 Running optimization for collection: {args.collection}")
                self._run_optimization(analyzer, args, result)

            print_analysis_result(result, args.output)
        except Exception as e:
            print(f"Error analyzing collection {args.collection}: {e}")
            return 1

    def _run_optimization(self, analyzer: HolocronAnalyzer, args, result) -> None:
        """Run optimization for a single collection."""
        # Get content for optimization
        files = analyzer._get_collection_files(args.collection)
        if files:
            # Combine content from all files
            content_parts = []
            for file_path in files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content_parts.append(f.read())
                except Exception as e:
                    print(f"⚠️  Could not read {file_path}: {e}")

            if content_parts:
                combined_content = "\n\n".join(content_parts)
                optimization_results = analyzer._run_optimization(
                    args.collection,
                    combined_content,
                    args.optimizer_iterations,
                    args.optimizer_method,
                )

                # Add optimization results to the analysis
                result.optimization = optimization_results

                # Print optimization results
                print_optimization_results(optimization_results)
            else:
                print("⚠️  No content found for optimization")
        else:
            print("⚠️  No files found for optimization")


class AllCollectionsAnalysisCommand(AnalysisCommand):
    """Command for analyzing all collections."""

    def execute(self, analyzer: HolocronAnalyzer, args) -> None:
        """Analyze all collections with optional optimization."""
        results = analyzer.analyze_all_collections(args.verbose)

        # Run optimization for all collections if requested
        if args.optimize:
            print("\n🎲 Running optimization for all collections")
            for collection_name, result in results.items():
                print(f"\n🔍 Optimizing {collection_name}...")
                self._run_optimization_for_collection(
                    analyzer, args, collection_name, result
                )

        if args.output:
            # Save to file
            output_data = {
                "timestamp": (
                    analyzer.config.timestamp
                    if hasattr(analyzer.config, "timestamp")
                    else None
                ),
                "collections": {
                    name: result.__dict__ for name, result in results.items()
                },
            }
            with open(args.output, "w") as f:
                import json

                json.dump(output_data, f, indent=2, default=str)
            print(f"Analysis results saved to {args.output}")
        else:
            # Print summary
            print("\n📊 Analysis Summary:")
            print("=" * 50)
            for collection_name, result in results.items():
                metrics = result.metrics
                print(f"{collection_name}:")
                print(f"  Files: {metrics.files_analyzed}")
                print(f"  Chunks: {metrics.chunk_count}")
                print(f"  Searchable: {metrics.searchable_ratio * 100:.1f}%")
                print()

    def _run_optimization_for_collection(
        self, analyzer: HolocronAnalyzer, args, collection_name: str, result
    ) -> None:
        """Run optimization for a specific collection."""
        # Get content for optimization
        files = analyzer._get_collection_files(collection_name)
        if files:
            # Combine content from all files
            content_parts = []
            for file_path in files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content_parts.append(f.read())
                except Exception as e:
                    print(f"⚠️  Could not read {file_path}: {e}")

            if content_parts:
                combined_content = "\n\n".join(content_parts)
                optimization_results = analyzer._run_optimization(
                    collection_name,
                    combined_content,
                    args.optimizer_iterations,
                    args.optimizer_method,
                )

                # Add optimization results to the analysis
                result.optimization = optimization_results

                # Print optimization results
                print_optimization_results(optimization_results)
            else:
                print(f"⚠️  No content found for {collection_name}")
        else:
            print(f"⚠️  No files found for {collection_name}")


class AnalysisCommandFactory:
    """Factory for creating analysis commands."""

    @staticmethod
    def create_command(collection: Optional[str]) -> AnalysisCommand:
        """Create the appropriate analysis command."""
        if collection:
            return SingleCollectionAnalysisCommand()
        else:
            return AllCollectionsAnalysisCommand()
