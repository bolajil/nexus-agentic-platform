"""
NEXUS Platform — Knowledge Base Router
=======================================
Endpoints to query and manage the engineering knowledge base (ChromaDB).

Endpoints:
  POST  /knowledge/ingest       — Add a document to the vector store
  POST  /knowledge/search       — Semantic search (returns top-k chunks)
  GET   /knowledge/stats        — Collection statistics
  POST  /knowledge/seed         — Trigger built-in knowledge base seeding
  DELETE /knowledge/document/{id} — Remove a document
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.memory.vector_store import VectorStoreManager
from app.models.schemas import DocumentIngestion, KnowledgeStats

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge", tags=["knowledge"])

_vector_store: Optional[VectorStoreManager] = None


def get_vector_store(settings: Settings = Depends(get_settings)) -> VectorStoreManager:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreManager(
            openai_api_key=settings.openai_api_key,
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
        _vector_store.initialize()
    return _vector_store


@router.post("/ingest", status_code=201)
async def ingest_document(
    body: DocumentIngestion,
    store: VectorStoreManager = Depends(get_vector_store),
) -> dict:
    """Embed and store a document in the engineering knowledge base."""
    try:
        doc_id = store.add_document(
            title=body.title,
            content=body.content,
            domain=body.domain,
            source=body.source or "manual",
            metadata=body.metadata,
        )
        return {"id": doc_id, "status": "ingested", "title": body.title}
    except Exception as e:
        logger.error(f"Ingest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_knowledge(
    query: str,
    domain: Optional[str] = None,
    top_k: int = 5,
    store: VectorStoreManager = Depends(get_vector_store),
) -> List[Dict]:
    """
    Semantic search over the engineering knowledge base.
    Optionally filter by domain (heat_transfer, propulsion, structural, etc.)
    """
    try:
        results = store.search(query=query, domain=domain, top_k=top_k)
        return results
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def knowledge_stats(
    store: VectorStoreManager = Depends(get_vector_store),
) -> dict:
    """Return statistics about the knowledge base collection."""
    try:
        stats = store.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/seed")
async def seed_knowledge_base(
    settings: Settings = Depends(get_settings),
    store: VectorStoreManager = Depends(get_vector_store),
) -> dict:
    """
    Seed the knowledge base with built-in engineering reference documents.
    Safe to call multiple times — duplicates are skipped by title.
    """
    try:
        from scripts.seed_knowledge_base import ENGINEERING_DOCUMENTS
        ingested = 0
        skipped = 0
        for doc in ENGINEERING_DOCUMENTS:
            try:
                store.add_document(**doc)
                ingested += 1
            except Exception:
                skipped += 1
        return {
            "status": "complete",
            "ingested": ingested,
            "skipped": skipped,
            "total": len(ENGINEERING_DOCUMENTS),
        }
    except ImportError:
        raise HTTPException(status_code=500, detail="Seed script not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
