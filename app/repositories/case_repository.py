from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import (
    Case,
    CaseNote,
    CasePriority,
    CaseStatus,
    CaseStatusHistory,
)


class CaseRepository:
    def get(self, db: Session, case_id: UUID, *, lock: bool = False) -> Case | None:
        statement = select(Case).where(Case.id == case_id)
        if lock:
            statement = statement.with_for_update()
        return db.scalar(statement)

    def list_for_client(self, db: Session, client_id: int) -> list[Case]:
        return list(
            db.scalars(
                select(Case)
                .where(Case.client_id == client_id)
                .order_by(Case.updated_at.desc(), Case.id)
            )
        )

    def list_for_lawyer(self, db: Session, lawyer_id: int) -> list[Case]:
        return list(
            db.scalars(
                select(Case)
                .where(Case.lawyer_id == lawyer_id)
                .order_by(Case.updated_at.desc(), Case.id)
            )
        )

    def list_all(
        self,
        db: Session,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Case]:
        return list(
            db.scalars(
                select(Case)
                .order_by(Case.updated_at.desc(), Case.id)
                .offset(offset)
                .limit(limit)
            )
        )

    def add(self, db: Session, case: Case) -> Case:
        db.add(case)
        db.flush()
        return case

    def add_note(self, db: Session, note: CaseNote) -> CaseNote:
        db.add(note)
        db.flush()
        return note

    def list_notes(self, db: Session, case_id: UUID) -> list[CaseNote]:
        return list(
            db.scalars(
                select(CaseNote)
                .where(CaseNote.case_id == case_id)
                .order_by(CaseNote.created_at, CaseNote.id)
            )
        )

    def add_status_history(
        self,
        db: Session,
        history: CaseStatusHistory,
    ) -> CaseStatusHistory:
        db.add(history)
        db.flush()
        return history

    def list_status_history(
        self,
        db: Session,
        case_id: UUID,
    ) -> list[CaseStatusHistory]:
        return list(
            db.scalars(
                select(CaseStatusHistory)
                .where(CaseStatusHistory.case_id == case_id)
                .order_by(CaseStatusHistory.created_at, CaseStatusHistory.id)
            )
        )
