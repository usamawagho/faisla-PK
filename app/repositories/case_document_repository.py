from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import Case, CaseDocument


class CaseDocumentRepository:
    def get_case(self, db: Session, case_id: UUID) -> Case | None:
        return db.get(Case, case_id)

    def get(self, db: Session, document_id: UUID) -> CaseDocument | None:
        return db.get(CaseDocument, document_id)

    def list_for_case(self, db: Session, case_id: UUID) -> list[CaseDocument]:
        return list(
            db.scalars(
                select(CaseDocument)
                .where(CaseDocument.case_id == case_id)
                .order_by(CaseDocument.uploaded_at, CaseDocument.id)
            )
        )

    def add(self, db: Session, document: CaseDocument) -> CaseDocument:
        db.add(document)
        db.flush()
        return document

    def delete(self, db: Session, document: CaseDocument) -> None:
        db.delete(document)
