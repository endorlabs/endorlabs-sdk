#!/usr/bin/env python3
"""
Vector Database Initialization Script

This script initializes a ChromaDB vector database from documentation files
using semantic chunking strategies optimized for different content types.

Usage:
    python workflow/init_vector_db.py [--rebuild] [--verbose]

Features:
- Semantic chunking by content type (markdown, code, api_spec)
- Incremental updates based on file hashes
- Manifest tracking for reproducibility
- ChromaDB integration with OpenAI embeddings
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sys
from datetime import datetime
from typing import Dict, List

import chromadb
from chromadb.config import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Chunking strategies for different content types
CHUNKING_STRATEGY = {
    "markdown": {
        "max_chunk_size": 1000,  # tokens
        "overlap": 200,          # tokens
        "split_on": ["##", "###", "\n\n"],  # Headers and paragraphs
        "preserve_structure": True
    },
    "code": {
        "max_chunk_size": 800,   # tokens
        "overlap": 100,          # tokens
        "split_on": ["\n\n", "def ", "class "],  # Functions and classes
        "preserve_structure": True
    },
    "api_spec": {
        "max_chunk_size": 2000,  # tokens
        "overlap": 300,          # tokens
        "split_on": ["\"paths\":", "\"components\":", "\"definitions\":"],
        "preserve_structure": True
    }
}

# Content type detection patterns
CONTENT_TYPE_PATTERNS = {
    "markdown": [r"\.md$", r"\.rst$"],
    "code": [r"\.py$", r"\.js$", r"\.ts$", r"\.go$", r"\.java$"],
    "api_spec": [r"openapi.*\.json$", r"swagger.*\.json$", r"\.yaml$", r"\.yml$"]
}

# Directories to include in vector DB
INCLUDE_DIRS = [
    "docs/",
    "src/",
    "tests/",
    "tmp/openapiv2.swagger.json"
]

# Directories to exclude
EXCLUDE_DIRS = [
    "__pycache__/",
    ".git/",
    "node_modules/",
    "venv/",
    ".venv/",
    "env/",
    ".env/"
]


class VectorDBManager:
    """Manages ChromaDB vector database initialization and updates."""

    def __init__(
        self,
        db_path: str = "workflow/vector_db",
        manifest_path: str = "workflow/vector_db_manifest.json"
    ):
        self.db_path = db_path
        self.manifest_path = manifest_path
        self.client = None
        self.collection = None
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> Dict:
        """Load or create manifest file."""
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path, 'r') as f:
                return json.load(f)
        else:
            return {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "embedding_model": "text-embedding-3-small",
                "chunking_strategy": "semantic_headers",
                "documents": {},
                "total_chunks": 0,
                "total_documents": 0
            }

    def _save_manifest(self):
        """Save manifest file."""
        self.manifest["last_updated"] = datetime.now().isoformat()
        with open(self.manifest_path, 'w') as f:
            json.dump(self.manifest, f, indent=2)

    def _get_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file."""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    def _detect_content_type(self, file_path: str) -> str:
        """Detect content type based on file path and content."""
        for content_type, patterns in CONTENT_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, file_path, re.IGNORECASE):
                    return content_type

        # Default to markdown for unknown types
        return "markdown"

    def _semantic_chunk(self, content: str, content_type: str) -> List[Dict]:
        """Chunk content using semantic strategies."""
        strategy = CHUNKING_STRATEGY.get(content_type, CHUNKING_STRATEGY["markdown"])
        chunks = []

        if content_type == "markdown":
            chunks = self._chunk_markdown(content, strategy)
        elif content_type == "code":
            chunks = self._chunk_code(content, strategy)
        elif content_type == "api_spec":
            chunks = self._chunk_api_spec(content, strategy)
        else:
            chunks = self._chunk_generic(content, strategy)

        return chunks

    def _chunk_markdown(self, content: str, strategy: Dict) -> List[Dict]:
        """Chunk markdown content by headers and paragraphs."""
        chunks = []
        lines = content.split('\n')
        current_chunk = []
        current_size = 0

        for line in lines:
            # Check if this is a header (starts with #)
            if line.strip().startswith('#'):
                # Save current chunk if it has content
                if current_chunk:
                    chunk_text = '\n'.join(current_chunk)
                    chunks.append({
                        "text": chunk_text,
                        "metadata": {
                            "content_type": "markdown",
                            "chunk_index": len(chunks),
                            "size": len(chunk_text)
                        }
                    })

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
                    chunk_text = '\n'.join(current_chunk)
                    chunks.append({
                        "text": chunk_text,
                        "metadata": {
                            "content_type": "markdown",
                            "chunk_index": len(chunks),
                            "size": len(chunk_text)
                        }
                    })

                    # Start new chunk
                    current_chunk = []
                    current_size = 0

        # Add final chunk
        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "content_type": "markdown",
                    "chunk_index": len(chunks),
                    "size": len(chunk_text)
                }
            })

        return chunks

    def _chunk_code(self, content: str, strategy: Dict) -> List[Dict]:
        """Chunk code content by functions and classes."""
        chunks = []
        lines = content.split('\n')
        current_chunk = []
        current_size = 0

        for line in lines:
            # Check if this is a function or class definition
            if line.strip().startswith(('def ', 'class ')):
                # Save current chunk if it has content
                if current_chunk:
                    chunk_text = '\n'.join(current_chunk)
                    chunks.append({
                        "text": chunk_text,
                        "metadata": {
                            "content_type": "code",
                            "chunk_index": len(chunks),
                            "size": len(chunk_text)
                        }
                    })

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
                    chunk_text = '\n'.join(current_chunk)
                    chunks.append({
                        "text": chunk_text,
                        "metadata": {
                            "content_type": "code",
                            "chunk_index": len(chunks),
                            "size": len(chunk_text)
                        }
                    })

                    # Start new chunk
                    current_chunk = []
                    current_size = 0

        # Add final chunk
        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "content_type": "code",
                    "chunk_index": len(chunks),
                    "size": len(chunk_text)
                }
            })

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
                chunks.append({
                    "text": section_text,
                    "metadata": {
                        "content_type": "api_spec",
                        "section": section_name,
                        "chunk_index": len(chunks),
                        "size": len(section_text)
                    }
                })

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
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        "content_type": "generic",
                        "chunk_index": len(chunks),
                        "size": len(chunk_text)
                    }
                })

                current_chunk = []
                current_size = 0

        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "content_type": "generic",
                    "chunk_index": len(chunks),
                    "size": len(chunk_text)
                }
            })

        return chunks

    def _should_rebuild_file(self, file_path: str) -> bool:
        """Check if file needs to be rebuilt based on manifest."""
        if file_path not in self.manifest["documents"]:
            return True

        current_hash = self._get_file_hash(file_path)
        stored_hash = self.manifest["documents"][file_path]["file_hash"]

        return current_hash != stored_hash

    def _get_files_to_process(self) -> List[str]:
        """Get list of files to process for vector DB."""
        files_to_process = []

        for include_path in INCLUDE_DIRS:
            if os.path.isfile(include_path):
                files_to_process.append(include_path)
            elif os.path.isdir(include_path):
                for root, dirs, files in os.walk(include_path):
                    # Skip excluded directories
                    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

                    for file in files:
                        file_path = os.path.join(root, file)
                        if self._should_rebuild_file(file_path):
                            files_to_process.append(file_path)

        return files_to_process

    def initialize_db(self, rebuild: bool = False):
        """Initialize or rebuild the vector database."""
        # Create database directory
        os.makedirs(self.db_path, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(anonymized_telemetry=False)
        )

        # Create or get collection
        collection_name = "endor_cockpit_docs"
        if rebuild:
            try:
                self.client.delete_collection(collection_name)
            except Exception:
                pass

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Endor Cockpit documentation vector database"}
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
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                content_type = self._detect_content_type(file_path)
                chunks = self._semantic_chunk(content, content_type)

                # Add file metadata to chunks
                for i, chunk in enumerate(chunks):
                    chunk["metadata"]["file_path"] = file_path
                    chunk["metadata"]["file_name"] = os.path.basename(file_path)
                    chunk["metadata"]["chunk_id"] = f"{file_path}:{i}"

                all_chunks.extend(chunks)

                # Update manifest
                file_hash = self._get_file_hash(file_path)
                document_metadata[file_path] = {
                    "file_hash": file_hash,
                    "chunks": len(chunks),
                    "last_modified": datetime.now().isoformat(),
                    "content_type": content_type
                }

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                continue

        # Add chunks to collection
        if all_chunks:
            texts = [chunk["text"] for chunk in all_chunks]
            metadatas = [chunk["metadata"] for chunk in all_chunks]
            ids = [chunk["metadata"]["chunk_id"] for chunk in all_chunks]

            self.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )

            logger.info(f"Added {len(all_chunks)} chunks to vector database")

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

        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )

        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize Endor Cockpit vector database"
    )
    parser.add_argument(
        "--rebuild", action="store_true", help="Rebuild the entire database"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize vector DB manager
    manager = VectorDBManager()

    try:
        manager.initialize_db(rebuild=args.rebuild)
        print("[OK] Vector database initialization complete")
    except Exception as e:
        logger.error(f"Error initializing vector database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
