import sqlite3
from pathlib import Path
from typing import Optional
from app.core.config import get_settings


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Creates a thread-safe connection to the SQLite database."""
    target_path = db_path or get_settings().DATABASE_PATH
    conn = sqlite3.connect(target_path, timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initializes minimal webhook event storage schema."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS webhook_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    payment_id TEXT,
                    payment_link_id TEXT,
                    order_id TEXT,
                    amount INTEGER,
                    currency TEXT,
                    status TEXT,
                    error_code TEXT,
                    error_description TEXT,
                    payload_json TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    processing_status TEXT NOT NULL
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_webhook_payment_id 
                ON webhook_events(payment_id);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_webhook_payment_link_id 
                ON webhook_events(payment_link_id);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_webhook_order_id 
                ON webhook_events(order_id);
            """)
    finally:
        conn.close()
