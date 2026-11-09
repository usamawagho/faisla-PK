from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.user import (
    LawyerProfile,
    User,
    UserRole,
    VerificationStatus,
)


class LawyerProfileRepository:
    def get_by_id(self, db: Session, profile_id: int) -> LawyerProfile | None:
        return db.get(LawyerProfile, profile_id)

    def get_by_user_id(self, db: Session, user_id: int) -> LawyerProfile | None:
        return db.scalar(
            select(LawyerProfile).where(LawyerProfile.user_id == user_id)
        )

    def list(
        self,
        db: Session,
        offset: int = 0,
        limit: int = 100,
    ) -> list[LawyerProfile]:
        return list(
            db.scalars(
                select(LawyerProfile)
                .order_by(LawyerProfile.id)
                .offset(offset)
                .limit(limit)
            )
        )

    def search_public(
        self,
        db: Session,
        *,
        city: str | None = None,
        preferred_city: str | None = None,
        specialization: str | None = None,
        min_years_experience: int | None = None,
        max_years_experience: int | None = None,
        verification_status: VerificationStatus | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[LawyerProfile]:
        statement = (
            select(LawyerProfile)
            .join(User, LawyerProfile.user_id == User.id)
            .where(
                User.is_active.is_(True),
                User.role == UserRole.LAWYER,
                LawyerProfile.verification_status == VerificationStatus.APPROVED,
            )
        )
        if city:
            statement = statement.where(LawyerProfile.city.ilike(city.strip()))
        if specialization:
            statement = statement.where(
                LawyerProfile.specialization.ilike(f"%{specialization.strip()}%")
            )
        if min_years_experience is not None:
            statement = statement.where(
                LawyerProfile.years_of_experience >= min_years_experience
            )
        if max_years_experience is not None:
            statement = statement.where(
                LawyerProfile.years_of_experience <= max_years_experience
            )
        if verification_status is not None:
            statement = statement.where(
                LawyerProfile.verification_status == verification_status
            )

        ordering = []
        if preferred_city:
            ordering.append(
                case(
                    (
                        func.lower(LawyerProfile.city) == preferred_city.strip().lower(),
                        0,
                    ),
                    else_=1,
                )
            )
        statement = (
            statement.order_by(
                *ordering,
                LawyerProfile.years_of_experience.desc(),
                LawyerProfile.id,
            )
            .offset(offset)
            .limit(limit)
        )
        return list(db.scalars(statement))

    def get_public_by_id(
        self,
        db: Session,
        profile_id: int,
    ) -> LawyerProfile | None:
        return db.scalar(
            select(LawyerProfile)
            .join(User, LawyerProfile.user_id == User.id)
            .where(
                LawyerProfile.id == profile_id,
                User.is_active.is_(True),
                User.role == UserRole.LAWYER,
                LawyerProfile.verification_status == VerificationStatus.APPROVED,
            )
        )

    def add(self, db: Session, profile: LawyerProfile) -> LawyerProfile:
        db.add(profile)
        db.flush()
        return profile

    def delete(self, db: Session, profile: LawyerProfile) -> None:
        db.delete(profile)
