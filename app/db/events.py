import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.db.session import get_db_connection


class WebhookEventRepository:
    """Repository managing webhook event persistence and race-safe idempotency."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def record_event(
        self,
        event_id: str,
        event_type: str,
        payload: Dict[str, Any],
        payment_id: Optional[str] = None,
        payment_link_id: Optional[str] = None,
        order_id: Optional[str] = None,
        amount: Optional[int] = None,
        currency: Optional[str] = None,
        status: Optional[str] = None,
        error_code: Optional[str] = None,
        error_description: Optional[str] = None,
        processing_status: str = "received"
    ) -> bool:
        """
        Persists a webhook event.
        
        Enforces race-safe idempotency using PRIMARY KEY constraint on event_id.
        Returns True if inserted successfully, False if duplicate.
        """
        received_at = datetime.now(timezone.utc).isoformat()
        payload_json = json.dumps(payload)

        conn = get_db_connection(self.db_path)
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO webhook_events (
                        event_id, event_type, payment_id, payment_link_id, order_id,
                        amount, currency, status, error_code, error_description,
                        payload_json, received_at, processing_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        event_type,
                        payment_id,
                        payment_link_id,
                        order_id,
                        amount,
                        currency,
                        status,
                        error_code,
                        error_description,
                        payload_json,
                        received_at,
                        processing_status
                    )
                )
            return True
        except sqlite3.IntegrityError:
            # Race condition safe: duplicate event_id caught by primary key constraint
            return False
        finally:
            conn.close()

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a stored webhook event by ID."""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM webhook_events WHERE event_id = ?",
                (event_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            data = dict(row)
            data["payload"] = json.loads(data["payload_json"])
            return data
        finally:
            conn.close()

    def is_duplicate(self, event_id: str) -> bool:
        """Checks if an event_id is already recorded."""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM webhook_events WHERE event_id = ?",
                (event_id,)
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()
