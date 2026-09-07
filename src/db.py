"""
src/db.py
---------
Database connection and session management for Neon Postgres.
Supports automatic dialect normalization (postgres:// -> postgresql://)
and safe graceful degradation when DATABASE_URL is not configured.
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger("kaushalsetu.db")

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# Normalize legacy postgres:// to postgresql:// (required by SQLAlchemy 1.4+)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

Base = declarative_base()

engine = None
SessionLocal = None

def get_engine():
    global engine, SessionLocal
    if engine is not None:
        return engine

    if not DATABASE_URL:
        logger.info("[DB] DATABASE_URL is not set. Operating in local CSV-first mode.")
        return None

    try:
        connect_args = {}
        # Ensure SSL for remote postgres (e.g. Neon)
        if "postgresql" in DATABASE_URL and "sslmode" not in DATABASE_URL and "localhost" not in DATABASE_URL:
            connect_args["sslmode"] = "require"

        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args=connect_args,
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("[DB] Connected engine initialized successfully.")
        return engine
    except Exception as e:
        logger.warning(f"[DB] Could not initialize database engine: {e}")
        return None

def get_db():
    """Dependency for FastAPI endpoints or helper contexts."""
    eng = get_engine()
    if eng is None or SessionLocal is None:
        yield None
        return

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def is_db_available() -> bool:
    """Checks if database is configured and reachable."""
    eng = get_engine()
    if eng is None:
        return False
    try:
        with eng.connect() as conn:
            conn.execute(Base.metadata.tables.get("dummy", None) or "SELECT 1")
        return True
    except Exception:
        return False
