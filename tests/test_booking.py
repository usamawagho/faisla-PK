import unittest
from datetime import date, time, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.user import (
    AppointmentStatus,
    ConsultationType,
    LawyerProfile,
    Notification,
    User,
    UserRole,
    VerificationStatus,
)
from app.schemas.booking import AppointmentCreate, AvailabilityCreate, AvailabilityUpdate
from app.services.booking_service import (
    BookingConflictError,
    BookingPermissionError,
    BookingService,
    BookingValidationError,
)


class BookingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.service = BookingService(self.db)
        self.client = self.add_user(UserRole.CLIENT, "client")
        self.lawyer = self.add_user(UserRole.LAWYER, "lawyer")
        self.lawyer.lawyer_profile = LawyerProfile(
            full_name="Ayesha Khan",
            license_number="LIC-BOOK-1",
            bar_council="Sindh Bar Council",
            bar_council_number="BC-BOOK-1",
            cnic="4210112345671",
            city="Karachi",
            verification_status=VerificationStatus.APPROVED,
        )
        self.db.commit()

        self.appointment_date = self.next_weekday(2)
        self.service.create_availability(
            self.lawyer,
            {
                "day_of_week": self.appointment_date.weekday(),
                "start_time": time(9, 0),
                "end_time": time(17, 0),
                "is_active": True,
            },
        )

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def add_user(self, role: UserRole, label: str) -> User:
        user = User(
            email=f"{label}@example.com",
            hashed_password="not-used",
            role=role,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    @staticmethod
    def next_weekday(weekday: int) -> date:
        today = date.today()
        days_ahead = (weekday - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return today + timedelta(days=days_ahead)

    def create_booking(self, start: time = time(10, 0)):
        payload = AppointmentCreate(
            lawyer_id=self.lawyer.id,
            appointment_date=self.appointment_date,
            appointment_time=start,
            consultation_type=ConsultationType.ONLINE,
            notes="Initial consultation",
        )
        return self.service.create_appointment(self.client, payload.model_dump())

    def test_booking_with_approved_lawyer_and_availability(self) -> None:
        appointment = self.create_booking()
        self.assertEqual(appointment.status, AppointmentStatus.PENDING)
        self.assertEqual(appointment.client_id, self.client.id)
        self.assertEqual(appointment.lawyer_id, self.lawyer.id)
        notification = self.db.query(Notification).filter_by(
            user_id=self.lawyer.id
        ).one()
        self.assertEqual(notification.title, "Appointment requested")

    def test_rejects_double_booking_and_overlapping_client_booking(self) -> None:
        self.create_booking()
        with self.assertRaises(BookingConflictError):
            self.create_booking(time(10, 30))

        another_lawyer = self.add_user(UserRole.LAWYER, "lawyer2")
        another_lawyer.lawyer_profile = LawyerProfile(
            full_name="Bilal Ahmed",
            license_number="LIC-BOOK-2",
            bar_council="Sindh Bar Council",
            bar_council_number="BC-BOOK-2",
            cnic="4210112345672",
            city="Karachi",
            verification_status=VerificationStatus.APPROVED,
        )
        self.db.commit()
        self.service.create_availability(
            another_lawyer,
            {
                "day_of_week": self.appointment_date.weekday(),
                "start_time": time(9, 0),
                "end_time": time(17, 0),
                "is_active": True,
            },
        )
        with self.assertRaises(BookingConflictError):
            self.service.create_appointment(
                self.client,
                {
                    "lawyer_id": another_lawyer.id,
                    "appointment_date": self.appointment_date,
                    "appointment_time": time(10, 15),
                    "consultation_type": ConsultationType.ONLINE,
                    "notes": None,
                },
            )

    def test_requires_future_approved_lawyer_and_available_slot(self) -> None:
        with self.assertRaises(BookingValidationError):
            self.service.create_appointment(
                self.client,
                {
                    "lawyer_id": self.lawyer.id,
                    "appointment_date": date.today() - timedelta(days=1),
                    "appointment_time": time(10, 0),
                    "consultation_type": ConsultationType.ONLINE,
                    "notes": None,
                },
            )
        with self.assertRaises(BookingValidationError):
            self.create_booking(time(17, 0))

        self.lawyer.lawyer_profile.verification_status = VerificationStatus.PENDING
        self.db.commit()
        with self.assertRaises(BookingValidationError):
            self.create_booking()

    def test_availability_overlap_and_owner_checks(self) -> None:
        with self.assertRaises(BookingConflictError):
            self.service.create_availability(
                self.lawyer,
                {
                    "day_of_week": self.appointment_date.weekday(),
                    "start_time": time(16, 0),
                    "end_time": time(18, 0),
                    "is_active": True,
                },
            )

        availability = self.service.list_my_availability(self.lawyer.id)[0]
        with self.assertRaises(BookingPermissionError):
            self.service.update_availability(
                self.add_user(UserRole.LAWYER, "other"),
                availability.id,
                {"is_active": False},
            )
        with self.assertRaises(ValueError):
            AvailabilityUpdate()
        with self.assertRaises(ValueError):
            AvailabilityCreate(
                day_of_week=0,
                start_time=time(10, 0),
                end_time=time(9, 0),
            )

    def test_status_transitions_and_client_cancellation(self) -> None:
        appointment = self.create_booking()
        approved = self.service.transition(
            self.lawyer,
            appointment.id,
            AppointmentStatus.APPROVED,
        )
        self.assertEqual(approved.status, AppointmentStatus.APPROVED)
        approved_notification = self.db.query(Notification).filter_by(
            user_id=self.client.id
        ).one()
        self.assertEqual(approved_notification.title, "Appointment approved")

        with self.assertRaises(BookingValidationError):
            self.service.transition(
                self.lawyer,
                appointment.id,
                AppointmentStatus.APPROVED,
            )

        cancelled = self.service.transition(
            self.client,
            appointment.id,
            AppointmentStatus.CANCELLED,
        )
        self.assertEqual(cancelled.status, AppointmentStatus.CANCELLED)
        cancellation_notification = self.db.query(Notification).filter_by(
            user_id=self.lawyer.id
        ).order_by(Notification.created_at.desc()).first()
        self.assertEqual(cancellation_notification.title, "Appointment cancelled")
        replacement = self.create_booking()
        self.assertNotEqual(replacement.id, appointment.id)
        rejected = self.service.transition(
            self.lawyer,
            replacement.id,
            AppointmentStatus.REJECTED,
        )
        self.assertEqual(rejected.status, AppointmentStatus.REJECTED)
        rejection_notification = self.db.query(Notification).filter_by(
            user_id=self.client.id,
            title="Appointment rejected",
        ).one()
        self.assertEqual(rejection_notification.title, "Appointment rejected")
        with self.assertRaises(BookingValidationError):
            self.service.transition(
                self.lawyer,
                appointment.id,
                AppointmentStatus.COMPLETED,
            )

    def test_completion_only_after_appointment_end(self) -> None:
        appointment = self.create_booking()
        self.service.transition(
            self.lawyer,
            appointment.id,
            AppointmentStatus.APPROVED,
        )
        with self.assertRaises(BookingValidationError):
            self.service.transition(
                self.lawyer,
                appointment.id,
                AppointmentStatus.COMPLETED,
            )

        appointment.appointment_date = date.today() - timedelta(days=1)
        self.db.commit()
        completed = self.service.transition(
            self.lawyer,
            appointment.id,
            AppointmentStatus.COMPLETED,
        )
        self.assertEqual(completed.status, AppointmentStatus.COMPLETED)

    def test_non_owner_cannot_approve_booking(self) -> None:
        appointment = self.create_booking()
        other_lawyer = self.add_user(UserRole.LAWYER, "other-lawyer")
        with self.assertRaises(BookingPermissionError):
            self.service.transition(
                other_lawyer,
                appointment.id,
                AppointmentStatus.APPROVED,
            )


if __name__ == "__main__":
    unittest.main()
