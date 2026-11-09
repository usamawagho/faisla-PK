from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService, InvalidTokenError
from app.services.booking_service import BookingService
from app.services.admin_service import AdminService
from app.services.case_service import CaseService
from app.services.document_service import CaseDocumentService
from app.services.lawyer_profile_service import LawyerProfileService
from app.services.notification_service import NotificationService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    try:
        claims = AuthService.verify_token(token, expected_type="access")
        user_id = int(claims["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive account",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_lawyer_profile_service(
    db: Annotated[Session, Depends(get_db)],
) -> LawyerProfileService:
    return LawyerProfileService(db)


def get_booking_service(
    db: Annotated[Session, Depends(get_db)],
) -> BookingService:
    return BookingService(db)


def get_case_service(
    db: Annotated[Session, Depends(get_db)],
) -> CaseService:
    return CaseService(db)


def get_case_document_service(
    db: Annotated[Session, Depends(get_db)],
) -> CaseDocumentService:
    return CaseDocumentService(db)


def get_admin_service(
    db: Annotated[Session, Depends(get_db)],
) -> AdminService:
    return AdminService(db)


def get_notification_service(
    db: Annotated[Session, Depends(get_db)],
) -> NotificationService:
    return NotificationService(db)
