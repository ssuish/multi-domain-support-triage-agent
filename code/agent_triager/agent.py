from google.adk.agents import Agent, SequentialAgent
from agent_triager.tools.search_knowledge_base import search_knowledge_base
from agent_triager.schema import PredictionOut, SupportTicketInput

_retrieval_agent = Agent(
    model="gemini-flash-latest",
    name="retrieval_agent",
    description="Searches internal docs and surfaces relevant chunks for triage.",
    instruction="""
    You receive a support ticket (Company, Subject, Issue).
    Bootstrap retrieval already ran before this pipeline; session state may include
    retrieval_evidence as the authoritative hit list for gating.
    1. Identify the corpus: hackerrank, claude, or visa.
    2. Call search_knowledge_base up to 4 times with tight, varied queries.
       Pass corpus= to restrict to the matching index.
    3. Do NOT write a customer response. Stop after retrieval is complete.
    """,
    input_schema=SupportTicketInput,
    tools=[search_knowledge_base],
)

_format_agent = Agent(
    model="gemini-flash-latest",
    name="format_agent",
    description="Produces a grounded PredictionOut from retrieval evidence.",
    instruction="""
    You are the final triage formatter.
    You have access to the ticket (Company, Subject, Issue), retrieval_evidence
    in session state, and search_knowledge_base results from the prior retrieval step.

    Bootstrap retrieval in session state (retrieval_evidence) is the source of truth
    for whether documentation supports a reply. If retrieval_evidence is weak, empty,
    or missing, you MUST set status to "escalated" — never status "replied".

    Using only that evidence, fill every PredictionOut field:
    - issue, subject, company: copy verbatim from the ticket (session state)
    - response: customer-facing reply
    - product_area: short label
    - status: "replied" or "escalated"
    - request_type: product_issue | feature_request | bug | invalid
    - justification: cite rel_path or source_url for every factual claim

    ESCALATE when: security incident, legal threat, abuse, large financial/contractual
    commitment, regulated data, production-critical risk, or insufficient retrieval evidence.
    Never fabricate policies, SLAs, steps, or features absent from retrieval.
    """,
    output_schema=PredictionOut,
    output_key="triage_result",
)

root_agent = SequentialAgent(
    name="root_agent",
    description="Retrieval then structured triage output.",
    sub_agents=[_retrieval_agent, _format_agent],
)
