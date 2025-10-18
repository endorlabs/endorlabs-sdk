#!/usr/bin/env python3
"""
Standalone CLI tool for querying Endor Cockpit documentation.

This script provides a command-line interface for semantic search
over the Endor Cockpit documentation using the RAG system.
"""

import argparse
import json
import sys
from typing import Any, Dict


def query_docs(
    query: str,
    max_results: int = 5,
    include_metadata: bool = True,
    format_output: str = "text"
) -> Dict[str, Any]:
    """
    Query the Endor Cockpit documentation.

    Args:
        query: Natural language query
        max_results: Maximum number of results to return
        include_metadata: Whether to include source metadata
        format_output: Output format ("text", "json", "markdown")

    Returns:
        Dictionary containing query results
    """
    try:
        from endor_cockpit.rag import get_vector_db_info, query_vector_db

        # Get database info
        info = get_vector_db_info()

        # Query the documentation
        results = query_vector_db(
            query_text=query,
            n_results=max_results,
            include_metadata=include_metadata
        )

        # Add database info to results
        results["database_info"] = {
            "total_chunks": info["chunk_count"],
            "total_documents": info.get("total_documents", "Unknown"),
            "last_updated": info.get("last_updated", "Unknown")
        }

        return results

    except ImportError as e:
        return {
            "error": f"Import error: {e}",
            "suggestion": "Make sure endor-cockpit is installed with RAG dependencies"
        }
    except Exception as e:
        return {
            "error": f"Query failed: {e}",
            "query": query
        }


def format_text_output(results: Dict[str, Any]) -> str:
    """Format results as plain text."""
    if "error" in results:
        return f"Error: {results['error']}"

    output = []
    output.append(f"Query: {results['query']}")
    output.append(
        f"Database: {results['database_info']['total_chunks']} chunks, "
        f"{results['database_info']['total_documents']} documents"
    )
    output.append(f"Found {len(results['results'])} results:\n")

    for i, result in enumerate(results['results'], 1):
        output.append(f"{i}. Score: {result['similarity_score']:.3f}")
        if 'metadata' in result and 'source' in result['metadata']:
            output.append(f"   Source: {result['metadata']['source']}")
        output.append(f"   Content: {result['content']}")
        output.append("")

    return "\n".join(output)


def format_json_output(results: Dict[str, Any]) -> str:
    """Format results as JSON."""
    return json.dumps(results, indent=2)


def format_markdown_output(results: Dict[str, Any]) -> str:
    """Format results as Markdown."""
    if "error" in results:
        return f"# Error\n\n{results['error']}"

    output = []
    output.append(f"# Query: {results['query']}")
    output.append(f"**Database**: {results['database_info']['total_chunks']} chunks, {results['database_info']['total_documents']} documents")
    output.append(f"**Results**: {len(results['results'])} found\n")

    for i, result in enumerate(results['results'], 1):
        output.append(f"## Result {i} (Score: {result['similarity_score']:.3f})")
        if 'metadata' in result and 'source' in result['metadata']:
            output.append(f"**Source**: {result['metadata']['source']}")
        output.append(f"\n{result['content']}\n")

    return "\n".join(output)


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Query Endor Cockpit documentation using semantic search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python standalone_cli.py "How do I create a namespace?"
  python standalone_cli.py "API quirks" --max-results 3 --format json
  python standalone_cli.py "troubleshoot 403" --no-metadata --format markdown
        """
    )

    parser.add_argument(
        "query",
        help="Natural language query to search the documentation"
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=5,
        help="Maximum number of results to return (default: 5)"
    )

    parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="Exclude source metadata from results"
    )

    parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format (default: text)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    # Query the documentation
    if args.verbose:
        print(f"Querying: {args.query}", file=sys.stderr)
        print(f"Max results: {args.max_results}", file=sys.stderr)
        print(f"Format: {args.format}", file=sys.stderr)

    results = query_docs(
        query=args.query,
        max_results=args.max_results,
        include_metadata=not args.no_metadata,
        format_output=args.format
    )

    # Format and output results
    if args.format == "json":
        output = format_json_output(results)
    elif args.format == "markdown":
        output = format_markdown_output(results)
    else:
        output = format_text_output(results)

    print(output)


if __name__ == "__main__":
    main()
