import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.user import (
    Case,
    CasePriority,
    CaseStatus,
    Notification,
    User,
    UserRole,
)
from app.schemas.case_management import CaseCreate, CaseNoteCreate, CaseUpdate
from app.services.case_service import (
    CaseNotFoundError,
    CasePermissionError,
    CaseService,
    CaseValidationError,
)


class CaseManagementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.service = CaseService(self.db)
        self.client = self.add_user(UserRole.CLIENT, "client")
        self.lawyer = self.add_user(UserRole.LAWYER, "lawyer")
        self.other_client = self.add_user(UserRole.CLIENT, "other-client")
        self.other_lawyer = self.add_user(UserRole.LAWYER, "other-lawyer")
        self.admin = self.add_user(UserRole.ADMIN, "admin")

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def add_user(self, role: UserRole, label: str) -> User:
        user = User(
            email=f"{label}@case-test.example",
            hashed_password="not-used",
            role=role,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_case(self) -> Case:
        payload = CaseCreate(
            client_id=self.client.id,
            title="Property dispute",
            description="Dispute regarding property ownership.",
            case_type="Property",
            priority=CasePriority.HIGH,
        )
        return self.service.create(self.lawyer, payload.model_dump())

    def test_create_case_records_initial_status_and_lists_for_participants(self) -> None:
        case = self.create_case()
        self.assertEqual(case.status, CaseStatus.OPEN)
        self.assertEqual(
            self.db.query(Notification).filter_by(user_id=self.client.id).one().title,
            "Case created",
        )
        self.assertEqual(self.service.list_for_user(self.client), [case])
        self.assertEqual(self.service.list_for_user(self.lawyer), [case])
        history = self.service.list_status_history(case.id, self.admin)
        self.assertEqual(len(history), 1)
        self.assertIsNone(history[0].previous_status)
        self.assertEqual(history[0].new_status, CaseStatus.OPEN)

    def test_only_assigned_lawyer_can_update_status_and_add_notes(self) -> None:
        case = self.create_case()
        with self.assertRaises(CasePermissionError):
            self.service.update(case.id, self.other_lawyer, {"title": "Changed"})
        with self.assertRaises(CasePermissionError):
            self.service.change_status(
                case.id,
                self.other_lawyer,
                CaseStatus.IN_PROGRESS,
            )
        with self.assertRaises(CasePermissionError):
            self.service.add_note(case.id, self.other_lawyer, "Private update")

        updated = self.service.update(case.id, self.lawyer, {"title": "Updated title"})
        self.assertEqual(updated.title, "Updated title")
        update_notification = self.db.query(Notification).filter_by(
            user_id=self.client.id,
            title="Case updated",
        ).one()
        self.assertIn("Updated title", update_notification.message)

    def test_notes_are_readable_by_participants_but_not_others(self) -> None:
        case = self.create_case()
        note_input = CaseNoteCreate(note="  Court hearing scheduled.  ")
        note = self.service.add_note(case.id, self.lawyer, note_input.note)
        self.assertEqual(note.note, "Court hearing scheduled.")
        self.assertEqual(self.service.list_notes(case.id, self.client), [note])
        self.assertEqual(self.service.list_notes(case.id, self.lawyer), [note])
        self.assertEqual(self.service.list_notes(case.id, self.admin), [note])
        with self.assertRaises(CasePermissionError):
            self.service.list_notes(case.id, self.other_client)
        with self.assertRaises(ValueError):
            CaseNoteCreate(note="  ")

    def test_case_visibility_and_admin_listing(self) -> None:
        case = self.create_case()
        self.assertEqual(self.service.get(case.id, self.client).id, case.id)
        self.assertEqual(self.service.get(case.id, self.lawyer).id, case.id)
        self.assertEqual(self.service.get(case.id, self.admin).id, case.id)
        with self.assertRaises(CasePermissionError):
            self.service.get(case.id, self.other_client)
        self.assertEqual(self.service.list_all(self.admin), [case])
        with self.assertRaises(CasePermissionError):
            self.service.list_all(self.lawyer)
        with self.assertRaises(CasePermissionError):
            self.service.list_for_user(self.admin)

    def test_status_transitions_are_logged_and_closed_is_terminal(self) -> None:
        case = self.create_case()
        for status in (
            CaseStatus.IN_PROGRESS,
            CaseStatus.WAITING_CLIENT,
            CaseStatus.ON_HOLD,
            CaseStatus.IN_PROGRESS,
            CaseStatus.CLOSED,
        ):
            case = self.service.change_status(case.id, self.lawyer, status)
        history = self.service.list_status_history(case.id, self.client)
        self.assertEqual(
            self.db.query(Notification).filter_by(user_id=self.client.id).count(),
            6,
        )
        self.assertEqual(len(history), 6)
        self.assertEqual(history[-1].new_status, CaseStatus.CLOSED)
        self.assertEqual(history[-1].previous_status, CaseStatus.IN_PROGRESS)
        with self.assertRaises(CaseValidationError):
            self.service.change_status(case.id, self.lawyer, CaseStatus.OPEN)

    def test_creation_requires_an_active_client_and_lawyer_role(self) -> None:
        values = {
            "client_id": self.client.id,
            "title": "Test",
            "description": "Description",
            "case_type": "Civil",
        }
        with self.assertRaises(CasePermissionError):
            self.service.create(self.client, values)

        invalid_client_values = {**values, "client_id": self.other_lawyer.id}
        with self.assertRaises(CaseValidationError):
            self.service.create(self.lawyer, invalid_client_values)

    def test_not_found_case_is_explicit(self) -> None:
        from uuid import uuid4

        with self.assertRaises(CaseNotFoundError):
            self.service.get(uuid4(), self.client)

    def test_update_schema_requires_non_empty_patch(self) -> None:
        with self.assertRaises(ValueError):
            CaseUpdate()
        with self.assertRaises(ValueError):
            CaseUpdate(title=" ")


if __name__ == "__main__":
    unittest.main()
