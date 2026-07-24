"""
MediAgent — Knowledge Agent (RAG)

Answers questions about diseases, hospital policies, treatment
guidelines, and FAQs by retrieving relevant chunks from hospital
documents (via ChromaDB — see backend/rag/) and grounding an LLM
answer in them. Degrades honestly rather than faking a result:
  - No matching chunks found -> says so, doesn't invent an answer.
  - Chunks found but no LLM provider configured -> shows the raw retrieved
    text directly instead of a synthesized answer.
"""

from backend.config import settings
from backend.tools.llm import call_llm
from backend.tools.search_tool import search_knowledge_base
from backend.workflow.state import WorkflowState

SYSTEM_PROMPT = """You are the Knowledge Agent in MediAgent. Answer the
patient's question using ONLY the provided context chunks from hospital
documents. If the context doesn't fully answer the question, say so
clearly and recommend they ask hospital staff directly. Keep the
answer to 2-4 sentences, plain language, no medical jargon."""


def knowledge_agent_node(state: WorkflowState) -> WorkflowState:
    query = state.get("user_message", "")
    chunks = search_knowledge_base(query)

    if not chunks:
        answer_text = (
            "I couldn't find anything on that in the hospital's knowledge base yet. "
            "Add relevant documents to docs/ and run `python -m backend.rag.ingest`, "
            "or ask hospital staff directly."
        )
    elif settings.has_llm_key():
        context = "\n\n".join(f"[{c['source']}] {c['text']}" for c in chunks)
        try:
            answer_text = call_llm(SYSTEM_PROMPT, f"Question: {query}\n\nContext:\n{context}")
        except Exception as e:
            # LLM call failed — fall back to the raw retrieved text rather than losing the result
            answer_text = f"(Answer generation unavailable — showing retrieved text.) {chunks[0]['text']}"
    else:
        # No LLM configured — show the raw retrieved chunk instead of a fake synthesized answer
        answer_text = chunks[0]["text"]

    answer = {
        "answer": answer_text,
        "sources": sorted({c["source"] for c in chunks}),
    }

    history = list(state.get("history", []))
    history.append("knowledge_agent")

    return {**state, "knowledge_answer": answer, "history": history}