import pytest

from agent_triager.retrieval_confidence import RetrievalConfidence
from agent_triager.schema import PredictionOut, SupportTicketInput
from agent_triager.triage_service import auto_escalated_row, triage_ticket


def test_auto_escalated_row_is_valid_prediction_out():
    ticket = SupportTicketInput(
        issue="Who played Iron Man?",
        subject="Movie question",
        company="none",
    )
    confidence = RetrievalConfidence(
        is_confident=False,
        reason="best_distance_above_threshold",
        best_distance=0.9,
        hit_count=5,
        top_hits=[],
    )
    row = auto_escalated_row(ticket, confidence)
    validated = PredictionOut.model_validate(row)

    assert validated.status == "escalated"
    assert validated.product_area == "general_support"
    assert "documentation" in validated.response.lower()
    assert "best_distance" in validated.justification


@pytest.mark.asyncio
async def test_triage_ticket_auto_escalates_on_low_confidence(monkeypatch):
    ticket = SupportTicketInput(
        issue="Who played Iron Man?",
        subject="Movie question",
        company="HackerRank",
    )

    monkeypatch.setattr(
        "agent_triager.triage_service.bootstrap_retrieve",
        lambda *_args, **_kwargs: [{"distance": 0.9, "chunk_id": "x", "text": "irrelevant"}],
    )
    monkeypatch.setattr(
        "agent_triager.triage_service.bootstrap_retrieve_retry",
        lambda *_args, **_kwargs: [{"distance": 0.88, "chunk_id": "y", "text": "still bad"}],
    )

    async def fail_if_called(*_args, **_kwargs):
        raise AssertionError("agent runner should not be called on auto-escalate")

    monkeypatch.setattr("agent_triager.triage_service.runner.run_async", fail_if_called)

    outcome = await triage_ticket(ticket, user_id="test-user", session_id="test-session")

    assert outcome.outcome == "auto_escalated"
    assert outcome.gate_action == "auto_escalate"
    assert outcome.retrieval_confident is False
    assert outcome.row["status"] == "escalated"
    assert outcome.row["company"] == "hackerrank"
