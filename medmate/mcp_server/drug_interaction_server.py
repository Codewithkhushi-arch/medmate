"""
MedMate Drug Interaction MCP Server
====================================
A standalone MCP server exposing a single tool: check_drug_interactions.

For the hackathon demo this uses a small local interaction table so the
project runs with zero external API keys. Swap `_INTERACTION_TABLE` for a
real call to RxNav/OpenFDA's interaction endpoints for production use --
the tool interface below would not need to change.

Run directly for local testing:
    python -m mcp_server.drug_interaction_server

The medmate_agent connects to this process over stdio via ADK's McpToolset
(see medmate_agent/tools/interaction_mcp_client.py).
"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(name="medmate-drug-interactions")

# A tiny illustrative interaction table: (drug_a, drug_b) -> risk info.
# Keys are stored lowercase and order-independent.
_INTERACTION_TABLE = {
    frozenset({"warfarin", "aspirin"}): {
        "severity": "high",
        "summary": "Combined use significantly increases bleeding risk.",
    },
    frozenset({"metformin", "alcohol"}): {
        "severity": "moderate",
        "summary": "Increases risk of lactic acidosis; use caution.",
    },
    frozenset({"lisinopril", "ibuprofen"}): {
        "severity": "moderate",
        "summary": "NSAIDs can reduce the blood-pressure-lowering effect and stress kidneys.",
    },
    frozenset({"simvastatin", "clarithromycin"}): {
        "severity": "high",
        "summary": "Raises simvastatin levels and risk of muscle damage (rhabdomyolysis).",
    },
}


@mcp.tool()
def check_drug_interactions(medications: list[str]) -> dict:
    """Checks a list of medication names for known pairwise interactions.

    Args:
        medications: List of medication names currently being taken, e.g.
            ["warfarin", "aspirin", "metformin"].

    Returns:
        A dict with a list of any flagged interaction pairs and their severity.
    """
    normalized = [m.strip().lower() for m in medications]
    flagged = []
    for i in range(len(normalized)):
        for j in range(i + 1, len(normalized)):
            pair = frozenset({normalized[i], normalized[j]})
            info = _INTERACTION_TABLE.get(pair)
            if info:
                flagged.append(
                    {
                        "drug_a": normalized[i],
                        "drug_b": normalized[j],
                        "severity": info["severity"],
                        "summary": info["summary"],
                    }
                )
    return {
        "checked_medications": normalized,
        "interactions_found": len(flagged),
        "flagged_interactions": flagged,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
