from dotenv import load_dotenv

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import ValidationError

from agent_triager.agent import root_agent
from agent_triager.schema import PredictionOut, SupportTicketInput
from paths import ENV_FILE, INPUT_CSV, OUTPUT_CSV, RUNS_DIR

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from time import perf_counter

import pandas as pd

load_dotenv(ENV_FILE)

APP_NAME = "support-ticket-triager"

session_service = InMemorySessionService()

runner = Runner(
    app_name=APP_NAME,
    agent=root_agent,
    session_service=session_service,
)

# Use REPO_ROOT / "support_tickets" / "sample_support_tickets.csv" to cross-check agent output.
input_csv = str(INPUT_CSV)
output_csv = str(OUTPUT_CSV)

USER_ID = "batch-user"

SUBJECT_PREVIEW_MAX_LEN = 120


def _subject_preview(subject: str, max_len: int = SUBJECT_PREVIEW_MAX_LEN) -> str:
    s = subject or ""
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


async def main():
    try:
        input_file_path_abs = os.path.abspath(input_csv)
        input_df = pd.read_csv(input_file_path_abs)
        input_df["Issue"] = input_df["Issue"].fillna("Untitled")
        input_df["Subject"] = input_df["Subject"].fillna("No Subject")
        input_df["Company"] = input_df["Company"].fillna("None")

        results: list[dict] = []

        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        run_id = str(uuid.uuid4())
        batch_started_wall = datetime.now(timezone.utc)
        timestamp_slug = batch_started_wall.strftime("%Y%m%dT%H%M%SZ")
        jsonl_path = RUNS_DIR / f"{timestamp_slug}_{run_id}_batch.jsonl"

        with open(jsonl_path, "w", encoding="utf-8") as jsonl_f:
            for n, (_, row) in enumerate(input_df.iterrows()):
                session_id = f"ticket-{n}"

                ticket = SupportTicketInput(
                    company=str(row["Company"]),
                    subject=str(row["Subject"]),
                    issue=str(row["Issue"]),
                )

                await session_service.create_session(
                    app_name=APP_NAME,
                    user_id=USER_ID,
                    session_id=session_id,
                    state=ticket.model_dump(mode="json"),
                )

                text = ticket.model_dump_json()

                started_mono = perf_counter()
                started_at_wall = datetime.now(timezone.utc)
                started_at_iso = started_at_wall.isoformat()

                async for _event in runner.run_async(
                    user_id=USER_ID,
                    session_id=session_id,
                    new_message=types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=text)],
                    ),
                ):
                    pass

                session = await session_service.get_session(
                    app_name=APP_NAME,
                    user_id=USER_ID,
                    session_id=session_id,
                )

                finished_at_wall = datetime.now(timezone.utc)
                finished_at_iso = finished_at_wall.isoformat()
                latency_ms = int(round((perf_counter() - started_mono) * 1000))

                raw = session.state.get("triage_result")
                ticket_dump = ticket.model_dump(mode="json")
                if raw is None:
                    outcome = "missing_triage_result"
                    row_out = {
                        "issue": ticket_dump["issue"],
                        "subject": ticket_dump["subject"],
                        "company": ticket_dump["company"],
                        "response": "We could not complete automated triage for this ticket. A human will review it.",
                        "product_area": "system",
                        "status": "escalated",
                        "request_type": "product_issue",
                        "justification": "triage_result missing from session state after agent run.",
                    }
                else:
                    try:
                        triage = (
                            PredictionOut.model_validate(raw)
                            if isinstance(raw, dict)
                            else raw
                        )
                        row_out = triage.model_dump(mode="json")
                        outcome = "ok_validated"
                    except ValidationError:
                        outcome = "validation_error"
                        row_out = {
                            "issue": ticket_dump["issue"],
                            "subject": ticket_dump["subject"],
                            "company": ticket_dump["company"],
                            "response": "Automated triage returned an invalid structured result; escalating for human review.",
                            "product_area": "system",
                            "status": "escalated",
                            "request_type": "product_issue",
                            "justification": f"PredictionOut validation failed for raw payload keys: {list(raw.keys()) if isinstance(raw, dict) else type(raw)}.",
                        }
                results.append(row_out)

                telemetry = {
                    "run_id": run_id,
                    "ticket_index": n,
                    "session_id": session_id,
                    "started_at": started_at_iso,
                    "finished_at": finished_at_iso,
                    "latency_ms": latency_ms,
                    "outcome": outcome,
                    "company": ticket_dump["company"],
                    "subject_preview": _subject_preview(ticket_dump["subject"]),
                }
                jsonl_f.write(json.dumps(telemetry, ensure_ascii=False) + "\n")
                jsonl_f.flush()

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
        pd.DataFrame(results, columns=OUTPUT_COLUMNS).to_csv(output_csv, index=False)

    except Exception as e:
        raise


if __name__ == "__main__":
    asyncio.run(main())
