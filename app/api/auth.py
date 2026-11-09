from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import CurrentUser
from app.core.database import get_db
from app.models.user import LawyerProfile, User, UserRole, VerificationStatus
from app.schemas.auth import RefreshTokenRequest, TokenResponse
from app.schemas.user import ClientRegisterRequest, LawyerRegisterRequest, UserResponse
from app.services.auth_service import AuthService, InvalidTokenError

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _commit_registration(db: Session, user: User) -> User:
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Registration conflicts with an existing record",
        ) from exc
    return user


@router.post(
    "/register/client",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_client(
    payload: ClientRegisterRequest,
    db: Session = Depends(get_db),
) -> User:
    user = User(
        email=str(payload.email),
        phone=payload.phone,
        hashed_password=AuthService.hash_password(payload.password),
        role=UserRole.CLIENT,
    )
    return _commit_registration(db, user)


@router.post(
    "/register/lawyer",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_lawyer(
    payload: LawyerRegisterRequest,
    db: Session = Depends(get_db),
) -> User:
    profile = LawyerProfile(
        full_name=payload.full_name,
        license_number=payload.license_number,
        bar_council=payload.bar_council,
        bar_council_number=payload.bar_council_number,
        cnic=payload.cnic,
        specialization=payload.specialization,
        city=payload.city,
        verification_status=VerificationStatus.PENDING,
    )
    user = User(
        email=str(payload.email),
        phone=payload.phone,
        hashed_password=AuthService.hash_password(payload.password),
        role=UserRole.LAWYER,
        lawyer_profile=profile,
    )
    return _commit_registration(db, user)


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = AuthService.authenticate(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=AuthService.create_access_token(user),
        refresh_token=AuthService.create_refresh_session(db, user),
        token_type="bearer",
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        user, refresh_token = AuthService.rotate_refresh_token(db, payload.refresh_token)
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return TokenResponse(
        access_token=AuthService.create_access_token(user),
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> Response:
    try:
        AuthService.revoke_refresh_family(db, payload.refresh_token)
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse)
def get_me(user: CurrentUser) -> User:
    return user
