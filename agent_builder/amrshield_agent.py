from google.adk.agents import LlmAgent
from google.adk.tools import agent_tool
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.adk.tools import url_context

amrshield_clinical_agent_google_search_agent = LlmAgent(
  name='AMRShield_Clinical_Agent_google_search_agent',
  model='gemini-2.5-flash',
  description='Agent specialized in performing Google searches.',
  sub_agents=[],
  instruction='Use the GoogleSearchTool to find information on the web.',
  tools=[GoogleSearchTool()],
)

amrshield_clinical_agent_url_context_agent = LlmAgent(
  name='AMRShield_Clinical_Agent_url_context_agent',
  model='gemini-2.5-flash',
  description='Agent specialized in fetching content from URLs.',
  sub_agents=[],
  instruction='Use the UrlContextTool to retrieve content from provided URLs.',
  tools=[url_context],
)

root_agent = LlmAgent(
  name='AMRShield_Clinical_Agent',
  model='gemini-2.5-flash',
  description='AMRShield AI-powered Antibiotic Stewardship agent built on Google Cloud Agent Builder with Arize Phoenix MCP observability.',
  sub_agents=[],
  instruction="""You are AMRShield's Clinical Recommendation Agent for antibiotic stewardship.
Given a patient case, recommend the most appropriate antibiotic following WHO AWaRe guidelines.
Always check: renal function (CrCl), drug interactions, local antibiogram, and allergy conflicts.
Prefer Access-tier antibiotics when clinically appropriate.
Every recommendation is audited by the Self-Audit Agent via Arize Phoenix MCP for safety.""",
  tools=[
    agent_tool.AgentTool(agent=amrshield_clinical_agent_google_search_agent),
    agent_tool.AgentTool(agent=amrshield_clinical_agent_url_context_agent),
  ],
)
