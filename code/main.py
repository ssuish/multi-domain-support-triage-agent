from dotenv import load_dotenv

from agent_triager.schema import SupportTicketInput
from agent_triager.triage_service import OUTPUT_COLUMNS, triage_ticket
from paths import ENV_FILE, INPUT_CSV, OUTPUT_CSV, RUNS_DIR

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone

import pandas as pd

load_dotenv(ENV_FILE)

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
        input_df["Company"] = input_df["Company"].fillna("none")

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

                started_at_wall = datetime.now(timezone.utc)
                started_at_iso = started_at_wall.isoformat()

                outcome = await triage_ticket(
                    ticket,
                    user_id=USER_ID,
                    session_id=session_id,
                )

                finished_at_wall = datetime.now(timezone.utc)
                finished_at_iso = finished_at_wall.isoformat()

                results.append(outcome.row)

                telemetry = {
                    "run_id": run_id,
                    "ticket_index": n,
                    "session_id": session_id,
                    "started_at": started_at_iso,
                    "finished_at": finished_at_iso,
                    "latency_ms": outcome.latency_ms,
                    "outcome": outcome.outcome,
                    "company": outcome.row.get("company"),
                    "subject_preview": _subject_preview(outcome.row.get("subject", "")),
                    "retrieval_confident": outcome.retrieval_confident,
                    "retrieval_reason": outcome.retrieval_reason,
                    "best_distance": outcome.best_distance,
                    "hit_count": outcome.hit_count,
                    "gate_action": outcome.gate_action,
                }
                jsonl_f.write(json.dumps(telemetry, ensure_ascii=False) + "\n")
                jsonl_f.flush()

        pd.DataFrame(results, columns=OUTPUT_COLUMNS).to_csv(output_csv, index=False)

    except Exception as e:
        raise


if __name__ == "__main__":
    asyncio.run(main())
