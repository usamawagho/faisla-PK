import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base
from app.api.auth import logout, refresh_tokens, register_client, register_lawyer
from app.models.user import RefreshSession, User, UserRole
from app.schemas.auth import RefreshTokenRequest
from app.schemas.user import ClientRegisterRequest, LawyerRegisterRequest, UserResponse
from app.services.admin_service import AdminService
from app.services.auth_service import AuthService, InvalidTokenError


class RefreshSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_secret = settings.SECRET_KEY
        self.original_expiry = settings.REFRESH_TOKEN_EXPIRE_DAYS
        settings.SECRET_KEY = "test-secret-key-with-at-least-32-characters"
        settings.REFRESH_TOKEN_EXPIRE_DAYS = 7
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.admin = self.add_user(UserRole.ADMIN, "admin")
        self.user = self.add_user(UserRole.CLIENT, "client")

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()
        settings.SECRET_KEY = self.original_secret
        settings.REFRESH_TOKEN_EXPIRE_DAYS = self.original_expiry

    def add_user(self, role: UserRole, label: str) -> User:
        user = User(
            email=f"{label}@auth-test.example",
            hashed_password="not-used",
            role=role,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def test_refresh_rotates_token_and_reuse_revokes_family(self) -> None:
        original_token = AuthService.create_refresh_session(self.db, self.user)
        original_session = self.db.scalar(
            select(RefreshSession).where(
                RefreshSession.token_hash == AuthService._hash_token(original_token)
            )
        )
        self.assertIsNotNone(original_session)
        self.assertNotEqual(original_session.token_hash, original_token)

        user, replacement_token = AuthService.rotate_refresh_token(
            self.db,
            original_token,
        )
        self.assertEqual(user.id, self.user.id)
        replacement_session = self.db.scalar(
            select(RefreshSession).where(
                RefreshSession.token_hash
                == AuthService._hash_token(replacement_token)
            )
        )
        self.db.refresh(original_session)
        self.assertIsNotNone(original_session.revoked_at)
        self.assertEqual(original_session.replaced_by, replacement_session.id)
        self.assertIsNone(replacement_session.revoked_at)

        with self.assertRaises(InvalidTokenError):
            AuthService.rotate_refresh_token(self.db, original_token)
        self.db.refresh(replacement_session)
        self.assertIsNotNone(replacement_session.revoked_at)

    def test_logout_revokes_the_entire_refresh_family(self) -> None:
        token = AuthService.create_refresh_session(self.db, self.user)
        _, replacement_token = AuthService.rotate_refresh_token(self.db, token)

        AuthService.revoke_refresh_family(self.db, replacement_token)

        sessions = self.db.scalars(
            select(RefreshSession).where(RefreshSession.user_id == self.user.id)
        ).all()
        self.assertEqual(len(sessions), 2)
        self.assertTrue(all(session.revoked_at is not None for session in sessions))

    def test_refresh_endpoint_rotates_and_rejects_reuse(self) -> None:
        original_token = AuthService.create_refresh_session(self.db, self.user)

        response = refresh_tokens(
            RefreshTokenRequest(refresh_token=original_token),
            self.db,
        )

        self.assertNotEqual(response.refresh_token, original_token)
        with self.assertRaises(HTTPException) as raised:
            refresh_tokens(
                RefreshTokenRequest(refresh_token=original_token),
                self.db,
            )
        self.assertEqual(raised.exception.status_code, 401)

    def test_logout_endpoint_revokes_refresh_family(self) -> None:
        token = AuthService.create_refresh_session(self.db, self.user)
        _, replacement_token = AuthService.rotate_refresh_token(self.db, token)

        response = logout(
            RefreshTokenRequest(refresh_token=replacement_token),
            self.db,
        )

        self.assertEqual(response.status_code, 204)
        with self.assertRaises(HTTPException) as raised:
            refresh_tokens(
                RefreshTokenRequest(refresh_token=replacement_token),
                self.db,
            )
        self.assertEqual(raised.exception.status_code, 401)

    def test_deactivation_revokes_all_user_refresh_sessions(self) -> None:
        AuthService.create_refresh_session(self.db, self.user)

        AdminService(self.db).set_user_active(
            self.admin,
            self.user.id,
            is_active=False,
        )

        session = self.db.scalar(
            select(RefreshSession).where(RefreshSession.user_id == self.user.id)
        )
        self.assertIsNotNone(session.revoked_at)

    def test_client_registration_persists_profile_without_exposing_private_fields(self) -> None:
        payload = ClientRegisterRequest(
            full_name="  Sara Ahmed ",
            email="SARA@EXAMPLE.COM",
            phone="+923001234567",
            city=" Lahore ",
            address="  Model Town ",
            cnic="4210112345671",
            password="SecurePass1",
        )

        user = register_client(payload, self.db)

        self.assertEqual(user.full_name, "Sara Ahmed")
        self.assertEqual(user.email, "sara@example.com")
        self.assertEqual(user.city, "Lahore")
        self.assertEqual(user.address, "Model Town")
        self.assertEqual(user.cnic, "4210112345671")
        response = UserResponse.model_validate(user)
        self.assertNotIn("cnic", response.model_dump())
        self.assertNotIn("address", response.model_dump())

    def test_lawyer_registration_persists_experience_and_office_address(self) -> None:
        payload = LawyerRegisterRequest(
            email="lawyer-registration@example.com",
            phone="+923001234568",
            password="SecurePass1",
            full_name="Ayesha Khan",
            license_number="LIC-REG-1",
            bar_council="Punjab Bar Council",
            bar_council_number="BC-REG-1",
            cnic="4210112345672",
            city="Lahore",
            specialization="Civil law",
            years_of_experience=12,
            office_address="Court Road",
        )

        user = register_lawyer(payload, self.db)

        self.assertEqual(user.lawyer_profile.years_of_experience, 12)
        self.assertEqual(user.lawyer_profile.office_address, "Court Road")
        self.assertEqual(user.lawyer_profile.specialization, "Civil law")
        self.assertEqual(user.lawyer_profile.city, "Lahore")


if __name__ == "__main__":
    unittest.main()
