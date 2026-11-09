from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import CurrentUser, get_notification_service
from app.schemas.notifications import NotificationResponse
from app.services.notification_service import (
    NotificationNotFoundError,
    NotificationService,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])
NotificationManager = Annotated[
    NotificationService,
    Depends(get_notification_service),
]


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    user: CurrentUser,
    service: NotificationManager,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[NotificationResponse]:
    return service.list_for_user(user.id, offset=offset, limit=limit)


@router.put("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: UUID,
    user: CurrentUser,
    service: NotificationManager,
) -> NotificationResponse:
    try:
        return service.mark_read(notification_id, user.id)
    except NotificationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
