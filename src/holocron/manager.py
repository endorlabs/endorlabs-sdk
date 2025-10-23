"""
Vector Database Manager for Holocron

Manages ChromaDB vector database initialization and updates using semantic
chunking strategies optimized for different content types.
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from .config import HolocronConfig, load_config
from .content_types import ContentTypeRegistry
from .services import DatabaseService, FileProcessor

logger = logging.getLogger(__name__)


class VectorDBManager:
    """Manages ChromaDB vector database initialization and updates."""

    @staticmethod
    def _normalize_path(file_path: str) -> str:
        """
        Normalize file path for cross-platform compatibility.

        CRITICAL: This method ensures consistent path handling across Windows,
        macOS, and Linux. Always use this method before any path operations to
        prevent cross-platform issues.
        Source: Logbook entry 2025-01-27 - Cross-platform path handling learnings.
        """
        return os.path.normpath(file_path)

    def __init__(
        self,
        config: Optional[HolocronConfig] = None,
        db_path: Optional[str] = None,
        manifest_path: Optional[str] = None,
    ):
        """
        Initialize VectorDBManager with configuration.

        Args:
            config: HolocronConfig instance (loads from pyproject.toml if None)
            db_path: Override database path (deprecated, use config)
            manifest_path: Override manifest path (deprecated, use config)
        """
        # Load configuration
        if config is None:
            try:
                self.config = load_config()
            except Exception as e:
                logger.warning(f"Could not load configuration: {e}. Using defaults.")
                from .config import get_default_config

                self.config = get_default_config()
        else:
            self.config = config

        # Support legacy parameters for backward compatibility
        self.db_path = db_path or self.config.db_path
        self.manifest_path = manifest_path or self.config.manifest_path

        # Initialize content type registry
        self.content_registry = ContentTypeRegistry(
            content_types=self.config.content_types,
            collection_mapping=self.config.collection_mapping,
            collections=self.config.collections,
        )

        # Initialize services
        self.database_service = DatabaseService(self.config)
        self.file_processor = FileProcessor(self.config, self.content_registry)

        self.client = None
        self.collection = None
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> Dict:
        """Load or create manifest file."""
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path, "r") as f:
                return json.load(f)
        else:
            return {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "embedding_model": self.config.embedding_model,
                "chunking_strategy": "semantic_headers",
                "documents": {},
                "total_chunks": 0,
                "total_documents": 0,
            }

    def _save_manifest(self):
        """Save manifest file."""
        self.manifest["last_updated"] = datetime.now().isoformat()
        with open(self.manifest_path, "w") as f:
            json.dump(self.manifest, f, indent=2)

    def get_available_collections(self) -> Dict[str, Dict]:
        """
        Get available content collections with metadata.

        Returns:
            Dict mapping content_type to collection info (count, description, etc.)
        """
        if not self.client:
            self.initialize_db()

        if not self.collection and self.client:
            # Collection is initialized in initialize_db, but we need to get it
            collection_name = self.config.default_collection
            self.collection = self.client.get_collection(name=collection_name)

        # Get all unique content types from the database
        try:
            # Get all documents to determine available content types
            if self.collection:
                all_results = self.collection.get()
                content_types = set()

                metadatas = all_results.get("metadatas", [])
                if metadatas:
                    for metadata in metadatas:
                        if "content_type" in metadata:
                            content_types.add(metadata["content_type"])
            else:
                content_types = set()

            collections = {}
            if self.collection:
                for content_type in content_types:
                    # Count documents of this type by filtering
                    count_results = self.collection.get(
                        where={"content_type": content_type}
                    )
                    count = len(count_results.get("ids", []))

                    # Get description
                    description = self._get_content_type_description(content_type)

                    collections[content_type] = {
                        "count": count,
                        "description": description,
                        "enabled": True,
                    }

            return collections

        except Exception as e:
            logger.warning(f"Could not determine available collections: {e}")
            return {}

    def _get_content_type_description(self, content_type: str) -> str:
        """Get human-readable description for content type."""
        # Check if it's a collection first
        if content_type in self.config.collections:
            return self.config.collections[content_type].name

        # Legacy descriptions
        descriptions = {
            "markdown": "Internal documentation (docs/)",
            "external_docs": "External user documentation (docs.endorlabs.com)",
            "code": "Source code files (src/, tests/)",
            "api_spec": "OpenAPI specifications",
        }
        return descriptions.get(content_type, f"Unknown content type: {content_type}")

    def validate_chunking_config(self) -> Dict[str, str]:
        """Validate chunking configuration against actual content."""
        warnings = {}

        # Check collections (new format)
        for collection_name, config in self.config.collections.items():
            max_size = config.chunk_size
            if collection_name == "endor_user_docs" and max_size < 4000:
                warnings[collection_name] = (
                    f"max_chunk_size {max_size} may fragment sections "
                    "(recommended: 6000+)"
                )

        # Check legacy content types
        if self.config.content_types:
            for content_type_name, config in self.config.content_types.items():
                max_size = config.chunk_size
                if content_type_name == "external_docs" and max_size < 4000:
                    warnings[content_type_name] = (
                        f"max_chunk_size {max_size} may fragment sections "
                        "(recommended: 6000+)"
                    )

        return warnings

    def get_collection_filter(
        self, include: Optional[List[str]] = None, exclude: Optional[List[str]] = None
    ) -> Dict:
        """
        Build collection filter for database queries.

        Args:
            include: List of content types to include (None = all)
            exclude: List of content types to exclude

        Returns:
            Dict with 'where' clause for ChromaDB query
        """
        available = self.get_available_collections()

        if not include and not exclude:
            # No filtering - return all
            return {}

        # Start with all available types
        allowed_types = set(available.keys())

        # Apply include filter
        if include:
            include_set = set(include)
            # Validate include types
            invalid_types = include_set - allowed_types
            if invalid_types:
                raise ValueError(
                    f"Invalid content types: {invalid_types}. "
                    f"Available: {list(allowed_types)}"
                )
            allowed_types = include_set

        # Apply exclude filter
        if exclude:
            exclude_set = set(exclude)
            # Validate exclude types
            invalid_types = exclude_set - allowed_types
            if invalid_types:
                raise ValueError(
                    f"Invalid content types to exclude: {invalid_types}. "
                    f"Available: {list(allowed_types)}"
                )
            allowed_types = allowed_types - exclude_set

        if not allowed_types:
            raise ValueError("No content types remaining after filtering")

        return {"content_type": {"$in": list(allowed_types)}}

    def update_external_docs_metadata(
        self,
        openapi_metadata: Optional[Dict] = None,
        user_docs_count: Optional[int] = None,
    ):
        """
        Update manifest with external documentation metadata.

        Args:
            openapi_metadata: Metadata from OpenAPI spec download
            user_docs_count: Number of user docs pages downloaded
        """
        if "external_docs" not in self.manifest:
            self.manifest["external_docs"] = {}

        timestamp = datetime.now().isoformat()

        if openapi_metadata:
            self.manifest["external_docs"]["openapi_spec"] = {
                "last_downloaded": timestamp,
                "file_hash": openapi_metadata.get("file_hash"),
                "size": openapi_metadata.get("size"),
                "url": openapi_metadata.get("url"),
            }

        if user_docs_count is not None:
            self.manifest["external_docs"]["user_docs"] = {
                "last_downloaded": timestamp,
                "page_count": user_docs_count,
                "sitemap_url": "https://docs.endorlabs.com/sitemap.xml",
            }

        self._save_manifest()

    def _get_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file."""
        with open(file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def _detect_content_type(self, file_path: str) -> str:
        """Detect content type based on file path and content."""
        # Use content type registry for detection
        detected_type = self.content_registry.detect_content_type(file_path)
        return detected_type or "markdown"  # Default to markdown for unknown types

    def _semantic_chunk(
        self, content: str, content_type: str, file_path: str = ""
    ) -> List[Dict]:
        """Chunk content using semantic strategies."""
        try:
            # Use content type registry for chunking
            chunks = self.content_registry.chunk_content(
                content, file_path, content_type
            )

            # Convert Chunk objects to dictionaries for compatibility
            return [
                {"text": chunk.text, "metadata": chunk.metadata} for chunk in chunks
            ]
        except Exception as e:
            logger.warning(f"Failed to chunk {content_type} content: {e}")
            # Fallback to generic chunking
            return self._chunk_generic(content, content_type)

    def _chunk_generic(
        self, content: str, content_type: str = "markdown"
    ) -> List[Dict]:
        """Generic chunking fallback for unknown content types."""
        chunks = []
        words = content.split()
        current_chunk = []
        current_size = 0

        # Use default chunk size from config
        max_chunk_size = 1000  # Default fallback

        for word in words:
            current_chunk.append(word)
            current_size += len(word) + 1  # +1 for space

            if current_size > max_chunk_size:
                chunk_text = " ".join(current_chunk)
                chunks.append(
                    {
                        "text": chunk_text,
                        "metadata": {
                            "content_type": content_type,
                            "chunk_index": len(chunks),
                            "size": len(chunk_text),
                        },
                    }
                )

                current_chunk = []
                current_size = 0

        # Add final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append(
                {
                    "text": chunk_text,
                    "metadata": {
                        "content_type": content_type,
                        "chunk_index": len(chunks),
                        "size": len(chunk_text),
                    },
                }
            )

        return chunks

    def _should_rebuild_file(self, file_path: str) -> bool:
        """Check if file needs to be rebuilt based on manifest."""
        # Normalize path for consistent comparison
        normalized_path = self._normalize_path(file_path)

        if normalized_path not in self.manifest["documents"]:
            return True

        current_hash = self._get_file_hash(file_path)
        stored_hash = self.manifest["documents"][normalized_path]["file_hash"]

        return current_hash != stored_hash

    def _is_text_file(self, file_path: str) -> bool:
        """Check if file is a text file that should be processed."""
        # Skip binary file extensions
        binary_extensions = {
            ".pyc",
            ".pyo",
            ".pyd",
            ".so",
            ".dll",
            ".exe",
            ".bin",
            ".obj",
            ".o",
        }
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext in binary_extensions:
            return False

        # Skip files in __pycache__ directories
        if "__pycache__" in file_path:
            return False

        # Skip hidden files
        if os.path.basename(file_path).startswith("."):
            return False

        return True

    def _process_single_file(self, file_path: str) -> bool:
        """Process a single file and return True if it should be included."""
        logger.info(f"  -> File: {file_path}")
        if self._is_text_file(file_path):
            if self._should_rebuild_file(file_path):
                logger.info("    -> INCLUDED")
                return True
            else:
                logger.info("    -> SKIPPED (already processed)")
        else:
            logger.info("    -> EXCLUDED (not text file)")
        return False

    def _process_directory(self, dir_path: str) -> List[str]:
        """Process a directory and return list of files to include."""
        files_to_process = []
        logger.info(f"  -> Directory: {dir_path}")

        for root, dirs, files in os.walk(dir_path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in self.config.paths.exclude_dirs]

            # OS-agnostic path normalization
            normalized_root = os.path.normpath(root).replace(os.path.sep, "/")
            logger.info(f"    -> Walking: {normalized_root}")

            # Check for excluded paths using normalized paths
            if any(
                excluded in normalized_root
                for excluded in self.config.paths.exclude_dirs
            ):
                logger.info(f"    -> SKIPPED (excluded path): {normalized_root}")
                continue

            for file in files:
                file_path = os.path.normpath(os.path.join(root, file))

                if self._is_text_file(file_path):
                    if self._should_rebuild_file(file_path):
                        files_to_process.append(file_path)
                        logger.info(f"      -> INCLUDED: {file}")
                    else:
                        logger.info(f"      -> SKIPPED (already processed): {file}")
                else:
                    logger.info(f"      -> EXCLUDED (not text file): {file}")

        return files_to_process

    def _get_files_to_process(self) -> List[str]:
        """Get list of files to process for vector DB."""
        files_to_process = []

        logger.info("=== FILE DISCOVERY DEBUG ===")
        logger.info(f"INCLUDE_DIRS: {self.config.paths.include_dirs}")
        logger.info(f"EXCLUDE_DIRS: {self.config.paths.exclude_dirs}")

        for include_path in self.config.paths.include_dirs:
            logger.info(f"Processing include path: {include_path}")

            if os.path.isfile(include_path):
                if self._process_single_file(include_path):
                    files_to_process.append(include_path)
            elif os.path.isdir(include_path):
                files_to_process.extend(self._process_directory(include_path))
            else:
                logger.info(f"  -> NOT FOUND: {include_path}")

        logger.info(f"Total files to process: {len(files_to_process)}")
        return files_to_process

    def initialize_db(self, rebuild: bool = False, verbose: bool = False):
        """Initialize or rebuild the vector database."""
        # Initialize database service
        self.database_service.initialize_client(self.db_path)

        # Setup collection
        collection_name = self.config.default_collection
        if rebuild:
            # Clear manifest on rebuild
            self.manifest = self.database_service.create_manifest(
                self.config.embedding_model
            )
            logger.info("Manifest cleared for rebuild")

        self.database_service.setup_collection(collection_name, rebuild)

        # Update references for backward compatibility
        self.client = self.database_service.client
        self.collection = self.database_service.collection

        # Process files
        files_to_process = self._get_files_to_process()

        if not files_to_process:
            logger.info("No files need processing")
            return

        logger.info(f"Processing {len(files_to_process)} files")

        # Process files using FileProcessor service
        result = self.file_processor.process_files_batch(files_to_process)

        all_chunks = result["chunks"]
        document_metadata = result["document_metadata"]

        # Store chunks using DatabaseService
        if all_chunks:
            self.database_service.store_chunks_batch(all_chunks)

        # Update manifest
        self.manifest["documents"] = document_metadata
        self.manifest["total_chunks"] = len(all_chunks)
        self.manifest["total_documents"] = len(document_metadata)
        self.manifest["last_updated"] = datetime.now().isoformat()

        # Save manifest
        self._save_manifest()

        logger.info("Vector database initialization complete!")
        logger.info(f"   Total chunks: {len(all_chunks)}")
        logger.info(f"   Total documents: {len(document_metadata)}")
        logger.info(f"   Last updated: {self.manifest['last_updated']}")

    def query(self, query_text: str, n_results: int = 5) -> Dict:
        """Query the vector database."""
        if not self.collection:
            self.initialize_db()

        if self.collection:
            results = self.collection.query(
                query_texts=[query_text], n_results=n_results
            )
            # Convert QueryResult to Dict for compatibility
            return {
                "documents": results.get("documents", []),
                "metadatas": results.get("metadatas", []),
                "distances": results.get("distances", []),
                "ids": results.get("ids", []),
            }
        else:
            return {"documents": [], "metadatas": [], "distances": [], "ids": []}
