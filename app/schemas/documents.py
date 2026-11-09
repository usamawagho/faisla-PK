from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.user import DocumentType


class CaseDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_id: UUID
    uploaded_by: int
    document_type: DocumentType
    file_name: str
    original_file_name: str
    file_type: str
    file_size: int
    storage_url: str
    description: str | None
    uploaded_at: datetime
