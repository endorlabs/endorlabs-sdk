"""
Vector Database Manager for Holocron

Manages ChromaDB vector database initialization and updates using semantic
chunking strategies optimized for different content types.
"""

import hashlib
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

# Chunking strategies for different content types
# Updated based on empirical analysis with 1000 token buffer
CHUNKING_STRATEGY = {
    "markdown": {
        "max_chunk_size": 1607,  # tokens - P95 (607) + 1000 buffer
        "overlap": 400,  # tokens - increased for better context
        "split_on": ["##"],  # Only H2 headers - preserve H3 subsections
        "preserve_structure": True,
        "preserve_complete_sections": True,  # Never split H2 sections
    },
    "external_docs": {
        "max_chunk_size": 2165,  # tokens - P95 (1165) + 1000 buffer
        "overlap": 500,  # tokens - increased for better context
        "split_on": [
            "===",
            "---",
            "\n\n",
            "Introduction",
            "About", 
            "Prerequisites",
        ],  # External doc patterns - prioritize major sections
        "preserve_structure": True,
        "preserve_complete_sections": True,  # Preserve complete procedures
    },
    "code": {
        "max_chunk_size": 6851,  # tokens - P95 (5851) + 1000 buffer
        "overlap": 500,  # tokens - increased for better context
        "split_on": ["def ", "class "],  # Functions and classes only
        "preserve_structure": True,
        "preserve_complete_sections": True,  # Keep complete functions/classes
    },
    "api_spec": {
        "max_chunk_size": 5000,  # tokens - split by individual endpoints
        "overlap": 300,  # tokens
        "split_on": ['"paths":', '"components":', '"definitions":'],
        "preserve_structure": True,
        "split_by_endpoints": True,  # Split large service groups by individual endpoints
    },
}

# Content type detection patterns
CONTENT_TYPE_PATTERNS = {
    "external_docs": [
        r"\.workspace/downloads/user-docs/.*\.md$"
    ],  # External user docs (check first)
    "markdown": [r"\.md$", r"\.rst$"],
    "code": [r"\.py$", r"\.js$", r"\.ts$", r"\.go$", r"\.java$"],
    "api_spec": [r"openapi.*\.json$", r"swagger.*\.json$", r"\.yaml$", r"\.yml$"],
}

# Directories to include in vector DB
INCLUDE_DIRS = [
    "docs/",
    "src/",
    "tests/",
    ".workspace/downloads/openapi-swagger.json",
    ".workspace/downloads/user-docs/",
]

# Directories to exclude
EXCLUDE_DIRS = [
    "__pycache__",
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "holocron_data",  # Exclude old data directory
    ".workspace/holocron_data",  # Exclude only the vector database directory
    "tmp",  # Exclude old tmp directory
]


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
        db_path: str = ".workspace/holocron_data/vector_db",
        manifest_path: str = ".workspace/holocron_data/vector_db_manifest.json",
    ):
        self.db_path = db_path
        self.manifest_path = manifest_path
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
                "embedding_model": "text-embedding-3-small",
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
        # Normalize path for cross-platform compatibility
        normalized_path = self._normalize_path(file_path).replace(os.path.sep, "/")

        for content_type, patterns in CONTENT_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, normalized_path, re.IGNORECASE):
                    return content_type

        # Default to markdown for unknown types
        return "markdown"

    def _semantic_chunk(self, content: str, content_type: str) -> List[Dict]:
        """Chunk content using semantic strategies."""
        strategy = CHUNKING_STRATEGY.get(content_type, CHUNKING_STRATEGY["markdown"])
        chunks = []

        if content_type == "markdown":
            chunks = self._chunk_markdown(content, strategy)
        elif content_type == "external_docs":
            chunks = self._chunk_external_docs(content, strategy)
        elif content_type == "code":
            chunks = self._chunk_code(content, strategy)
        elif content_type == "api_spec":
            chunks = self._chunk_api_spec(content, strategy)
        else:
            chunks = self._chunk_generic(content, strategy)

        return chunks

    def _chunk_markdown(self, content: str, strategy: Dict) -> List[Dict]:
        """Chunk markdown content by headers and paragraphs with enhanced metadata."""
        chunks = []
        lines = content.split("\n")
        current_chunk = []
        current_size = 0

        # Track document structure for enhanced metadata
        h1_title = None
        resource_type = None
        current_section = None
        current_subsection = None
        current_header_level = None

        for line in lines:
            # Check if this is an H2 header (starts with ## but not ###)
            if line.strip().startswith("## ") and not line.strip().startswith("### "):
                # Save current chunk if it has content
                if current_chunk:
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "metadata": {
                                "content_type": "markdown",
                                "chunk_index": len(chunks),
                                "size": len(chunk_text),
                                "resource_type": resource_type,
                                "h1_title": h1_title,
                                "section_name": current_section,
                                "subsection_name": current_subsection,
                                "header_level": current_header_level,
                            },
                        }
                    )

                # Parse header level and content
                header_level = self._get_header_level(line)
                header_text = self._clean_header_text(line)

                # Update tracking variables
                if header_level == "h1":
                    h1_title = header_text
                    resource_type = self._extract_resource_type(header_text)
                    current_section = None
                    current_subsection = None
                elif header_level == "h2":
                    current_section = header_text
                    current_subsection = None
                elif header_level == "h3":
                    current_subsection = header_text

                current_header_level = header_level

                # Start new chunk with header
                current_chunk = [line]
                current_size = len(line)
            else:
                # Add line to current chunk
                current_chunk.append(line)
                current_size += len(line) + 1  # +1 for newline

                # Check if chunk is too large (only split if not preserving complete sections)
                if (current_size > strategy["max_chunk_size"] and 
                    not strategy.get("preserve_complete_sections", False)):
                    # Save current chunk
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "metadata": {
                                "content_type": "markdown",
                                "chunk_index": len(chunks),
                                "size": len(chunk_text),
                                "resource_type": resource_type,
                                "h1_title": h1_title,
                                "section_name": current_section,
                                "subsection_name": current_subsection,
                                "header_level": current_header_level,
                            },
                        }
                    )

                    # Start new chunk
                    current_chunk = []
                    current_size = 0

        # Add final chunk
        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                {
                    "text": chunk_text,
                    "metadata": {
                        "content_type": "markdown",
                        "chunk_index": len(chunks),
                        "size": len(chunk_text),
                        "resource_type": resource_type,
                        "h1_title": h1_title,
                        "section_name": current_section,
                        "subsection_name": current_subsection,
                        "header_level": current_header_level,
                    },
                }
            )

        return chunks

    def _extract_source_url(self, lines: List[str]) -> str:
        """Extract source URL from HTML comment in first few lines."""
        for line in lines[:5]:  # Check first few lines for source URL
            if line.strip().startswith("<!-- Source:"):
                return line.strip().replace("<!-- Source: ", "").replace(" -->", "")
        return ""

    def _should_skip_line(self, line: str) -> bool:
        """Check if line should be skipped (HTML comments, breadcrumbs)."""
        stripped = line.strip()
        return (
            stripped.startswith("<!--")
            or stripped.startswith("1. [")
            or stripped.startswith("2. [")
            or stripped.startswith("3. [")
        )

    def _create_chunk_metadata(
        self,
        chunk_text: str,
        chunk_index: int,
        source_url: str,
        h1_title: str,
        current_section: str,
        current_subsection: str,
    ) -> Dict:
        """Create metadata dictionary for a chunk."""
        return {
            "content_type": "external_docs",
            "chunk_index": chunk_index,
            "size": len(chunk_text),
            "source_url": source_url or "",
            "h1_title": h1_title or "",
            "section_name": current_section or "",
            "subsection_name": current_subsection or "",
        }

    def _save_current_chunk(
        self,
        current_chunk: List[str],
        chunks: List[Dict],
        source_url: str,
        h1_title: Optional[str],
        current_section: Optional[str],
        current_subsection: Optional[str],
    ) -> None:
        """Save current chunk to chunks list."""
        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                {
                    "text": chunk_text,
                    "metadata": self._create_chunk_metadata(
                        chunk_text,
                        len(chunks),
                        source_url,
                        h1_title,
                        current_section,
                        current_subsection,
                    ),
                }
            )

    def _update_header_tracking(
        self, line: str, h1_title: Optional[str], current_section: Optional[str], current_subsection: Optional[str]
    ) -> tuple:
        """Update header tracking variables based on line content."""
        header_text = self._clean_external_header_text(line)

        if line.strip().endswith("="):
            return header_text, "", ""
        elif line.strip().endswith("-"):
            return h1_title or "", header_text, ""
        else:
            return h1_title or "", current_section or "", header_text

    def _chunk_external_docs(self, content: str, strategy: Dict) -> List[Dict]:
        """Chunk external documentation content optimized for downloaded user docs."""
        chunks = []
        lines = content.split("\n")
        current_chunk = []
        current_size = 0

        # Track document structure for enhanced metadata
        h1_title = None
        current_section = None
        current_subsection = None
        source_url = self._extract_source_url(lines)

        for line in lines:
            # Skip HTML comments and breadcrumbs
            if self._should_skip_line(line):
                continue

            # Check if this is a header (using underline style or title case)
            if self._is_external_doc_header(line):
                # Save current chunk if it has content
                self._save_current_chunk(
                    current_chunk,
                    chunks,
                    source_url,
                    h1_title,
                    current_section,
                    current_subsection,
                )

                # Update tracking variables
                h1_title, current_section, current_subsection = (
                    self._update_header_tracking(
                        line, h1_title, current_section, current_subsection
                    )
                )

                # Start new chunk with header
                current_chunk = [line]
                current_size = len(line)
            else:
                # Add line to current chunk
                current_chunk.append(line)
                current_size += len(line) + 1  # +1 for newline

                # Check if chunk is too large
                if current_size > strategy["max_chunk_size"]:
                    # Save current chunk
                    self._save_current_chunk(
                        current_chunk,
                        chunks,
                        source_url,
                        h1_title,
                        current_section,
                        current_subsection,
                    )

                    # Start new chunk
                    current_chunk = []
                    current_size = 0

        # Add final chunk
        self._save_current_chunk(
            current_chunk,
            chunks,
            source_url,
            h1_title,
            current_section,
            current_subsection,
        )

        return chunks

    def _is_external_doc_header(self, line: str) -> bool:
        """Check if line is a header in external docs format."""
        stripped = line.strip()
        # Check for underline headers (=== or ---)
        if len(stripped) > 0 and stripped.endswith("=") and len(stripped) > 3:
            return True
        if len(stripped) > 0 and stripped.endswith("-") and len(stripped) > 3:
            return True
        # Check for title case headers (no markdown #)
        if (
            len(stripped) > 0
            and not stripped.startswith("#")
            and not stripped.startswith("*")
            and not stripped.startswith("-")
            and stripped.isupper()
            and len(stripped) > 5
        ):
            return True
        return False

    def _clean_external_header_text(self, line: str) -> str:
        """Clean external doc header text."""
        # Remove underline characters
        text = line.strip().rstrip("=-")

        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def _get_header_level(self, line: str) -> str:
        """Extract header level from markdown line."""
        stripped = line.strip()
        if stripped.startswith("# "):
            return "h1"
        elif stripped.startswith("## "):
            return "h2"
        elif stripped.startswith("### "):
            return "h3"
        elif stripped.startswith("#### "):
            return "h4"
        elif stripped.startswith("##### "):
            return "h5"
        elif stripped.startswith("###### "):
            return "h6"
        else:
            return "unknown"

    def _clean_header_text(self, line: str) -> str:
        """Clean header text by removing markdown formatting and emojis."""
        # Remove markdown header markers
        text = line.strip().lstrip("#").strip()

        # Remove emojis and special characters
        text = re.sub(r"[^\w\s\-\.]", "", text)

        # Clean up extra whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def _extract_resource_type(self, h1_title: str) -> str:
        """Extract resource type from H1 title."""
        # Look for patterns like "Project Resource Deep-Dive",
        # "Finding Resource Deep-Dive"
        if "Project" in h1_title:
            return "project"
        elif "Finding" in h1_title:
            return "finding"
        elif "Policy" in h1_title:
            return "policy"
        elif "Namespace" in h1_title:
            return "namespace"
        elif "Scan" in h1_title:
            return "scan"
        else:
            return "unknown"

    def _chunk_code(self, content: str, strategy: Dict) -> List[Dict]:
        """Chunk code content by functions and classes."""
        chunks = []
        lines = content.split("\n")
        current_chunk = []
        current_size = 0

        for line in lines:
            # Check if this is a function or class definition
            if line.strip().startswith(("def ", "class ")):
                # Save current chunk if it has content
                if current_chunk:
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "metadata": {
                                "content_type": "code",
                                "chunk_index": len(chunks),
                                "size": len(chunk_text),
                            },
                        }
                    )

                # Start new chunk
                current_chunk = [line]
                current_size = len(line)
            else:
                # Add line to current chunk
                current_chunk.append(line)
                current_size += len(line) + 1

                # Check if chunk is too large
                if current_size > strategy["max_chunk_size"]:
                    # Save current chunk
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "metadata": {
                                "content_type": "code",
                                "chunk_index": len(chunks),
                                "size": len(chunk_text),
                            },
                        }
                    )

                    # Start new chunk
                    current_chunk = []
                    current_size = 0

        # Add final chunk
        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                {
                    "text": chunk_text,
                    "metadata": {
                        "content_type": "code",
                        "chunk_index": len(chunks),
                        "size": len(chunk_text),
                    },
                }
            )

        return chunks

    def _chunk_api_spec(self, content: str, strategy: Dict) -> List[Dict]:
        """Chunk API specification content by sections."""
        chunks = []
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # If not JSON, treat as generic content
            return self._chunk_generic(content, strategy)

        # Chunk by major sections
        for section_name, section_content in data.items():
            if isinstance(section_content, dict):
                section_text = json.dumps({section_name: section_content}, indent=2)
                chunks.append(
                    {
                        "text": section_text,
                        "metadata": {
                            "content_type": "api_spec",
                            "section": section_name,
                            "chunk_index": len(chunks),
                            "size": len(section_text),
                        },
                    }
                )

        return chunks

    def _chunk_generic(self, content: str, strategy: Dict) -> List[Dict]:
        """Generic chunking for unknown content types."""
        chunks = []
        words = content.split()
        current_chunk = []
        current_size = 0

        for word in words:
            current_chunk.append(word)
            current_size += len(word) + 1  # +1 for space

            if current_size > strategy["max_chunk_size"]:
                chunk_text = " ".join(current_chunk)
                chunks.append(
                    {
                        "text": chunk_text,
                        "metadata": {
                            "content_type": "generic",
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
                        "content_type": "generic",
                        "chunk_index": len(chunk_text),
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

    def _get_files_to_process(self) -> List[str]:
        """Get list of files to process for vector DB."""
        files_to_process = []
        
        logger.info("=== FILE DISCOVERY DEBUG ===")
        logger.info(f"INCLUDE_DIRS: {INCLUDE_DIRS}")
        logger.info(f"EXCLUDE_DIRS: {EXCLUDE_DIRS}")

        for include_path in INCLUDE_DIRS:
            logger.info(f"Processing include path: {include_path}")
            
            if os.path.isfile(include_path):
                logger.info(f"  -> File: {include_path}")
                if self._is_text_file(include_path) and self._should_rebuild_file(include_path):
                    files_to_process.append(include_path)
                    logger.info(f"    -> INCLUDED")
                else:
                    logger.info(f"    -> EXCLUDED (not text or should not rebuild)")
            elif os.path.isdir(include_path):
                logger.info(f"  -> Directory: {include_path}")
                for root, dirs, files in os.walk(include_path):
                    # Skip excluded directories
                    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

                    # OS-agnostic path normalization
                    normalized_root = os.path.normpath(root).replace(os.path.sep, "/")
                    logger.info(f"    -> Walking: {normalized_root}")
                    
                    # Check for excluded paths using normalized paths
                    if any(excluded in normalized_root for excluded in EXCLUDE_DIRS):
                        logger.info(f"    -> SKIPPED (excluded path): {normalized_root}")
                        continue

                    for file in files:
                        file_path = os.path.normpath(os.path.join(root, file))
                        normalized_file_path = file_path.replace(os.path.sep, "/")
                        
                        if self._is_text_file(file_path) and self._should_rebuild_file(file_path):
                            files_to_process.append(file_path)
                            logger.info(f"      -> INCLUDED: {file}")
                        else:
                            logger.info(f"      -> EXCLUDED: {file}")
            else:
                logger.info(f"  -> NOT FOUND: {include_path}")

        logger.info(f"Total files to process: {len(files_to_process)}")
        return files_to_process

    def initialize_db(self, rebuild: bool = False, verbose: bool = False):
        """Initialize or rebuild the vector database."""
        # Create database directory
        os.makedirs(self.db_path, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.db_path, settings=Settings(anonymized_telemetry=False)
        )

        # Create or get collection
        collection_name = "endor_cockpit_docs"
        if rebuild:
            try:
                self.client.delete_collection(collection_name)
            except Exception:
                pass
            # Clear manifest on rebuild
            self.manifest = {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                "documents": {},
                "total_chunks": 0,
                "total_documents": 0,
            }
            logger.info("Manifest cleared for rebuild")

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Endor Cockpit documentation vector database"},
        )

        # Process files
        files_to_process = self._get_files_to_process()

        if not files_to_process:
            logger.info("No files need processing")
            return

        logger.info(f"Processing {len(files_to_process)} files")

        all_chunks = []
        document_metadata = {}

        for file_path in files_to_process:
            logger.info(f"Processing: {file_path}")

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                content_type = self._detect_content_type(file_path)
                chunks = self._semantic_chunk(content, content_type)

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

                all_chunks.extend(chunks)

                # Update manifest
                file_hash = self._get_file_hash(file_path)
                normalized_path = self._normalize_path(file_path)
                document_metadata[normalized_path] = {
                    "file_hash": file_hash,
                    "chunks": len(chunks),
                    "last_modified": datetime.now().isoformat(),
                    "content_type": content_type,
                }

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                continue

        # Add chunks to collection in batches
        if all_chunks:
            batch_size = 1000  # ChromaDB batch size limit
            total_chunks = len(all_chunks)

            for i in range(0, total_chunks, batch_size):
                batch_chunks = all_chunks[i : i + batch_size]
                texts = [chunk["text"] for chunk in batch_chunks]
                metadatas = [chunk["metadata"] for chunk in batch_chunks]
                ids = [chunk["metadata"]["chunk_id"] for chunk in batch_chunks]

                self.collection.add(documents=texts, metadatas=metadatas, ids=ids)

                if verbose:
                    logger.info(
                        f"Added batch {i // batch_size + 1}/"
                        f"{(total_chunks + batch_size - 1) // batch_size} "
                        f"({len(batch_chunks)} chunks)"
                    )

            logger.info(f"Added {total_chunks} chunks to vector database")

        # Update manifest
        self.manifest["documents"].update(document_metadata)
        self.manifest["total_chunks"] = len(all_chunks)
        self.manifest["total_documents"] = len(document_metadata)
        self._save_manifest()

        logger.info("Vector database initialization complete")

    def query(self, query_text: str, n_results: int = 5) -> List[Dict]:
        """Query the vector database."""
        if not self.collection:
            self.initialize_db()

        results = self.collection.query(query_texts=[query_text], n_results=n_results)

        return results
