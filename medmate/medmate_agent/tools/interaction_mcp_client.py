"""
Wires the interaction-checker sub-agent to the drug-interaction MCP server.

ADK's McpToolset launches the server as a subprocess over stdio and exposes
its tools to the agent automatically -- no manual schema duplication needed.
"""
# Design Choice Rationale: We wrap the drug interaction checking logic inside 
# a standalone MCP server rather than an in-process tool. This separates 
# concerns and allows the checker to run in its own subprocess. A failure/hang 
# there won't block the rest of the concierge, and the interaction database 
# can be upgraded or replaced with zero changes to the agent graph.
import sys
from google.adk.tools import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
    StdioServerParameters,
)

drug_interaction_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server.drug_interaction_server"],
        ),
        timeout=10.0,
    ),
)
