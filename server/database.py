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
