#!/usr/bin/env python3
"""
Example integrations for Endor Cockpit RAG system.

This file demonstrates how to integrate the RAG system with various
AI frameworks and use cases.
"""

import json
import sys
from typing import Dict, Any, List

# Example 1: Basic Usage
def basic_rag_example():
    """Basic RAG query example."""
    print("=== Basic RAG Example ===")
    
    try:
        from endor_cockpit.rag import query_vector_db, get_vector_db_info
        
        # Get database info
        info = get_vector_db_info()
        print(f"Database contains {info['chunk_count']} chunks")
        
        # Query the documentation
        results = query_vector_db("How do I create a namespace?", n_results=3)
        
        print(f"\nQuery: {results['query']}")
        print(f"Found {len(results['results'])} results:\n")
        
        for i, result in enumerate(results['results'], 1):
            print(f"{i}. Score: {result['similarity_score']:.3f}")
            print(f"   Content: {result['content'][:150]}...")
            print()
            
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure endor-cockpit is installed with RAG dependencies")
    except Exception as e:
        print(f"Error: {e}")


# Example 2: OpenAI Function Calling
def openai_integration_example():
    """Example of integrating with OpenAI function calling."""
    print("=== OpenAI Integration Example ===")
    
    try:
        import openai
        from endor_cockpit.rag import RAG_TOOL_SCHEMA, query_endor_documentation_tool
        
        # Simulate OpenAI function call
        def simulate_openai_call(query: str):
            """Simulate OpenAI function calling."""
            print(f"Simulating OpenAI call for: {query}")
            
            # This would normally come from OpenAI's tool_choice
            tool_call_args = {
                "query": query,
                "max_results": 3,
                "include_metadata": True
            }
            
            # Execute the tool
            results = query_endor_documentation_tool(**tool_call_args)
            return results
        
        # Test the integration
        results = simulate_openai_call("How do I troubleshoot 403 errors?")
        
        if results["success"]:
            print(f"Found {results['result_count']} results")
            for result in results["results"]:
                print(f"  Score: {result['similarity_score']:.3f}")
                print(f"  Content: {result['content'][:100]}...")
        else:
            print(f"Query failed: {results['error']}")
            
    except ImportError as e:
        print(f"OpenAI not available: {e}")
    except Exception as e:
        print(f"Error: {e}")


# Example 3: LangChain Integration
def langchain_integration_example():
    """Example of integrating with LangChain."""
    print("=== LangChain Integration Example ===")
    
    try:
        from langchain.tools import Tool
        from endor_cockpit.rag import query_endor_documentation_tool
        
        # Create LangChain tool
        rag_tool = Tool(
            name="query_endor_documentation",
            description="Search Endor Cockpit documentation using semantic search",
            func=query_endor_documentation_tool
        )
        
        print("Created LangChain tool:")
        print(f"  Name: {rag_tool.name}")
        print(f"  Description: {rag_tool.description}")
        
        # Test the tool
        results = rag_tool.run({
            "query": "What are the design principles?",
            "max_results": 2,
            "include_metadata": True
        })
        
        print(f"\nTool execution results:")
        print(f"  Success: {results.get('success', False)}")
        if results.get('success'):
            print(f"  Result count: {results.get('result_count', 0)}")
            for result in results.get('results', []):
                print(f"    Score: {result['similarity_score']:.3f}")
                print(f"    Content: {result['content'][:100]}...")
        
    except ImportError as e:
        print(f"LangChain not available: {e}")
    except Exception as e:
        print(f"Error: {e}")


# Example 4: Custom Agent Framework
class EndorRAGAgent:
    """Custom agent framework example."""
    
    def __init__(self):
        self.rag_tool = None
        try:
            from endor_cockpit.rag import query_endor_documentation_tool
            self.rag_tool = query_endor_documentation_tool
        except ImportError:
            print("RAG tool not available")
    
    def get_context(self, query: str, max_results: int = 3) -> str:
        """Get relevant context for a query."""
        if not self.rag_tool:
            return "RAG tool not available"
        
        try:
            results = self.rag_tool(
                query=query,
                max_results=max_results,
                include_metadata=True
            )
            
            if not results.get("success", False):
                return f"Query failed: {results.get('error', 'Unknown error')}"
            
            # Format context
            context_parts = []
            for result in results.get("results", []):
                context_parts.append(f"Score: {result['similarity_score']:.3f}\n{result['content']}")
            
            return "\n\n---\n\n".join(context_parts)
            
        except Exception as e:
            return f"Error getting context: {e}"
    
    def respond(self, user_query: str) -> str:
        """Generate response with RAG context."""
        context = self.get_context(user_query)
        
        # Simulate LLM response (in real implementation, use actual LLM)
        response = f"""
Based on the Endor Cockpit documentation:

{context}

User question: {user_query}

[This would be the LLM's response based on the context above]
"""
        return response


def custom_agent_example():
    """Example of custom agent framework."""
    print("=== Custom Agent Framework Example ===")
    
    agent = EndorRAGAgent()
    
    # Test queries
    test_queries = [
        "How do I create a namespace?",
        "What are the API quirks?",
        "How do I troubleshoot errors?"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        response = agent.respond(query)
        print(f"Response: {response[:200]}...")


# Example 5: CLI Tool
def cli_tool_example():
    """Example CLI tool for RAG queries."""
    print("=== CLI Tool Example ===")
    
    def query_docs_cli(query: str, max_results: int = 3):
        """CLI function for querying documentation."""
        try:
            from endor_cockpit.rag import query_vector_db
            
            results = query_vector_db(query, n_results=max_results)
            
            print(f"Query: {query}")
            print(f"Found {len(results['results'])} results:\n")
            
            for i, result in enumerate(results['results'], 1):
                print(f"{i}. Score: {result['similarity_score']:.3f}")
                print(f"   Content: {result['content'][:200]}...")
                print()
                
        except Exception as e:
            print(f"Error: {e}")
    
    # Test CLI functionality
    test_queries = [
        "How do I create a namespace?",
        "What are the security best practices?",
        "How do I troubleshoot 403 errors?"
    ]
    
    for query in test_queries:
        query_docs_cli(query, max_results=2)
        print("-" * 50)


# Example 6: Batch Processing
def batch_processing_example():
    """Example of batch processing multiple queries."""
    print("=== Batch Processing Example ===")
    
    try:
        from endor_cockpit.rag import query_vector_db
        
        queries = [
            "How do I create a namespace?",
            "What are the API quirks for canonical naming?",
            "How do I troubleshoot 403 Forbidden errors?",
            "What are the security best practices?",
            "How do I write tests?"
        ]
        
        results = {}
        for query in queries:
            try:
                result = query_vector_db(query, n_results=2)
                results[query] = {
                    "success": True,
                    "result_count": len(result['results']),
                    "top_score": max(r['similarity_score'] for r in result['results']) if result['results'] else 0
                }
            except Exception as e:
                results[query] = {
                    "success": False,
                    "error": str(e)
                }
        
        print("Batch processing results:")
        for query, result in results.items():
            if result["success"]:
                print(f"  {query}: {result['result_count']} results, top score: {result['top_score']:.3f}")
            else:
                print(f"  {query}: FAILED - {result['error']}")
                
    except Exception as e:
        print(f"Batch processing error: {e}")


def main():
    """Run all examples."""
    print("Endor Cockpit RAG Integration Examples")
    print("=" * 50)
    
    examples = [
        basic_rag_example,
        openai_integration_example,
        langchain_integration_example,
        custom_agent_example,
        cli_tool_example,
        batch_processing_example
    ]
    
    for example in examples:
        try:
            example()
            print("\n" + "=" * 50)
        except Exception as e:
            print(f"Example failed: {e}")
            print("\n" + "=" * 50)


if __name__ == "__main__":
    main()
