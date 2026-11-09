from datetime import date, datetime, time, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import (
    Appointment,
    AppointmentStatus,
    LawyerAvailability,
    User,
    UserRole,
)
from app.repositories.booking_repository import BookingRepository
from app.services.notification_service import NotificationService

PAKISTAN_TIMEZONE = ZoneInfo("Asia/Karachi")
APPOINTMENT_DURATION = timedelta(minutes=60)


class BookingError(Exception):
    pass


class BookingNotFoundError(BookingError):
    pass


class BookingPermissionError(BookingError):
    pass


class BookingConflictError(BookingError):
    pass


class BookingValidationError(BookingError):
    pass


class BookingService:
    def __init__(
        self,
        db: Session,
        repository: BookingRepository | None = None,
    ) -> None:
        self.db = db
        self.repository = repository or BookingRepository()
        self.notifications = NotificationService(db)

    @staticmethod
    def _ensure_availability_range(start_time: time, end_time: time) -> None:
        if start_time >= end_time:
            raise BookingValidationError("Availability end_time must be after start_time")

    @staticmethod
    def _ensure_no_overlap(
        start_time: time,
        end_time: time,
        existing: list[LawyerAvailability],
    ) -> None:
        for item in existing:
            if start_time < item.end_time and end_time > item.start_time:
                raise BookingConflictError("Availability overlaps an active schedule")

    def create_availability(self, lawyer: User, values: dict[str, Any]) -> LawyerAvailability:
        if lawyer.role != UserRole.LAWYER:
            raise BookingPermissionError("Only lawyers can manage availability")
        day = values["day_of_week"]
        start_time = values["start_time"]
        end_time = values["end_time"]
        self._ensure_availability_range(start_time, end_time)
        self.repository.lock_users(self.db, {lawyer.id})
        if values.get("is_active", True):
            existing = self.repository.get_active_availability_for_day(
                self.db, lawyer.id, day
            )
            self._ensure_no_overlap(start_time, end_time, existing)

        availability = LawyerAvailability(lawyer_id=lawyer.id, **values)
        try:
            self.repository.add_availability(self.db, availability)
            self.db.commit()
            self.db.refresh(availability)
        except IntegrityError as exc:
            self.db.rollback()
            raise BookingConflictError("Availability conflicts with existing data") from exc
        return availability

    def list_my_availability(self, lawyer_id: int) -> list[LawyerAvailability]:
        return self.repository.get_availabilities_for_lawyer(self.db, lawyer_id)

    def update_availability(
        self,
        lawyer: User,
        availability_id: UUID,
        values: dict[str, Any],
    ) -> LawyerAvailability:
        if lawyer.role != UserRole.LAWYER:
            raise BookingPermissionError("Only lawyers can manage availability")
        self.repository.lock_users(self.db, {lawyer.id})
        availability = self.repository.get_availability(self.db, availability_id)
        if availability is None:
            raise BookingNotFoundError("Availability not found")
        if availability.lawyer_id != lawyer.id:
            raise BookingPermissionError("You cannot modify another lawyer's availability")

        proposed = {
            "day_of_week": values.get("day_of_week", availability.day_of_week),
            "start_time": values.get("start_time", availability.start_time),
            "end_time": values.get("end_time", availability.end_time),
            "is_active": values.get("is_active", availability.is_active),
        }
        self._ensure_availability_range(proposed["start_time"], proposed["end_time"])
        if proposed["is_active"]:
            existing = self.repository.get_active_availability_for_day(
                self.db,
                lawyer.id,
                proposed["day_of_week"],
                excluding_id=availability.id,
            )
            self._ensure_no_overlap(
                proposed["start_time"],
                proposed["end_time"],
                existing,
            )
        for field, value in proposed.items():
            setattr(availability, field, value)
        try:
            self.db.commit()
            self.db.refresh(availability)
        except IntegrityError as exc:
            self.db.rollback()
            raise BookingConflictError("Availability conflicts with existing data") from exc
        return availability

    def delete_availability(self, lawyer: User, availability_id: UUID) -> None:
        if lawyer.role != UserRole.LAWYER:
            raise BookingPermissionError("Only lawyers can manage availability")
        self.repository.lock_users(self.db, {lawyer.id})
        availability = self.repository.get_availability(self.db, availability_id)
        if availability is None:
            raise BookingNotFoundError("Availability not found")
        if availability.lawyer_id != lawyer.id:
            raise BookingPermissionError("You cannot delete another lawyer's availability")
        self.repository.delete_availability(self.db, availability)
        self.db.commit()

    def create_appointment(self, client: User, values: dict[str, Any]) -> Appointment:
        if client.role != UserRole.CLIENT:
            raise BookingPermissionError("Only clients can book appointments")
        lawyer_id = values["lawyer_id"]
        if client.id == lawyer_id:
            raise BookingValidationError("A lawyer cannot book an appointment with themselves")

        self.repository.lock_users(self.db, {client.id, lawyer_id})
        lawyer = self.repository.get_approved_active_lawyer(self.db, lawyer_id)
        if lawyer is None:
            raise BookingValidationError("Lawyer must have an active, approved profile")

        appointment_date: date = values["appointment_date"]
        appointment_time: time = values["appointment_time"]
        start = datetime.combine(appointment_date, appointment_time, PAKISTAN_TIMEZONE)
        end = start + APPOINTMENT_DURATION
        if start <= datetime.now(PAKISTAN_TIMEZONE):
            raise BookingValidationError("Appointment must be in the future")
        if end.date() != appointment_date:
            raise BookingValidationError("Appointment must finish before midnight")

        availability = self.repository.find_active_availability(
            self.db,
            lawyer_id,
            appointment_date.weekday(),
            appointment_time,
            end.time().replace(tzinfo=None),
        )
        if availability is None:
            raise BookingValidationError("Requested time is outside lawyer availability")

        conflicts = self.repository.get_active_appointments_for_date(
            self.db,
            appointment_date,
            client.id,
            lawyer_id,
        )
        for existing in conflicts:
            existing_start = datetime.combine(
                existing.appointment_date,
                existing.appointment_time,
            )
            existing_end = existing_start + APPOINTMENT_DURATION
            candidate_start = datetime.combine(appointment_date, appointment_time)
            candidate_end = candidate_start + APPOINTMENT_DURATION
            if candidate_start < existing_end and candidate_end > existing_start:
                raise BookingConflictError(
                    "The client or lawyer already has a booking during that time"
                )

        appointment = Appointment(
            client_id=client.id,
            lawyer_id=lawyer_id,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            consultation_type=values["consultation_type"],
            notes=values.get("notes"),
            status=AppointmentStatus.PENDING,
        )
        try:
            self.repository.add_appointment(self.db, appointment)
            self.notifications.create(
                lawyer_id,
                "Appointment requested",
                "A client requested an appointment. Review it in your appointments.",
            )
            self.db.commit()
            self.db.refresh(appointment)
        except IntegrityError as exc:
            self.db.rollback()
            raise BookingConflictError("Appointment conflicts with existing data") from exc
        return appointment

    def list_for_client(self, client_id: int) -> list[Appointment]:
        return self.repository.list_for_client(self.db, client_id)

    def list_for_lawyer(self, lawyer_id: int) -> list[Appointment]:
        return self.repository.list_for_lawyer(self.db, lawyer_id)

    def transition(
        self,
        actor: User,
        appointment_id: UUID,
        target: AppointmentStatus,
    ) -> Appointment:
        appointment = self.repository.get_appointment(
            self.db,
            appointment_id,
            lock=True,
        )
        if appointment is None:
            raise BookingNotFoundError("Appointment not found")

        allowed = {
            AppointmentStatus.APPROVED: (
                UserRole.LAWYER,
                appointment.lawyer_id,
                {AppointmentStatus.PENDING},
            ),
            AppointmentStatus.REJECTED: (
                UserRole.LAWYER,
                appointment.lawyer_id,
                {AppointmentStatus.PENDING},
            ),
            AppointmentStatus.COMPLETED: (
                UserRole.LAWYER,
                appointment.lawyer_id,
                {AppointmentStatus.APPROVED},
            ),
            AppointmentStatus.CANCELLED: (
                UserRole.CLIENT,
                appointment.client_id,
                {AppointmentStatus.PENDING, AppointmentStatus.APPROVED},
            ),
        }
        expected_role, expected_user_id, previous_states = allowed[target]
        if actor.role != expected_role or actor.id != expected_user_id:
            raise BookingPermissionError("You cannot change this appointment")
        if appointment.status not in previous_states:
            raise BookingValidationError(
                f"Cannot transition appointment from {appointment.status.value} "
                f"to {target.value}"
            )

        if target == AppointmentStatus.COMPLETED:
            end = datetime.combine(
                appointment.appointment_date,
                appointment.appointment_time,
                PAKISTAN_TIMEZONE,
            ) + APPOINTMENT_DURATION
            if datetime.now(PAKISTAN_TIMEZONE) < end:
                raise BookingValidationError("Appointment cannot be completed before it ends")

        appointment.status = target
        notification_targets = {
            AppointmentStatus.APPROVED: appointment.client_id,
            AppointmentStatus.REJECTED: appointment.client_id,
            AppointmentStatus.CANCELLED: appointment.lawyer_id,
        }
        recipient_id = notification_targets.get(target)
        if recipient_id is not None:
            self.notifications.create(
                recipient_id,
                f"Appointment {target.value}",
                f"Your appointment request is now {target.value}.",
            )
        self.db.commit()
        self.db.refresh(appointment)
        return appointment
