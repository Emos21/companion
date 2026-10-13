"""Escalation decision engine for the human-in-the-loop support assistant.

The bot answers routine, high-confidence questions on its own and hands anything
risky, uncertain, or sensitive to a human. This module is the decision core:
pure, deterministic, and unit-tested, with no network or model dependency, so the
routing rules can be reasoned about and verified in isolation.

Design stance for a safety-critical, clinical-adjacent setting: bias toward
over-escalation. A false alarm costs a human a minute; a missed crisis costs more.
Safety triggers win over confidence, always.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from enum import Enum


class Action(str, Enum):
    AUTO = "auto"
    ESCALATE = "escalate"


class Severity(str, Enum):
    NONE = "none"
    LOW = "low"
    HIGH = "high"
    CRITICAL = "critical"


# Trigger categories. Patterns are deliberately broad. In a clinical-adjacent
# setting we would rather escalate a false alarm than miss a real crisis.
CRISIS_PATTERNS = [
    r"\bkill(?:ing)? myself\b",
    r"\bsuicid",
    r"\bself[\s-]?harm",
    r"\bend(?:ing)? (?:it all|my life)\b",
    r"\bwant to die\b",
    r"\bhurt(?:ing)? myself\b",
    r"\boverdos",
    r"\bno reason to live\b",
    r"\bdon'?t want to be here anymore\b",
]
MEDICAL_PATTERNS = [
    r"\bdiagnos",
    r"\bmedication\b",
    r"\bdosage\b",
    r"\bprescri",
    r"\bside[\s-]effects?\b",
    r"\b(?:stop|start|change) (?:my |taking )?(?:meds|medication|pills|antidepressants)\b",
]
SAFEGUARDING_PATTERNS = [
    r"\babuse(?:d|r)?\b",
    r"\bviolen",
    r"\bthreaten",
    r"\bunsafe\b",
    r"\bhurt(?:ing)? (?:someone|somebody|a child|them)\b",
]

_SEVERITY_ORDER = {
    Severity.NONE: 0,
    Severity.LOW: 1,
    Severity.HIGH: 2,
    Severity.CRITICAL: 3,
}


@dataclass
class EscalationConfig:
    """Thresholds that govern auto vs escalate. Tunable from real data over time."""

    min_answer_confidence: float = 0.6   # model's own confidence; below this = uncertain
    min_retrieval_score: float = 0.25    # top RAG similarity; below this = KB did not cover it

    def __post_init__(self) -> None:
        for name in ("min_answer_confidence", "min_retrieval_score"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0, 1], got {value}")


@dataclass
class Decision:
    action: Action
    severity: Severity
    reason: str
    confidence: float
    retrieval_score: float
    matched: list[str] = field(default_factory=list)

    @property
    def escalate(self) -> bool:
        return self.action is Action.ESCALATE

    def to_dict(self) -> dict:
        d = asdict(self)
        d["action"] = self.action.value
        d["severity"] = self.severity.value
        return d


def _matches(text: str, patterns: list[str]) -> list[str]:
    hits = []
    for pat in patterns:
        if re.search(pat, text, flags=re.IGNORECASE):
            hits.append(pat)
    return hits


def safety_trigger(
    user_message: str,
    answer_confidence: float = 0.0,
    retrieval_score: float = 0.0,
) -> Decision | None:
    """Return an escalate Decision if the message hits a hard safety trigger, else None.

    Exposed separately so the pipeline can short-circuit: a crisis or clinical message
    is routed to a human without ever calling the model (safer, faster, no spend).
    """
    text = user_message or ""
    crisis = _matches(text, CRISIS_PATTERNS)
    if crisis:
        return Decision(
            action=Action.ESCALATE,
            severity=Severity.CRITICAL,
            reason="Crisis language detected; route to a human immediately with full context.",
            confidence=answer_confidence,
            retrieval_score=retrieval_score,
            matched=crisis,
        )
    clinical = _matches(text, MEDICAL_PATTERNS) + _matches(text, SAFEGUARDING_PATTERNS)
    if clinical:
        return Decision(
            action=Action.ESCALATE,
            severity=Severity.HIGH,
            reason="Clinical or safeguarding topic; outside the bot's authority, hand to a human.",
            confidence=answer_confidence,
            retrieval_score=retrieval_score,
            matched=clinical,
        )
    return None


def decide(
    user_message: str,
    answer_confidence: float,
    retrieval_score: float,
    config: EscalationConfig | None = None,
) -> Decision:
    """Decide whether the bot answers or a human takes over.

    Order of checks (highest priority first):
      1. Safety triggers (crisis / medical / safeguarding) -> escalate regardless of confidence.
      2. Uncertainty: low model confidence OR weak retrieval -> escalate.
      3. Otherwise -> auto-answer.
    """
    config = config or EscalationConfig()

    # 1. Safety first, never silent.
    safety = safety_trigger(user_message, answer_confidence, retrieval_score)
    if safety is not None:
        return safety

    # 2. Uncertainty / novelty.
    low_conf = answer_confidence < config.min_answer_confidence
    weak_kb = retrieval_score < config.min_retrieval_score
    if low_conf or weak_kb:
        bits = []
        if low_conf:
            bits.append(f"model confidence {answer_confidence:.2f} < {config.min_answer_confidence:.2f}")
        if weak_kb:
            bits.append(f"retrieval {retrieval_score:.2f} < {config.min_retrieval_score:.2f}")
        return Decision(
            action=Action.ESCALATE,
            severity=Severity.LOW,
            reason="Uncertain or novel question (" + "; ".join(bits) + "); escalate rather than guess.",
            confidence=answer_confidence,
            retrieval_score=retrieval_score,
        )

    # 3. Routine and well-covered: the bot answers.
    return Decision(
        action=Action.AUTO,
        severity=Severity.NONE,
        reason="Routine, high-confidence, well-covered by the knowledge base.",
        confidence=answer_confidence,
        retrieval_score=retrieval_score,
    )


def max_severity(decisions: list[Decision]) -> Severity:
    """Highest severity across a set of decisions (for a conversation-level view)."""
    if not decisions:
        return Severity.NONE
    return max((d.severity for d in decisions), key=lambda s: _SEVERITY_ORDER[s])
