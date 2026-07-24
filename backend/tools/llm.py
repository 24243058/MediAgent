"""
MediAgent — LLM Tool

Thin wrapper so every agent calls the model the same way, regardless
of which provider is configured. Two callers use this:
  - supervisor.py — ReAct-style "Thought → Action" planning
  - knowledge_agent.py — synthesizing an answer grounded in RAG chunks

settings.LLM_PROVIDER selects "gemini" (default) or "groq" — call_llm()
routes to the matching implementation below. Groq's API is OpenAI-
compatible, so it's called via plain requests rather than adding
another SDK dependency.

Raises rather than silently degrading: callers decide what to do when
the LLM isn't configured or the call fails (usually: fall back to a
deterministic path), so failures never get hidden here.
"""

import requests

from backend.config import settings

_gemini_model = None


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.3, json_mode: bool = False) -> str:
    """
    Send a prompt to the configured LLM provider and return the text response.

    Args:
        json_mode: when True, asks the model to return a raw JSON object
            (used by the Supervisor's ReAct step, which parses
            {"thought": ..., "action": ...} from the result).

    Raises RuntimeError if the selected provider's API key isn't set, or
    whatever the underlying call raises on a network/API failure —
    callers should catch this and fall back to a deterministic path
    rather than crash the workflow.
    """
    if settings.LLM_PROVIDER == "groq":
        return _call_groq(system_prompt, user_prompt, temperature, json_mode)
    return _call_gemini(system_prompt, user_prompt, temperature, json_mode)


# ----------------------------------------------------------------- Gemini ----

def _get_gemini_model():
    """Lazily create and cache the Gemini client so import doesn't require the SDK/key to be present."""
    global _gemini_model
    if _gemini_model is not None:
        return _gemini_model

    import google.generativeai as genai

    genai.configure(api_key=settings.GEMINI_API_KEY)
    _gemini_model = genai.GenerativeModel(settings.GEMINI_MODEL)
    return _gemini_model


def _call_gemini(system_prompt: str, user_prompt: str, temperature: float, json_mode: bool) -> str:
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set — cannot call Gemini.")

    model = _get_gemini_model()
    generation_config = {"temperature": temperature}
    if json_mode:
        generation_config["response_mime_type"] = "application/json"

    response = model.generate_content(
        [system_prompt, user_prompt],
        generation_config=generation_config,
    )
    return response.text


# ------------------------------------------------------------------- Groq ----

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


def _call_groq(system_prompt: str, user_prompt: str, temperature: float, json_mode: bool) -> str:
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set — cannot call Groq.")

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }
    if json_mode:
        # Groq's OpenAI-compatible JSON mode — the word "JSON" must also
        # appear somewhere in the prompt itself, which REACT_SYSTEM_PROMPT
        # and the Knowledge Agent's SYSTEM_PROMPT already satisfy.
        payload["response_format"] = {"type": "json_object"}

    response = requests.post(
        GROQ_CHAT_URL,
        headers={
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Groq API error {response.status_code}: {response.text[:300]}")

    data = response.json()
    return data["choices"][0]["message"]["content"]