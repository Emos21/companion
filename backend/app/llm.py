"""Provider-agnostic LLM client: Claude Sonnet 5.5 primary, MiniMax M3 fallback.

Both providers speak the Anthropic Messages API, so switching provider is a client
swap, not a rewrite. If the primary (Anthropic) fails for any reason - out of
credits, rate limit, overload, or a network blip - we fall back to MiniMax M3 so
the assistant never goes dark. Every answer records which provider actually served
it, which is also what we surface in the UI and the metrics.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()  # read backend/.env (git-ignored); real keys live only there / in host env

log = logging.getLogger("llm")


@dataclass
class LLMResult:
    text: str
    provider: str      # "anthropic" | "minimax"
    model: str
    fell_back: bool
    stop_reason: str | None = None


def _text(message) -> str:
    """Join the text blocks of an Anthropic-format response."""
    parts = []
    for block in getattr(message, "content", []) or []:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts).strip()


class LLMClient:
    """Primary -> fallback completion over the Anthropic Messages API."""

    def __init__(self) -> None:
        self.anthropic_model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
        self.minimax_model = os.environ.get("MINIMAX_MODEL", "MiniMax-M3")
        minimax_base = os.environ.get("MINIMAX_ANTHROPIC_BASE_URL", "https://api.minimax.io/anthropic")

        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        minimax_key = os.environ.get("MINIMAX_API_KEY")
        if not anthropic_key and not minimax_key:
            raise RuntimeError("No LLM credentials: set ANTHROPIC_API_KEY and/or MINIMAX_API_KEY in .env")

        # Primary: real Anthropic (default base_url = api.anthropic.com).
        # Low retry count so a credit/quota failure falls through to MiniMax fast.
        self.primary = Anthropic(api_key=anthropic_key, max_retries=1, timeout=60) if anthropic_key else None
        # Fallback: MiniMax, Anthropic-compatible endpoint.
        self.fallback = (
            Anthropic(api_key=minimax_key, base_url=minimax_base, max_retries=1, timeout=60)
            if minimax_key else None
        )

    def complete(self, system: str, messages: list[dict], max_tokens: int = 512) -> LLMResult:
        """Answer with the primary model; on any primary failure, fall back to MiniMax."""
        if self.primary is not None:
            try:
                msg = self.primary.messages.create(
                    model=self.anthropic_model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=messages,
                )
                return LLMResult(
                    _text(msg),
                    "anthropic",
                    self.anthropic_model,
                    fell_back=False,
                    stop_reason=getattr(msg, "stop_reason", None),
                )
            except Exception as exc:  # out of credits, 429, 5xx, network - keep the service up
                log.warning("Primary (Anthropic) failed: %s -- falling back to MiniMax", exc)
                if self.fallback is None:
                    raise

        msg = self.fallback.messages.create(
            model=self.minimax_model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        return LLMResult(
            _text(msg),
            "minimax",
            self.minimax_model,
            fell_back=True,
            stop_reason=getattr(msg, "stop_reason", None),
        )


_client: LLMClient | None = None


def get_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
