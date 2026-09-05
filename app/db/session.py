"""
Database session management.

Two separate layers:
1. Raw sqlite3 (Phase 0) — used exclusively by webhook_events via WebhookEventRepository.
   Preserved as-is for full backward compatibility with the working webhook receiver.

2. SQLAlchemy (Phase 1+) — used for all new domain tables (merchants, customers, orders,
   payments, recovery_opportunities, agent_decisions, recovery_actions, recovery_outcomes,
   audit_events). Supports both SQLite (local dev) and PostgreSQL (production).
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine

from app.core.config import get_settings


# ---------------------------------------------------------------------------
# Phase 0 — Raw sqlite3 (webhook_events only; do not modify)
# ---------------------------------------------------------------------------

def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Creates a thread-safe connection to the SQLite database."""
    target_path = db_path or get_settings().DATABASE_PATH
    conn = sqlite3.connect(target_path, timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initializes minimal webhook event storage schema (Phase 0)."""
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


# ---------------------------------------------------------------------------
# Phase 1+ — SQLAlchemy engine + session
# ---------------------------------------------------------------------------

def _make_engine() -> Engine:
    """Creates the SQLAlchemy engine from settings.DATABASE_URL."""
    settings = get_settings()
    url = settings.DATABASE_URL

    if url.startswith("sqlite"):
        # SQLite — enable WAL + foreign keys per connection
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            echo=settings.DEBUG,
        )

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_conn, _):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    else:
        # PostgreSQL (or other)
        engine = create_engine(url, echo=settings.DEBUG, pool_pre_ping=True)

    return engine


# Lazily created engine + session factory (avoids import-time side effects)
_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = _make_engine()
    return _engine


def get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
    return _SessionLocal


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager yielding a SQLAlchemy session with auto-commit/rollback."""
    factory = get_session_factory()
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_domain_db() -> None:
    """Creates all domain tables (Phase 1+) from SQLAlchemy metadata.

    Safe to call on every startup — uses CREATE IF NOT EXISTS semantics.
    Does NOT touch webhook_events (managed by init_db() above).
    """
    from app.db.models import Base  # local import avoids circular deps at module level
    Base.metadata.create_all(bind=get_engine())
