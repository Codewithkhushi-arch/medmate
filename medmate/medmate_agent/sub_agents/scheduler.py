"""Scheduler sub-agent: owns medication timing, reminders, and dose logging."""
# Design Choice Rationale: We split medication scheduling, reminders, and dose 
# logging into a dedicated Scheduler sub-agent. This ensures the scheduling
# domain stays isolated with clean, scoped tools, minimizing context window
# overhead and preventing other agents (like Refill or Interaction) from
# inadvertently altering user schedules.
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from medmate_agent.tools.schedule_tools import (
    add_medication_schedule,
    get_today_schedule,
    mark_dose_taken,
    check_missed_doses,
)

scheduler_agent = LlmAgent(
    name="scheduler_agent",
    model="gemini-2.5-flash",
    description="Manages when medications should be taken and logs doses.",
    instruction="""You are the Scheduler sub-agent for MedMate.
Your job is strictly limited to:
1. Adding medications to a user's daily schedule (add_medication_schedule).
2. Reporting what's scheduled for today (get_today_schedule).
3. Logging when a dose was actually taken (mark_dose_taken).
4. Checking for scheduled doses that have not been logged yet today (check_missed_doses).
Always confirm back to the user in plain language what you scheduled, logged, or found.
Never give medical advice about whether a medication is appropriate -- that is
out of scope. If asked about interactions, tell the user the interaction
checker will handle that.""",
    tools=[
        FunctionTool(add_medication_schedule),
        FunctionTool(get_today_schedule),
        FunctionTool(mark_dose_taken),
        FunctionTool(check_missed_doses),
    ],
)

