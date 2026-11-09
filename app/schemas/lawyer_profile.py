from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.user import VerificationStatus
from app.schemas.user import LawyerProfileFields


class LawyerProfileCreate(LawyerProfileFields):
    pass


class AdminLawyerProfileCreate(LawyerProfileCreate):
    user_id: int = Field(gt=0)


class LawyerProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    license_number: str | None = Field(default=None, min_length=1, max_length=100)
    bar_council: str | None = Field(default=None, min_length=1, max_length=100)
    bar_council_number: str | None = Field(default=None, min_length=1, max_length=100)
    cnic: str | None = Field(default=None, min_length=1, max_length=32)
    specialization: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    years_of_experience: int | None = Field(default=None, ge=0, le=80)
    consultation_fee: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    languages: list[str] | None = Field(default=None, max_length=20)
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
    def strip_updated_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank")
        return value

    @field_validator("languages")
    @classmethod
    def strip_updated_languages(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("Languages must not contain blank values")
        return list(dict.fromkeys(normalized))

    @model_validator(mode="after")
    def validate_changes(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        non_nullable_fields = {
            "full_name",
            "license_number",
            "bar_council",
            "bar_council_number",
            "cnic",
            "years_of_experience",
            "languages",
        }
        if any(
            field in self.model_fields_set and getattr(self, field) is None
            for field in non_nullable_fields
        ):
            raise ValueError("Required profile fields cannot be null")
        return self


class AdminLawyerProfileUpdate(LawyerProfileUpdate):
    verification_status: VerificationStatus | None = None

    @model_validator(mode="after")
    def require_verification_status_value(self):
        if (
            "verification_status" in self.model_fields_set
            and self.verification_status is None
        ):
            raise ValueError("Verification status cannot be null")
        return self


class LawyerProfileResponse(LawyerProfileFields):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    verification_status: VerificationStatus


class LawyerMarketplaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    full_name: str
    specialization: str | None
    city: str | None
    years_of_experience: int
    consultation_fee: Decimal | None
    languages: list[str]
    office_address: str | None
    verified: bool
