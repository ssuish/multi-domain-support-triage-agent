from google.adk.agents.llm_agent import Agent
from agent_triager.tools.get_file_content import get_file_content
from agent_triager.tools.get_files_info import get_files_info
from agent_triager.tools.read_support_tickets import read_support_tickets
from agent_triager.tools.write_support_report import write_file


root_agent = Agent(
    model="gemini-flash-latest",
    name="root_agent",
    description="Triages given support ticket and provide reasonable response",
    instruction=(
        "You are a strict support ticket triage agent. "
        "On any ambiguity, uncertainty, or missing context, immediately stop further reasoning. "
        "Never infer unstated facts. Never fabricate ticket details."
    ),
    tools=[get_file_content, get_files_info, read_support_tickets],
)
