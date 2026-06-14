from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from agent_triager.agent import root_agent

APP_NAME = "support-ticket-triager"

session_service = InMemorySessionService()

runner = Runner(
    app_name=APP_NAME,
    agent=root_agent,
    session_service=session_service,
)
