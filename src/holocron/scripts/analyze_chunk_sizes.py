#!/usr/bin/env python3
"""
Document Chunk Size Analysis Script

Analyzes the actual size distribution of document sections across different
content types to inform optimal chunking strategy decisions.

Categories analyzed:
- Internal Documentation (docs/)
- External Documentation (.workspace/downloads/user-docs/)
- OpenAPI Spec (.workspace/downloads/openapi-swagger.json)
- Code Files (src/endor_cockpit/resources/, tests/)
"""

import json
import os
import re
import statistics
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass


@dataclass
class SectionMetrics:
    """Metrics for a document section."""
    size_chars: int
    size_tokens: int  # Approximate: chars / 4
    section_type: str
    header_text: str
    file_path: str


@dataclass
class CategoryAnalysis:
    """Analysis results for a content category."""
    category_name: str
    files_analyzed: int
    sections_found: int
    sizes_chars: List[int]
    sizes_tokens: List[int]
    recommendations: List[str]


def estimate_tokens(text: str) -> int:
    """Estimate token count from character count (rough approximation)."""
    return len(text) // 4


def analyze_markdown_sections(file_path: Path) -> List[SectionMetrics]:
    """Analyze markdown file for H2 sections."""
    try:
        content = file_path.read_text(encoding='utf-8')
        sections = []
        lines = content.split('\n')
        
        current_section = []
        current_header = ""
        in_section = False
        
        for line in lines:
            # Check for H2 headers (## )
            if line.strip().startswith('## ') and not line.strip().startswith('### '):
                # Save previous section if exists
                if current_section and in_section:
                    section_text = '\n'.join(current_section)
                    sections.append(SectionMetrics(
                        size_chars=len(section_text),
                        size_tokens=estimate_tokens(section_text),
                        section_type="h2",
                        header_text=current_header.strip('# ').strip(),
                        file_path=str(file_path)
                    ))
                
                # Start new section
                current_section = [line]
                current_header = line
                in_section = True
            elif in_section:
                current_section.append(line)
        
        # Add final section
        if current_section and in_section:
            section_text = '\n'.join(current_section)
            sections.append(SectionMetrics(
                size_chars=len(section_text),
                size_tokens=estimate_tokens(section_text),
                section_type="h2",
                header_text=current_header.strip('# ').strip(),
                file_path=str(file_path)
            ))
        
        return sections
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return []


def analyze_external_docs_sections(file_path: Path) -> List[SectionMetrics]:
    """Analyze external docs for major sections (underline headers)."""
    try:
        content = file_path.read_text(encoding='utf-8')
        sections = []
        lines = content.split('\n')
        
        current_section = []
        current_header = ""
        in_section = False
        
        for i, line in enumerate(lines):
            # Check for underline headers (=== or ---)
            if (len(line.strip()) > 3 and 
                (line.strip().endswith('=') or line.strip().endswith('-')) and
                i > 0 and len(lines[i-1].strip()) > 0):
                
                # Save previous section if exists
                if current_section and in_section:
                    section_text = '\n'.join(current_section)
                    sections.append(SectionMetrics(
                        size_chars=len(section_text),
                        size_tokens=estimate_tokens(section_text),
                        section_type="underline",
                        header_text=current_header.strip('=-').strip(),
                        file_path=str(file_path)
                    ))
                
                # Start new section
                current_section = [lines[i-1], line]  # Include header line
                current_header = lines[i-1]
                in_section = True
            elif in_section:
                current_section.append(line)
        
        # Add final section
        if current_section and in_section:
            section_text = '\n'.join(current_section)
            sections.append(SectionMetrics(
                size_chars=len(section_text),
                size_tokens=estimate_tokens(section_text),
                section_type="underline",
                header_text=current_header.strip('=-').strip(),
                file_path=str(file_path)
            ))
        
        return sections
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return []


def analyze_openapi_services(file_path: Path) -> List[SectionMetrics]:
    """Analyze OpenAPI spec for service endpoint groups."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            spec = json.load(f)
        
        sections = []
        paths = spec.get('paths', {})
        
        # Group endpoints by service (extract service name from path)
        service_groups = {}
        for path, methods in paths.items():
            # Extract service name from path (e.g., /v1/namespaces/{namespace}/projects -> projects)
            path_parts = path.strip('/').split('/')
            if len(path_parts) >= 3:
                service_name = path_parts[-1]  # Last part is usually the resource
            else:
                service_name = 'root'
            
            if service_name not in service_groups:
                service_groups[service_name] = []
            
            service_groups[service_name].append({
                'path': path,
                'methods': methods
            })
        
        # Calculate size for each service group
        for service_name, endpoints in service_groups.items():
            service_content = json.dumps({service_name: endpoints}, indent=2)
            sections.append(SectionMetrics(
                size_chars=len(service_content),
                size_tokens=estimate_tokens(service_content),
                section_type="service",
                header_text=f"{service_name} service",
                file_path=str(file_path)
            ))
        
        return sections
    except Exception as e:
        print(f"Error analyzing OpenAPI spec {file_path}: {e}")
        return []


def analyze_code_files(file_path: Path) -> List[SectionMetrics]:
    """Analyze code files for complete file size."""
    try:
        content = file_path.read_text(encoding='utf-8')
        return [SectionMetrics(
            size_chars=len(content),
            size_tokens=estimate_tokens(content),
            section_type="file",
            header_text=file_path.name,
            file_path=str(file_path)
        )]
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return []


def calculate_statistics(sizes: List[int]) -> Dict[str, Any]:
    """Calculate statistics for a list of sizes."""
    if not sizes:
        return {"min": 0, "max": 0, "median": 0, "p95": 0, "mean": 0}
    
    sizes_sorted = sorted(sizes)
    n = len(sizes_sorted)
    
    return {
        "min": min(sizes),
        "max": max(sizes),
        "median": statistics.median(sizes),
        "p95": sizes_sorted[int(0.95 * n)] if n > 0 else 0,
        "mean": statistics.mean(sizes)
    }


def analyze_category(category_name: str, file_patterns: List[str], 
                   analyzer_func, base_path: Path = None) -> CategoryAnalysis:
    """Analyze a category of files."""
    if base_path is None:
        base_path = Path('.')
    
    all_sections = []
    files_analyzed = 0
    
    for pattern in file_patterns:
        for file_path in base_path.glob(pattern):
            if file_path.is_file():
                sections = analyzer_func(file_path)
                all_sections.extend(sections)
                files_analyzed += 1
    
    sizes_chars = [s.size_chars for s in all_sections]
    sizes_tokens = [s.size_tokens for s in all_sections]
    
    char_stats = calculate_statistics(sizes_chars)
    token_stats = calculate_statistics(sizes_tokens)
    
    # Generate recommendations
    recommendations = []
    if token_stats["max"] > 5000:
        recommendations.append(f"WARNING: Some sections exceed 5000 tokens (max: {token_stats['max']})")
    
    if token_stats["p95"] > 3000:
        recommendations.append(f"Consider chunk size >= {token_stats['p95']} to preserve 95% of sections")
    else:
        recommendations.append(f"Recommended chunk size: {token_stats['p95']} tokens (P95)")
    
    if token_stats["median"] < 1000:
        recommendations.append(f"Many small sections (median: {token_stats['median']} tokens) - good for granular retrieval")
    
    return CategoryAnalysis(
        category_name=category_name,
        files_analyzed=files_analyzed,
        sections_found=len(all_sections),
        sizes_chars=sizes_chars,
        sizes_tokens=sizes_tokens,
        recommendations=recommendations
    )


def main():
    """Main analysis function."""
    print("=" * 80)
    print("DOCUMENT CHUNK SIZE ANALYSIS")
    print("=" * 80)
    print()
    
    # Define analysis categories
    categories = [
        {
            "name": "Internal Documentation (docs/)",
            "patterns": ["docs/**/*.md"],
            "analyzer": analyze_markdown_sections,
            "base_path": Path(".")
        },
        {
            "name": "External Documentation (.workspace/downloads/user-docs/)",
            "patterns": ["*.md"],
            "analyzer": analyze_external_docs_sections,
            "base_path": Path(".workspace/downloads/user-docs/")
        },
        {
            "name": "OpenAPI Spec (.workspace/downloads/openapi-swagger.json)",
            "patterns": ["openapi-swagger.json"],
            "analyzer": analyze_openapi_services,
            "base_path": Path(".workspace/downloads/")
        },
        {
            "name": "Code Files (src/endor_cockpit/resources/, tests/)",
            "patterns": ["src/endor_cockpit/resources/*.py", "tests/*.py"],
            "analyzer": analyze_code_files,
            "base_path": Path(".")
        }
    ]
    
    results = []
    
    for category in categories:
        print(f"Analyzing {category['name']}...")
        analysis = analyze_category(
            category["name"],
            category["patterns"],
            category["analyzer"],
            category["base_path"]
        )
        results.append(analysis)
        print(f"  Files analyzed: {analysis.files_analyzed}")
        print(f"  Sections found: {analysis.sections_found}")
        print()
    
    # Print detailed results
    print("=" * 80)
    print("ANALYSIS RESULTS")
    print("=" * 80)
    print()
    
    for analysis in results:
        if analysis.sections_found == 0:
            print(f"Category: {analysis.category_name}")
            print("  No sections found - check file paths and patterns")
            print()
            continue
        
        char_stats = calculate_statistics(analysis.sizes_chars)
        token_stats = calculate_statistics(analysis.sizes_tokens)
        
        print(f"Category: {analysis.category_name}")
        print(f"  Files analyzed: {analysis.files_analyzed}")
        print(f"  Sections found: {analysis.sections_found}")
        print(f"  Size distribution (tokens):")
        print(f"    Min: {token_stats['min']}")
        print(f"    Median: {token_stats['median']:.0f}")
        print(f"    P95: {token_stats['p95']:.0f}")
        print(f"    Max: {token_stats['max']}")
        print(f"    Mean: {token_stats['mean']:.0f}")
        print()
        
        if analysis.recommendations:
            print("  Recommendations:")
            for rec in analysis.recommendations:
                print(f"    - {rec}")
            print()
    
    # Overall recommendations
    print("=" * 80)
    print("OVERALL RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    # Find the maximum P95 across all categories
    max_p95 = max(
        calculate_statistics(analysis.sizes_tokens)["p95"] 
        for analysis in results 
        if analysis.sections_found > 0
    )
    
    print(f"Recommended chunk sizes based on analysis:")
    print(f"  - Minimum chunk size: {max_p95:.0f} tokens (to preserve 95% of sections)")
    print(f"  - Target chunk size: {max_p95 * 1.2:.0f} tokens (with 20% buffer)")
    print(f"  - Hard limit: 5000 tokens (for extremely large sections)")
    print()
    print("Chunking strategy recommendations:")
    print("  - Use H2 headers as primary split boundaries for markdown")
    print("  - Preserve complete sections even if they exceed target size")
    print("  - Implement 400-500 token overlap between chunks")
    print("  - Only split sections that exceed 5000 token hard limit")
    print()


if __name__ == "__main__":
    main()
