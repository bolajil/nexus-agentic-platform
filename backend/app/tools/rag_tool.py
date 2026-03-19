"""
NEXUS Platform — RAG (Retrieval-Augmented Generation) Tool
LangChain tool wrapper around ChromaDB vector search for engineering knowledge base.
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Module-level reference to vector store manager (set during app startup)
_vector_store_manager = None


def set_vector_store(manager) -> None:
    """Register the global VectorStoreManager instance."""
    global _vector_store_manager
    _vector_store_manager = manager


@tool
def search_engineering_knowledge(
    query: str,
    domain: str = "",
    k: int = 5,
) -> list[dict[str, Any]]:
    """
    Search the NEXUS engineering knowledge base using semantic similarity.
    Returns top-k relevant document chunks with metadata and relevance scores.

    Args:
        query: Natural language search query
        domain: Optional domain filter (heat_transfer|propulsion|structural|electronics_cooling)
        k: Number of results to return (default 5)
    """
    global _vector_store_manager
    if _vector_store_manager is None:
        logger.warning("VectorStoreManager not initialized — returning empty results")
        return []

    try:
        results = _vector_store_manager.similarity_search(
            query=query,
            k=k,
            filter_domain=domain if domain else None,
        )
        return results
    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        return [{"error": str(e), "content": "", "metadata": {}}]


@tool
def get_knowledge_base_stats() -> dict[str, Any]:
    """
    Get statistics about the engineering knowledge base.
    Returns document counts, available domains, and collection metadata.
    """
    global _vector_store_manager
    if _vector_store_manager is None:
        return {"status": "unavailable", "total_documents": 0}

    try:
        return _vector_store_manager.get_collection_stats()
    except Exception as e:
        logger.error(f"Failed to get KB stats: {e}")
        return {"status": "error", "error": str(e)}


# Export RAG tools
RAG_TOOLS = [search_engineering_knowledge, get_knowledge_base_stats]
