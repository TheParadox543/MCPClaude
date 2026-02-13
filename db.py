import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "sales.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deals (
            deal_id TEXT PRIMARY KEY,
            company TEXT,
            value INTEGER,
            stage TEXT,
            days_in_pipeline INTEGER,
            last_contact_days INTEGER
        )
    """)

    conn.commit()
    conn.close()
