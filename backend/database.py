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
    
    Also removes any tenant-related columns and tables from the database if they exist.
    """
    try:
        # Create any missing tables (no-op if they already exist)
        Base.metadata.create_all(bind=engine)

        inspector = inspect(engine)
        
        # Remove tenant-related columns and tables (if they exist)
        # This ensures backward compatibility after removing multi-tenant architecture
        
        # Remove parking_records.tenant_id column
        if "parking_records" in inspector.get_table_names():
            pr_columns = {col["name"] for col in inspector.get_columns("parking_records")}
            if "tenant_id" in pr_columns:
                logger.info("Removing tenant_id column from parking_records table")
                with engine.begin() as conn:
                    # Foreign key constraint'i kaldır
                    try:
                        conn.execute(text("ALTER TABLE parking_records DROP CONSTRAINT IF EXISTS fk_parking_records_tenant_id"))
                    except:
                        pass
                    try:
                        conn.execute(text("DROP INDEX IF EXISTS ix_parking_records_tenant_id"))
                    except:
                        pass
                    # Sütunu kaldır
                    conn.execute(text("ALTER TABLE parking_records DROP COLUMN IF EXISTS tenant_id"))
        
        # Remove payments.tenant_id column
        if "payments" in inspector.get_table_names():
            payment_columns = {col["name"] for col in inspector.get_columns("payments")}
            if "tenant_id" in payment_columns:
                logger.info("Removing tenant_id column from payments table")
                with engine.begin() as conn:
                    # Foreign key constraint'i kaldır
                    try:
                        conn.execute(text("ALTER TABLE payments DROP CONSTRAINT IF EXISTS fk_payments_tenant_id"))
                    except:
                        pass
                    try:
                        conn.execute(text("DROP INDEX IF EXISTS ix_payments_tenant_id"))
                    except:
                        pass
                    # Sütunu kaldır
                    conn.execute(text("ALTER TABLE payments DROP COLUMN IF EXISTS tenant_id"))
        
        # Remove users.tenant_id and role columns
        if "users" in inspector.get_table_names():
            user_columns = {col["name"] for col in inspector.get_columns("users")}
            
            if "tenant_id" in user_columns:
                logger.info("Removing tenant_id column from users table")
                with engine.begin() as conn:
                    # Foreign key constraint'i kaldır
                    try:
                        conn.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS fk_users_tenant_id"))
                    except:
                        pass
                    try:
                        conn.execute(text("DROP INDEX IF EXISTS ix_users_tenant_id"))
                    except:
                        pass
                    # Sütunu kaldır
                    conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS tenant_id"))
            
            if "role" in user_columns:
                logger.info("Removing role column from users table")
                with engine.begin() as conn:
                    try:
                        conn.execute(text("DROP INDEX IF EXISTS ix_users_role"))
                    except:
                        pass
                    # Sütunu kaldır
                    conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS role"))
        
        # Remove vehicles.tenant_id column
        if "vehicles" in inspector.get_table_names():
            vehicle_columns = {col["name"] for col in inspector.get_columns("vehicles")}
            if "tenant_id" in vehicle_columns:
                logger.info("Removing tenant_id column from vehicles table")
                with engine.begin() as conn:
                    # Foreign key constraint'i kaldır
                    try:
                        conn.execute(text("ALTER TABLE vehicles DROP CONSTRAINT IF EXISTS fk_vehicles_tenant_id"))
                    except:
                        pass
                    try:
                        conn.execute(text("DROP INDEX IF EXISTS ix_vehicles_tenant_id"))
                    except:
                        pass
                    try:
                        conn.execute(text("DROP INDEX IF EXISTS ix_vehicles_plate_tenant"))
                    except:
                        pass
                    # Sütunu kaldır
                    conn.execute(text("ALTER TABLE vehicles DROP COLUMN IF EXISTS tenant_id"))
                    # plate_number'ı unique yap (tenant_id olmadan)
                    try:
                        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_vehicles_plate_number ON vehicles(plate_number)"))
                    except:
                        pass
        
        # Remove tenants table
        if "tenants" in inspector.get_table_names():
            logger.info("Removing tenants table")
            with engine.begin() as conn:
                # Önce foreign key constraint'leri kaldır (yukarıda yapıldı)
                # Sonra tabloyu kaldır
                conn.execute(text("DROP TABLE IF EXISTS tenants CASCADE"))
        
        # Remove userrole enum (if it exists)
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    DO $$ 
                    BEGIN
                        DROP TYPE IF EXISTS userrole;
                    EXCEPTION
                        WHEN OTHERS THEN null;
                    END $$;
                """))
        except:
            pass

        # parking_records.confidence sütunu
        if "parking_records" in inspector.get_table_names():
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
        
        # parking_records.payment_id sütunu
        if "parking_records" in inspector.get_table_names():
            pr_columns = {col["name"] for col in inspector.get_columns("parking_records")}
            if "payment_id" not in pr_columns:
                logger.info("Adding payment_id column to parking_records table")
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            "ALTER TABLE parking_records "
                            "ADD COLUMN IF NOT EXISTS payment_id INTEGER"
                        )
                    )
                    conn.execute(
                        text(
                            "CREATE INDEX IF NOT EXISTS ix_parking_records_payment_id "
                            "ON parking_records(payment_id)"
                        )
                    )
            
            # Create vehicles table
            if "vehicles" not in inspector.get_table_names():
                logger.info("Creating vehicles table")
                with engine.begin() as conn:
                    # Create vehicles table
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS vehicles (
                            id SERIAL PRIMARY KEY,
                            plate_number VARCHAR(32) NOT NULL UNIQUE,
                            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_vehicles_plate_number ON vehicles(plate_number)"))
            
            # parking_records.vehicle_id sütunu
            if "vehicle_id" not in pr_columns:
                logger.info("Adding vehicle_id column to parking_records table")
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            "ALTER TABLE parking_records "
                            "ADD COLUMN IF NOT EXISTS vehicle_id INTEGER REFERENCES vehicles(id) ON DELETE SET NULL"
                        )
                    )
                    conn.execute(
                        text(
                            "CREATE INDEX IF NOT EXISTS ix_parking_records_vehicle_id "
                            "ON parking_records(vehicle_id)"
                        )
                    )
        
        # Create payments table
        if "payments" not in inspector.get_table_names():
            logger.info("Creating payments table")
            with engine.begin() as conn:
                # PaymentStatus enum'u oluştur
                conn.execute(text("""
                    DO $$ BEGIN
                        CREATE TYPE paymentstatus AS ENUM ('PENDING', 'PAID', 'CANCELLED');
                    EXCEPTION
                        WHEN duplicate_object THEN null;
                    END $$;
                """))
                
                # Payments tablosunu oluştur
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS payments (
                        id SERIAL PRIMARY KEY,
                        reference VARCHAR(64) NOT NULL UNIQUE,
                        amount DOUBLE PRECISION NOT NULL,
                        currency VARCHAR(3) NOT NULL DEFAULT 'TRY',
                        status paymentstatus NOT NULL DEFAULT 'PENDING',
                        parking_record_id INTEGER,
                        receiver_name VARCHAR(255) NOT NULL DEFAULT 'La Parque A.Ş.',
                        iban VARCHAR(34) NOT NULL,
                        merchant_code VARCHAR(64) NOT NULL,
                        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        paid_at TIMESTAMP WITHOUT TIME ZONE
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_payments_id ON payments(id)"))
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_payments_reference ON payments(reference)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_payments_status ON payments(status)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_payments_parking_record_id ON payments(parking_record_id)"))
    except Exception as exc:
        logger.error("Failed to ensure database schema is up-to-date: %s", exc)
        raise
