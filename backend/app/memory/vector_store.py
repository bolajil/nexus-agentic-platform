"""
NEXUS Platform — ChromaDB Vector Store Manager
Manages the engineering knowledge base with OpenAI embeddings.
Falls back to in-memory ChromaDB if the HTTP server is unavailable.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """
    Manages a ChromaDB collection for engineering knowledge retrieval.
    Automatically falls back to ephemeral in-memory storage if the
    ChromaDB HTTP server cannot be reached.
    """

    def __init__(
        self,
        openai_api_key: str,
        host: str = "localhost",
        port: int = 8000,
        collection_name: str = "nexus_engineering_kb",
        embedding_model: str = "text-embedding-3-small",
    ) -> None:
        self.openai_api_key = openai_api_key
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self._client = None
        self._collection = None
        self._embeddings = None
        self._langchain_store = None
        self._initialized = False

    def initialize(self) -> bool:
        """
        Initialize ChromaDB client and embeddings.
        Returns True if successfully initialized.
        """
        if self._initialized:
            return True

        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            try:
                self._client = chromadb.HttpClient(
                    host=self.host,
                    port=self.port,
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
                # Test connectivity
                self._client.heartbeat()
                logger.info(f"Connected to ChromaDB HTTP server at {self.host}:{self.port}")
            except Exception:
                logger.warning("ChromaDB HTTP server unavailable — falling back to in-memory EphemeralClient")
                self._client = chromadb.EphemeralClient(
                    settings=ChromaSettings(anonymized_telemetry=False)
                )

            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"Collection '{self.collection_name}' ready ({self._collection.count()} docs)")

        except ImportError:
            logger.error("chromadb not installed — vector store unavailable")
            return False

        # Set up LangChain embeddings wrapper
        try:
            from langchain_openai import OpenAIEmbeddings

            self._embeddings = OpenAIEmbeddings(
                model=self.embedding_model,
                openai_api_key=self.openai_api_key,
            )
        except ImportError:
            logger.error("langchain-openai not installed — embeddings unavailable")
            return False

        self._initialized = True
        return True

    def add_documents(
        self,
        documents: list[dict[str, Any]],
    ) -> int:
        """
        Add documents to the vector store.
        Each document dict must have: 'content' (str), 'metadata' (dict), 'id' (str, optional)
        Returns number of documents added.
        """
        if not self._initialized and not self.initialize():
            logger.error("Cannot add documents — vector store not initialized")
            return 0

        if not documents:
            return 0

        texts = [doc["content"] for doc in documents]
        metadatas = [doc.get("metadata", {}) for doc in documents]
        ids = [doc.get("id", f"doc_{i}") for i, doc in enumerate(documents)]

        try:
            # Generate embeddings via OpenAI
            embeddings = self._embeddings.embed_documents(texts)

            # Upsert into ChromaDB
            self._collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
            logger.info(f"Added {len(documents)} documents to collection '{self.collection_name}'")
            return len(documents)
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            return 0

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter_domain: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Perform semantic similarity search against the knowledge base.
        Returns top-k results with content, metadata, and relevance distance.
        """
        if not self._initialized and not self.initialize():
            return []

        try:
            query_embedding = self._embeddings.embed_query(query)

            where_filter = None
            if filter_domain:
                where_filter = {"domain": {"$eq": filter_domain}}

            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(k, max(self._collection.count(), 1)),
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )

            formatted = []
            if results and results["documents"]:
                for i, (doc, meta, dist) in enumerate(
                    zip(
                        results["documents"][0],
                        results["metadatas"][0],
                        results["distances"][0],
                    )
                ):
                    relevance_score = 1.0 - dist  # cosine distance → similarity
                    formatted.append(
                        {
                            "rank": i + 1,
                            "content": doc,
                            "metadata": meta,
                            "relevance_score": round(relevance_score, 4),
                        }
                    )
            return formatted

        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []

    def get_collection_stats(self) -> dict[str, Any]:
        """Return collection statistics."""
        if not self._initialized and not self.initialize():
            return {"status": "unavailable", "total_documents": 0}

        try:
            count = self._collection.count()
            return {
                "status": "ok",
                "collection_name": self.collection_name,
                "total_documents": count,
                "embedding_model": self.embedding_model,
                "host": self.host,
                "port": self.port,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def delete_collection(self) -> bool:
        """Delete and recreate the collection (useful for re-seeding)."""
        if not self._initialized:
            return False
        try:
            self._client.delete_collection(self.collection_name)
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"Collection '{self.collection_name}' reset")
            return True
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            return False

    # ── Convenience aliases (used by routers and seed script) ─────────────────

    def add_document(
        self,
        title: str,
        content: str,
        domain: str,
        source: str = "manual",
        metadata: dict | None = None,
    ) -> str:
        """
        Add a single named document to the vector store.
        Normalizes terminology before embedding.
        Returns the generated document ID.
        """
        import hashlib
        from app.tools.terminology import normalize_document

        doc_id = hashlib.md5(f"{title}{domain}".encode()).hexdigest()[:16]
        normalized = normalize_document(content)

        self.add_documents([{
            "id": doc_id,
            "content": normalized,
            "metadata": {
                "title":  title,
                "domain": domain,
                "source": source,
                **(metadata or {}),
            },
        }])
        return doc_id

    def search(
        self,
        query: str,
        domain: str | None = None,
        top_k: int = 5,
        project_id: str | None = None,
    ) -> list[dict]:
        """
        Hybrid search: normalizes query terminology then runs cosine similarity.

        Terminology normalization ensures that querying "junction-to-ambient
        thermal resistance" finds documents that use "θ_ja", and vice versa,
        because both are expanded to the same canonical form before embedding.
        """
        from app.tools.terminology import normalize_query

        # Normalize query: expand Greek letters, abbreviations, project glossary
        normalized_query = normalize_query(query, project_id=project_id)

        results = self.similarity_search(
            query=normalized_query,
            k=top_k,
            filter_domain=domain,
        )

        # Re-label fields for API consistency
        output = []
        for r in results:
            meta = r.get("metadata", {})
            output.append({
                "title":   meta.get("title", ""),
                "domain":  meta.get("domain", domain or ""),
                "content": r.get("content", ""),
                "score":   r.get("relevance_score", 0.0),
                "source":  meta.get("source", ""),
                "project_id": meta.get("project_id", ""),
            })
        return output

    def get_stats(self) -> dict:
        """Return collection statistics (alias for get_collection_stats)."""
        stats = self.get_collection_stats()
        # Add domain list from metadata scan (best-effort)
        try:
            results = self._collection.get(include=["metadatas"])
            domains = list({m.get("domain", "") for m in (results.get("metadatas") or []) if m.get("domain")})
            stats["domains"] = sorted(domains)
        except Exception:
            stats["domains"] = []
        return stats
