import json
from pathlib import Path
from fastmcp import FastMCP
from db import get_connection, init_db

init_db()

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
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT deal_id, company FROM deals")
    rows = cursor.fetchall()

    conn.close()

    return [{"deal_id": r[0], "company": r[1]} for r in rows]


@mcp.tool()
def get_deal(deal_id: str):
    """Get details of a specific deal."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM deals WHERE deal_id = ?", (deal_id,))
    row = cursor.fetchone()

    conn.close()

    if not row:
        return {"error": "Deal not found"}
    return {
        "deal_id": row[0],
        "company": row[1],
        "value": row[2],
        "stage": row[3],
        "days_in_pipeline": row[4],
        "last_contact_days": row[5]
    }


def calculate_score(deal):
    risk = 0

    if deal["days_in_pipeline"] > 30:
        risk += 15

    if deal["last_contact_days"] > 7:
        risk += 20

    if deal["stage"] == "Negotiation":
        risk -= 10

    probability = max(5, 100 - risk)
    return probability


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


@mcp.tool()
def create_deal(deal_id: str, company: str, value: int, stage: str):
    """Create a new sales deal."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO deals (deal_id, company, value, stage, days_in_pipeline, last_contact_days)
        VALUES (?, ?, ?, ?, 0, 0)
    """, (deal_id, company, value, stage))

    conn.commit()
    conn.close()

    return {"status": "Deal created", "deal_id": deal_id}


@mcp.tool()
def update_deal(deal_id: str, company: str, value: int, stage: str):
    """Update an existing sales deal."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE deals
        SET company = ?, value = ?, stage = ?
        WHERE deal_id = ?
    """, (company, value, stage, deal_id))

    conn.commit()
    conn.close()

    return {"status": "Deal updated", "deal_id": deal_id}


@mcp.tool()
def prioritize_deals():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT deal_id, company, value, stage, days_in_pipeline, last_contact_days
        FROM deals
    """)

    rows = cursor.fetchall()
    conn.close()

    results = []

    for row in rows:
        deal = {
            "company": row[1],
            "value": row[2],
            "stage": row[3],
            "days_in_pipeline": row[4],
            "last_contact_days": row[5]
        }

        probability = calculate_score(deal)

        results.append({
            "deal_id": row[0],
            "company": row[1],
            "value": row[2],
            "close_probability": probability
        })

    return sorted(results, key=lambda x: x["close_probability"], reverse=True)


@mcp.tool()
def summarize_pipeline():
    """
    Provide executive-level summary of the sales pipeline.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT deal_id, value, stage, days_in_pipeline, last_contact_days
        FROM deals
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {"message": "No deals in pipeline."}

    total_value = 0
    probabilities = []
    high_risk_count = 0
    high_value_count = 0
    attention_needed = 0

    for row in rows:
        deal = {
            "value": row[1],
            "stage": row[2],
            "days_in_pipeline": row[3],
            "last_contact_days": row[4]
        }

        total_value += deal["value"]

        probability = calculate_score(deal)
        probabilities.append(probability)

        if probability < 50:
            high_risk_count += 1

        if deal["value"] > 75000:
            high_value_count += 1

        if deal["last_contact_days"] > 7:
            attention_needed += 1

    avg_probability = sum(probabilities) / len(probabilities)

    return {
        "total_deals": len(rows),
        "total_pipeline_value": total_value,
        "average_close_probability": round(avg_probability, 2),
        "high_risk_deals": high_risk_count,
        "high_value_deals": high_value_count,
        "deals_needing_attention": attention_needed
    }


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
    
