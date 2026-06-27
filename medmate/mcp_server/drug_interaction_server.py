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
import urllib.request
import urllib.parse
import json
import logging

mcp = FastMCP(name="medmate-drug-interactions")
logger = logging.getLogger("mcp_server")

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


def _get_rxcui(name: str) -> str | None:
    """Helper to look up a drug's RxNorm Concept Unique Identifier (RxCUI)."""
    try:
        url = f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={urllib.parse.quote(name)}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=2.0) as response:
            data = json.loads(response.read().decode())
            rxnorm_id = data.get("idGroup", {}).get("rxnormId")
            if rxnorm_id:
                return rxnorm_id[0]
    except Exception as e:
        logger.warning(f"Error fetching Rxcui for {name}: {e}")
    return None


def _fetch_api_interactions(rxcuis: list[str], drug_mapping: dict[str, str]) -> list[dict]:
    """Helper to query the NIH RxNav interaction API using RxCUIs."""
    if len(rxcuis) < 2:
        return []
    try:
        rxcuis_str = "+".join(rxcuis)
        url = f"https://rxnav.nlm.nih.gov/REST/interaction/list.json?rxcuis={rxcuis_str}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as response:
            data = json.loads(response.read().decode())
            flagged = []
            
            groups = data.get("fullInteractionTypeGroup", [])
            for group in groups:
                for interaction_type in group.get("fullInteractionType", []):
                    for pair in interaction_type.get("interactionPair", []):
                        severity = pair.get("severity", "N/A").lower()
                        if "high" in severity or "severe" in severity:
                            sev = "high"
                        elif "moderate" in severity:
                            sev = "moderate"
                        else:
                            sev = "low"
                            
                        description = pair.get("description", "Interaction reported.")
                        
                        concepts = pair.get("interactionConcept", [])
                        matching_drugs = []
                        for c in concepts:
                            cui = c.get("minConceptItem", {}).get("rxcui")
                            if cui in drug_mapping:
                                matching_drugs.append(drug_mapping[cui])
                        
                        if len(matching_drugs) >= 2:
                            flagged.append({
                                "drug_a": matching_drugs[0],
                                "drug_b": matching_drugs[1],
                                "severity": sev,
                                "summary": description
                            })
            return flagged
    except Exception as e:
        logger.warning(f"Error fetching RxNav interactions: {e}")
    return []


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
    
    # 1. Try RxNav API
    rxcuis = []
    drug_mapping = {}
    for name in normalized:
        cui = _get_rxcui(name)
        if cui:
            rxcuis.append(cui)
            drug_mapping[cui] = name
            
    if len(rxcuis) >= 2:
        api_results = _fetch_api_interactions(rxcuis, drug_mapping)
        flagged.extend(api_results)
        
    # 2. Local fallback if API failed or returned no interactions, to prevent false negatives
    if not flagged:
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
                    
    # Remove duplicate drug pairs from flagged list to avoid duplicate listings
    unique_flagged = []
    seen_pairs = set()
    for item in flagged:
        pair_key = frozenset({item["drug_a"], item["drug_b"]})
        if pair_key not in seen_pairs:
            seen_pairs.add(pair_key)
            unique_flagged.append(item)
            
    return {
        "checked_medications": normalized,
        "interactions_found": len(unique_flagged),
        "flagged_interactions": unique_flagged,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
