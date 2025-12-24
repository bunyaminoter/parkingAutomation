import os
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:123@localhost/parkingAutomation")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


@contextmanager
def session_scope() -> Session:
    """
    Uygulama genelinde kullanılabilecek tek bir wrapped session.
    Commit / rollback ve close yönetimini merkezi hale getirir.
    """
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def ensure_schema() -> None:
    """
    Ensure required tables/columns exist so the API can run even if Alembic migrations
    were not executed yet. This keeps backwards compatibility for existing databases.
    """
    try:
        # Create any missing tables (no-op if they already exist)
        Base.metadata.create_all(bind=engine)

        inspector = inspect(engine)

        # parking_records.confidence sütunu
        pr_columns = {col["name"] for col in inspector.get_columns("parking_records")}
        if "confidence" not in pr_columns:
            logger.info("Adding missing confidence column to parking_records table")
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE parking_records "
                        "ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION"
                    )
                )

        # users tablosu kontrolleri
        if "users" in inspector.get_table_names():
            user_columns = {col["name"] for col in inspector.get_columns("users")}
            
            # is_super_admin sütunu
            if "is_super_admin" not in user_columns:
                logger.info("Adding is_super_admin column to users table")
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            "ALTER TABLE users "
                            "ADD COLUMN IF NOT EXISTS is_super_admin INTEGER NOT NULL DEFAULT 0"
                        )
                    )
            
            # username'den email'e geçiş
            if "username" in user_columns and "email" not in user_columns:
                logger.info("Migrating username column to email in users table")
                with engine.begin() as conn:
                    # Mevcut username değerlerini email formatına çevir
                    conn.execute(
                        text("""
                            UPDATE users 
                            SET username = CASE 
                                WHEN username LIKE '%@%' THEN username 
                                ELSE username || '@gmail.com' 
                            END
                        """)
                    )
                    # Index'i kaldır
                    try:
                        conn.execute(text("DROP INDEX IF EXISTS ix_users_username"))
                    except:
                        pass
                    # Sütunu yeniden adlandır
                    conn.execute(text("ALTER TABLE users RENAME COLUMN username TO email"))
                    # Yeni index oluştur
                    conn.execute(
                        text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users(email)")
                    )
            elif "username" in user_columns and "email" in user_columns:
                # Her iki sütun da varsa, username'deki değerleri email'e kopyala ve username'i sil
                logger.info("Migrating username values to email and removing username column")
                with engine.begin() as conn:
                    conn.execute(
                        text("""
                            UPDATE users 
                            SET email = CASE 
                                WHEN username LIKE '%@%' THEN username 
                                ELSE username || '@gmail.com' 
                            END
                            WHERE email IS NULL OR email = ''
                        """)
                    )
                    try:
                        conn.execute(text("DROP INDEX IF EXISTS ix_users_username"))
                    except:
                        pass
                    conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS username"))
    except Exception as exc:
        logger.error("Failed to ensure database schema is up-to-date: %s", exc)
        raise
