"""
File Processor Service for Holocron.

Handles file processing, content detection, and chunking operations.
Extracted from VectorDBManager to reduce complexity.
"""

import hashlib
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from ..config import HolocronConfig
from ..content_types import ContentTypeRegistry

logger = logging.getLogger(__name__)


class FileProcessor:
    """Service for processing files and generating chunks."""

    def __init__(self, config: HolocronConfig, content_registry: ContentTypeRegistry):
        """Initialize file processor with configuration and content registry."""
        self.config = config
        self.content_registry = content_registry

    def _normalize_path(self, file_path: str) -> str:
        """Normalize file path for cross-platform compatibility."""
        return os.path.normpath(file_path)

    def _get_file_hash(self, file_path: str) -> str:
        """Get MD5 hash of file content."""
        try:
            with open(file_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return "unknown"

    def _detect_content_type(self, file_path: str) -> Optional[str]:
        """Detect content type for a file."""
        return self.content_registry.detect_content_type(file_path)

    def _semantic_chunk(
        self, content: str, content_type: str, file_path: str
    ) -> List[Dict]:
        """Generate semantic chunks for content."""
        return self.content_registry.chunk_content(content, file_path, content_type)

    def process_file(self, file_path: str) -> Dict:
        """Process a single file and return chunks with metadata."""
        logger.info(f"Processing: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            content_type = self._detect_content_type(file_path)
            logger.info(f"  -> Detected content type: {content_type}")
            logger.info(f"  -> Content length: {len(content)} characters")

            # Log before chunking
            logger.info(f"  -> Starting chunking for {content_type} content")
            chunks = self._semantic_chunk(content, content_type, file_path)
            logger.info(f"  -> Generated {len(chunks)} chunks")

            # Log chunk details
            for i, chunk in enumerate(chunks):
                chunk_content_type = chunk["metadata"].get("content_type", "unknown")
                chunk_size = chunk["metadata"].get("size", 0)
                logger.info(
                    f"    -> Chunk {i}: content_type={chunk_content_type}, "
                    f"size={chunk_size}"
                )

            # Add file metadata to chunks
            normalized_path = self._normalize_path(file_path)
            for i, chunk in enumerate(chunks):
                chunk["metadata"]["file_path"] = normalized_path
                chunk["metadata"]["file_name"] = os.path.basename(file_path)
                chunk["metadata"]["chunk_id"] = f"{normalized_path}:{i}"

                # Clean metadata to remove None values
                chunk["metadata"] = {
                    k: v for k, v in chunk["metadata"].items() if v is not None
                }

            # Create file metadata
            file_hash = self._get_file_hash(file_path)
            file_metadata = {
                "file_hash": file_hash,
                "chunks": len(chunks),
                "last_modified": datetime.now().isoformat(),
                "content_type": content_type,
            }

            logger.info(f"  -> Added {len(chunks)} chunks to batch")
            logger.info(f"  -> Updated manifest for {normalized_path}")

            return {
                "chunks": chunks,
                "file_metadata": file_metadata,
                "normalized_path": normalized_path,
                "success": True,
            }

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return {
                "chunks": [],
                "file_metadata": {},
                "normalized_path": self._normalize_path(file_path),
                "success": False,
                "error": str(e),
            }

    def process_files_batch(self, file_paths: List[str]) -> Dict:
        """Process multiple files and return all chunks and metadata."""
        all_chunks = []
        document_metadata = {}
        processed_count = 0
        error_count = 0

        for file_path in file_paths:
            result = self.process_file(file_path)

            if result["success"]:
                all_chunks.extend(result["chunks"])
                document_metadata[result["normalized_path"]] = result["file_metadata"]
                processed_count += 1
            else:
                error_count += 1

        logger.info(
            f"Processed {processed_count} files successfully, {error_count} errors"
        )

        return {
            "chunks": all_chunks,
            "document_metadata": document_metadata,
            "processed_count": processed_count,
            "error_count": error_count,
        }
