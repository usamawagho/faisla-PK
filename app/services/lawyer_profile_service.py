from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import LawyerProfile, User, UserRole, VerificationStatus
from app.repositories.lawyer_profile_repository import LawyerProfileRepository


class LawyerProfileNotFoundError(Exception):
    pass


class LawyerProfileConflictError(Exception):
    pass


class InvalidLawyerOwnerError(Exception):
    pass


class LawyerProfileService:
    def __init__(
        self,
        db: Session,
        repository: LawyerProfileRepository | None = None,
    ) -> None:
        self.db = db
        self.repository = repository or LawyerProfileRepository()

    def get(self, profile_id: int) -> LawyerProfile:
        profile = self.repository.get_by_id(self.db, profile_id)
        if profile is None:
            raise LawyerProfileNotFoundError
        return profile

    def get_for_user(self, user_id: int) -> LawyerProfile:
        profile = self.repository.get_by_user_id(self.db, user_id)
        if profile is None:
            raise LawyerProfileNotFoundError
        return profile

    def list(self, offset: int = 0, limit: int = 100) -> list[LawyerProfile]:
        return self.repository.list(self.db, offset=offset, limit=limit)

    def search_public(
        self,
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
        return self.repository.search_public(
            self.db,
            city=city,
            preferred_city=preferred_city,
            specialization=specialization,
            min_years_experience=min_years_experience,
            max_years_experience=max_years_experience,
            verification_status=verification_status,
            offset=offset,
            limit=limit,
        )

    def get_public(self, profile_id: int) -> LawyerProfile:
        profile = self.repository.get_public_by_id(self.db, profile_id)
        if profile is None:
            raise LawyerProfileNotFoundError
        return profile

    def create(self, user_id: int, values: dict) -> LawyerProfile:
        owner = self.db.get(User, user_id)
        if owner is None or owner.role != UserRole.LAWYER:
            raise InvalidLawyerOwnerError
        if self.repository.get_by_user_id(self.db, user_id) is not None:
            raise LawyerProfileConflictError

        profile = LawyerProfile(user_id=user_id, **values)
        try:
            self.repository.add(self.db, profile)
            self.db.commit()
            self.db.refresh(profile)
        except IntegrityError as exc:
            self.db.rollback()
            raise LawyerProfileConflictError from exc
        return profile

    def update(self, profile: LawyerProfile, values: dict) -> LawyerProfile:
        for field, value in values.items():
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    raise ValueError(f"{field} must not be blank")
            setattr(profile, field, value)
        try:
            self.db.commit()
            self.db.refresh(profile)
        except IntegrityError as exc:
            self.db.rollback()
            raise LawyerProfileConflictError from exc
        return profile

    def delete(self, profile: LawyerProfile) -> None:
        self.repository.delete(self.db, profile)
        self.db.commit()
