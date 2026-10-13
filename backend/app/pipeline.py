"""The chat pipeline: retrieve -> answer from context -> derive confidence -> decide
escalation. Pure orchestration; the retriever and LLM are injected so the whole flow
is testable without a network call or an API key.
"""
from __future__ import annotations

from .escalation import Decision, EscalationConfig, Severity, decide, safety_trigger
from .rag import Hit

SYSTEM = (
    "You are Companion, a warm, concise assistant for a peer wellbeing program. "
    "Answer ONLY using the Context below, in a few plain sentences. "
    "Do not give clinical, medical, or crisis advice. "
    "If the Context does not clearly contain the answer, reply with exactly: INSUFFICIENT_CONTEXT."
)
SENTINEL = "INSUFFICIENT_CONTEXT"


def _context(hits: list[Hit]) -> str:
    return "\n\n".join(f"[{h.title}] {h.text}" for h in hits) if hits else "(no documents found)"


def _handoff(dec: Decision) -> str:
    if dec.severity is Severity.CRITICAL:
        return (
            "I'm really glad you reached out, and I want a person to support you with this. "
            "I'm connecting you to a member of our team now. If you are in immediate danger, "
            "please contact your local emergency number or a crisis line straight away."
        )
    if dec.severity is Severity.HIGH:
        return (
            "This is something our team should handle directly rather than me. "
            "I've flagged it to a staff member who will follow up with you."
        )
    return (
        "I want to make sure you get an accurate answer, so I'm bringing in a member of the team. "
        "They'll follow up shortly."
    )


def answer(user_message, history, retriever, llm=None, config=None, k: int = 4) -> dict:
    config = config or EscalationConfig()
    hits = retriever.search(user_message, k=k)
    retrieval_score = hits[0].score if hits else 0.0
    sources = [{"id": h.id, "title": h.title, "score": round(h.score, 3)} for h in hits]

    # Hard safety triggers: escalate to a human without calling the model at all.
    safety = safety_trigger(user_message, 0.0, retrieval_score)
    if safety is not None:
        return {
            "answer": None,
            "decision": safety,
            "handoff": _handoff(safety),
            "confidence": 0.0,
            "retrieval_score": round(retrieval_score, 3),
            "provider": "none",
            "model": "n/a",
            "fell_back": False,
            "sources": sources,
        }

    if llm is None:
        from .llm import get_client

        llm = get_client()

    system = SYSTEM + "\n\nContext:\n" + _context(hits)
    messages = list(history) + [{"role": "user", "content": user_message}]
    out = llm.complete(system, messages, max_tokens=600)

    raw = (out.text or "").strip()
    # Never show a response that the provider cut off at the token limit. A
    # partial wellbeing instruction is worse than a clean human handoff.
    truncated = getattr(out, "stop_reason", None) == "max_tokens"
    answered = bool(raw) and SENTINEL not in raw.upper() and not truncated
    # Confidence: the model's own "can't answer" signal, else scaled by retrieval strength.
    confidence = 0.2 if not answered else max(0.0, min(0.95, 0.55 + 0.4 * retrieval_score))

    dec = decide(user_message, confidence, retrieval_score, config)
    return {
        "answer": raw if answered else None,
        "decision": dec,
        "handoff": _handoff(dec),
        "confidence": round(confidence, 3),
        "retrieval_score": round(retrieval_score, 3),
        "provider": out.provider,
        "model": out.model,
        "fell_back": out.fell_back,
        "sources": sources,
    }
