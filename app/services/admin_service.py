from dataclasses import dataclass

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.user import LawyerProfile, User, UserRole, VerificationStatus
from app.repositories.admin_repository import AdminRepository
from app.services.auth_service import AuthService


class AdminError(Exception):
    pass


class AdminNotFoundError(AdminError):
    pass


class AdminPermissionError(AdminError):
    pass


class AdminValidationError(AdminError):
    pass


class AdminService:
    def __init__(
        self,
        db: Session,
        repository: AdminRepository | None = None,
    ) -> None:
        self.db = db
        self.repository = repository or AdminRepository()

    def list_users(
        self,
        *,
        role: UserRole | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[User]:
        return self.repository.list_users(
            self.db,
            role=role,
            is_active=is_active,
            search=search,
            offset=offset,
            limit=limit,
        )

    def get_user(self, user_id: int) -> User:
        user = self.repository.get_user(self.db, user_id)
        if user is None:
            raise AdminNotFoundError("User not found")
        return user

    def set_user_active(
        self,
        actor: User,
        user_id: int,
        *,
        is_active: bool,
    ) -> User:
        if actor.role != UserRole.ADMIN or not actor.is_active:
            raise AdminPermissionError("An active admin account is required")
        user = self.repository.get_user(self.db, user_id)
        if user is None:
            raise AdminNotFoundError("User not found")
        if actor.id == user.id and not is_active:
            raise AdminValidationError("You cannot deactivate your own account")

        if user.role == UserRole.ADMIN:
            admins = self.repository.lock_admins(self.db)
            user = next((admin for admin in admins if admin.id == user_id), None)
            if user is None:
                raise AdminNotFoundError("User not found")
            active_admin_count = sum(admin.is_active for admin in admins)
            if not is_active and user.is_active and active_admin_count <= 1:
                raise AdminValidationError(
                    "The last active admin account cannot be deactivated"
                )
        else:
            user = self.repository.get_user(self.db, user_id, lock=True)
            if user is None:
                raise AdminNotFoundError("User not found")

        if not is_active and user.is_active:
            AuthService.revoke_user_sessions(self.db, user.id)
        user.is_active = is_active
        try:
            self.db.commit()
            self.db.refresh(user)
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise AdminValidationError("User status could not be updated") from exc
        return user

    def list_pending_lawyers(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[LawyerProfile]:
        return self.repository.list_pending_lawyer_profiles(
            self.db,
            offset=offset,
            limit=limit,
        )

    def set_lawyer_verification(
        self,
        user_id: int,
        verification_status: VerificationStatus,
    ) -> LawyerProfile:
        profile = self.repository.get_lawyer_profile(
            self.db,
            user_id,
            lock=True,
        )
        if profile is None:
            raise AdminNotFoundError("Lawyer profile not found")
        profile.verification_status = verification_status
        try:
            self.db.commit()
            self.db.refresh(profile)
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise AdminValidationError(
                "Lawyer verification status could not be updated"
            ) from exc
        return profile

    def dashboard(self) -> "AdminDashboardStats":
        return AdminDashboardStats(
            total_users=self.repository.count_users(self.db),
            total_lawyers=self.repository.count_users(self.db, UserRole.LAWYER),
            total_clients=self.repository.count_users(self.db, UserRole.CLIENT),
            total_cases=self.repository.count_cases(self.db),
            pending_appointments=self.repository.count_pending_appointments(self.db),
            approved_lawyers=self.repository.count_approved_lawyers(self.db),
        )


@dataclass(frozen=True)
class AdminDashboardStats:
    total_users: int
    total_lawyers: int
    total_clients: int
    total_cases: int
    pending_appointments: int
    approved_lawyers: int
