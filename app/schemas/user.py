from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole
from app.utils.password_validator import validate_password


class RegistrationBase(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = Field(default=None, max_length=32)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("password")
    @classmethod
    def check_password_policy(cls, value: str) -> str:
        if not validate_password(value):
            raise ValueError(
                "Password must contain uppercase and lowercase letters, "
                "a digit, and be at least 8 characters"
            )
        return value


class LawyerProfileFields(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    license_number: str = Field(min_length=1, max_length=100)
    bar_council: str = Field(min_length=1, max_length=100)
    bar_council_number: str = Field(min_length=1, max_length=100)
    cnic: str = Field(min_length=1, max_length=32)
    specialization: str | None = Field(default=None, max_length=200)
    city: str = Field(default="Karachi", min_length=1, max_length=100)
    years_of_experience: int = Field(default=0, ge=0, le=80)
    consultation_fee: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    languages: list[str] = Field(default_factory=list, max_length=20)
    office_address: str | None = Field(default=None, max_length=500)

    @field_validator(
        "full_name",
        "license_number",
        "bar_council",
        "bar_council_number",
        "cnic",
        "specialization",
        "city",
        "office_address",
    )
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank")
        return value

    @field_validator("languages")
    @classmethod
    def normalize_languages(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("Languages must not contain blank values")
        return list(dict.fromkeys(normalized))


class ClientRegisterRequest(RegistrationBase):
    pass


class LawyerRegisterRequest(RegistrationBase, LawyerProfileFields):
    pass


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    phone: str | None
    role: UserRole
    is_active: bool
