from pathlib import Path
from dotenv import load_dotenv

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import ValidationError

from agent_triager.agent import root_agent
from agent_triager.schema import schemas

import asyncio
import pandas as pd
import os

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

APP_NAME = "support-ticket-triager"

session_service = InMemorySessionService()

runner = Runner(
    app_name=APP_NAME,
    agent=root_agent,
    session_service=session_service,
)

repo_root = Path(__file__).resolve().parent.parent
input_csv = f"{repo_root}/support_tickets/support_tickets.csv"  # Use sample_support_tickets.csv to cross-check agent output to sample.
output_csv = f"{repo_root}/support_tickets/output.csv"

USER_ID = "batch-user"


async def main():
    try:
        input_file_path_abs = os.path.abspath(input_csv)
        input_df = pd.read_csv(input_file_path_abs)
        input_df["Issue"] = input_df["Issue"].fillna("Untitled")
        input_df["Subject"] = input_df["Subject"].fillna("No Subject")
        input_df["Company"] = input_df["Company"].fillna("None")

        results: list[dict] = []

        for n, (_, row) in enumerate(input_df.iterrows()):
            session_id = f"ticket-{n}"

            ticket = schemas.SupportTicketInput(
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

            async for _event in runner.run_async(
                user_id=USER_ID,
                session_id=session_id,
                new_message=types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=text)],
                ),
            ):
                # inspect _event
                pass

            session = await session_service.get_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=session_id,
            )

            raw = session.state.get("triage_result")
            ticket_dump = ticket.model_dump(mode="json")
            if raw is None:
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
                        schemas.PredictionOut.model_validate(raw)
                        if isinstance(raw, dict)
                        else raw
                    )
                    row_out = triage.model_dump(mode="json")
                except ValidationError:
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
