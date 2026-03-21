"""
NEXUS Platform — ChromaDB Vector Store Manager
Manages the engineering knowledge base with OpenAI embeddings.
Falls back to in-memory ChromaDB if the HTTP server is unavailable.

Hybrid search: combines BM25 keyword scoring (rank-bm25) with ChromaDB
cosine similarity using Reciprocal Rank Fusion (RRF).  This ensures that
precise engineering terminology — "Isp", "LMTD", "Re", "Nu", "Von Mises",
"NTU", "Rθjc" — is retrieved even when semantic similarity alone misses it.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Engineering abbreviations / Greek-letter symbols to keep whole during tokenisation
_ENG_TERMS = re.compile(
    r"\b("
    r"Isp|ISP|LMTD|NTU|FEA|CAD|STL|CFD|STEP|"
    r"Re|Nu|Pr|Bi|Gr|Ra|Ma|"
    r"COP|FOS|TRL|MTBF|"
    r"Al6061|Ti6Al4V|Inconel|"
    r"θ_ja|Rθjc|Rθjb|"
    r"Von\s*Mises|De\s*Laval"
    r")\b",
    re.IGNORECASE,
)


def _tokenize(text: str) -> list[str]:
    """
    Engineering-aware tokeniser for BM25.
    Preserves domain abbreviations and splits on whitespace/punctuation.
    """
    # Lowercase, keep alphanumeric + underscore + Greek
    tokens = re.findall(r"[A-Za-z_θαβγδεζηΔΣΩμκλρ][A-Za-z0-9_θαβγδεζηΔΣΩμκλρ]*"
                        r"|[0-9]+(?:[.,][0-9]+)?", text)
    # Filter very short tokens except known 2-letter symbols (Re, Nu, Pr …)
    _two_letter = {"Re", "Nu", "Pr", "Bi", "Gr", "Ra", "Ma"}
    return [t for t in tokens if len(t) > 1 or t in _two_letter]


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

        # ── BM25 state ────────────────────────────────────────────────────────
        self._bm25 = None               # BM25Okapi instance (rebuilt on change)
        self._bm25_docs: list[dict] = []  # [{content, metadata, id}, …] mirror

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

        # Sync BM25 index from existing ChromaDB documents (e.g. after restart)
        self._sync_bm25_from_chroma()

        return True

    # ── BM25 index management ─────────────────────────────────────────────────

    def _rebuild_bm25(self) -> None:
        """Rebuild BM25Okapi index from _bm25_docs corpus."""
        if not self._bm25_docs:
            self._bm25 = None
            return
        try:
            from rank_bm25 import BM25Okapi
            corpus = [_tokenize(d["content"]) for d in self._bm25_docs]
            self._bm25 = BM25Okapi(corpus)
        except ImportError:
            logger.warning("rank-bm25 not installed — BM25 hybrid search disabled; "
                           "run: pip install rank-bm25")
            self._bm25 = None

    def _sync_bm25_from_chroma(self) -> None:
        """Load all documents from the ChromaDB collection into the BM25 index."""
        if self._collection is None:
            return
        try:
            result = self._collection.get(include=["documents", "metadatas"])
            ids   = result.get("ids", []) or []
            docs  = result.get("documents", []) or []
            metas = result.get("metadatas", []) or []
            self._bm25_docs = [
                {"id": i, "content": d, "metadata": m}
                for i, d, m in zip(ids, docs, metas)
                if d  # skip empty docs
            ]
            self._rebuild_bm25()
            logger.info(f"BM25 index synced: {len(self._bm25_docs)} documents")
        except Exception as e:
            logger.warning(f"BM25 sync from ChromaDB failed: {e}")

    def _bm25_search(self, query: str, k: int, filter_domain: Optional[str]) -> list[dict]:
        """
        Run BM25 keyword search over the in-memory corpus.
        Returns up to k results as [{rank, content, metadata, bm25_score}, …].
        """
        if self._bm25 is None or not self._bm25_docs:
            return []

        tokens = _tokenize(query)
        if not tokens:
            return []

        scores = self._bm25.get_scores(tokens)

        # Apply domain filter
        candidates = [
            (i, score)
            for i, score in enumerate(scores)
            if score > 0 and (
                filter_domain is None
                or self._bm25_docs[i].get("metadata", {}).get("domain") == filter_domain
            )
        ]
        # Sort descending and take top-k
        candidates.sort(key=lambda x: x[1], reverse=True)
        results = []
        for rank, (idx, score) in enumerate(candidates[:k]):
            doc = self._bm25_docs[idx]
            results.append({
                "rank": rank + 1,
                "content": doc["content"],
                "metadata": doc.get("metadata", {}),
                "bm25_score": float(score),
            })
        return results

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

            # Keep BM25 mirror in sync — replace existing docs by id, append new ones
            existing_ids = {d["id"] for d in self._bm25_docs}
            for doc_id, text, meta in zip(ids, texts, metadatas):
                if doc_id in existing_ids:
                    for entry in self._bm25_docs:
                        if entry["id"] == doc_id:
                            entry["content"]  = text
                            entry["metadata"] = meta
                else:
                    self._bm25_docs.append({"id": doc_id, "content": text, "metadata": meta})
            self._rebuild_bm25()

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

    def hybrid_search(
        self,
        query: str,
        k: int = 5,
        filter_domain: Optional[str] = None,
        semantic_weight: float = 0.6,
        bm25_weight: float = 0.4,
        rrf_k: int = 60,
    ) -> list[dict[str, Any]]:
        """
        Reciprocal Rank Fusion (RRF) over semantic + BM25 results.

        RRF score for each document = Σ_i  w_i / (rrf_k + rank_i)
        where rank_i is the 1-based rank from retriever i.

        Returns top-k merged results with a combined `relevance_score`.
        Falls back to pure semantic search if BM25 is unavailable.
        """
        fetch_k = max(k * 3, 15)  # fetch more candidates so RRF can re-rank

        semantic_results = self.similarity_search(query, k=fetch_k, filter_domain=filter_domain)
        bm25_results     = self._bm25_search(query, k=fetch_k, filter_domain=filter_domain)

        # If BM25 not available, return pure semantic results (truncated to k)
        if not bm25_results:
            return semantic_results[:k]

        # Build a score accumulator keyed by document content fingerprint
        scores: dict[str, dict] = {}

        def _key(content: str) -> str:
            return content[:120]

        for rank, r in enumerate(semantic_results, start=1):
            ck = _key(r["content"])
            if ck not in scores:
                scores[ck] = {"content": r["content"], "metadata": r["metadata"], "rrf": 0.0}
            scores[ck]["rrf"] += semantic_weight / (rrf_k + rank)

        for rank, r in enumerate(bm25_results, start=1):
            ck = _key(r["content"])
            if ck not in scores:
                scores[ck] = {"content": r["content"], "metadata": r["metadata"], "rrf": 0.0}
            scores[ck]["rrf"] += bm25_weight / (rrf_k + rank)

        merged = sorted(scores.values(), key=lambda x: x["rrf"], reverse=True)

        return [
            {
                "rank": i + 1,
                "content":         doc["content"],
                "metadata":        doc["metadata"],
                "relevance_score": round(doc["rrf"], 4),
            }
            for i, doc in enumerate(merged[:k])
        ]

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
        metadata: Optional[dict] = None,
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
        domain: Optional[str] = None,
        top_k: int = 5,
        project_id: Optional[str] = None,
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

        results = self.hybrid_search(
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
