"""Pipeline orchestration tests. Retriever and LLM are faked, so these run offline
and spend no API credits - they check the routing logic, not the model."""
from app import pipeline
from app.escalation import Action, Severity
from app.llm import LLMResult
from app.rag import Hit

GOOD_HITS = [Hit("reschedule", "Rescheduling a session", "Open your dashboard and pick a slot.", 0.82)]
WEAK_HITS = [Hit("x", "Unrelated", "Nothing useful here.", 0.08)]


class FakeRetriever:
    def __init__(self, hits):
        self._hits = hits

    def search(self, query, k=4):
        return self._hits


class FakeLLM:
    def __init__(self, text):
        self._text = text

    def complete(self, system, messages, max_tokens=400):
        return LLMResult(self._text, "anthropic", "claude-sonnet-5-5", fell_back=False)


def test_covered_question_auto_answers():
    r = pipeline.answer(
        "How do I reschedule my session?", [], FakeRetriever(GOOD_HITS),
        FakeLLM("Open your dashboard and choose a new slot at least 24 hours ahead."),
    )
    assert r["decision"].action is Action.AUTO
    assert r["answer"]
    assert not r["decision"].escalate


def test_crisis_escalates_critical_regardless_of_context():
    r = pipeline.answer(
        "I want to kill myself", [], FakeRetriever(GOOD_HITS), FakeLLM("Open your dashboard."),
    )
    assert r["decision"].escalate
    assert r["decision"].severity is Severity.CRITICAL
    assert "connecting you to a member of our team" in r["handoff"]


def test_insufficient_context_escalates_and_hides_answer():
    r = pipeline.answer(
        "What is the capital of France?", [], FakeRetriever(GOOD_HITS), FakeLLM("INSUFFICIENT_CONTEXT"),
    )
    assert r["decision"].escalate
    assert r["answer"] is None


def test_weak_retrieval_escalates():
    r = pipeline.answer(
        "Can I bring my dog to sessions?", [], FakeRetriever(WEAK_HITS), FakeLLM("Sure, pets are welcome."),
    )
    assert r["decision"].escalate


def test_sources_are_returned():
    r = pipeline.answer(
        "How do I reschedule?", [], FakeRetriever(GOOD_HITS), FakeLLM("Open your dashboard."),
    )
    assert r["sources"] and r["sources"][0]["id"] == "reschedule"


def test_truncated_model_output_is_not_shown_as_a_complete_answer():
    truncated = LLMResult(
        "Any fees are shown before you join, but this answer stops",
        "anthropic",
        "claude-sonnet-5-5",
        fell_back=False,
        stop_reason="max_tokens",
    )
    # Use a small provider-shaped fake so the pipeline sees the stop reason.
    class TruncatedLLM:
        def complete(self, system, messages, max_tokens=600):
            return truncated

    r = pipeline.answer("How do groups work?", [], FakeRetriever(GOOD_HITS), TruncatedLLM())
    assert r["decision"].escalate
    assert r["answer"] is None
