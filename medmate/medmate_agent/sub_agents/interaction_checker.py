"""Interaction-checker sub-agent: the only sub-agent that talks to the MCP server."""
# Design Choice Rationale: Decoupling interaction-checking into its own agent 
# connects it strictly with the drug_interaction_toolset (MCP). This prevents
# other agents from hallucinating clinical advice. It also demonstrates process-level
# isolation: the MCP server runs as a separate subprocess, ensuring bugs or crashes
# there cannot impact scheduler or refill tasks.
from google.adk.agents import LlmAgent
from medmate_agent.tools.interaction_mcp_client import drug_interaction_toolset

interaction_checker_agent = LlmAgent(
    name="interaction_checker_agent",
    model="gemini-2.5-flash",
    description="Checks a set of medications for known dangerous interactions via the MCP drug-interaction server.",
    instruction="""You are the Interaction Checker sub-agent for MedMate.
Use the check_drug_interactions tool (served over MCP) to flag risky
combinations whenever the user lists two or more medications.
If any interaction is flagged as 'high' severity, clearly recommend the user
confirm with a pharmacist or doctor before continuing -- do not minimize it.
You do not modify schedules or inventory; that belongs to other sub-agents.""",
    tools=[drug_interaction_toolset],
)
