"""Unit tests for the escalation decision engine.

These prove the routing behaviour that the product promises: safety first,
uncertainty escalates, routine high-confidence answers go straight through.
"""
import pytest

from app.escalation import (
    Action,
    Decision,
    EscalationConfig,
    Severity,
    decide,
    max_severity,
)

HIGH = 0.9   # confident answer
LOWC = 0.3   # low model confidence
STRONG = 0.8  # strong retrieval
WEAK = 0.1    # weak retrieval


def test_routine_question_auto_answers():
    d = decide("What time does the Tuesday group session start?", HIGH, STRONG)
    assert d.action is Action.AUTO
    assert d.severity is Severity.NONE
    assert not d.escalate


@pytest.mark.parametrize(
    "msg",
    [
        "I want to kill myself",
        "Sometimes I think about suicide",
        "I have been self-harming again",
        "I don't want to be here anymore",
        "I am in immediate danger and need urgent help",
    ],
)
def test_crisis_always_escalates_even_when_confident(msg):
    # Safety wins over confidence: high confidence + strong retrieval must still escalate.
    d = decide(msg, HIGH, STRONG)
    assert d.action is Action.ESCALATE
    assert d.severity is Severity.CRITICAL
    assert d.matched


def test_medical_topic_escalates():
    d = decide("Should I stop taking my medication this week?", HIGH, STRONG)
    assert d.escalate
    assert d.severity is Severity.HIGH


def test_safeguarding_topic_escalates():
    d = decide("I think my partner is abusive and I feel unsafe", HIGH, STRONG)
    assert d.escalate
    assert d.severity is Severity.HIGH


def test_low_confidence_escalates():
    d = decide("How does the deposit refund interact with partial attendance?", LOWC, STRONG)
    assert d.escalate
    assert d.severity is Severity.LOW
    assert "confidence" in d.reason


def test_weak_retrieval_escalates():
    d = decide("Can I bring my support dog to the retreat?", HIGH, WEAK)
    assert d.escalate
    assert d.severity is Severity.LOW
    assert "retrieval" in d.reason


def test_thresholds_are_configurable():
    strict = EscalationConfig(min_answer_confidence=0.95, min_retrieval_score=0.25)
    # An answer that passes the default now fails the stricter bar.
    d = decide("What time does the session start?", 0.9, STRONG, config=strict)
    assert d.escalate


def test_config_rejects_out_of_range():
    with pytest.raises(ValueError):
        EscalationConfig(min_answer_confidence=1.5)


def test_decision_serialises_to_plain_dict():
    d = decide("hello", HIGH, STRONG)
    out = d.to_dict()
    assert out["action"] == "auto"
    assert out["severity"] == "none"
    assert isinstance(out["matched"], list)


def test_max_severity_picks_highest():
    decisions = [
        decide("what time is group?", HIGH, STRONG),          # none
        decide("refund question", LOWC, STRONG),              # low
        decide("I want to kill myself", HIGH, STRONG),        # critical
    ]
    assert max_severity(decisions) is Severity.CRITICAL
    assert max_severity([]) is Severity.NONE
