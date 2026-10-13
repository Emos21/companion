"""Companion backend API (FastAPI).

Endpoints:
  GET  /health                     liveness
  POST /chat                       user turn -> auto-answer or escalate to a human
  GET  /escalations                staff inbox (open items)
  POST /escalations/{id}/resolve   staff replies, closes the item
  GET  /metrics                    simple counts for the dashboard

A sliding-window per-IP rate limit protects the upstream LLM credits on a public demo.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import pipeline, store
from .knowledge_base import KB
from .rag import Retriever

RATE_MAX = int(os.environ.get("RATE_MAX_PER_WINDOW", "20"))
RATE_WINDOW = int(os.environ.get("RATE_WINDOW_SECONDS", "600"))
_rate: dict[str, deque] = defaultdict(deque)


def _rate_ok(ip: str) -> bool:
    now = time.time()
    dq = _rate[ip]
    while dq and now - dq[0] > RATE_WINDOW:
        dq.popleft()
    if len(dq) >= RATE_MAX:
        return False
    dq.append(now)
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .embeddings import get_embedder

    retriever = Retriever(get_embedder())
    retriever.index(KB)
    app.state.retriever = retriever
    yield


app = FastAPI(title="Companion API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get("FRONTEND_ORIGIN", "*").split(",") if o.strip()],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["content-type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    return response


class ChatIn(BaseModel):
    message: str
    conversation_id: int | None = None


class ResolveIn(BaseModel):
    reply: str


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/chat")
def chat(body: ChatIn, request: Request) -> dict:
    ip = request.client.host if request.client else "unknown"
    if not _rate_ok(ip):
        raise HTTPException(status_code=429, detail="Rate limit reached. Please wait a moment.")
    msg = (body.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Message is empty.")

    cid = store.get_or_create(body.conversation_id)
    hist = store.history(cid)
    store.add_message(cid, "user", msg)

    result = pipeline.answer(msg, hist, request.app.state.retriever)
    dec = result["decision"]

    if dec.escalate:
        eid = store.create_escalation(cid, msg, result)
        reply = result["handoff"]
        store.add_message(cid, "assistant", reply)
        payload = {"escalated": True, "escalation_id": eid}
    else:
        reply = result["answer"]
        store.add_message(cid, "assistant", reply)
        payload = {"escalated": False}

    payload.update(
        conversation_id=cid,
        reply=reply,
        decision=dec.to_dict(),
        confidence=result["confidence"],
        retrieval_score=result["retrieval_score"],
        provider=result["provider"],
        model=result["model"],
        fell_back=result["fell_back"],
        sources=result["sources"],
    )
    return payload


@app.get("/escalations")
def escalations(open_only: bool = True) -> dict:
    return {"escalations": store.list_escalations(open_only=open_only)}


@app.post("/escalations/{escalation_id}/resolve")
def resolve(escalation_id: int, body: ResolveIn) -> dict:
    if not store.resolve_escalation(escalation_id, (body.reply or "").strip()):
        raise HTTPException(status_code=404, detail="Escalation not found or already resolved.")
    return {"ok": True}


@app.get("/conversations/{conversation_id}/messages")
def conversation_messages(conversation_id: int) -> dict:
    return {"messages": store.conversation_messages(conversation_id)}


@app.get("/metrics")
def metrics() -> dict:
    return store.counts()
