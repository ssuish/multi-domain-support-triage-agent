from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Literal

from google.genai import types
from pydantic import ValidationError

from agent_triager.retrieval_bootstrap import (
    bootstrap_retrieve,
    bootstrap_retrieve_retry,
    corpus_filter_for_company,
    normalize_company,
)
from agent_triager.retrieval_confidence import (
    RetrievalConfidence,
    evaluate_retrieval_confidence,
)
from agent_triager.schema import PredictionOut, SupportTicketInput
from runner_bootstrap import APP_NAME, runner, session_service

GateAction = Literal["proceed", "retry", "auto_escalate", "post_override"]
TriageOutcomeKind = Literal[
    "ok_validated",
    "missing_triage_result",
    "validation_error",
    "exception",
    "auto_escalated",
]

OUTPUT_COLUMNS = [
    "issue",
    "subject",
    "company",
    "response",
    "product_area",
    "status",
    "request_type",
    "justification",
]

_GATE_SAFE_RESPONSE = (
    "We could not find enough relevant documentation to answer this safely. "
    "A support specialist will review your ticket."
)


@dataclass
class TriageOutcome:
    row: dict
    outcome: TriageOutcomeKind
    gate_action: GateAction
    retrieval_confident: bool
    retrieval_reason: str
    best_distance: float | None
    hit_count: int
    error: BaseException | None = None
    latency_ms: int | None = None


def normalize_ticket(ticket: SupportTicketInput) -> SupportTicketInput:
    return SupportTicketInput(
        issue=ticket.issue,
        subject=ticket.subject,
        company=normalize_company(ticket.company),
    )


def auto_escalated_row(
    ticket: SupportTicketInput,
    confidence: RetrievalConfidence,
    *,
    request_type: str = "product_issue",
) -> dict:
    normalized_company = normalize_company(ticket.company)
    best_distance = confidence.best_distance
    best_distance_text = "None" if best_distance is None else f"{best_distance:.4f}"
    return {
        "issue": ticket.issue,
        "subject": ticket.subject,
        "company": normalized_company,
        "status": "escalated",
        "request_type": request_type,
        "product_area": "general_support",
        "response": _GATE_SAFE_RESPONSE,
        "justification": (
            "Retrieval confidence below threshold: "
            f"{confidence.reason}. best_distance={best_distance_text}, "
            f"hit_count={confidence.hit_count}."
        ),
    }


def system_escalated_row(ticket: SupportTicketInput, *, internal_reason: str) -> dict:
    normalized_company = normalize_company(ticket.company)
    return {
        "issue": ticket.issue,
        "subject": ticket.subject,
        "company": normalized_company,
        "response": (
            "We could not finish automated triage for this ticket. "
            "A team member will review it."
        ),
        "product_area": "system",
        "status": "escalated",
        "request_type": "product_issue",
        "justification": internal_reason,
    }


def _confidence_telemetry(confidence: RetrievalConfidence) -> dict:
    return {
        "retrieval_confident": confidence.is_confident,
        "retrieval_reason": confidence.reason,
        "best_distance": confidence.best_distance,
        "hit_count": confidence.hit_count,
    }


def _run_retrieval_gate(ticket: SupportTicketInput) -> tuple[list[dict], RetrievalConfidence, GateAction]:
    normalized = normalize_company(ticket.company)
    used_corpus_filter = corpus_filter_for_company(normalized) is not None

    hits = bootstrap_retrieve(ticket)
    confidence = evaluate_retrieval_confidence(hits)
    if confidence.is_confident:
        return hits, confidence, "proceed"

    if used_corpus_filter:
        retry_hits = bootstrap_retrieve_retry(ticket)
        retry_confidence = evaluate_retrieval_confidence(retry_hits)
        if retry_confidence.is_confident:
            return retry_hits, retry_confidence, "retry"

        return retry_hits, retry_confidence, "auto_escalate"

    return hits, confidence, "auto_escalate"


async def triage_ticket(
    ticket: SupportTicketInput,
    *,
    user_id: str,
    session_id: str,
) -> TriageOutcome:
    started = perf_counter()
    ticket = normalize_ticket(ticket)

    try:
        hits, confidence, gate_action = _run_retrieval_gate(ticket)
        telemetry = _confidence_telemetry(confidence)

        if gate_action == "auto_escalate":
            latency_ms = int(round((perf_counter() - started) * 1000))
            return TriageOutcome(
                row=auto_escalated_row(ticket, confidence),
                outcome="auto_escalated",
                gate_action=gate_action,
                latency_ms=latency_ms,
                **telemetry,
            )

        session_state = {
            **ticket.model_dump(mode="json"),
            "retrieval_evidence": hits,
        }
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
            state=session_state,
        )

        async for _event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part.from_text(text=ticket.model_dump_json())],
            ),
        ):
            pass

        session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )

        raw = session.state.get("triage_result")
        if raw is None:
            latency_ms = int(round((perf_counter() - started) * 1000))
            return TriageOutcome(
                row=system_escalated_row(
                    ticket,
                    internal_reason="triage_result missing from session state after agent run.",
                ),
                outcome="missing_triage_result",
                gate_action=gate_action,
                latency_ms=latency_ms,
                **telemetry,
            )

        try:
            triage = PredictionOut.model_validate(raw) if isinstance(raw, dict) else raw
            row_out = triage.model_dump(mode="json")
            outcome: TriageOutcomeKind = "ok_validated"
        except ValidationError:
            latency_ms = int(round((perf_counter() - started) * 1000))
            return TriageOutcome(
                row=system_escalated_row(
                    ticket,
                    internal_reason=(
                        "PredictionOut validation failed for agent output: "
                        f"{list(raw.keys()) if isinstance(raw, dict) else type(raw)}."
                    ),
                ),
                outcome="validation_error",
                gate_action=gate_action,
                latency_ms=latency_ms,
                **telemetry,
            )

        post_confidence = evaluate_retrieval_confidence(hits)
        if row_out.get("status") == "replied" and not post_confidence.is_confident:
            latency_ms = int(round((perf_counter() - started) * 1000))
            return TriageOutcome(
                row=auto_escalated_row(ticket, post_confidence),
                outcome="auto_escalated",
                gate_action="post_override",
                latency_ms=latency_ms,
                retrieval_confident=post_confidence.is_confident,
                retrieval_reason=post_confidence.reason,
                best_distance=post_confidence.best_distance,
                hit_count=post_confidence.hit_count,
            )

        latency_ms = int(round((perf_counter() - started) * 1000))
        return TriageOutcome(
            row=row_out,
            outcome=outcome,
            gate_action=gate_action,
            latency_ms=latency_ms,
            **telemetry,
        )
    except Exception as exc:
        latency_ms = int(round((perf_counter() - started) * 1000))
        return TriageOutcome(
            row=system_escalated_row(ticket, internal_reason=str(exc)),
            outcome="exception",
            gate_action="auto_escalate",
            retrieval_confident=False,
            retrieval_reason="exception",
            best_distance=None,
            hit_count=0,
            error=exc,
            latency_ms=latency_ms,
        )
