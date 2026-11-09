import logging
import re
import uuid
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.user import Case, CaseDocument, DocumentType, User, UserRole
from app.repositories.case_document_repository import CaseDocumentRepository
from app.services.cloudinary_storage import (
    CloudinaryStorage,
    CloudinaryStorageError,
)
from app.services.notification_service import NotificationService
from app.utils.document_validation import (
    DOCUMENT_CONTENT_TYPES,
    validate_document_content,
)

logger = logging.getLogger(__name__)


class CaseDocumentError(Exception):
    pass


class CaseDocumentNotFoundError(CaseDocumentError):
    pass


class CaseDocumentPermissionError(CaseDocumentError):
    pass


class CaseDocumentValidationError(CaseDocumentError):
    pass


class CaseDocumentPersistenceError(CaseDocumentError):
    pass


class CaseDocumentService:
    def __init__(
        self,
        db: Session,
        repository: CaseDocumentRepository | None = None,
        storage: CloudinaryStorage | None = None,
    ) -> None:
        self.db = db
        self.repository = repository or CaseDocumentRepository()
        self.storage = storage or CloudinaryStorage()
        self.notifications = NotificationService(db)

    def _get_case_for_actor(self, case_id: UUID, actor: User) -> Case:
        case = self.repository.get_case(self.db, case_id)
        if case is None:
            raise CaseDocumentNotFoundError("Case not found")
        if actor.role == UserRole.ADMIN:
            return case
        if actor.role == UserRole.CLIENT and actor.id == case.client_id:
            return case
        if actor.role == UserRole.LAWYER and actor.id == case.lawyer_id:
            return case
        raise CaseDocumentPermissionError("You cannot access this case")

    def authorize_case(self, case_id: UUID, actor: User) -> None:
        self._get_case_for_actor(case_id, actor)

    @staticmethod
    def _safe_original_name(file_name: str | None) -> str:
        name = (file_name or "").replace("\\", "/").rsplit("/", maxsplit=1)[-1]
        name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
        if not name or len(name) > 255:
            raise CaseDocumentValidationError("A valid file name is required")
        return name

    @staticmethod
    def _validated_description(description: str | None) -> str | None:
        if description is None:
            return None
        description = description.strip()
        if len(description) > 1000:
            raise CaseDocumentValidationError(
                "Description must be at most 1000 characters"
            )
        return description or None

    def upload(
        self,
        case_id: UUID,
        actor: User,
        *,
        file_name: str | None,
        content: bytes,
        document_type: DocumentType,
        description: str | None = None,
    ) -> CaseDocument:
        case = self._get_case_for_actor(case_id, actor)
        original_file_name = self._safe_original_name(file_name)
        description = self._validated_description(description)
        try:
            extension = validate_document_content(original_file_name, content)
        except ValueError as exc:
            raise CaseDocumentValidationError(str(exc)) from exc

        document_id = uuid.uuid4()
        stored_file_name = f"{document_id.hex}{extension}"
        storage_public_id = f"case-documents/{stored_file_name}"
        stored_asset = self.storage.upload(content, storage_public_id)
        document = CaseDocument(
            id=document_id,
            case_id=case.id,
            uploaded_by=actor.id,
            document_type=document_type,
            file_name=stored_file_name,
            original_file_name=original_file_name,
            file_type=DOCUMENT_CONTENT_TYPES[extension],
            file_size=len(content),
            storage_url=stored_asset.secure_url,
            storage_public_id=storage_public_id,
            description=description,
        )
        try:
            self.repository.add(self.db, document)
            recipients = {case.client_id, case.lawyer_id} - {actor.id}
            if actor.role == UserRole.ADMIN:
                recipients = {case.client_id, case.lawyer_id}
            for user_id in recipients:
                self.notifications.create(
                    user_id,
                    "Document uploaded",
                    f"A document was uploaded to the case: {original_file_name}.",
                )
            self.db.commit()
        except SQLAlchemyError as exc:
            self.db.rollback()
            try:
                self.storage.delete(storage_public_id)
            except CloudinaryStorageError:
                logger.exception(
                    "Failed to clean up Cloudinary asset %s after database failure",
                    storage_public_id,
                )
            raise CaseDocumentPersistenceError(
                "Document metadata could not be saved"
            ) from exc
        return document

    def list_for_case(self, case_id: UUID, actor: User) -> list[CaseDocument]:
        case = self._get_case_for_actor(case_id, actor)
        return self.repository.list_for_case(self.db, case.id)

    def get(self, document_id: UUID, actor: User) -> CaseDocument:
        document = self.repository.get(self.db, document_id)
        if document is None:
            raise CaseDocumentNotFoundError("Document not found")
        self._get_case_for_actor(document.case_id, actor)
        return document

    def download_url(self, document: CaseDocument) -> str:
        return self.storage.get_download_url(document.storage_public_id)

    def delete(self, document_id: UUID, actor: User) -> None:
        document = self.get(document_id, actor)
        case = self.repository.get_case(self.db, document.case_id)
        if case is None:
            raise CaseDocumentNotFoundError("Case not found")
        if actor.role != UserRole.ADMIN and actor.id != document.uploaded_by:
            if actor.role != UserRole.LAWYER or actor.id != case.lawyer_id:
                raise CaseDocumentPermissionError(
                    "Only the assigned lawyer, uploader, or an admin can delete"
                )

        try:
            recipients = {case.client_id, case.lawyer_id} - {actor.id}
            if actor.role == UserRole.ADMIN:
                recipients = {case.client_id, case.lawyer_id}
            for user_id in recipients:
                self.notifications.create(
                    user_id,
                    "Document deleted",
                    f"A document was deleted from the case: "
                    f"{document.original_file_name}.",
                )
            self.storage.delete(document.storage_public_id)
            self.repository.delete(self.db, document)
            self.db.commit()
        except CloudinaryStorageError:
            self.db.rollback()
            raise
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise CaseDocumentPersistenceError(
                "Document metadata could not be deleted"
            ) from exc
