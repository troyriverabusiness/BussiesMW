from sqlalchemy import select
from sqlalchemy.orm import Session

from models.legal_case import LegalCase


class LegalCaseRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[LegalCase]:
        statement = select(LegalCase).order_by(LegalCase.last_updated.desc())
        return list(self._db.scalars(statement).all())
