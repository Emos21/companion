# Companion — a support assistant that knows when to bring in a human

Companion is a small, production-shaped **human-in-the-loop support assistant**. It answers
routine questions from a knowledge base, and it reliably hands anything risky, clinical, or
uncertain to a real person instead of guessing. I designed it for a peer wellbeing setting,
where a wrong confident answer is worse than no answer.

I built this as a working demonstration of the pattern, not a drop-in product. The live demo
and a full architecture walkthrough are available on request.

## What it does

- **Answers routine questions** (scheduling, deposits, how groups work) from a curated
  knowledge base using retrieval-augmented generation.
- **Escalates to a human** when it should:
  - **Safety first** — crisis, clinical, or safeguarding language routes straight to a
    person, without even calling the model.
  - **Uncertainty** — low answer confidence or weak retrieval escalates rather than guessing.
- **Closes the loop** — escalations land in a staff inbox; a team member replies, and that
  reply appears back in the member's chat.
- **Shows its work** — every reply states whether it was answered or escalated, the
  confidence, the retrieval score, the model that served it, and the sources it used.
- **Resilient and cost-aware** — Claude Sonnet 5.5 as the primary model with an automatic
  fallback to a second provider if the primary is unavailable, plus per-IP rate limiting.

## Why it works this way

The hard part of a support bot is not answering, it is knowing when not to. I built Companion
around that: it takes a chatbot from a prototype someone has to watch to a system that knows
when to act and when to call a human, with the reasoning, monitoring, and a human fallback
around it.

## Stack

- **Frontend:** Next.js (App Router) + TypeScript + Tailwind CSS
- **Backend:** FastAPI (Python)
- **Retrieval:** bge-small embeddings + cosine search (pgvector-ready)
- **LLM:** Anthropic Messages API, primary + automatic fallback provider
- **Safety:** deterministic, unit-tested escalation engine (safety triggers + confidence thresholds)

## Architecture

```
Member → Next.js chat ──POST /chat──▶ FastAPI
                                        ├─ retrieve (embeddings, top-k)
                                        ├─ safety check ─(crisis/clinical)─▶ escalate (no model call)
                                        ├─ answer from context (LLM, primary→fallback)
                                        └─ decide: auto-answer OR escalate (confidence + retrieval)
                                               │
                        Staff inbox ◀──────────┘  (open escalations)
                            │ reply
                            └─▶ reply written back into the member's conversation
```

## Running locally

Backend:
```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your keys (never commit .env)
uvicorn app.main:app --port 8099
```

Frontend:
```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:8099" > .env.local
npm run dev
```

Open http://localhost:3000 for the member chat and http://localhost:3000/staff for the inbox.

## Tests

```bash
cd backend && . .venv/bin/activate && python -m pytest -q
```

The escalation engine and the chat pipeline are unit-tested with mocked retrieval and model,
so the routing logic is verified without any network call.

## Notes

- Secrets live only in `.env` / host environment variables, never in the repo.
- The knowledge base is generic sample content, not tied to any real organisation.
