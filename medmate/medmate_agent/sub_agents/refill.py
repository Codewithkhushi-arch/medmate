"""Refill sub-agent: pill-count tracking, refill prediction, and drafting pharmacy messages."""
# Design Choice Rationale: Inventory tracking and refills are separated into 
# their own Refill specialist. This design encapsulates pill count math and 
# refill logic. Most importantly, it ensures that refill messaging remains 
# strictly draft-only, keeping a human in the loop for any external operations.
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from medmate_agent.tools.inventory_tools import (
    set_pill_count,
    predict_refill_date,
    draft_refill_message,
)

refill_agent = LlmAgent(
    name="refill_agent",
    model="gemini-2.5-flash",
    description="Tracks medication inventory and predicts/drafts refills.",
    instruction="""You are the Refill sub-agent for MedMate.
Track pill counts (set_pill_count), predict when supply will run out
(predict_refill_date), and draft -- never auto-send -- refill request
messages (draft_refill_message). Every drafted message must be presented to
the user as a draft requiring their explicit approval before it's sent
anywhere; you have no ability to send messages yourself.""",
    tools=[
        FunctionTool(set_pill_count),
        FunctionTool(predict_refill_date),
        FunctionTool(draft_refill_message),
    ],
)
