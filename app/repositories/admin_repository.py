from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import (
    Appointment,
    AppointmentStatus,
    Case,
    LawyerProfile,
    User,
    UserRole,
    VerificationStatus,
)


class AdminRepository:
    def list_users(
        self,
        db: Session,
        *,
        role: UserRole | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[User]:
        statement = select(User)
        if role is not None:
            statement = statement.where(User.role == role)
        if is_active is not None:
            statement = statement.where(User.is_active.is_(is_active))
        if search:
            statement = statement.where(User.email.ilike(f"%{search}%"))
        return list(
            db.scalars(
                statement.order_by(User.id).offset(offset).limit(limit)
            )
        )

    def get_user(
        self,
        db: Session,
        user_id: int,
        *,
        lock: bool = False,
    ) -> User | None:
        statement = select(User).where(User.id == user_id)
        if lock:
            statement = statement.with_for_update()
        return db.scalar(statement)

    def lock_admins(self, db: Session) -> list[User]:
        return list(
            db.scalars(
                select(User)
                .where(User.role == UserRole.ADMIN)
                .order_by(User.id)
                .with_for_update()
            )
        )

    def get_lawyer_profile(
        self,
        db: Session,
        user_id: int,
        *,
        lock: bool = False,
    ) -> LawyerProfile | None:
        statement = (
            select(LawyerProfile)
            .join(User, User.id == LawyerProfile.user_id)
            .where(
                LawyerProfile.user_id == user_id,
                User.role == UserRole.LAWYER,
            )
        )
        if lock:
            statement = statement.with_for_update()
        return db.scalar(statement)

    def list_pending_lawyer_profiles(
        self,
        db: Session,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[LawyerProfile]:
        return list(
            db.scalars(
                select(LawyerProfile)
                .join(User, User.id == LawyerProfile.user_id)
                .where(
                    User.role == UserRole.LAWYER,
                    LawyerProfile.verification_status == VerificationStatus.PENDING,
                )
                .order_by(LawyerProfile.id)
                .offset(offset)
                .limit(limit)
            )
        )

    def count_users(self, db: Session, role: UserRole | None = None) -> int:
        statement = select(func.count(User.id))
        if role is not None:
            statement = statement.where(User.role == role)
        return db.scalar(statement) or 0

    def count_cases(self, db: Session) -> int:
        return db.scalar(select(func.count(Case.id))) or 0

    def count_pending_appointments(self, db: Session) -> int:
        return (
            db.scalar(
                select(func.count(Appointment.id)).where(
                    Appointment.status == AppointmentStatus.PENDING
                )
            )
            or 0
        )

    def count_approved_lawyers(self, db: Session) -> int:
        return (
            db.scalar(
                select(func.count(LawyerProfile.id))
                .join(User, User.id == LawyerProfile.user_id)
                .where(
                    User.role == UserRole.LAWYER,
                    LawyerProfile.verification_status == VerificationStatus.APPROVED,
                )
            )
            or 0
        )
