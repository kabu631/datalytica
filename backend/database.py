"""
database.py — SQLite connection + SQLAlchemy setup.
Database is stored at ~/.datalytica/datalytica.db.
The directory is created automatically if it does not exist.
"""
import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

# ── Resolve DB path ───────────────────────────────────────────────────────────
DB_DIR  = Path.home() / ".datalytica"
DB_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DB_DIR / "datalytica.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # required for SQLite + FastAPI
    echo=False,                                  # set True to log SQL statements
)

# Enable WAL mode for better concurrent read performance
@event.listens_for(engine, "connect")
def set_wal_mode(dbapi_conn, _):
    dbapi_conn.execute("PRAGMA journal_mode=WAL;")
    dbapi_conn.execute("PRAGMA foreign_keys=ON;")

# ── Session factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ── Declarative base ──────────────────────────────────────────────────────────
Base = declarative_base()


def get_db():
    """
    FastAPI dependency — yields a DB session and ensures it is closed
    after the request completes (even on error).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
