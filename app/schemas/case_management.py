from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.user import CasePriority, CaseStatus


class CaseCreate(BaseModel):
    client_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    case_type: str = Field(min_length=1, max_length=100)
    priority: CasePriority = CasePriority.MEDIUM

    @field_validator("title", "description", "case_type")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field must not be blank")
        return value


class CaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=10000)
    case_type: str | None = Field(default=None, min_length=1, max_length=100)
    priority: CasePriority | None = None

    @field_validator("title", "description", "case_type")
    @classmethod
    def strip_updated_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Field must not be blank")
        return value

    @model_validator(mode="after")
    def validate_changes(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Case fields cannot be null")
        return self


class CaseStatusUpdate(BaseModel):
    status: CaseStatus


class CaseNoteCreate(BaseModel):
    note: str = Field(min_length=1, max_length=10000)

    @field_validator("note")
    @classmethod
    def strip_note(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Note must not be blank")
        return value


class CaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: int
    lawyer_id: int
    title: str
    description: str
    case_type: str
    status: CaseStatus
    priority: CasePriority
    created_at: datetime
    updated_at: datetime


class CaseNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_id: UUID
    author_id: int
    note: str
    created_at: datetime


class CaseStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_id: UUID
    changed_by_id: int
    previous_status: CaseStatus | None
    new_status: CaseStatus
    created_at: datetime
