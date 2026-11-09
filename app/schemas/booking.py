from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.user import AppointmentStatus, ConsultationType


class AvailabilityCreate(BaseModel):
    day_of_week: int = Field(ge=0, le=6, description="Monday=0 through Sunday=6")
    start_time: time
    end_time: time
    is_active: bool = True

    @field_validator("start_time", "end_time")
    @classmethod
    def require_local_schedule_time(cls, value: time) -> time:
        if value.tzinfo is not None:
            raise ValueError("Availability times must be local Asia/Karachi times")
        return value

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.start_time >= self.end_time:
            raise ValueError("end_time must be later than start_time")
        return self


class AvailabilityUpdate(BaseModel):
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    start_time: time | None = None
    end_time: time | None = None
    is_active: bool | None = None

    @field_validator("start_time", "end_time")
    @classmethod
    def require_local_schedule_time(cls, value: time | None) -> time | None:
        if value is not None and value.tzinfo is not None:
            raise ValueError("Availability times must be local Asia/Karachi times")
        return value

    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if (
            "day_of_week" in self.model_fields_set
            and self.day_of_week is None
        ) or ("start_time" in self.model_fields_set and self.start_time is None) or (
            "end_time" in self.model_fields_set and self.end_time is None
        ) or ("is_active" in self.model_fields_set and self.is_active is None):
            raise ValueError("Availability fields cannot be null")
        return self


class AvailabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lawyer_id: int
    day_of_week: int
    start_time: time
    end_time: time
    is_active: bool


class AppointmentCreate(BaseModel):
    lawyer_id: int = Field(gt=0)
    appointment_date: date
    appointment_time: time
    consultation_type: ConsultationType
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_local_time_without_offset(self):
        if self.appointment_time.tzinfo is not None:
            raise ValueError(
                "appointment_time must be a local Asia/Karachi time without a UTC offset"
            )
        if self.notes is not None:
            self.notes = self.notes.strip() or None
        return self


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: int
    lawyer_id: int
    appointment_date: date
    appointment_time: time
    consultation_type: ConsultationType
    notes: str | None
    status: AppointmentStatus
    created_at: datetime
    updated_at: datetime
