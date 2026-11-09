from datetime import date, time
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.user import (
    Appointment,
    AppointmentStatus,
    LawyerAvailability,
    LawyerProfile,
    User,
    UserRole,
    VerificationStatus,
)


BLOCKING_APPOINTMENT_STATUSES = (
    AppointmentStatus.PENDING,
    AppointmentStatus.APPROVED,
)


class BookingRepository:
    def lock_users(self, db: Session, user_ids: set[int]) -> None:
        db.scalars(
            select(User)
            .where(User.id.in_(user_ids))
            .order_by(User.id)
            .with_for_update()
        ).all()

    def get_approved_active_lawyer(self, db: Session, lawyer_id: int) -> User | None:
        return db.scalar(
            select(User)
            .join(LawyerProfile, LawyerProfile.user_id == User.id)
            .where(
                User.id == lawyer_id,
                User.role == UserRole.LAWYER,
                User.is_active.is_(True),
                LawyerProfile.verification_status == VerificationStatus.APPROVED,
            )
        )

    def get_availability(
        self,
        db: Session,
        availability_id: UUID,
    ) -> LawyerAvailability | None:
        return db.get(LawyerAvailability, availability_id)

    def get_availabilities_for_lawyer(
        self,
        db: Session,
        lawyer_id: int,
        day_of_week: int | None = None,
    ) -> list[LawyerAvailability]:
        statement = select(LawyerAvailability).where(
            LawyerAvailability.lawyer_id == lawyer_id
        )
        if day_of_week is not None:
            statement = statement.where(
                LawyerAvailability.day_of_week == day_of_week
            )
        return list(
            db.scalars(
                statement.order_by(
                    LawyerAvailability.day_of_week,
                    LawyerAvailability.start_time,
                )
            )
        )

    def find_active_availability(
        self,
        db: Session,
        lawyer_id: int,
        day_of_week: int,
        start_time: time,
        end_time: time,
    ) -> LawyerAvailability | None:
        return db.scalar(
            select(LawyerAvailability)
            .where(
                LawyerAvailability.lawyer_id == lawyer_id,
                LawyerAvailability.day_of_week == day_of_week,
                LawyerAvailability.is_active.is_(True),
                LawyerAvailability.start_time <= start_time,
                LawyerAvailability.end_time >= end_time,
            )
            .limit(1)
        )

    def get_active_availability_for_day(
        self,
        db: Session,
        lawyer_id: int,
        day_of_week: int,
        excluding_id: UUID | None = None,
    ) -> list[LawyerAvailability]:
        statement = select(LawyerAvailability).where(
            LawyerAvailability.lawyer_id == lawyer_id,
            LawyerAvailability.day_of_week == day_of_week,
            LawyerAvailability.is_active.is_(True),
        )
        if excluding_id is not None:
            statement = statement.where(LawyerAvailability.id != excluding_id)
        return list(db.scalars(statement))

    def add_availability(
        self,
        db: Session,
        availability: LawyerAvailability,
    ) -> LawyerAvailability:
        db.add(availability)
        db.flush()
        return availability

    def delete_availability(self, db: Session, availability: LawyerAvailability) -> None:
        db.delete(availability)

    def get_appointment(
        self,
        db: Session,
        appointment_id: UUID,
        *,
        lock: bool = False,
    ) -> Appointment | None:
        statement = select(Appointment).where(Appointment.id == appointment_id)
        if lock:
            statement = statement.with_for_update()
        return db.scalar(statement)

    def get_active_appointments_for_date(
        self,
        db: Session,
        appointment_date: date,
        client_id: int,
        lawyer_id: int,
    ) -> list[Appointment]:
        return list(
            db.scalars(
                select(Appointment).where(
                    Appointment.appointment_date == appointment_date,
                    Appointment.status.in_(BLOCKING_APPOINTMENT_STATUSES),
                    or_(
                        Appointment.client_id == client_id,
                        Appointment.lawyer_id == lawyer_id,
                    ),
                )
            )
        )

    def add_appointment(self, db: Session, appointment: Appointment) -> Appointment:
        db.add(appointment)
        db.flush()
        return appointment

    def list_for_client(self, db: Session, client_id: int) -> list[Appointment]:
        return list(
            db.scalars(
                select(Appointment)
                .where(Appointment.client_id == client_id)
                .order_by(Appointment.appointment_date, Appointment.appointment_time)
            )
        )

    def list_for_lawyer(self, db: Session, lawyer_id: int) -> list[Appointment]:
        return list(
            db.scalars(
                select(Appointment)
                .where(Appointment.lawyer_id == lawyer_id)
                .order_by(Appointment.appointment_date, Appointment.appointment_time)
            )
        )
