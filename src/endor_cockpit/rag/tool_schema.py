"""
OpenAI-compatible tool schema for RAG queries.

This module provides the tool definition that can be used with OpenAI function calling,
LangChain tools, and other LLM frameworks that support function calling.
"""

RAG_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "query_endor_documentation",
        "description": (
            "Search the Endor Cockpit documentation using semantic search. "
            "Use this to find relevant context about API usage, troubleshooting, "
            "design patterns, and best practices."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Natural language query describing what information you need "
                        "from the documentation. Examples: "
                        "'How do I create a namespace?', "
                        "'What are the API quirks for canonical naming?', "
                        "'How do I troubleshoot 403 errors?'"
                    ),
                },
                "max_results": {
                    "type": "integer",
                    "description": (
                        "Maximum number of results to return (default: 5, max: 10)"
                    ),
                    "minimum": 1,
                    "maximum": 10,
                    "default": 5,
                },
                "include_metadata": {
                    "type": "boolean",
                    "description": (
                        "Whether to include source file metadata in results "
                        "(default: true)"
                    ),
                    "default": True,
                },
            },
            "required": ["query"],
        },
    },
}

# Alternative schema for different frameworks
LANGCHAIN_TOOL_SCHEMA = {
    "name": "query_endor_documentation",
    "description": (
        "Search the Endor Cockpit documentation using semantic search. "
        "Use this to find relevant context about API usage, troubleshooting, "
        "design patterns, and best practices."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Natural language query describing what information you need "
                    "from the documentation."
                ),
            },
            "max_results": {
                "type": "integer",
                "description": (
                    "Maximum number of results to return (default: 5, max: 10)"
                ),
                "minimum": 1,
                "maximum": 10,
                "default": 5,
            },
            "include_metadata": {
                "type": "boolean",
                "description": (
                    "Whether to include source file metadata in results (default: true)"
                ),
                "default": True,
            },
        },
        "required": ["query"],
    },
}


# Function implementation for tool frameworks
def query_endor_documentation_tool(
    query: str, max_results: int = 5, include_metadata: bool = True
) -> dict:
    """
    Tool function for querying Endor Cockpit documentation.

    This function can be used directly with tool frameworks or wrapped
    for specific LLM integrations.

    Args:
        query: Natural language query
        max_results: Maximum number of results to return
        include_metadata: Whether to include source file metadata

    Returns:
        Dictionary containing query results
    """
    from .query import query_vector_db

    try:
        results = query_vector_db(
            query_text=query, n_results=max_results, include_metadata=include_metadata
        )

        # Format results for tool output
        formatted_results = {
            "success": True,
            "query": query,
            "result_count": len(results["results"]),
            "results": [],
        }

        for result in results["results"]:
            formatted_result = {
                "content": result["content"],
                "similarity_score": result["similarity_score"],
            }

            if include_metadata and "metadata" in result:
                formatted_result["source"] = result["metadata"].get("source", "Unknown")

            formatted_results["results"].append(formatted_result)

        return formatted_results

    except Exception as e:
        return {"success": False, "error": str(e), "query": query}
