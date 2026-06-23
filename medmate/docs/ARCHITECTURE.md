# MedMate Architecture Notes

## Agent topology

`medmate_orchestrator` is an `LlmAgent` with three `sub_agents`. ADK adds
automatic transfer tooling when `sub_agents` is set, so the orchestrator's
model picks the right specialist per turn based on each sub-agent's
`description` field — no manual if/else routing logic was written.

## Why a separate MCP server instead of a FunctionTool for interactions

`check_drug_interactions` is deliberately implemented as an MCP server
rather than an in-process `FunctionTool`, for two reasons relevant to the
"meaningful use of MCP" judging criterion:

1. **Swappability.** The interaction data source is the part of this
   project most likely to change (illustrative local table today, a real
   drug database API tomorrow). Putting it behind an MCP server means
   that swap happens entirely inside `mcp_server/drug_interaction_server.py`
   with zero changes to the agent graph.
2. **Process isolation.** Interaction-checking logic runs in its own
   subprocess, so a bug or hang there can't take down the scheduler or
   refill sub-agents — `StdioConnectionParams(timeout=10.0)` bounds the
   blast radius.

## State management

This demo uses simple in-memory dicts (`_SCHEDULE_DB`, `_INVENTORY_DB`,
`AUDIT_LOG`) so the whole thing runs with zero external infrastructure.
Swapping these for `DatabaseSessionService` / Firestore is a drop-in
replacement at the tool-function level — the agent and tool signatures
don't change, only what's inside each function body.
