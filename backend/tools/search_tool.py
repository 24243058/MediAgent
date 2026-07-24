"""
MediAgent — Search Tool

Generic search interface used by the Knowledge Agent to query the
RAG retriever. Kept separate from rag/retriever.py so agents depend
on a stable tool interface even if the retrieval backend changes.
"""

from backend.rag.retriever import retrieve_relevant_chunks


def search_knowledge_base(query: str, top_k: int = 4) -> list[dict]:
    """
    Return the top_k most relevant chunks from hospital documents
    (disease info, policies, treatment guidelines, FAQs) for a query.
    """
    return retrieve_relevant_chunks(query, top_k=top_k)
