import unittest
from datetime import date, time

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.user import (
    Appointment,
    AppointmentStatus,
    Case,
    CasePriority,
    CaseStatus,
    ConsultationType,
    LawyerProfile,
    User,
    UserRole,
    VerificationStatus,
)
from app.services.admin_service import (
    AdminNotFoundError,
    AdminPermissionError,
    AdminService,
    AdminValidationError,
)
from app.services.notification_service import (
    NotificationNotFoundError,
    NotificationService,
)


class AdminAndNotificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.admin_service = AdminService(self.db)
        self.notification_service = NotificationService(self.db)
        self.admin = self.add_user(UserRole.ADMIN, "admin")
        self.client = self.add_user(UserRole.CLIENT, "client")
        self.lawyer = self.add_user(UserRole.LAWYER, "lawyer")
        self.other_admin = self.add_user(UserRole.ADMIN, "other-admin")
        self.lawyer.lawyer_profile = LawyerProfile(
            full_name="Ayesha Khan",
            license_number="LIC-ADMIN-1",
            bar_council="Sindh Bar Council",
            bar_council_number="BC-ADMIN-1",
            cnic="4210112345671",
            verification_status=VerificationStatus.PENDING,
        )
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def add_user(self, role: UserRole, label: str) -> User:
        user = User(
            email=f"{label}@admin-test.example",
            hashed_password="not-used",
            role=role,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def test_admin_lists_users_and_changes_account_state(self) -> None:
        users = self.admin_service.list_users(
            role=UserRole.CLIENT,
            is_active=True,
        )
        self.assertEqual(users, [self.client])
        with self.assertRaises(AdminNotFoundError):
            self.admin_service.get_user(999999)
        deactivated = self.admin_service.set_user_active(
            self.admin,
            self.client.id,
            is_active=False,
        )
        self.assertFalse(deactivated.is_active)
        activated = self.admin_service.set_user_active(
            self.admin,
            self.client.id,
            is_active=True,
        )
        self.assertTrue(activated.is_active)

    def test_admin_cannot_deactivate_self_or_last_active_admin(self) -> None:
        with self.assertRaises(AdminValidationError):
            self.admin_service.set_user_active(
                self.admin,
                self.admin.id,
                is_active=False,
            )
        self.admin_service.set_user_active(
            self.admin,
            self.other_admin.id,
            is_active=False,
        )
        with self.assertRaises(AdminPermissionError):
            self.admin_service.set_user_active(
                self.other_admin,
                self.admin.id,
                is_active=False,
            )

    def test_lawyer_verification_and_dashboard_counts(self) -> None:
        pending = self.admin_service.list_pending_lawyers()
        self.assertEqual([profile.user_id for profile in pending], [self.lawyer.id])
        profile = self.admin_service.set_lawyer_verification(
            self.lawyer.id,
            VerificationStatus.APPROVED,
        )
        self.assertEqual(profile.verification_status, VerificationStatus.APPROVED)

        case = Case(
            client_id=self.client.id,
            lawyer_id=self.lawyer.id,
            title="Matter",
            description="Description",
            case_type="Civil",
            status=CaseStatus.OPEN,
            priority=CasePriority.MEDIUM,
        )
        self.db.add(case)
        self.db.add(
            Appointment(
                client_id=self.client.id,
                lawyer_id=self.lawyer.id,
                appointment_date=date(2030, 1, 1),
                appointment_time=time(10, 0),
                consultation_type=ConsultationType.ONLINE,
                status=AppointmentStatus.PENDING,
            )
        )
        self.db.commit()

        dashboard = self.admin_service.dashboard()
        self.assertEqual(dashboard.total_users, 4)
        self.assertEqual(dashboard.total_lawyers, 1)
        self.assertEqual(dashboard.total_clients, 1)
        self.assertEqual(dashboard.total_cases, 1)
        self.assertEqual(dashboard.pending_appointments, 1)
        self.assertEqual(dashboard.approved_lawyers, 1)

    def test_notifications_are_private_and_can_be_marked_read(self) -> None:
        notification = self.notification_service.create(
            self.client.id,
            "Appointment requested",
            "A new appointment is awaiting your review.",
        )
        self.db.commit()
        self.assertEqual(
            self.notification_service.list_for_user(self.client.id),
            [notification],
        )
        with self.assertRaises(NotificationNotFoundError):
            self.notification_service.mark_read(notification.id, self.lawyer.id)

        read_notification = self.notification_service.mark_read(
            notification.id,
            self.client.id,
        )
        self.assertTrue(read_notification.is_read)


if __name__ == "__main__":
    unittest.main()
