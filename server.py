from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from db import get_connection, init_db

# Initialize DB
init_db()

mcp = FastMCP("Sales Demo Server")


# ----------------------------
# Utility Functions
# ----------------------------

def calculate_score(deal: dict[str, Any]) -> int:
    """
    Calculate close probability score for a deal.
    """
    risk: int = 0

    if deal["days_in_pipeline"] > 30:
        risk += 15

    if deal["last_contact_days"] > 7:
        risk += 20

    if deal["stage"] == "Negotiation":
        risk -= 10

    probability: int = max(5, 100 - risk)
    return probability


def fetch_deal_from_db(deal_id: str) -> dict[str, Any] | None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM deals WHERE deal_id = ?", (deal_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "deal_id": row[0],
        "company": row[1],
        "value": row[2],
        "stage": row[3],
        "days_in_pipeline": row[4],
        "last_contact_days": row[5],
    }


# ----------------------------
# MCP Tools
# ----------------------------

@mcp.tool()
def list_open_deals() -> list[dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT deal_id, company FROM deals")
    rows = cursor.fetchall()
    conn.close()

    return [{"deal_id": r[0], "company": r[1]} for r in rows]


@mcp.tool()
def get_deal(deal_id: str) -> dict[str, Any]:
    deal = fetch_deal_from_db(deal_id)

    if not deal:
        return {"error": "Deal not found"}

    return deal


@mcp.tool()
def create_deal(
    deal_id: str,
    company: str,
    value: int,
    stage: str
) -> dict[str, str]:

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO deals
        (deal_id, company, value, stage, days_in_pipeline, last_contact_days)
        VALUES (?, ?, ?, ?, 0, 0)
        """,
        (deal_id, company, value, stage),
    )

    conn.commit()
    conn.close()

    return {"status": "Deal created", "deal_id": deal_id}


@mcp.tool()
def update_deal(
    deal_id: str,
    company: str,
    value: int,
    stage: str
) -> dict[str, str]:

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE deals
        SET company = ?, value = ?, stage = ?
        WHERE deal_id = ?
        """,
        (company, value, stage, deal_id),
    )

    conn.commit()
    conn.close()

    return {"status": "Deal updated", "deal_id": deal_id}


@mcp.tool()
def suggest_next_action(deal_id: str) -> dict[str, Any]:

    deal = fetch_deal_from_db(deal_id)
    if not deal:
        return {"error": "Deal not found"}

    actions: list[str] = []

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

    if deal["value"] > 75000:
        priority: str = "High"
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
        "recommended_actions": actions,
    }


@mcp.tool()
def prioritize_deals() -> list[dict[str, Any]]:

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT deal_id, company, value, stage, days_in_pipeline, last_contact_days
        FROM deals
        """
    )

    rows = cursor.fetchall()
    conn.close()

    results: list[dict[str, Any]] = []

    for row in rows:
        deal = {
            "value": row[2],
            "stage": row[3],
            "days_in_pipeline": row[4],
            "last_contact_days": row[5],
        }

        probability = calculate_score(deal)

        results.append(
            {
                "deal_id": row[0],
                "company": row[1],
                "value": row[2],
                "close_probability": probability,
            }
        )

    return sorted(results, key=lambda x: x["close_probability"], reverse=True)


@mcp.tool()
def summarize_pipeline() -> dict[str, Any]:

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT deal_id, value, stage, days_in_pipeline, last_contact_days
        FROM deals
        """
    )

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {"message": "No deals in pipeline."}

    total_value: int = 0
    probabilities: list[int] = []
    high_risk_count: int = 0
    high_value_count: int = 0
    attention_needed: int = 0

    for row in rows:
        deal = {
            "value": row[1],
            "stage": row[2],
            "days_in_pipeline": row[3],
            "last_contact_days": row[4],
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

    avg_probability: float = sum(probabilities) / len(probabilities)

    return {
        "total_deals": len(rows),
        "total_pipeline_value": total_value,
        "average_close_probability": round(avg_probability, 2),
        "high_risk_deals": high_risk_count,
        "high_value_deals": high_value_count,
        "deals_needing_attention": attention_needed,
    }


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
