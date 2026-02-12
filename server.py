import json
from pathlib import Path
from fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("Sales Demo Server")

# Load data at startup
DATA_PATH = Path(__file__).parent / "data" / "deals.json"

with open(DATA_PATH, "r") as f:
    DEALS = json.load(f)


def calculate_score(deal):
    risk = 0

    if deal["days_in_pipeline"] > 30:
        risk += 15

    if deal["last_contact_days"] > 7:
        risk += 20

    if deal["stage"] == "Negotiation":
        risk -= 10

    probability = max(5, 100 - risk)

    if probability > 75:
        level = "Low"
    elif probability > 50:
        level = "Medium"
    else:
        level = "High"

    return {
        "close_probability": probability,
        "risk_level": level
    }


@mcp.tool()
def list_open_deals():
    """List all open deal IDs with company names."""
    return [
        {"deal_id": deal_id, "company": deal["company"]}
        for deal_id, deal in DEALS.items()
    ]


@mcp.tool()
def get_deal(deal_id: str):
    """Get details of a specific deal."""
    deal = DEALS.get(deal_id)
    if not deal:
        return {"error": "Deal not found"}
    return deal


@mcp.tool()
def score_deal(deal_id: str):
    """Analyze deal risk and return close probability."""
    deal = DEALS.get(deal_id)
    if not deal:
        return {"error": "Deal not found"}

    score = calculate_score(deal)

    return {
        "deal_id": deal_id,
        "company": deal["company"],
        "analysis": score
    }


@mcp.tool()
def suggest_next_action(deal_id: str):
    """
    Suggest the next best action for a deal based on risk factors
    and pipeline characteristics.
    """
    deal = DEALS.get(deal_id)
    if not deal:
        return {"error": "Deal not found"}

    actions = []

    # Risk-based triggers
    if deal["last_contact_days"] > 7:
        actions.append("Re-engage client with follow-up call or email")

    if deal["days_in_pipeline"] > 30:
        actions.append("Schedule decision-maker meeting to accelerate closure")

    if deal["stage"] == "Discovery":
        actions.append("Clarify business requirements and confirm budget")

    if deal["stage"] == "Proposal":
        actions.append("Follow up on proposal feedback and objections")

    if deal["stage"] == "Negotiation":
        actions.append("Offer incentive or revised pricing to close deal")

    # Priority classification
    if deal["value"] > 75000:
        priority = "High"
    elif deal["value"] > 30000:
        priority = "Medium"
    else:
        priority = "Low"

    if not actions:
        actions.append("Maintain regular communication cadence")

    return {
        "deal_id": deal_id,
        "company": deal["company"],
        "priority": priority,
        "recommended_actions": actions
    }



if __name__ == "__main__":
    mcp.run()
