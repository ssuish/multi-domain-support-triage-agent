from __future__ import annotations

import asyncio
import io
import logging
import os
import uuid

import pandas as pd
import streamlit as st

from agent_triager.schema import SupportTicketInput
from agent_triager.triage_service import OUTPUT_COLUMNS, triage_ticket
from config import RAG_PERSIST_DIR
from paths import REPO_ROOT

logger = logging.getLogger(__name__)

REQUIRED_CSV_COLUMNS = ["Issue", "Subject", "Company"]

COMPANY_OPTIONS: dict[str, str] = {
    "HackerRank": "hackerrank",
    "Claude": "claude",
    "Visa": "visa",
    "Other": "none",
}

STATUS_LABELS = {
    "replied": "Answered",
    "escalated": "Needs follow-up",
}

REQUEST_TYPE_LABELS = {
    "product_issue": "Product issue",
    "feature_request": "Feature request",
    "bug": "Bug",
    "invalid": "Invalid",
}

CSV_TEMPLATE = (
    "Issue,Subject,Company\n"
    '"Cannot reset password","Password reset link expired","hackerrank"\n'
    '"Card declined online","Payment failed at checkout","visa"\n'
)


def _humanize(value: str | None, labels: dict[str, str]) -> str:
    if not value:
        return "—"
    return labels.get(value, value.replace("_", " ").title())


def _friendly_error_message(exc: BaseException) -> str:
    message = str(exc).lower()

    if "rag index missing" in message:
        return (
            "Knowledge base is not ready. From the project folder, run: "
            "`python scripts/build_rag_index.py`"
        )
    if any(
        token in message
        for token in ("api key", "api_key", "unauthorized", "authentication", "401")
    ):
        return (
            "Google API key is missing or invalid. Add `GOOGLE_API_KEY` to your `.env` file."
        )
    if any(token in message for token in ("quota", "rate limit", "429", "resource exhausted")):
        return "The AI service is temporarily unavailable. Wait a moment and try again."
    if any(
        token in message
        for token in ("connection", "timeout", "network", "unavailable", "503", "502")
    ):
        return "Could not reach the AI service. Check your internet connection and try again."

    return "Something went wrong while triaging this ticket. Try again or contact your admin."


def _get_setup_issues() -> list[str]:
    issues: list[str] = []
    if not os.getenv("GOOGLE_API_KEY", "").strip():
        issues.append("Add `GOOGLE_API_KEY` to `.env` in the project folder.")
    rag_path = (REPO_ROOT / RAG_PERSIST_DIR).resolve()
    if not rag_path.exists():
        issues.append("Build the knowledge base: `python scripts/build_rag_index.py`")
    return issues


def _render_setup_banner() -> bool:
    issues = _get_setup_issues()
    if not issues:
        return True

    st.warning("Setup needed before triage can run:")
    for issue in issues:
        st.markdown(f"- {issue}")
    return False


def _run_triage_safe(
    ticket: SupportTicketInput,
    *,
    user_id: str,
    session_id: str,
) -> tuple[dict, str | None]:
    try:
        outcome = asyncio.run(
            triage_ticket(ticket, user_id=user_id, session_id=session_id)
        )
        if outcome.error is not None:
            return outcome.row, _friendly_error_message(outcome.error)
        return outcome.row, None
    except Exception as exc:
        logger.exception("triage failed for subject=%r", ticket.subject)
        from agent_triager.triage_service import system_escalated_row

        return system_escalated_row(ticket, internal_reason=str(exc)), _friendly_error_message(
            exc
        )


def _render_result(result: dict, *, show_error: str | None = None) -> None:
    if show_error:
        st.error(show_error)

    col1, col2, col3 = st.columns(3)
    col1.metric("Outcome", _humanize(result.get("status"), STATUS_LABELS))
    col2.metric("Topic", result.get("product_area", "—"))
    col3.metric("Type", _humanize(result.get("request_type"), REQUEST_TYPE_LABELS))

    st.markdown("**Suggested reply**")
    st.write(result.get("response", ""))

    justification = result.get("justification", "")
    if justification:
        with st.expander("Internal notes"):
            st.write(justification)


def _render_single_ticket_mode(*, setup_ready: bool) -> None:
    st.subheader("Single ticket")
    st.caption("Enter one support ticket and get a suggested reply.")

    if "history" not in st.session_state:
        st.session_state.history = []

    with st.form("ticket_form", clear_on_submit=False):
        subject = st.text_input("Subject", placeholder="Short summary of the issue")
        issue = st.text_area(
            "Issue details",
            height=160,
            placeholder="Paste the full ticket message here",
        )
        company_label = st.selectbox(
            "Customer",
            options=list(COMPANY_OPTIONS.keys()),
            help="Choose which help center content applies to this ticket.",
        )
        submitted = st.form_submit_button("Get suggested reply", type="primary")

    if not submitted:
        _render_history()
        return

    company = COMPANY_OPTIONS[company_label]
    if not issue.strip() or not subject.strip():
        st.error("Subject and issue details are required.")
        _render_history()
        return

    if not setup_ready:
        st.error("Complete setup steps above before running triage.")
        _render_history()
        return

    ticket = SupportTicketInput(
        issue=issue.strip(),
        subject=subject.strip(),
        company=company,
    )
    session_id = f"chat-{uuid.uuid4()}"

    with st.spinner("Reviewing ticket..."):
        result, error_message = _run_triage_safe(
            ticket,
            user_id="ui-chat-user",
            session_id=session_id,
        )

    st.session_state.history.insert(
        0,
        {
            "ticket": ticket.model_dump(mode="json"),
            "result": result,
            "error_message": error_message,
        },
    )
    _render_result(result, show_error=error_message)
    _render_history()


def _render_history() -> None:
    if not st.session_state.get("history"):
        return

    with st.expander(f"Previous tickets ({len(st.session_state.history)})"):
        for idx, entry in enumerate(st.session_state.history):
            ticket = entry["ticket"]
            result = entry["result"]
            st.markdown(f"**#{idx + 1}** — {ticket['subject']} ({ticket['company']})")
            st.caption(
                f"{_humanize(result.get('status'), STATUS_LABELS)} · "
                f"{_humanize(result.get('request_type'), REQUEST_TYPE_LABELS)}"
            )
            st.write(result.get("response", ""))
            if entry.get("error_message"):
                st.caption(entry["error_message"])
            st.divider()


def _normalize_batch_df(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized["Issue"] = normalized["Issue"].fillna("Untitled")
    normalized["Subject"] = normalized["Subject"].fillna("No Subject")
    normalized["Company"] = normalized["Company"].fillna("none")
    return normalized


def _render_csv_mode(*, setup_ready: bool) -> None:
    st.subheader("Upload CSV")
    st.caption(
        "Upload a spreadsheet with columns **Issue**, **Subject**, and **Company**. "
        "Company values: `hackerrank`, `claude`, `visa`, or `none`."
    )

    st.download_button(
        label="Download example CSV",
        data=CSV_TEMPLATE,
        file_name="ticket_template.csv",
        mime="text/csv",
    )

    uploaded = st.file_uploader("Choose CSV file", type=["csv"])

    if uploaded is None:
        return

    try:
        input_df = pd.read_csv(uploaded)
    except Exception as exc:
        logger.exception("csv read failed")
        st.error(
            "This file could not be read. Save it as a comma-separated CSV and try again."
        )
        return

    missing = [col for col in REQUIRED_CSV_COLUMNS if col not in input_df.columns]
    if missing:
        st.error(
            f"This file is missing required columns: {', '.join(missing)}. "
            "Use the example CSV as a template."
        )
        return

    input_df = _normalize_batch_df(input_df)
    st.write(f"{len(input_df)} ticket(s) ready.")
    st.dataframe(input_df, use_container_width=True)

    if not st.button("Process all tickets", type="primary"):
        return

    if not setup_ready:
        st.error("Complete setup steps above before running triage.")
        return

    results: list[dict] = []
    failed_count = 0
    progress = st.progress(0.0, text="Starting...")
    status = st.status("Processing tickets...", expanded=True)

    for n, (_, row) in enumerate(input_df.iterrows()):
        ticket = SupportTicketInput(
            company=str(row["Company"]),
            subject=str(row["Subject"]),
            issue=str(row["Issue"]),
        )
        session_id = f"batch-{n}-{uuid.uuid4()}"
        status.write(f"Ticket {n + 1} of {len(input_df)}: {ticket.subject[:80]}")

        result, error_message = _run_triage_safe(
            ticket,
            user_id="ui-batch-user",
            session_id=session_id,
        )
        results.append(result)

        outcome = _humanize(result.get("status"), STATUS_LABELS)
        if error_message:
            failed_count += 1
            status.write(f"Could not finish — marked for follow-up ({outcome})")
        else:
            status.write(f"Done — {outcome}")

        progress.progress(
            (n + 1) / len(input_df),
            text=f"Processed {n + 1} of {len(input_df)}",
        )

    status.update(label="Processing complete", state="complete", expanded=False)
    progress.empty()

    if failed_count:
        st.warning(
            f"{failed_count} ticket(s) could not be fully processed and were marked for follow-up."
        )

    display_df = pd.DataFrame(results, columns=OUTPUT_COLUMNS).copy()
    display_df["status"] = display_df["status"].map(
        lambda value: _humanize(value, STATUS_LABELS)
    )
    display_df["request_type"] = display_df["request_type"].map(
        lambda value: _humanize(value, REQUEST_TYPE_LABELS)
    )

    st.subheader("Results")
    st.dataframe(display_df, use_container_width=True)

    csv_buffer = io.StringIO()
    pd.DataFrame(results, columns=OUTPUT_COLUMNS).to_csv(csv_buffer, index=False)
    st.download_button(
        label="Download results CSV",
        data=csv_buffer.getvalue(),
        file_name="triage_results.csv",
        mime="text/csv",
    )


def main() -> None:
    st.set_page_config(
        page_title="Support Ticket Triager",
        layout="wide",
    )
    st.title("Support Ticket Triager")
    st.caption("Review support tickets and get suggested replies.")

    setup_ready = _render_setup_banner()

    mode = st.sidebar.radio(
        "How to submit",
        ["Single ticket", "Upload CSV"],
        index=0,
    )

    if mode == "Single ticket":
        _render_single_ticket_mode(setup_ready=setup_ready)
    else:
        _render_csv_mode(setup_ready=setup_ready)


if __name__ == "__main__":
    main()
