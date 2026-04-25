import os
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://bussiesmw:bussiesmw@localhost:5432/bussiesmw",
)


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_database_schema() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE legal_cases "
                "ADD COLUMN IF NOT EXISTS type VARCHAR(120) NOT NULL DEFAULT 'General Matter'"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE legal_cases "
                "ADD COLUMN IF NOT EXISTS last_updated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE legal_cases "
                "ADD COLUMN IF NOT EXISTS recent BOOLEAN NOT NULL DEFAULT FALSE"
            )
        )
        connection.execute(text("ALTER TABLE legal_cases ADD COLUMN IF NOT EXISTS case_number VARCHAR(40)"))
        connection.execute(
            text("ALTER TABLE legal_cases ADD COLUMN IF NOT EXISTS assigned_attorney VARCHAR(120)")
        )
        connection.execute(
            text(
                "ALTER TABLE legal_cases "
                "ADD COLUMN IF NOT EXISTS created_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE legal_cases "
                "ADD COLUMN IF NOT EXISTS last_updated_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()"
            )
        )
        connection.execute(
            text("ALTER TABLE legal_cases ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'::jsonb")
        )
        connection.execute(text("ALTER TABLE legal_cases ADD COLUMN IF NOT EXISTS short_summary TEXT"))
        connection.execute(text("ALTER TABLE legal_cases ADD COLUMN IF NOT EXISTS plaintiff_name VARCHAR(160)"))
        connection.execute(
            text(
                "ALTER TABLE legal_cases "
                "ADD COLUMN IF NOT EXISTS compensation_amount NUMERIC(12, 2) DEFAULT 0"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE legal_cases "
                "ADD COLUMN IF NOT EXISTS next_due_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE legal_cases "
                "ADD COLUMN IF NOT EXISTS external_law_firm_involved VARCHAR(160)"
            )
        )
        connection.execute(text("ALTER TABLE legal_cases ADD COLUMN IF NOT EXISTS court_involved VARCHAR(160)"))
        connection.execute(text("ALTER TABLE legal_cases ADD COLUMN IF NOT EXISTS jurisdiction VARCHAR(120)"))
        connection.execute(
            text("ALTER TABLE legal_cases ADD COLUMN IF NOT EXISTS priority_risk_level VARCHAR(20)")
        )
        connection.execute(text("ALTER TABLE legal_cases ADD COLUMN IF NOT EXISTS last_correspondence TEXT"))
        connection.execute(text("ALTER TABLE legal_cases ADD COLUMN IF NOT EXISTS waiting_for TEXT"))
