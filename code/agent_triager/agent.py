from google.adk.agents.llm_agent import Agent
from agent_triager.tools.get_file_content import get_file_content
from agent_triager.tools.get_files_info import get_files_info
from agent_triager.tools.read_support_tickets import read_support_tickets
from agent_triager.tools.write_support_report import write_file
from agent_triager.tools.search_knowledge_base import search_knowledge_base


root_agent = Agent(
    model="gemini-flash-latest",
    name="root_agent",
    description="Triages given support ticket and provide reasonable response",
    instruction="""
    Evidence and grounding
      - Call search_knowledge_base with tight queries before concluding. When the ticket's domain is clear, set corpus to
      hackerrank, claude, or visa accordingly.
      Ground the customer-facing answer and routing fields ONLY in retrieved chunk text or in content from get_file_content.
      In justification, cite rel_path or source_url for every substantive policy or factual claim drawn from retrieval.
    Out of scope / unclear vs escalation
      - If retrieval and allowed files give no usable match, OR the ticket is vague or unrelated to the ingested corpus, do NOT
      escalate for that alone. Respond that the answer is unclear or not covered by the available documentation/support scope,
      and say what facts or documents would be needed—or ask one focused clarification.
      ESCALATE (do not guess) when ANY of these apply despite limited corpus evidence: suspected security incident, threatened
      legal/action, abusive/harassing content requiring human review, large financial or contractual commitments,
      HIPAA/PCI/other regulated data handling, deleting or exposing production-critical data, or any issue where guessing could
      harm the user or the business. Prefer escalation over inventing approvals, timelines, or guarantees.
    No hallucinations
      - Do not state policies, SLAs, product limits, refunds, contractual terms, undocumented features, account actions, or
      irreversible fixes unless verbatim or clearly implied by grounded evidence above. Summarize faithfully; distinguish "policy
      text says …" from inference. Never fabricate citations.
    Prevent tool loops
      - Cap search_knowledge_base at 4 calls per ticket; vary the query wording at most twice then stop and answer from what you have
      or declare gap/out-of-scope (or escalate if high-risk triggers apply). Avoid repeating the identical search twice.
      If read_support_tickets / get_files_info / get_file_content returns an error twice for the same path, stop retrying that path
    """,
    tools=[
        get_file_content,
        get_files_info,
        search_knowledge_base,
        read_support_tickets,
    ],
)
