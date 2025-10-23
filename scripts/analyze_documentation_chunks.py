#!/usr/bin/env python3
"""
Standalone script for analyzing documentation chunk size compliance.

This script checks protocol files for chunk size compliance and provides
recommendations for splitting oversized protocols. It does NOT fail CI/CD.
"""

from pathlib import Path
from typing import Any, Dict, List


def estimate_tokens(text: str) -> int:
    """Estimate token count from character count (rough approximation)."""
    return len(text) // 4


def find_h2_headers(content: str) -> List[Dict[str, Any]]:
    """Find H2 headers and their positions in content."""
    headers = []
    lines = content.split("\n")

    for i, line in enumerate(lines):
        if line.strip().startswith("## ") and not line.strip().startswith("### "):
            header_text = line.strip("# ").strip()
            headers.append(
                {
                    "line_number": i + 1,
                    "text": header_text,
                    "position": len("\n".join(lines[:i])),
                }
            )

    return headers


def analyze_protocol_file(file_path: Path) -> Dict[str, Any]:
    """Analyze a single protocol file for chunk compliance."""
    try:
        content = file_path.read_text(encoding="utf-8")
        token_count = estimate_tokens(content)

        # Find H2 headers for potential split points
        h2_headers = find_h2_headers(content)

        # Calculate section sizes
        sections = []
        for i, header in enumerate(h2_headers):
            start_pos = header["position"]
            end_pos = (
                h2_headers[i + 1]["position"]
                if i + 1 < len(h2_headers)
                else len(content)
            )
            section_content = content[start_pos:end_pos]
            section_tokens = estimate_tokens(section_content)

            sections.append(
                {
                    "header": header["text"],
                    "line_number": header["line_number"],
                    "tokens": section_tokens,
                }
            )

        return {
            "file_path": str(file_path),
            "total_tokens": token_count,
            "is_oversized": token_count > 3000,
            "h2_headers": h2_headers,
            "sections": sections,
            "recommendations": [],
        }
    except Exception as e:
        return {
            "file_path": str(file_path),
            "error": str(e),
            "total_tokens": 0,
            "is_oversized": False,
            "h2_headers": [],
            "sections": [],
            "recommendations": [f"Error reading file: {e}"],
        }


def generate_recommendations(analysis: Dict[str, Any]) -> List[str]:
    """Generate recommendations for oversized protocols."""
    recommendations = []

    if not analysis["is_oversized"]:
        return recommendations

    total_tokens = analysis["total_tokens"]
    sections = analysis["sections"]

    recommendations.append(f"Protocol exceeds 3000 token limit ({total_tokens} tokens)")

    if len(sections) > 1:
        # Suggest split points based on section sizes
        large_sections = [s for s in sections if s["tokens"] > 1000]
        if large_sections:
            recommendations.append("Large sections that could be split:")
            for section in large_sections:
                recommendations.append(
                    f"  - {section['header']} ({section['tokens']} tokens)"
                )

        # Suggest natural split points
        recommendations.append("Suggested split points at H2 headers:")
        for section in sections:
            if section["tokens"] > 500:  # Only suggest splits for substantial sections
                recommendations.append(
                    f"  - Line {section['line_number']}: {section['header']}"
                )

    recommendations.append(
        "Consider splitting at major section boundaries (H2 headers)"
    )
    recommendations.append("Maintain 200-300 token overlap between splits")
    recommendations.append("Test RAG queries to ensure discoverability after splitting")

    return recommendations


def _find_protocol_files() -> List[Path]:
    """Find all protocol files to analyze."""
    protocols_dir = Path("docs/protocols")

    if not protocols_dir.exists():
        print("WARNING: docs/protocols directory not found")
        return []

    # Find all protocol files
    protocol_files = []
    for pattern in ["**/*.md"]:
        protocol_files.extend(protocols_dir.glob(pattern))

    if not protocol_files:
        print("WARNING: No protocol files found in docs/protocols/")
        return []

    return protocol_files


def _analyze_protocol_files(protocol_files: List[Path]) -> tuple:
    """Analyze protocol files and return results."""
    oversized_protocols = []
    all_analyses = []

    for file_path in protocol_files:
        analysis = analyze_protocol_file(file_path)
        all_analyses.append(analysis)

        if analysis["is_oversized"]:
            oversized_protocols.append(analysis)
            analysis["recommendations"] = generate_recommendations(analysis)

    return oversized_protocols, all_analyses


def _print_results(oversized_protocols: List[Dict], all_analyses: List[Dict]) -> None:
    """Print analysis results."""
    print(f"Analyzed {len(all_analyses)} protocol files")
    print(f"Found {len(oversized_protocols)} oversized protocols")
    print()

    if oversized_protocols:
        print("OVERSIZED PROTOCOLS:")
        print("-" * 40)

        for analysis in oversized_protocols:
            print(f"\nFile: {analysis['file_path']}")
            print(f"Tokens: {analysis['total_tokens']} (limit: 3000)")
            print(f"H2 Headers: {len(analysis['h2_headers'])}")

            if analysis["recommendations"]:
                print("Recommendations:")
                for rec in analysis["recommendations"]:
                    print(f"  - {rec}")
    else:
        print("✅ All protocols are within size limits")


def _print_summary_stats(
    all_analyses: List[Dict], oversized_protocols: List[Dict]
) -> None:
    """Print summary statistics."""
    if not all_analyses:
        return

    total_tokens = sum(a["total_tokens"] for a in all_analyses)
    avg_tokens = total_tokens / len(all_analyses)
    max_tokens = max(a["total_tokens"] for a in all_analyses)

    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print(f"Total protocols: {len(all_analyses)}")
    print(f"Oversized protocols: {len(oversized_protocols)}")
    print(f"Average tokens: {avg_tokens:.0f}")
    print(f"Maximum tokens: {max_tokens}")
    compliance_rate = (
        (len(all_analyses) - len(oversized_protocols)) / len(all_analyses) * 100
    )
    print(f"Compliance rate: {compliance_rate:.1f}%")


def main():
    """Main function to analyze protocol files for chunk compliance."""
    print("=" * 80)
    print("PROTOCOL CHUNK SIZE COMPLIANCE CHECK")
    print("=" * 80)
    print()

    protocol_files = _find_protocol_files()
    if not protocol_files:
        return

    oversized_protocols, all_analyses = _analyze_protocol_files(protocol_files)
    _print_results(oversized_protocols, all_analyses)
    _print_summary_stats(all_analyses, oversized_protocols)

    print("\n" + "=" * 80)
    print(
        "NOTE: This is a standalone analysis script - it provides feedback "
        "without failing CI/CD"
    )
    print("=" * 80)


if __name__ == "__main__":
    main()
