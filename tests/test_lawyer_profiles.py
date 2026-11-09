import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base
from app.core.security import hash_password, verify_password
from app.models.user import (
    LawyerProfile,
    User,
    UserRole,
    VerificationStatus,
)
from app.schemas.lawyer_profile import (
    LawyerMarketplaceResponse,
    LawyerProfileCreate,
    LawyerProfileUpdate,
)
from app.schemas.user import LawyerRegisterRequest
from app.repositories.lawyer_profile_repository import LawyerProfileRepository
from app.services.auth_service import AuthService, InvalidTokenError
from app.services.lawyer_profile_service import (
    InvalidLawyerOwnerError,
    LawyerProfileConflictError,
    LawyerProfileNotFoundError,
    LawyerProfileService,
)
from app.utils.password_validator import validate_password


class LawyerProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.service = LawyerProfileService(self.db)
        self.old_secret = settings.SECRET_KEY
        settings.SECRET_KEY = "test-secret-key-that-is-at-least-32-bytes"

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()
        settings.SECRET_KEY = self.old_secret

    def add_user(self, role: UserRole = UserRole.LAWYER) -> User:
        user = User(
            email=f"{role.value}-{self.db.query(User).count()}@example.com",
            hashed_password="not-used-in-this-test",
            role=role,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    @staticmethod
    def profile_values() -> dict[str, object]:
        return {
            "full_name": "Ayesha Khan",
            "license_number": "LIC-101",
            "bar_council": "Sindh Bar Council",
            "bar_council_number": "BC-101",
            "cnic": "4210112345671",
            "specialization": "Civil law",
            "city": "Karachi",
            "years_of_experience": 8,
            "consultation_fee": "5000.00",
            "languages": ["Urdu", "English"],
            "office_address": "Court Road",
        }

    def test_profile_create_read_update_delete(self) -> None:
        user = self.add_user()
        profile = self.service.create(user.id, self.profile_values())
        self.assertEqual(profile.user_id, user.id)
        self.assertEqual(profile.verification_status, VerificationStatus.PENDING)
        self.assertEqual(self.service.get_for_user(user.id).id, profile.id)

        updated = self.service.update(profile, {"city": "Lahore"})
        self.assertEqual(updated.city, "Lahore")

        self.service.delete(updated)
        with self.assertRaises(LawyerProfileNotFoundError):
            self.service.get(profile.id)

    def test_profile_owner_and_unique_constraints_are_checked(self) -> None:
        client = self.add_user(UserRole.CLIENT)
        with self.assertRaises(InvalidLawyerOwnerError):
            self.service.create(client.id, self.profile_values())

        lawyer = self.add_user()
        self.service.create(lawyer.id, self.profile_values())
        with self.assertRaises(LawyerProfileConflictError):
            self.service.create(lawyer.id, self.profile_values())

    def test_registration_schema_requires_all_profile_fields(self) -> None:
        payload = LawyerRegisterRequest(
            email="LAWYER@EXAMPLE.COM",
            password="SecurePass1",
            **self.profile_values(),
        )
        self.assertEqual(str(payload.email), "lawyer@example.com")
        with self.assertRaises(ValueError):
            LawyerProfileCreate(
                full_name="   ",
                **{
                    key: value
                    for key, value in self.profile_values().items()
                    if key != "full_name"
                },
            )
        with self.assertRaises(ValueError):
            LawyerProfileUpdate()

    def test_password_policy_enforces_complexity_and_bcrypt_byte_limit(self) -> None:
        self.assertTrue(validate_password("SecurePass1"))
        self.assertFalse(validate_password("alllowercase1"))
        self.assertFalse(validate_password("NoDigitsHere"))
        self.assertFalse(validate_password("Aa1" + ("x" * 70)))
        password_hash = hash_password("SecurePass1")
        self.assertTrue(verify_password("SecurePass1", password_hash))
        self.assertFalse(verify_password("WrongPass1", password_hash))
        with self.assertRaises(ValueError):
            hash_password("Aa1" + ("x" * 70))

    def test_jwt_token_types_are_separated(self) -> None:
        user = self.add_user()
        access_token = AuthService.create_access_token(user)
        refresh_token = AuthService.create_refresh_session(self.db, user)
        self.assertEqual(
            AuthService.verify_token(access_token, "access")["sub"],
            str(user.id),
        )
        with self.assertRaises(InvalidTokenError):
            AuthService.verify_token(access_token, "refresh")
        self.assertEqual(
            AuthService.verify_token(refresh_token, "refresh")["sub"],
            str(user.id),
        )

    def test_public_search_only_returns_active_approved_lawyers(self) -> None:
        approved = self.add_user()
        approved.lawyer_profile = LawyerProfile(
            **self.profile_values(),
            verification_status=VerificationStatus.APPROVED,
        )
        pending = self.add_user()
        pending.lawyer_profile = LawyerProfile(
            **{
                **self.profile_values(),
                "license_number": "LIC-102",
                "bar_council_number": "BC-102",
                "cnic": "4210112345672",
            },
            verification_status=VerificationStatus.PENDING,
        )
        inactive = self.add_user()
        inactive.is_active = False
        inactive.lawyer_profile = LawyerProfile(
            **{
                **self.profile_values(),
                "license_number": "LIC-103",
                "bar_council_number": "BC-103",
                "cnic": "4210112345673",
            },
            verification_status=VerificationStatus.APPROVED,
        )
        self.db.commit()

        results = LawyerProfileRepository().search_public(
            self.db,
            city="karachi",
            specialization="civil",
            min_years_experience=5,
        )
        self.assertEqual([profile.user_id for profile in results], [approved.id])

        rejected_filter = LawyerProfileRepository().search_public(
            self.db,
            verification_status=VerificationStatus.PENDING,
        )
        self.assertEqual(rejected_filter, [])

    def test_marketplace_response_does_not_expose_sensitive_identifiers(self) -> None:
        public_fields = set(LawyerMarketplaceResponse.model_fields)
        self.assertNotIn("cnic", public_fields)
        self.assertNotIn("license_number", public_fields)
        self.assertNotIn("bar_council_number", public_fields)
        self.assertNotIn("hashed_password", public_fields)


if __name__ == "__main__":
    unittest.main()
