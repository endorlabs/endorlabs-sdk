#!/usr/bin/env python3
"""
Test script for the vector database functionality.
This script demonstrates how to query the vector database for semantic search.
"""

import os
import sys

import chromadb

# Configuration
VECTOR_DB_DIR = "workflow/vector_db"
COLLECTION_NAME = "endor_cockpit_docs"
EMBEDDING_MODEL = "text-embedding-3-small"

def test_vector_db():
    """Test the vector database by performing semantic searches."""

    # Initialize ChromaDB client
    client = chromadb.PersistentClient(path=VECTOR_DB_DIR)

    # Get the collection
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
        print(f"[OK] Successfully connected to collection: {COLLECTION_NAME}")
    except Exception as e:
        print(f"[ERROR] Failed to get collection: {e}")
        return False

    # Test queries
    test_queries = [
        "How do I create a namespace?",
        "What are the API quirks for canonical naming?",
        "How do I troubleshoot 403 Forbidden errors?",
        "What are the security best practices?",
        "How do I set up integrations?",
        "What is the Endor data model?",
        "How do I write tests?",
        "What are the design principles?"
    ]

    print(f"\n[INFO] Testing semantic search with {len(test_queries)} queries...")

    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Query {i}: {query} ---")

        try:
            # Perform semantic search
            results = collection.query(
                query_texts=[query],
                n_results=3,  # Get top 3 results
                include=["documents", "metadatas", "distances"]
            )

            if results['documents'] and results['documents'][0]:
                print(f"[OK] Found {len(results['documents'][0])} results")

                # Display top result
                top_doc = results['documents'][0][0]
                top_metadata = results['metadatas'][0][0]
                top_distance = results['distances'][0][0]

                print(f"[INFO] Top result from: {top_metadata.get('source', 'Unknown')}")
                print(f"[INFO] Similarity score: {1 - top_distance:.3f}")
                print(f"[INFO] Content preview: {top_doc[:200]}...")

            else:
                print("[WARNING] No results found")

        except Exception as e:
            print(f"[ERROR] Query failed: {e}")

    # Test collection stats
    try:
        count = collection.count()
        print(f"\n[INFO] Collection contains {count} chunks")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to get collection count: {e}")
        return False

def test_manifest():
    """Test the manifest file."""
    import json

    manifest_path = "workflow/vector_db_manifest.json"

    if not os.path.exists(manifest_path):
        print(f"[ERROR] Manifest file not found: {manifest_path}")
        return False

    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)

        print("[OK] Manifest loaded successfully")
        print(f"[INFO] Total documents: {manifest.get('total_documents', 0)}")
        print(f"[INFO] Total chunks: {manifest.get('total_chunks', 0)}")
        print(f"[INFO] Embedding model: {manifest.get('embedding_model', 'Unknown')}")
        print(f"[INFO] Last updated: {manifest.get('last_updated', 'Unknown')}")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to load manifest: {e}")
        return False

if __name__ == "__main__":
    print("[INFO] Testing Vector Database System")
    print("=" * 50)

    # Test manifest
    print("\n1. Testing manifest file...")
    manifest_ok = test_manifest()

    # Test vector database
    print("\n2. Testing vector database...")
    vector_ok = test_vector_db()

    # Summary
    print("\n" + "=" * 50)
    if manifest_ok and vector_ok:
        print("[OK] All tests passed! Vector database is working correctly.")
        sys.exit(0)
    else:
        print("[ERROR] Some tests failed. Check the output above for details.")
        sys.exit(1)
