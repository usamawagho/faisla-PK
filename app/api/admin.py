from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import CurrentUser, get_admin_service
from app.models.user import (
    LawyerProfile,
    User,
    UserRole,
    VerificationStatus,
)
from app.schemas.admin import (
    AdminDashboardResponse,
    AdminLawyerReviewResponse,
    AdminLawyerReviewResult,
    AdminUserResponse,
)
from app.services.admin_service import (
    AdminNotFoundError,
    AdminPermissionError,
    AdminService,
    AdminValidationError,
)

router = APIRouter(prefix="/admin", tags=["Admin"])
AdminManager = Annotated[AdminService, Depends(get_admin_service)]


def ensure_admin(user: User) -> None:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )


def admin_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AdminNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, AdminPermissionError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, AdminValidationError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Admin request could not be completed",
    )


def lawyer_review_response(profile: LawyerProfile) -> AdminLawyerReviewResponse:
    return AdminLawyerReviewResponse(
        id=profile.id,
        user_id=profile.user_id,
        full_name=profile.full_name,
        email=profile.user.email,
        phone=profile.user.phone,
        license_number=profile.license_number,
        bar_council=profile.bar_council,
        bar_council_number=profile.bar_council_number,
        cnic=profile.cnic,
        specialization=profile.specialization,
        city=profile.city,
        years_of_experience=profile.years_of_experience,
        verification_status=profile.verification_status,
    )


@router.get("/users", response_model=list[AdminUserResponse])
def list_users(
    user: CurrentUser,
    service: AdminManager,
    role: UserRole | None = None,
    is_active: bool | None = None,
    search: str | None = Query(default=None, min_length=1, max_length=254),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[User]:
    ensure_admin(user)
    return service.list_users(
        role=role,
        is_active=is_active,
        search=search,
        offset=offset,
        limit=limit,
    )


@router.get("/users/{user_id}", response_model=AdminUserResponse)
def get_user(
    user_id: int,
    user: CurrentUser,
    service: AdminManager,
) -> User:
    ensure_admin(user)
    try:
        return service.get_user(user_id)
    except AdminNotFoundError as exc:
        raise admin_http_error(exc) from exc


def set_user_active(
    user_id: int,
    user: User,
    service: AdminService,
    is_active: bool,
) -> User:
    try:
        return service.set_user_active(user, user_id, is_active=is_active)
    except (AdminNotFoundError, AdminPermissionError, AdminValidationError) as exc:
        raise admin_http_error(exc) from exc


@router.put("/users/{user_id}/activate", response_model=AdminUserResponse)
def activate_user(
    user_id: int,
    user: CurrentUser,
    service: AdminManager,
) -> User:
    ensure_admin(user)
    return set_user_active(user_id, user, service, True)


@router.put("/users/{user_id}/deactivate", response_model=AdminUserResponse)
def deactivate_user(
    user_id: int,
    user: CurrentUser,
    service: AdminManager,
) -> User:
    ensure_admin(user)
    return set_user_active(user_id, user, service, False)


@router.get(
    "/lawyers/pending",
    response_model=list[AdminLawyerReviewResponse],
)
def list_pending_lawyers(
    user: CurrentUser,
    service: AdminManager,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[AdminLawyerReviewResponse]:
    ensure_admin(user)
    return [
        lawyer_review_response(profile)
        for profile in service.list_pending_lawyers(offset=offset, limit=limit)
    ]


def review_lawyer(
    user_id: int,
    service: AdminService,
    verification_status: VerificationStatus,
) -> AdminLawyerReviewResult:
    try:
        profile = service.set_lawyer_verification(user_id, verification_status)
    except (AdminNotFoundError, AdminValidationError) as exc:
        raise admin_http_error(exc) from exc
    return AdminLawyerReviewResult(
        user_id=profile.user_id,
        verification_status=profile.verification_status,
    )


@router.put(
    "/lawyers/{user_id}/approve",
    response_model=AdminLawyerReviewResult,
)
def approve_lawyer(
    user_id: int,
    user: CurrentUser,
    service: AdminManager,
) -> AdminLawyerReviewResult:
    ensure_admin(user)
    return review_lawyer(
        user_id,
        service,
        VerificationStatus.APPROVED,
    )


@router.put(
    "/lawyers/{user_id}/reject",
    response_model=AdminLawyerReviewResult,
)
def reject_lawyer(
    user_id: int,
    user: CurrentUser,
    service: AdminManager,
) -> AdminLawyerReviewResult:
    ensure_admin(user)
    return review_lawyer(
        user_id,
        service,
        VerificationStatus.REJECTED,
    )


@router.get("/dashboard", response_model=AdminDashboardResponse)
def get_dashboard(
    user: CurrentUser,
    service: AdminManager,
) -> AdminDashboardResponse:
    ensure_admin(user)
    return service.dashboard()
