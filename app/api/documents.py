from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)

from app.core.dependencies import CurrentUser, get_case_document_service
from app.models.user import CaseDocument, DocumentType
from app.schemas.documents import CaseDocumentResponse
from app.services.cloudinary_storage import (
    CloudinaryStorageError,
    CloudinaryStorageNotConfigured,
)
from app.services.document_service import (
    CaseDocumentNotFoundError,
    CaseDocumentPermissionError,
    CaseDocumentPersistenceError,
    CaseDocumentService,
    CaseDocumentValidationError,
)
from app.utils.document_validation import MAX_DOCUMENT_SIZE

router = APIRouter(tags=["Case Documents"])
DocumentManager = Annotated[CaseDocumentService, Depends(get_case_document_service)]


def document_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, CaseDocumentNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, CaseDocumentPermissionError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, CaseDocumentValidationError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    if isinstance(exc, CloudinaryStorageNotConfigured):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    if isinstance(exc, CloudinaryStorageError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Document storage operation failed",
        )
    if isinstance(exc, CaseDocumentPersistenceError):
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document metadata operation failed",
        )
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Document request failed",
    )


def document_response(
    document: CaseDocument,
    service: CaseDocumentService,
) -> CaseDocumentResponse:
    response = CaseDocumentResponse.model_validate(document)
    return response.model_copy(update={"storage_url": service.download_url(document)})


@router.post(
    "/cases/{case_id}/documents",
    response_model=CaseDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_case_document(
    case_id: UUID,
    user: CurrentUser,
    service: DocumentManager,
    file: Annotated[UploadFile, File()],
    document_type: Annotated[DocumentType, Form()] = DocumentType.OTHER,
    description: Annotated[str | None, Form(max_length=1000)] = None,
) -> CaseDocumentResponse:
    try:
        service.authorize_case(case_id, user)
    except (CaseDocumentNotFoundError, CaseDocumentPermissionError) as exc:
        raise document_http_error(exc) from exc
    content = file.file.read(MAX_DOCUMENT_SIZE + 1)
    if len(content) > MAX_DOCUMENT_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 10 MB limit",
        )
    try:
        document = service.upload(
            case_id,
            user,
            file_name=file.filename,
            content=content,
            document_type=document_type,
            description=description,
        )
        return document_response(document, service)
    except (
        CaseDocumentNotFoundError,
        CaseDocumentPermissionError,
        CaseDocumentValidationError,
        CaseDocumentPersistenceError,
        CloudinaryStorageError,
    ) as exc:
        raise document_http_error(exc) from exc


@router.get(
    "/cases/{case_id}/documents",
    response_model=list[CaseDocumentResponse],
)
def list_case_documents(
    case_id: UUID,
    user: CurrentUser,
    service: DocumentManager,
) -> list[CaseDocumentResponse]:
    try:
        return [
            document_response(document, service)
            for document in service.list_for_case(case_id, user)
        ]
    except (
        CaseDocumentNotFoundError,
        CaseDocumentPermissionError,
        CloudinaryStorageError,
        CloudinaryStorageNotConfigured,
    ) as exc:
        raise document_http_error(exc) from exc


@router.get("/documents/{document_id}", response_model=CaseDocumentResponse)
def get_case_document(
    document_id: UUID,
    user: CurrentUser,
    service: DocumentManager,
) -> CaseDocumentResponse:
    try:
        document = service.get(document_id, user)
        return document_response(document, service)
    except (
        CaseDocumentNotFoundError,
        CaseDocumentPermissionError,
        CloudinaryStorageError,
        CloudinaryStorageNotConfigured,
    ) as exc:
        raise document_http_error(exc) from exc


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_case_document(
    document_id: UUID,
    user: CurrentUser,
    service: DocumentManager,
) -> Response:
    try:
        service.delete(document_id, user)
    except (
        CaseDocumentNotFoundError,
        CaseDocumentPermissionError,
        CaseDocumentPersistenceError,
        CloudinaryStorageError,
        CloudinaryStorageNotConfigured,
    ) as exc:
        raise document_http_error(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
