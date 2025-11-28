import os
import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:123@localhost/parkingAutomation")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def ensure_schema() -> None:
    """
    Ensure required tables/columns exist so the API can run even if Alembic migrations
    were not executed yet. This keeps backwards compatibility for existing databases.
    """
    try:
        # Create any missing tables (no-op if they already exist)
        Base.metadata.create_all(bind=engine)

        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("parking_records")}

        if "confidence" not in columns:
            logger.info("Adding missing confidence column to parking_records table")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE parking_records ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION"))
    except Exception as exc:
        logger.error("Failed to ensure database schema is up-to-date: %s", exc)
        raise
