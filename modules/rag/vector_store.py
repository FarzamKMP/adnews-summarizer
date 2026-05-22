"""
ChromaDB-backed vector store.
Each document is stored with its embedding (via Gemini) and metadata.
"""
import logging
import os
from typing import Optional

import chromadb
from chromadb.config import Settings

from modules.ai import gemini_client

logger = logging.getLogger(__name__)

_client: Optional[chromadb.Client] = None
COLLECTION_NAME = "jonas_knowledge"


def _get_client() -> chromadb.Client:
    global _client
    if _client is None:
        chroma_dir = os.getenv("CHROMA_DIR", "./chroma_db")
        _client = chromadb.PersistentClient(
            path=chroma_dir,
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def _get_collection():
    return _get_client().get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def upsert_document(doc_id: str, text: str, metadata: Optional[dict] = None) -> None:
    embedding = gemini_client.embed(text)
    col = _get_collection()
    col.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[text],
        metadatas=[metadata or {}],
    )
    logger.debug(f"Upserted doc {doc_id}")


def delete_document(doc_id: str) -> None:
    col = _get_collection()
    col.delete(ids=[doc_id])
    logger.debug(f"Deleted doc {doc_id}")


def query(text: str, n_results: int = 5) -> list[dict]:
    """Return top-n relevant documents for a query string."""
    embedding = gemini_client.embed_query(text)
    col = _get_collection()
    results = col.query(
        query_embeddings=[embedding],
        n_results=min(n_results, col.count() or 1),
        include=["documents", "metadatas", "distances"],
    )
    docs = []
    for i, doc in enumerate(results["documents"][0]):
        docs.append({
            "text": doc,
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return docs


def count() -> int:
    return _get_collection().count()
