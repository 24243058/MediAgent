"""
MediAgent — RAG Retriever (ChromaDB)

Loads the persisted ChromaDB collection (built by ingest.py) and
returns the most relevant chunks for a query via real vector
similarity search — not a hardcoded placeholder.
"""

from backend.config import settings
from backend.rag.ingest import COLLECTION_NAME

_collection = None
_load_attempted = False


def _get_collection():
    """Lazily open the persisted collection; returns None if it hasn't been built yet."""
    global _collection, _load_attempted
    if _load_attempted:
        return _collection
    _load_attempted = True

    try:
        import chromadb
        from chromadb.utils import embedding_functions

        client = chromadb.PersistentClient(path=settings.RAG_INDEX_DIR)
        embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        _collection = client.get_collection(COLLECTION_NAME, embedding_function=embedding_fn)
    except Exception:
        _collection = None

    return _collection


def retrieve_relevant_chunks(query: str, top_k: int = 4) -> list[dict]:
    """
    Return top_k relevant chunks as:
        [{"text": ..., "source": ..., "score": ...}, ...]
    Returns an empty list if the index hasn't been built yet (run
    `python -m backend.rag.ingest` first) — the Knowledge Agent
    handles that case gracefully rather than showing fake results.
    """
    collection = _get_collection()
    if collection is None:
        return []

    results = collection.query(query_texts=[query], n_results=top_k)
    chunks = []
    docs = (results.get("documents") or [[]])[0]
    metas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]
    for doc, meta, dist in zip(docs, metas, distances):
        chunks.append({
            "text": doc,
            "source": (meta or {}).get("source", "unknown"),
            "score": round(1 - dist, 3),  # cosine distance -> similarity-ish score for display
        })
    return chunks