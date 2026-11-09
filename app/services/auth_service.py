import hashlib
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from jose import JWTError, jwt
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models.user import RefreshSession, User


class InvalidTokenError(Exception):
    pass


class AuthService:
    @staticmethod
    def authenticate(db: Session, email: str, password: str) -> User | None:
        user = db.scalar(select(User).where(User.email == email.strip().lower()))
        if user is None or not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def hash_password(password: str) -> str:
        return hash_password(password)

    @staticmethod
    def _secret_key() -> str:
        if len(settings.SECRET_KEY.encode("utf-8")) < 32:
            raise RuntimeError("SECRET_KEY must be configured with at least 32 characters")
        return settings.SECRET_KEY

    @classmethod
    def create_access_token(cls, user: User) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        return jwt.encode(
            {
                "sub": str(user.id),
                "role": user.role.value,
                "type": "access",
                "jti": str(uuid4()),
                "exp": expires_at,
            },
            cls._secret_key(),
            algorithm="HS256",
        )

    @classmethod
    def create_refresh_session(cls, db: Session, user: User) -> str:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        family_id = uuid4()
        session_id = uuid4()
        token = cls._encode_refresh_token(user, family_id, session_id, expires_at)
        db.add(
            RefreshSession(
                id=session_id,
                user_id=user.id,
                token_hash=cls._hash_token(token),
                token_family=family_id,
                expires_at=expires_at,
            )
        )
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise
        return token

    @classmethod
    def _encode_refresh_token(
        cls,
        user: User,
        family_id: UUID,
        session_id: UUID,
        expires_at: datetime,
    ) -> str:
        return jwt.encode(
            {
                "sub": str(user.id),
                "type": "refresh",
                "jti": str(session_id),
                "family": str(family_id),
                "exp": expires_at,
            },
            cls._secret_key(),
            algorithm="HS256",
        )

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @classmethod
    def verify_token(cls, token: str, expected_type: str) -> dict[str, object]:
        try:
            claims = jwt.decode(token, cls._secret_key(), algorithms=["HS256"])
        except JWTError as exc:
            raise InvalidTokenError("Token signature or claims are invalid") from exc
        if (
            claims.get("type") != expected_type
            or not isinstance(claims.get("sub"), str)
            or not claims.get("jti")
            or "exp" not in claims
        ):
            raise InvalidTokenError("Token type or required claims are invalid")
        return claims

    @classmethod
    def rotate_refresh_token(cls, db: Session, token: str) -> tuple[User, str]:
        claims = cls.verify_token(token, expected_type="refresh")
        try:
            user_id = int(claims["sub"])
            session_id = UUID(str(claims["jti"]))
            family_id = UUID(str(claims["family"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidTokenError("Refresh token session claims are invalid") from exc

        user = db.scalar(select(User).where(User.id == user_id).with_for_update())
        if user is None:
            raise InvalidTokenError("Refresh token user is not recognized")
        now = datetime.now(timezone.utc)
        if not user.is_active:
            cls._revoke_family(db, family_id, now)
            db.commit()
            raise InvalidTokenError("User account is inactive")

        token_session = db.scalar(
            select(RefreshSession)
            .where(RefreshSession.token_hash == cls._hash_token(token))
            .with_for_update()
        )
        if (
            token_session is None
            or token_session.id != session_id
            or token_session.user_id != user_id
            or token_session.token_family != family_id
        ):
            raise InvalidTokenError("Refresh token session is not recognized")

        if token_session.revoked_at is not None:
            cls._revoke_family(db, family_id, now)
            db.commit()
            raise InvalidTokenError("Refresh token has already been used")

        session_expiry = token_session.expires_at
        if session_expiry.tzinfo is None:
            session_expiry = session_expiry.replace(tzinfo=timezone.utc)
        if session_expiry <= now:
            cls._revoke_family(db, family_id, now)
            db.commit()
            raise InvalidTokenError("Refresh session has expired")

        expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        replacement_id = uuid4()
        replacement_token = cls._encode_refresh_token(
            user,
            family_id,
            replacement_id,
            expires_at,
        )
        token_session.revoked_at = now
        token_session.replaced_by = replacement_id
        db.add(
            RefreshSession(
                id=replacement_id,
                user_id=user.id,
                token_hash=cls._hash_token(replacement_token),
                token_family=family_id,
                expires_at=expires_at,
            )
        )
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise
        return user, replacement_token

    @classmethod
    def revoke_refresh_family(cls, db: Session, token: str) -> None:
        claims = cls.verify_token(token, expected_type="refresh")
        try:
            user_id = int(claims["sub"])
            session_id = UUID(str(claims["jti"]))
            family_id = UUID(str(claims["family"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidTokenError("Refresh token session claims are invalid") from exc

        user = db.scalar(select(User).where(User.id == user_id).with_for_update())
        if user is None:
            raise InvalidTokenError("Refresh token user is not recognized")

        token_session = db.scalar(
            select(RefreshSession).where(
                RefreshSession.token_hash == cls._hash_token(token)
            )
        )
        if (
            token_session is None
            or token_session.id != session_id
            or token_session.user_id != user_id
            or token_session.token_family != family_id
        ):
            raise InvalidTokenError("Refresh token session is not recognized")

        cls._revoke_family(db, family_id, datetime.now(timezone.utc))
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise

    @staticmethod
    def _revoke_family(db: Session, family_id: UUID, revoked_at: datetime) -> None:
        db.execute(
            update(RefreshSession)
            .where(
                RefreshSession.token_family == family_id,
                RefreshSession.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )

    @staticmethod
    def revoke_user_sessions(db: Session, user_id: int) -> None:
        db.execute(
            update(RefreshSession)
            .where(
                RefreshSession.user_id == user_id,
                RefreshSession.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
