"""
Database Service for Holocron.

Handles ChromaDB operations and vector database management.
Extracted from VectorDBManager to reduce complexity.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import chromadb
from chromadb.config import Settings
from chromadb.api import ClientAPI

from ..config import HolocronConfig

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for managing ChromaDB operations."""

    def __init__(self, config: HolocronConfig):
        """Initialize database service with configuration."""
        self.config = config
        self.client: Optional[ClientAPI] = None
        self.collection: Optional[chromadb.Collection] = None

    def initialize_client(self, db_path: str) -> None:
        """Initialize ChromaDB client and collection."""
        # Create database directory
        import os

        os.makedirs(db_path, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=db_path, settings=Settings(anonymized_telemetry=False)
        )
        logger.info(f"ChromaDB client initialized at: {db_path}")

    def setup_collection(self, collection_name: str, rebuild: bool = False) -> None:
        """Create or get collection with proper metadata."""
        if not self.client:
            raise RuntimeError(
                "Client not initialized. Call initialize_client() first."
            )

        if rebuild:
            try:
                self.client.delete_collection(collection_name)
                logger.info(f"Deleted existing collection: {collection_name}")
            except Exception:
                logger.info(f"Collection {collection_name} did not exist")

        logger.info(f"Creating or getting collection: {collection_name}")
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Endor Cockpit documentation vector database"},
        )
        logger.info(f"Collection created/retrieved: {self.collection.name if self.collection else 'None'}")

    def store_chunks_batch(self, chunks: List[Dict], batch_size: int = 1000) -> None:
        """Store chunks in batches with proper error handling."""
        if not self.collection:
            raise RuntimeError(
                "Collection not initialized. Call setup_collection() first."
            )

        if not chunks:
            logger.info("No chunks to store")
            return

        logger.info("=== DATABASE STORAGE DEBUG ===")
        logger.info(f"Total chunks to store: {len(chunks)}")

        # Log content type distribution
        content_type_counts = {}
        for chunk in chunks:
            content_type = chunk["metadata"].get("content_type", "unknown")
            content_type_counts[content_type] = (
                content_type_counts.get(content_type, 0) + 1
            )
        logger.info(f"Content type distribution: {content_type_counts}")

        total_chunks = len(chunks)

        for i in range(0, total_chunks, batch_size):
            batch_chunks = chunks[i : i + batch_size]
            texts = [chunk["text"] for chunk in batch_chunks]
            metadatas = [chunk["metadata"] for chunk in batch_chunks]

            logger.info(
                f"  -> Processing batch {i // batch_size + 1}: "
                f"{len(batch_chunks)} chunks"
            )
            logger.info(
                f"  -> Batch content types: "
                f"{[chunk['metadata'].get('content_type') for chunk in batch_chunks[:5]]}"  # noqa: E501
            )

            # Log embedding model interface
            logger.info(f"  -> Calling embedding model for {len(texts)} texts")
            logger.info(
                f"  -> Sample text length: {len(texts[0]) if texts else 0} characters"
            )
            ids = [chunk["metadata"]["chunk_id"] for chunk in batch_chunks]

            try:
                self.collection.add(
                    documents=texts,
                    metadatas=metadatas,
                    ids=ids,
                )
                logger.info(f"  -> Stored batch {i // batch_size + 1} successfully")
            except Exception as e:
                logger.error(f"  -> Error storing batch {i // batch_size + 1}: {e}")
                raise

        logger.info("All chunks stored successfully")

    def get_collection_info(self) -> Dict:
        """Get information about the current collection."""
        if not self.collection:
            return {"count": 0, "name": "No collection"}

        try:
            count = self.collection.count()
            return {
                "count": count,
                "name": self.collection.name,
                "metadata": self.collection.metadata,
            }
        except Exception as e:
            logger.warning(f"Could not get collection info: {e}")
            return {"count": 0, "name": "Error", "error": str(e)}

    def create_manifest(self, embedding_model: str) -> Dict:
        """Create a new manifest for the database."""
        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "embedding_model": embedding_model,
            "documents": {},
            "total_chunks": 0,
            "total_documents": 0,
        }
