"""
MediAgent — RAG Ingestion (ChromaDB)

Loads documents from docs/ (hospital guidelines, disease info, FAQs),
splits them into overlapping chunks, embeds them, and persists a
ChromaDB collection so the Knowledge Agent can do real vector
similarity search at runtime — not a placeholder lookup.

Uses ChromaDB's bundled default embedding model (all-MiniLM-L6-v2 via
onnxruntime), so this works without a Gemini API key. The model is
downloaded once on first run and cached locally by ChromaDB.

Run: python -m backend.rag.ingest
"""

from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

from backend.config import settings

COLLECTION_NAME = "mediagent_knowledge"
CHUNK_SIZE = 800  # characters per chunk
CHUNK_OVERLAP = 100


def _read_file(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(encoding="utf-8", errors="ignore")


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = " ".join(text.split())  # normalize whitespace
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return [c for c in chunks if c.strip()]


def load_and_chunk_documents(docs_dir: str = settings.RAG_DOCS_DIR) -> list[dict]:
    """Read every supported file under docs_dir and return {"text", "source", "chunk_id"} records."""
    records = []
    for path in Path(docs_dir).rglob("*"):
        if path.suffix.lower() in {".pdf", ".txt", ".md"}:
            text = _read_file(path)
            for i, chunk in enumerate(_chunk_text(text)):
                records.append({"text": chunk, "source": path.name, "chunk_id": f"{path.stem}-{i}"})
    return records


def build_index(docs_dir: str = settings.RAG_DOCS_DIR, index_dir: str = settings.RAG_INDEX_DIR):
    """Chunk, embed, and persist a ChromaDB collection from every document in docs_dir."""
    records = load_and_chunk_documents(docs_dir)
    if not records:
        print(f"No documents found in {docs_dir} — add .pdf/.txt/.md files there and re-run.")
        return

    Path(index_dir).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=index_dir)
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()

    # Rebuild the collection from scratch each time this script runs
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME, embedding_function=embedding_fn)

    collection.add(
        ids=[r["chunk_id"] for r in records],
        documents=[r["text"] for r in records],
        metadatas=[{"source": r["source"]} for r in records],
    )
    print(f"Indexed {len(records)} chunk(s) from {docs_dir} into ChromaDB at {index_dir}.")


if __name__ == "__main__":
    build_index()