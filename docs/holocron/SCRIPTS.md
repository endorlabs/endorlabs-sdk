# Holocron Scripts and Utilities

> **Analysis scripts, development tools, and custom script development guide**

This document covers the analysis scripts included with Holocron, their usage, and guidance for developing custom scripts to work with the knowledge base system.

## 📊 Included Analysis Scripts

### System Validation Script (`validate_holocron.py`)

**Purpose**: Comprehensive health check for Holocron system components

**Location**: `scripts/validate_holocron.py`

**Usage**:
```bash
# Run full system validation
python scripts/validate_holocron.py

# Check specific components
python scripts/validate_holocron.py --check-config
python scripts/validate_holocron.py --check-database
python scripts/validate_holocron.py --check-chunking
```

**Features**:
- Configuration file validation (TOML syntax, required sections)
- Dependency validation (required packages, imports)
- Vector database health (collection existence, chunk counts)
- Content type detection validation
- Cross-platform path handling validation
- Query functionality testing

**Output Example**:
```
Holocron System Validation Results
==================================================

Holocron system validation passed!
   All components are properly configured and working.

Summary:
   Critical errors: 0
   Warnings: 0
   Overall status: Valid
```

**Reference**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for issue resolution and [CONFIGURATION.md](CONFIGURATION.md) for configuration validation details.

### Chunk Size Analysis (`analyze_chunk_sizes.py`)

**Purpose**: Analyze chunk size distributions and optimize chunking strategies

**Location**: `src/holocron/scripts/analyze_chunk_sizes.py`

**Usage**:
```bash
# Analyze current chunking strategy
uv run python -m holocron.scripts.analyze_chunk_sizes

# Analyze with custom parameters
uv run python -m holocron.scripts.analyze_chunk_sizes --content-type markdown --verbose
```

**Features**:
- Content type-specific analysis
- Chunk size distribution statistics
- Overlap analysis
- Chunking strategy recommendations
- Performance metrics

**Output Example**:
```
Content Type: markdown
Total Chunks: 1,250
Average Chunk Size: 1,607 characters
P95 Chunk Size: 2,100 characters
Recommended Chunk Size: 2,100 + 1,000 buffer = 3,100
Overlap Analysis: 400 characters (25% of average)
```

### Database Analysis Scripts

**Purpose**: Analyze vector database content and performance

**Available Scripts**:
- `debug_database.py`: Database state analysis
- `debug_collections.py`: Collection content analysis

**Usage**:
```bash
# Analyze database state
python .workspace/debug_database.py

# Analyze collection content
python .workspace/debug_collections.py
```

## 🛠️ Script Development Guide

### Creating Custom Analysis Scripts

#### 1. Basic Script Structure

```python
#!/usr/bin/env python3
"""
Custom Holocron Analysis Script

Analyzes [specific aspect] of the Holocron knowledge base.
"""

import argparse
import sys
from pathlib import Path

# Add holocron to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from holocron.config import load_config
from holocron.manager import VectorDBManager
from holocron.query import HolocronQuery


def main():
    """Main script entry point."""
    parser = argparse.ArgumentParser(description="Custom Holocron Analysis")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--output", help="Output file path")
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = load_config()
        
        # Initialize components
        manager = VectorDBManager(config=config)
        query = HolocronQuery(config=config)
        
        # Perform analysis
        results = analyze_knowledge_base(manager, query, args)
        
        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                f.write(results)
        else:
            print(results)
            
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def analyze_knowledge_base(manager, query, args):
    """Perform the analysis."""
    # Your analysis logic here
    pass


if __name__ == "__main__":
    main()
```

#### 2. Content Analysis Script

```python
def analyze_content_distribution(manager, args):
    """Analyze content distribution across content types."""
    collections = manager.get_available_collections()
    
    print("Content Type Distribution:")
    print("=" * 40)
    
    total_chunks = 0
    for content_type, info in collections.items():
        count = info['count']
        total_chunks += count
        percentage = (count / sum(c['count'] for c in collections.values())) * 100
        print(f"{content_type:15} | {count:4d} chunks | {percentage:5.1f}%")
    
    print(f"{'Total':15} | {total_chunks:4d} chunks | 100.0%")
    
    return {
        "total_chunks": total_chunks,
        "content_types": collections
    }
```

#### 3. Search Quality Analysis Script

```python
def analyze_search_quality(query, test_queries, args):
    """Analyze search quality with test queries."""
    results = {}
    
    for query_text in test_queries:
        try:
            response = query.query(query_text, n_results=5)
            
            # Analyze results
            scores = [r['similarity_score'] for r in response['results']]
            avg_score = sum(scores) / len(scores) if scores else 0
            
            results[query_text] = {
                "avg_score": avg_score,
                "result_count": len(response['results']),
                "scores": scores
            }
            
        except Exception as e:
            results[query_text] = {"error": str(e)}
    
    return results
```

### Script Categories

#### 1. Content Analysis Scripts

**Purpose**: Analyze content structure and chunking effectiveness

**Examples**:
- Chunk size distribution analysis
- Content type coverage analysis
- Metadata extraction analysis
- Chunking strategy effectiveness

**Template**:
```python
def analyze_content_structure(manager, content_type=None):
    """Analyze content structure for a specific content type."""
    collections = manager.get_available_collections()
    
    if content_type:
        target_types = [content_type]
    else:
        target_types = collections.keys()
    
    for ct in target_types:
        if ct in collections:
            analyze_content_type(manager, ct, collections[ct])
```

#### 2. Search Quality Scripts

**Purpose**: Analyze search quality and relevance

**Examples**:
- Query performance analysis
- Similarity score distribution
- Result relevance analysis
- Search coverage analysis

**Template**:
```python
def analyze_search_quality(query, test_cases):
    """Analyze search quality with test cases."""
    results = {}
    
    for test_case in test_cases:
        query_text = test_case['query']
        expected_content = test_case['expected']
        
        response = query.query(query_text, n_results=10)
        
        # Analyze relevance
        relevance_score = calculate_relevance(response, expected_content)
        results[query_text] = {
            "relevance_score": relevance_score,
            "result_count": len(response['results']),
            "top_score": max(r['similarity_score'] for r in response['results'])
        }
    
    return results
```

#### 3. Performance Analysis Scripts

**Purpose**: Analyze system performance and optimization opportunities

**Examples**:
- Database performance analysis
- Memory usage analysis
- Processing time analysis
- Optimization recommendations

**Template**:
```python
def analyze_performance(manager, query):
    """Analyze system performance."""
    import time
    import psutil
    
    # Database performance
    start_time = time.time()
    collections = manager.get_available_collections()
    db_time = time.time() - start_time
    
    # Query performance
    test_queries = [
        "How do I create a namespace?",
        "What are the API authentication methods?",
        "How do I troubleshoot errors?"
    ]
    
    query_times = []
    for query_text in test_queries:
        start_time = time.time()
        response = query.query(query_text, n_results=5)
        query_time = time.time() - start_time
        query_times.append(query_time)
    
    # Memory usage
    memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
    
    return {
        "db_query_time": db_time,
        "avg_query_time": sum(query_times) / len(query_times),
        "memory_usage_mb": memory_usage,
        "total_chunks": sum(c['count'] for c in collections.values())
    }
```

## 🔧 Development Utilities

### Configuration Testing

```python
def test_configuration(config_path="pyproject.toml"):
    """Test configuration loading and validation."""
    try:
        config = load_config(config_path)
        warnings = validate_config(config)
        
        print("✅ Configuration loaded successfully")
        
        if warnings:
            print("⚠️  Configuration warnings:")
            for warning in warnings:
                print(f"  - {warning}")
        else:
            print("✅ Configuration is valid")
            
        return True
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False
```

### Content Type Testing

```python
def test_content_types(config):
    """Test content type detection and processing."""
    from holocron.content_types import ContentTypeRegistry
    
    registry = ContentTypeRegistry(config.content_types)
    
    # Test files
    test_files = [
        "docs/README.md",
        "src/holocron/manager.py",
        ".workspace/downloads/openapi-swagger.json",
        ".workspace/downloads/user-docs/getting-started.md"
    ]
    
    print("Content Type Detection Test:")
    print("=" * 40)
    
    for file_path in test_files:
        detected_type = registry.detect_content_type(file_path)
        print(f"{file_path:40} → {detected_type}")
    
    return True
```

### Database Health Check

```python
def check_database_health(manager):
    """Check database health and integrity."""
    try:
        # Check if database is accessible
        collections = manager.get_available_collections()
        
        if not collections:
            print("❌ No collections found in database")
            return False
        
        # Check collection counts
        total_chunks = sum(info['count'] for info in collections.values())
        
        if total_chunks == 0:
            print("❌ No chunks found in database")
            return False
        
        print(f"✅ Database health check passed")
        print(f"  - Collections: {len(collections)}")
        print(f"  - Total chunks: {total_chunks}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database health check failed: {e}")
        return False
```

## 📊 Analysis Script Examples

### 1. Chunk Size Optimization Script

```python
#!/usr/bin/env python3
"""
Chunk Size Optimization Script

Analyzes chunk sizes and provides optimization recommendations.
"""

import argparse
import statistics
from collections import defaultdict

def analyze_chunk_sizes(manager, content_type=None):
    """Analyze chunk sizes for optimization."""
    collections = manager.get_available_collections()
    
    if content_type:
        target_types = [content_type]
    else:
        target_types = collections.keys()
    
    results = {}
    
    for ct in target_types:
        if ct in collections:
            # Get chunks for this content type
            chunks = get_chunks_by_content_type(manager, ct)
            
            if chunks:
                sizes = [chunk['metadata']['size'] for chunk in chunks]
                
                results[ct] = {
                    'count': len(chunks),
                    'avg_size': statistics.mean(sizes),
                    'median_size': statistics.median(sizes),
                    'p95_size': sorted(sizes)[int(len(sizes) * 0.95)],
                    'min_size': min(sizes),
                    'max_size': max(sizes),
                    'recommended_size': sorted(sizes)[int(len(sizes) * 0.95)] + 1000
                }
    
    return results

def print_optimization_report(results):
    """Print optimization recommendations."""
    print("Chunk Size Optimization Report")
    print("=" * 50)
    
    for content_type, stats in results.items():
        print(f"\n{content_type.upper()}:")
        print(f"  Total chunks: {stats['count']}")
        print(f"  Average size: {stats['avg_size']:.0f} characters")
        print(f"  P95 size: {stats['p95_size']:.0f} characters")
        print(f"  Recommended: {stats['recommended_size']:.0f} characters")
        
        if stats['avg_size'] < 500:
            print("  ⚠️  Average chunk size is very small")
        elif stats['avg_size'] > 5000:
            print("  ⚠️  Average chunk size is very large")
        else:
            print("  ✅ Chunk size is within optimal range")
```

### 2. Search Quality Assessment Script

```python
#!/usr/bin/env python3
"""
Search Quality Assessment Script

Evaluates search quality with test queries and expected results.
"""

def assess_search_quality(query, test_cases):
    """Assess search quality with test cases."""
    results = {}
    
    for test_case in test_cases:
        query_text = test_case['query']
        expected_keywords = test_case['expected_keywords']
        
        response = query.query(query_text, n_results=5)
        
        # Analyze relevance
        relevance_scores = []
        for result in response['results']:
            content = result['content'].lower()
            keyword_matches = sum(1 for keyword in expected_keywords 
                                if keyword.lower() in content)
            relevance = keyword_matches / len(expected_keywords)
            relevance_scores.append(relevance)
        
        avg_relevance = sum(relevance_scores) / len(relevance_scores)
        
        results[query_text] = {
            'avg_relevance': avg_relevance,
            'top_similarity': max(r['similarity_score'] for r in response['results']),
            'result_count': len(response['results'])
        }
    
    return results

def print_quality_report(results):
    """Print search quality report."""
    print("Search Quality Assessment Report")
    print("=" * 40)
    
    total_relevance = 0
    total_queries = len(results)
    
    for query, metrics in results.items():
        relevance = metrics['avg_relevance']
        total_relevance += relevance
        
        print(f"\nQuery: {query}")
        print(f"  Relevance: {relevance:.2f}")
        print(f"  Top similarity: {metrics['top_similarity']:.3f}")
        print(f"  Results: {metrics['result_count']}")
        
        if relevance < 0.3:
            print("  ❌ Low relevance")
        elif relevance < 0.6:
            print("  ⚠️  Moderate relevance")
        else:
            print("  ✅ High relevance")
    
    avg_relevance = total_relevance / total_queries
    print(f"\nOverall Quality Score: {avg_relevance:.2f}")
    
    if avg_relevance < 0.4:
        print("❌ Search quality needs improvement")
    elif avg_relevance < 0.7:
        print("⚠️  Search quality is acceptable")
    else:
        print("✅ Search quality is excellent")
```

### 3. Content Coverage Analysis Script

```python
#!/usr/bin/env python3
"""
Content Coverage Analysis Script

Analyzes content coverage and identifies gaps in the knowledge base.
"""

def analyze_content_coverage(manager, config):
    """Analyze content coverage across different areas."""
    collections = manager.get_available_collections()
    
    # Define expected content areas
    expected_areas = {
        'authentication': ['auth', 'login', 'token', 'credential'],
        'api_usage': ['api', 'endpoint', 'request', 'response'],
        'troubleshooting': ['error', 'debug', 'fix', 'issue'],
        'configuration': ['config', 'setting', 'parameter'],
        'deployment': ['deploy', 'install', 'setup', 'environment']
    }
    
    coverage_results = {}
    
    for area, keywords in expected_areas.items():
        # Search for content related to this area
        area_content = []
        for content_type, info in collections.items():
            # This would require implementing content search
            # For now, we'll use a simplified approach
            area_content.append({
                'content_type': content_type,
                'count': info['count']
            })
        
        coverage_results[area] = {
            'keywords': keywords,
            'content_found': len(area_content),
            'coverage_score': len(area_content) / len(expected_areas) * 100
        }
    
    return coverage_results

def print_coverage_report(results):
    """Print content coverage report."""
    print("Content Coverage Analysis Report")
    print("=" * 40)
    
    for area, metrics in results.items():
        score = metrics['coverage_score']
        print(f"\n{area.upper()}:")
        print(f"  Coverage: {score:.1f}%")
        print(f"  Keywords: {', '.join(metrics['keywords'])}")
        print(f"  Content found: {metrics['content_found']}")
        
        if score < 30:
            print("  ❌ Poor coverage")
        elif score < 60:
            print("  ⚠️  Moderate coverage")
        else:
            print("  ✅ Good coverage")
```

## 🚀 Advanced Script Development

### Custom Query Analysis

```python
def analyze_query_patterns(query, log_file=None):
    """Analyze query patterns and performance."""
    if log_file:
        # Load query log
        queries = load_query_log(log_file)
    else:
        # Use test queries
        queries = [
            "How do I create a namespace?",
            "What are the authentication methods?",
            "How do I troubleshoot errors?",
            "What are the API endpoints?",
            "How do I configure the system?"
        ]
    
    analysis = {
        'total_queries': len(queries),
        'avg_response_time': 0,
        'success_rate': 0,
        'content_type_distribution': defaultdict(int)
    }
    
    response_times = []
    successful_queries = 0
    
    for query_text in queries:
        try:
            start_time = time.time()
            response = query.query(query_text, n_results=5)
            response_time = time.time() - start_time
            response_times.append(response_time)
            
            if response['results']:
                successful_queries += 1
                
                # Analyze content type distribution
                for result in response['results']:
                    content_type = result['metadata'].get('content_type', 'unknown')
                    analysis['content_type_distribution'][content_type] += 1
            
        except Exception as e:
            print(f"Query failed: {query_text} - {e}")
    
    analysis['avg_response_time'] = sum(response_times) / len(response_times)
    analysis['success_rate'] = successful_queries / len(queries) * 100
    
    return analysis
```

### Performance Monitoring

```python
def monitor_performance(manager, query, duration=300):
    """Monitor system performance over time."""
    import time
    import psutil
    
    start_time = time.time()
    metrics = []
    
    while time.time() - start_time < duration:
        # Collect metrics
        memory_usage = psutil.Process().memory_info().rss / 1024 / 1024
        cpu_percent = psutil.Process().cpu_percent()
        
        # Test query performance
        query_start = time.time()
        response = query.query("test query", n_results=3)
        query_time = time.time() - query_start
        
        metrics.append({
            'timestamp': time.time(),
            'memory_mb': memory_usage,
            'cpu_percent': cpu_percent,
            'query_time': query_time
        })
        
        time.sleep(10)  # Sample every 10 seconds
    
    return metrics
```

## 📚 Script Best Practices

### 1. Error Handling

```python
def robust_script_execution(func, *args, **kwargs):
    """Execute script function with robust error handling."""
    try:
        return func(*args, **kwargs)
    except KeyboardInterrupt:
        print("\nScript interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Script error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
```

### 2. Configuration Management

```python
def load_script_config(config_path=None):
    """Load configuration for script execution."""
    if config_path:
        return load_config(config_path)
    else:
        return load_config()
```

### 3. Output Formatting

```python
def format_script_output(results, format_type='text'):
    """Format script output in different formats."""
    if format_type == 'json':
        import json
        return json.dumps(results, indent=2)
    elif format_type == 'csv':
        import csv
        # Convert results to CSV format
        pass
    else:
        # Default text format
        return str(results)
```

---

*This scripts guide provides comprehensive tools for analyzing, monitoring, and optimizing the Holocron knowledge base system.*
