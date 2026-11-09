from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserRole, VerificationStatus


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    phone: str | None
    role: UserRole
    is_active: bool


class AdminLawyerReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    full_name: str
    email: EmailStr
    phone: str | None
    license_number: str
    bar_council: str
    bar_council_number: str
    cnic: str
    specialization: str | None
    city: str | None
    years_of_experience: int
    verification_status: VerificationStatus


class AdminDashboardResponse(BaseModel):
    total_users: int
    total_lawyers: int
    total_clients: int
    total_cases: int
    pending_appointments: int
    approved_lawyers: int


class AdminLawyerReviewResult(BaseModel):
    user_id: int
    verification_status: VerificationStatus
