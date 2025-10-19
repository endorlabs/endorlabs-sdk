"""
Core RAG query functionality for semantic search over Endor Cockpit documentation.

This module provides the main query interface for retrieving relevant context
from the vector database using natural language queries.
"""

import json
from pathlib import Path
from typing import Any, Dict

import chromadb


class RAGQueryError(Exception):
    """Custom exception for RAG query errors."""

    pass


class VectorDBQuery:
    """Main class for querying the Endor Cockpit vector database."""

    def __init__(self, vector_db_path: str = "workflow/vector_db"):
        """
        Initialize the RAG query interface.

        Args:
            vector_db_path: Path to the ChromaDB database directory
        """
        self.vector_db_path = vector_db_path
        self.collection_name = "endor_cockpit_docs"
        self.client = None
        self.collection = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize ChromaDB client and collection."""
        try:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(path=self.vector_db_path)

            # Get the collection
            self.collection = self.client.get_collection(name=self.collection_name)

        except Exception as e:
            raise RAGQueryError(f"Failed to initialize vector database: {e}") from e

    def query(
        self, query_text: str, n_results: int = 5, include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Query the vector database for relevant context.

        Args:
            query_text: Natural language query
            n_results: Number of results to return (default: 5)
            include_metadata: Whether to include metadata in results

        Returns:
            Dictionary containing query results with documents, metadata, and distances

        Raises:
            RAGQueryError: If query fails
        """
        try:
            # Prepare include parameters
            include = ["documents", "distances"]
            if include_metadata:
                include.append("metadatas")

            # Perform the query
            results = self.collection.query(
                query_texts=[query_text], n_results=n_results, include=include
            )

            # Format results
            formatted_results = {"query": query_text, "results": []}

            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    result = {
                        "content": doc,
                        "similarity_score": (
                            1 - results["distances"][0][i]
                            if results["distances"]
                            else 0.0
                        ),
                    }

                    if (
                        include_metadata
                        and results["metadatas"]
                        and results["metadatas"][0]
                    ):
                        result["metadata"] = results["metadatas"][0][i]

                    formatted_results["results"].append(result)

            return formatted_results

        except Exception as e:
            raise RAGQueryError(f"Query failed: {e}") from e

    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the vector database.

        Returns:
            Dictionary containing database statistics and metadata
        """
        try:
            # Get collection count
            count = self.collection.count()

            # Load manifest if available
            manifest_path = Path(self.vector_db_path).parent / "vector_db_manifest.json"
            manifest_info = {}

            if manifest_path.exists():
                with open(manifest_path, "r") as f:
                    manifest = json.load(f)
                    manifest_info = {
                        "total_documents": manifest.get("total_documents", 0),
                        "total_chunks": manifest.get("total_chunks", 0),
                        "embedding_model": manifest.get("embedding_model", "unknown"),
                        "last_updated": manifest.get("last_updated", "unknown"),
                    }

            return {
                "collection_name": self.collection_name,
                "chunk_count": count,
                "vector_db_path": self.vector_db_path,
                **manifest_info,
            }

        except Exception as e:
            raise RAGQueryError(f"Failed to get database info: {e}") from e


# Global query instance
_query_instance = None


def get_query_instance() -> VectorDBQuery:
    """Get or create the global query instance."""
    global _query_instance
    if _query_instance is None:
        _query_instance = VectorDBQuery()
    return _query_instance


def query_vector_db(
    query_text: str, n_results: int = 5, include_metadata: bool = True
) -> Dict[str, Any]:
    """
    Query the Endor Cockpit vector database for relevant context.

    This is the main function for AI agents to retrieve relevant documentation
    context using natural language queries.

    Args:
        query_text: Natural language query (e.g., "How do I create a namespace?")
        n_results: Number of results to return (default: 5)
        include_metadata: Whether to include source file metadata

    Returns:
        Dictionary containing:
        - query: The original query text
        - results: List of relevant context chunks with similarity scores

    Example:
        >>> results = query_vector_db("How do I troubleshoot 403 errors?")
        >>> for result in results["results"]:
        ...     print(f"Score: {result['similarity_score']:.3f}")
        ...     print(f"Content: {result['content'][:100]}...")

    Raises:
        RAGQueryError: If the query fails or vector database is not available
    """
    query_instance = get_query_instance()
    return query_instance.query(query_text, n_results, include_metadata)


def get_vector_db_info() -> Dict[str, Any]:
    """
    Get information about the vector database.

    Returns:
        Dictionary containing database statistics and metadata

    Example:
        >>> info = get_vector_db_info()
        >>> print(f"Total chunks: {info['chunk_count']}")
        >>> print(f"Last updated: {info['last_updated']}")
    """
    query_instance = get_query_instance()
    return query_instance.get_info()
