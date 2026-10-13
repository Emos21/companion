"""In-memory persistence for conversations and escalations.

Keeps the demo runnable with zero infrastructure. The functions are the seam where
a Supabase/Postgres repository drops in for production (same signatures, durable
rows). Not for real multi-process use - a single demo process only.
"""
from __future__ import annotations

import itertools
import threading
import time

_lock = threading.Lock()
_conv_ids = itertools.count(1)
_esc_ids = itertools.count(1)

_conversations: dict[int, dict] = {}
_escalations: dict[int, dict] = {}


def new_conversation() -> int:
    with _lock:
        cid = next(_conv_ids)
        _conversations[cid] = {"id": cid, "created_at": time.time(), "messages": []}
        return cid


def get_or_create(conversation_id: int | None) -> int:
    if conversation_id and conversation_id in _conversations:
        return conversation_id
    return new_conversation()


def history(conversation_id: int) -> list[dict]:
    """LLM-facing history: only user and assistant turns (staff 'human' replies excluded)."""
    conv = _conversations.get(conversation_id)
    if not conv:
        return []
    return [
        {"role": m["role"], "content": m["content"]}
        for m in conv["messages"]
        if m["role"] in ("user", "assistant")
    ]


def conversation_messages(conversation_id: int) -> list[dict]:
    """Full transcript for the member UI, including staff ('human') replies."""
    conv = _conversations.get(conversation_id)
    return (
        [{"role": m["role"], "content": m["content"], "at": m["at"]} for m in conv["messages"]]
        if conv
        else []
    )


def add_message(conversation_id: int, role: str, content: str) -> None:
    with _lock:
        conv = _conversations.get(conversation_id)
        if conv is not None:
            conv["messages"].append({"role": role, "content": content, "at": time.time()})


def create_escalation(conversation_id: int, user_message: str, result: dict) -> int:
    with _lock:
        eid = next(_esc_ids)
        dec = result["decision"]
        _escalations[eid] = {
            "id": eid,
            "conversation_id": conversation_id,
            "user_message": user_message,
            "severity": dec.severity.value,
            "reason": dec.reason,
            "matched": dec.matched,
            "draft_answer": result.get("answer"),
            "sources": result.get("sources", []),
            "provider": result.get("provider"),
            "status": "open",
            "created_at": time.time(),
            "resolved_reply": None,
        }
        return eid


def list_escalations(open_only: bool = True) -> list[dict]:
    rows = sorted(_escalations.values(), key=lambda e: e["created_at"], reverse=True)
    return [e for e in rows if (e["status"] == "open" or not open_only)]


def resolve_escalation(escalation_id: int, reply: str) -> bool:
    with _lock:
        esc = _escalations.get(escalation_id)
        if not esc or esc["status"] != "open":
            return False
        esc["status"] = "resolved"
        esc["resolved_reply"] = reply
        esc["resolved_at"] = time.time()
        conv = _conversations.get(esc["conversation_id"])
        if conv is not None:
            conv["messages"].append({"role": "human", "content": reply, "at": esc["resolved_at"]})
        return True


def counts() -> dict:
    rows = list(_escalations.values())
    by_sev: dict[str, int] = {}
    for e in rows:
        by_sev[e["severity"]] = by_sev.get(e["severity"], 0) + 1
    return {
        "conversations": len(_conversations),
        "escalations_total": len(rows),
        "escalations_open": sum(1 for e in rows if e["status"] == "open"),
        "by_severity": by_sev,
    }


def reset() -> None:
    """Test helper."""
    with _lock:
        _conversations.clear()
        _escalations.clear()
