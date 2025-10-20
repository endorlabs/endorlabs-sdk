"""
Holocron Knowledge Base System

A workspace management tool for Endor Cockpit that provides semantic search
over documentation using vector embeddings. Designed for AI agents to quickly
retrieve relevant context from the knowledge base.

Usage:
    # CLI interface
    python -m holocron init     # Initialize workspace
    python -m holocron sync     # Sync knowledge base
    python -m holocron query    # Query knowledge base

    # Programmatic interface
    from holocron import query_holocron, init_workspace
    results = query_holocron("How do I create a namespace?")
"""

from .manager import VectorDBManager
from .query import query_holocron, get_holocron_info, HolocronQuery
from .workspace import init_workspace

__all__ = [
    "VectorDBManager",
    "query_holocron", 
    "get_holocron_info",
    "HolocronQuery",
    "init_workspace",
]

__version__ = "0.1.0"
