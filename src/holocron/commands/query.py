"""
Query command implementation for Holocron.

Handles knowledge base querying with both argument-based and interactive modes.
"""

import json
import sys
from typing import Dict, Any

from ..query import query_holocron, get_holocron_info


def format_result(result: Dict[str, Any], format_type: str = "text") -> str:
    """Format a single query result for display."""
    if format_type == "json":
        return json.dumps(result, indent=2)
    
    # Text format
    content = result["content"]
    score = result["similarity_score"]
    metadata = result.get("metadata", {})
    
    # Truncate content for display
    if len(content) > 200:
        content = content[:200] + "..."
    
    output = f"Score: {score:.3f}\n"
    output += f"Content: {content}\n"
    
    if metadata:
        file_path = metadata.get("file_path", "unknown")
        file_name = metadata.get("file_name", "unknown")
        output += f"Source: {file_name} ({file_path})\n"
        
        if "h1_title" in metadata:
            output += f"Section: {metadata['h1_title']}\n"
        if "section_name" in metadata:
            output += f"Subsection: {metadata['section_name']}\n"
    
    output += "-" * 50 + "\n"
    return output


def query_command(args):
    """Execute the query command."""
    if args.query_text:
        # Argument-based query
        try:
            results = query_holocron(
                query_text=args.query_text,
                n_results=args.results,
                include_metadata=True
            )
            
            if args.format == "json":
                print(json.dumps(results, indent=2))
            else:
                print(f"Query: {results['query']}\n")
                print(f"Found {len(results['results'])} results:\n")
                
                for result in results["results"]:
                    print(format_result(result, args.format))
                    
        except Exception as e:
            print(f"Query failed: {e}")
            exit(1)
    else:
        # Interactive mode
        print("Holocron Interactive Query Mode")
        print("Enter your questions (type 'quit' to exit):\n")
        
        try:
            while True:
                query_text = input("Query: ").strip()
                
                if query_text.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye!")
                    break
                
                if not query_text:
                    continue
                
                try:
                    results = query_holocron(
                        query_text=query_text,
                        n_results=args.results,
                        include_metadata=True
                    )
                    
                    print(f"\nFound {len(results['results'])} results:\n")
                    
                    for result in results["results"]:
                        print(format_result(result, args.format))
                    
                    print()  # Add spacing between queries
                    
                except Exception as e:
                    print(f"Query failed: {e}\n")
                    
        except KeyboardInterrupt:
            print("\nGoodbye!")
        except Exception as e:
            print(f"Interactive mode failed: {e}")
            exit(1)
