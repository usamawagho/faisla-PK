from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core.dependencies import CurrentUser, get_lawyer_profile_service
from app.models.user import LawyerProfile, UserRole
from app.schemas.lawyer_profile import (
    AdminLawyerProfileCreate,
    AdminLawyerProfileUpdate,
    LawyerProfileCreate,
    LawyerProfileResponse,
    LawyerProfileUpdate,
)
from app.services.lawyer_profile_service import (
    InvalidLawyerOwnerError,
    LawyerProfileConflictError,
    LawyerProfileNotFoundError,
    LawyerProfileService,
)

router = APIRouter(prefix="/lawyer-profiles", tags=["Lawyer Profiles"])


ProfileService = Annotated[
    LawyerProfileService,
    Depends(get_lawyer_profile_service),
]


def require_lawyer(user: CurrentUser) -> None:
    if user.role != UserRole.LAWYER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lawyer role required",
        )


def require_admin(user: CurrentUser) -> None:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )


def map_profile_error(exc: Exception) -> HTTPException:
    if isinstance(exc, LawyerProfileNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lawyer profile not found",
        )
    if isinstance(exc, LawyerProfileConflictError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile conflicts with an existing profile",
        )
    if isinstance(exc, InvalidLawyerOwnerError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Profile owner must be an existing lawyer",
        )
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(exc),
    )


@router.post(
    "/me",
    response_model=LawyerProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_my_profile(
    payload: LawyerProfileCreate,
    user: CurrentUser,
    service: ProfileService,
) -> LawyerProfile:
    require_lawyer(user)
    try:
        return service.create(user.id, payload.model_dump())
    except (LawyerProfileConflictError, InvalidLawyerOwnerError) as exc:
        raise map_profile_error(exc) from exc


@router.get("/me", response_model=LawyerProfileResponse)
def get_my_profile(user: CurrentUser, service: ProfileService) -> LawyerProfile:
    require_lawyer(user)
    try:
        return service.get_for_user(user.id)
    except LawyerProfileNotFoundError as exc:
        raise map_profile_error(exc) from exc


@router.patch("/me", response_model=LawyerProfileResponse)
def update_my_profile(
    payload: LawyerProfileUpdate,
    user: CurrentUser,
    service: ProfileService,
) -> LawyerProfile:
    require_lawyer(user)
    try:
        profile = service.get_for_user(user.id)
        return service.update(profile, payload.model_dump(exclude_unset=True))
    except (LawyerProfileNotFoundError, LawyerProfileConflictError, ValueError) as exc:
        raise map_profile_error(exc) from exc


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_profile(user: CurrentUser, service: ProfileService) -> Response:
    require_lawyer(user)
    try:
        service.delete(service.get_for_user(user.id))
    except LawyerProfileNotFoundError as exc:
        raise map_profile_error(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=list[LawyerProfileResponse])
def list_profiles(
    user: CurrentUser,
    service: ProfileService,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[LawyerProfile]:
    require_admin(user)
    return service.list(offset=offset, limit=limit)


@router.post(
    "",
    response_model=LawyerProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_profile(
    payload: AdminLawyerProfileCreate,
    user: CurrentUser,
    service: ProfileService,
) -> LawyerProfile:
    require_admin(user)
    values = payload.model_dump(exclude={"user_id"})
    try:
        return service.create(payload.user_id, values)
    except (LawyerProfileConflictError, InvalidLawyerOwnerError) as exc:
        raise map_profile_error(exc) from exc


@router.get("/{profile_id}", response_model=LawyerProfileResponse)
def get_profile(
    profile_id: int,
    user: CurrentUser,
    service: ProfileService,
) -> LawyerProfile:
    require_admin(user)
    try:
        return service.get(profile_id)
    except LawyerProfileNotFoundError as exc:
        raise map_profile_error(exc) from exc


@router.patch("/{profile_id}", response_model=LawyerProfileResponse)
def update_profile(
    profile_id: int,
    payload: AdminLawyerProfileUpdate,
    user: CurrentUser,
    service: ProfileService,
) -> LawyerProfile:
    require_admin(user)
    try:
        profile = service.get(profile_id)
        return service.update(profile, payload.model_dump(exclude_unset=True))
    except (LawyerProfileNotFoundError, LawyerProfileConflictError, ValueError) as exc:
        raise map_profile_error(exc) from exc


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    profile_id: int,
    user: CurrentUser,
    service: ProfileService,
) -> Response:
    require_admin(user)
    try:
        service.delete(service.get(profile_id))
    except LawyerProfileNotFoundError as exc:
        raise map_profile_error(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
