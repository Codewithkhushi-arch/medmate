"""
MedMate root orchestrator.

Routes user requests to one of three specialist sub-agents:
  - scheduler_agent: medication timing & dose logging
  - interaction_checker_agent: drug interaction checks (via MCP server)
  - refill_agent: inventory tracking & refill drafting

ADK's automatic sub-agent transfer lets the LLM pick the right specialist
per turn based on each sub-agent's `description` field, so this file stays
small -- the orchestrator's job is routing + consent enforcement, not domain
logic.
"""
from google.adk.agents import LlmAgent
from medmate_agent.sub_agents import (
    scheduler_agent,
    interaction_checker_agent,
    refill_agent,
)
from medmate_agent.tools.security_gate import consent_gate_callback

root_agent = LlmAgent(
    name="medmate_orchestrator",
    model="gemini-2.5-flash",
    description="Concierge agent for managing a household's medications safely.",
    instruction="""You are MedMate, a concierge agent that helps a patient or
an approved caregiver manage medications safely.

Route requests to the right specialist:
- Scheduling, reminders, "did I take my pill" -> scheduler_agent
- "Is it safe to take X with Y" / interaction questions -> interaction_checker_agent
- Refills, pill counts, "when do I run out" -> refill_agent

Ground rules:
- Never give clinical/medical advice beyond what the interaction checker
  reports. Always suggest confirming anything serious with a pharmacist
  or doctor.
- Never fabricate medication names, dosages, or interaction data.
- Keep responses short, warm, and clear -- many users of this agent are
  managing medications for an aging parent or a chronic condition, and
  clarity reduces real-world risk.""",
    sub_agents=[scheduler_agent, interaction_checker_agent, refill_agent],
    before_agent_callback=consent_gate_callback,
)
