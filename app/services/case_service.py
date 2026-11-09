from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import (
    Case,
    CaseNote,
    CasePriority,
    CaseStatus,
    CaseStatusHistory,
    User,
    UserRole,
)
from app.repositories.case_repository import CaseRepository
from app.services.notification_service import NotificationService


class CaseError(Exception):
    pass


class CaseNotFoundError(CaseError):
    pass


class CasePermissionError(CaseError):
    pass


class CaseValidationError(CaseError):
    pass


class CaseService:
    _status_transitions = {
        CaseStatus.OPEN: {
            CaseStatus.IN_PROGRESS,
            CaseStatus.WAITING_CLIENT,
            CaseStatus.ON_HOLD,
            CaseStatus.CLOSED,
        },
        CaseStatus.IN_PROGRESS: {
            CaseStatus.WAITING_CLIENT,
            CaseStatus.ON_HOLD,
            CaseStatus.CLOSED,
        },
        CaseStatus.WAITING_CLIENT: {
            CaseStatus.IN_PROGRESS,
            CaseStatus.ON_HOLD,
            CaseStatus.CLOSED,
        },
        CaseStatus.ON_HOLD: {
            CaseStatus.IN_PROGRESS,
            CaseStatus.WAITING_CLIENT,
            CaseStatus.CLOSED,
        },
        CaseStatus.CLOSED: set(),
    }

    def __init__(
        self,
        db: Session,
        repository: CaseRepository | None = None,
    ) -> None:
        self.db = db
        self.repository = repository or CaseRepository()
        self.notifications = NotificationService(db)

    def create(self, lawyer: User, values: dict[str, Any]) -> Case:
        if lawyer.role != UserRole.LAWYER:
            raise CasePermissionError("Only lawyers can create cases")
        client = self.db.get(User, values["client_id"])
        if client is None or client.role != UserRole.CLIENT or not client.is_active:
            raise CaseValidationError("Case client must be an active client account")

        case = Case(
            lawyer_id=lawyer.id,
            client_id=client.id,
            title=values["title"],
            description=values["description"],
            case_type=values["case_type"],
            priority=values.get("priority", CasePriority.MEDIUM),
            status=CaseStatus.OPEN,
        )
        try:
            self.repository.add(self.db, case)
            self.repository.add_status_history(
                self.db,
                CaseStatusHistory(
                    case=case,
                    changed_by_id=lawyer.id,
                    previous_status=None,
                    new_status=CaseStatus.OPEN,
                ),
            )
            self.notifications.create(
                client.id,
                "Case created",
                f"A case was created for you: {case.title}.",
            )
            self.db.commit()
            self.db.refresh(case)
        except IntegrityError as exc:
            self.db.rollback()
            raise CaseValidationError("Case could not be created") from exc
        return case

    def get(self, case_id: UUID, actor: User) -> Case:
        case = self.repository.get(self.db, case_id)
        if case is None:
            raise CaseNotFoundError("Case not found")
        self._ensure_can_view(case, actor)
        return case

    @staticmethod
    def _ensure_can_view(case: Case, actor: User) -> None:
        if actor.role == UserRole.ADMIN:
            return
        if actor.role == UserRole.CLIENT and actor.id == case.client_id:
            return
        if actor.role == UserRole.LAWYER and actor.id == case.lawyer_id:
            return
        raise CasePermissionError("You cannot access this case")

    def list_for_user(self, actor: User) -> list[Case]:
        if actor.role == UserRole.CLIENT:
            return self.repository.list_for_client(self.db, actor.id)
        if actor.role == UserRole.LAWYER:
            return self.repository.list_for_lawyer(self.db, actor.id)
        raise CasePermissionError("Use the admin case listing endpoint")

    def list_all(self, actor: User, offset: int = 0, limit: int = 100) -> list[Case]:
        if actor.role != UserRole.ADMIN:
            raise CasePermissionError("Admin role required")
        return self.repository.list_all(self.db, offset=offset, limit=limit)

    def update(self, case_id: UUID, lawyer: User, values: dict[str, Any]) -> Case:
        if lawyer.role != UserRole.LAWYER:
            raise CasePermissionError("Only lawyers can update cases")
        case = self.repository.get(self.db, case_id, lock=True)
        if case is None:
            raise CaseNotFoundError("Case not found")
        if case.lawyer_id != lawyer.id:
            raise CasePermissionError("Only the assigned lawyer can update this case")
        for field in ("title", "description", "case_type", "priority"):
            if field in values:
                setattr(case, field, values[field])
        try:
            self.notifications.create(
                case.client_id,
                "Case updated",
                f"Your case details were updated: {case.title}.",
            )
            self.db.commit()
            self.db.refresh(case)
        except IntegrityError as exc:
            self.db.rollback()
            raise CaseValidationError("Case update could not be saved") from exc
        return case

    def change_status(
        self,
        case_id: UUID,
        lawyer: User,
        new_status: CaseStatus,
    ) -> Case:
        if lawyer.role != UserRole.LAWYER:
            raise CasePermissionError("Only lawyers can change case status")
        case = self.repository.get(self.db, case_id, lock=True)
        if case is None:
            raise CaseNotFoundError("Case not found")
        if case.lawyer_id != lawyer.id:
            raise CasePermissionError("Only the assigned lawyer can change this case")
        if new_status not in self._status_transitions[case.status]:
            raise CaseValidationError(
                f"Invalid case status transition: {case.status.value} to {new_status.value}"
            )

        previous_status = case.status
        case.status = new_status
        self.repository.add_status_history(
            self.db,
            CaseStatusHistory(
                case=case,
                changed_by_id=lawyer.id,
                previous_status=previous_status,
                new_status=new_status,
            ),
        )
        try:
            self.notifications.create(
                case.client_id,
                "Case status changed",
                f"Your case status is now {new_status.value}.",
            )
            self.db.commit()
            self.db.refresh(case)
        except IntegrityError as exc:
            self.db.rollback()
            raise CaseValidationError("Case status could not be changed") from exc
        return case

    def add_note(self, case_id: UUID, lawyer: User, note_text: str) -> CaseNote:
        if lawyer.role != UserRole.LAWYER:
            raise CasePermissionError("Only lawyers can add case notes")
        case = self.repository.get(self.db, case_id, lock=True)
        if case is None:
            raise CaseNotFoundError("Case not found")
        if case.lawyer_id != lawyer.id:
            raise CasePermissionError("Only the assigned lawyer can add notes")
        note_text = note_text.strip()
        if not note_text:
            raise CaseValidationError("Note must not be blank")

        note = CaseNote(case_id=case.id, author_id=lawyer.id, note=note_text)
        try:
            self.repository.add_note(self.db, note)
            self.db.commit()
            self.db.refresh(note)
        except IntegrityError as exc:
            self.db.rollback()
            raise CaseValidationError("Case note could not be saved") from exc
        return note

    def list_notes(self, case_id: UUID, actor: User) -> list[CaseNote]:
        case = self.get(case_id, actor)
        return self.repository.list_notes(self.db, case.id)

    def list_status_history(
        self,
        case_id: UUID,
        actor: User,
    ) -> list[CaseStatusHistory]:
        case = self.get(case_id, actor)
        return self.repository.list_status_history(self.db, case.id)
