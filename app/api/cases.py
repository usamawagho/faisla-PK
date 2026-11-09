from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import CurrentUser, get_case_service
from app.models.user import (
    Case,
    CaseNote,
    CaseStatus,
    CaseStatusHistory,
    User,
    UserRole,
)
from app.schemas.case_management import (
    CaseCreate,
    CaseNoteCreate,
    CaseNoteResponse,
    CaseResponse,
    CaseStatusHistoryResponse,
    CaseStatusUpdate,
    CaseUpdate,
)
from app.services.case_service import (
    CaseNotFoundError,
    CasePermissionError,
    CaseService,
    CaseValidationError,
)

router = APIRouter(prefix="/cases", tags=["Case Management"])
CaseManager = Annotated[CaseService, Depends(get_case_service)]


def ensure_role(user: User, role: UserRole) -> None:
    if user.role != role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{role.value.title()} role required",
        )


def case_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, CaseNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, CasePermissionError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, CaseValidationError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Case request could not be completed",
    )


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    payload: CaseCreate,
    user: CurrentUser,
    service: CaseManager,
) -> Case:
    ensure_role(user, UserRole.LAWYER)
    try:
        return service.create(user, payload.model_dump())
    except (CasePermissionError, CaseValidationError) as exc:
        raise case_http_error(exc) from exc


@router.get("/my", response_model=list[CaseResponse])
def get_my_cases(user: CurrentUser, service: CaseManager) -> list[Case]:
    try:
        return service.list_for_user(user)
    except CasePermissionError as exc:
        raise case_http_error(exc) from exc


@router.get("", response_model=list[CaseResponse])
def get_all_cases(
    user: CurrentUser,
    service: CaseManager,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[Case]:
    ensure_role(user, UserRole.ADMIN)
    return service.list_all(user, offset=offset, limit=limit)


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(
    case_id: UUID,
    user: CurrentUser,
    service: CaseManager,
) -> Case:
    try:
        return service.get(case_id, user)
    except (CaseNotFoundError, CasePermissionError) as exc:
        raise case_http_error(exc) from exc


@router.put("/{case_id}", response_model=CaseResponse)
def update_case(
    case_id: UUID,
    payload: CaseUpdate,
    user: CurrentUser,
    service: CaseManager,
) -> Case:
    ensure_role(user, UserRole.LAWYER)
    try:
        return service.update(case_id, user, payload.model_dump(exclude_unset=True))
    except (CaseNotFoundError, CasePermissionError, CaseValidationError) as exc:
        raise case_http_error(exc) from exc


@router.post(
    "/{case_id}/notes",
    response_model=CaseNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_case_note(
    case_id: UUID,
    payload: CaseNoteCreate,
    user: CurrentUser,
    service: CaseManager,
) -> CaseNote:
    ensure_role(user, UserRole.LAWYER)
    try:
        return service.add_note(case_id, user, payload.note)
    except (CaseNotFoundError, CasePermissionError, CaseValidationError) as exc:
        raise case_http_error(exc) from exc


@router.get("/{case_id}/notes", response_model=list[CaseNoteResponse])
def get_case_notes(
    case_id: UUID,
    user: CurrentUser,
    service: CaseManager,
) -> list[CaseNote]:
    try:
        return service.list_notes(case_id, user)
    except (CaseNotFoundError, CasePermissionError) as exc:
        raise case_http_error(exc) from exc


@router.put("/{case_id}/status", response_model=CaseResponse)
def update_case_status(
    case_id: UUID,
    payload: CaseStatusUpdate,
    user: CurrentUser,
    service: CaseManager,
) -> Case:
    ensure_role(user, UserRole.LAWYER)
    try:
        return service.change_status(case_id, user, payload.status)
    except (CaseNotFoundError, CasePermissionError, CaseValidationError) as exc:
        raise case_http_error(exc) from exc


@router.get(
    "/{case_id}/status-history",
    response_model=list[CaseStatusHistoryResponse],
)
def get_case_status_history(
    case_id: UUID,
    user: CurrentUser,
    service: CaseManager,
) -> list[CaseStatusHistory]:
    try:
        return service.list_status_history(case_id, user)
    except (CaseNotFoundError, CasePermissionError) as exc:
        raise case_http_error(exc) from exc
