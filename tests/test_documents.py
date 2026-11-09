import io
import unittest
import zipfile

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.user import (
    Case,
    CasePriority,
    CaseStatus,
    DocumentType,
    Notification,
    User,
    UserRole,
)
from app.services.cloudinary_storage import StoredAsset
from app.services.document_service import (
    CaseDocumentPermissionError,
    CaseDocumentService,
    CaseDocumentValidationError,
)
from app.utils.document_validation import MAX_DOCUMENT_SIZE


class FakeStorage:
    def __init__(self) -> None:
        self.uploaded: dict[str, bytes] = {}
        self.deleted: list[str] = []

    def upload(self, content: bytes, public_id: str) -> StoredAsset:
        self.uploaded[public_id] = content
        return StoredAsset(secure_url=f"https://cloudinary.example/{public_id}")

    def get_download_url(self, public_id: str) -> str:
        return f"https://cloudinary.example/signed/{public_id}"

    def delete(self, public_id: str) -> None:
        self.deleted.append(public_id)
        self.uploaded.pop(public_id, None)


class CaseDocumentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.storage = FakeStorage()
        self.service = CaseDocumentService(self.db, storage=self.storage)
        self.client = self.add_user(UserRole.CLIENT, "client")
        self.lawyer = self.add_user(UserRole.LAWYER, "lawyer")
        self.other_client = self.add_user(UserRole.CLIENT, "other-client")
        self.admin = self.add_user(UserRole.ADMIN, "admin")
        self.case = Case(
            client_id=self.client.id,
            lawyer_id=self.lawyer.id,
            title="Property matter",
            description="Property dispute",
            case_type="Property",
            status=CaseStatus.OPEN,
            priority=CasePriority.MEDIUM,
        )
        self.db.add(self.case)
        self.db.commit()
        self.db.refresh(self.case)

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def add_user(self, role: UserRole, label: str) -> User:
        user = User(
            email=f"{label}@document-test.example",
            hashed_password="not-used",
            role=role,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def test_participant_can_upload_and_download_with_private_url(self) -> None:
        document = self.service.upload(
            self.case.id,
            self.client,
            file_name="C:\\uploads\\evidence.pdf",
            content=b"%PDF-1.7 document",
            document_type=DocumentType.EVIDENCE,
            description="  Supporting evidence  ",
        )
        self.assertEqual(document.original_file_name, "evidence.pdf")
        self.assertEqual(document.description, "Supporting evidence")
        self.assertEqual(document.file_size, len(b"%PDF-1.7 document"))
        upload_notification = self.db.query(Notification).filter_by(
            user_id=self.lawyer.id
        ).one()
        self.assertEqual(upload_notification.title, "Document uploaded")
        self.assertEqual(
            self.service.download_url(document),
            f"https://cloudinary.example/signed/{document.storage_public_id}",
        )
        self.assertEqual(
            self.service.list_for_case(self.case.id, self.lawyer),
            [document],
        )

    def test_unrelated_user_cannot_list_or_upload(self) -> None:
        with self.assertRaises(CaseDocumentPermissionError):
            self.service.list_for_case(self.case.id, self.other_client)
        with self.assertRaises(CaseDocumentPermissionError):
            self.service.upload(
                self.case.id,
                self.other_client,
                file_name="evidence.pdf",
                content=b"%PDF-1.7 document",
                document_type=DocumentType.EVIDENCE,
            )
        self.assertEqual(self.storage.uploaded, {})

    def test_delete_permissions_allow_uploader_assigned_lawyer_and_admin(self) -> None:
        document = self.service.upload(
            self.case.id,
            self.client,
            file_name="evidence.pdf",
            content=b"%PDF-1.7 document",
            document_type=DocumentType.EVIDENCE,
        )
        with self.assertRaises(CaseDocumentPermissionError):
            self.service.delete(document.id, self.other_client)
        self.service.delete(document.id, self.client)
        self.assertIn(document.storage_public_id, self.storage.deleted)
        self.assertEqual(
            self.db.query(Notification).filter_by(
                user_id=self.lawyer.id,
                title="Document deleted",
            ).count(),
            1,
        )

        second_document = self.service.upload(
            self.case.id,
            self.client,
            file_name="order.pdf",
            content=b"%PDF-1.7 order",
            document_type=DocumentType.COURT_ORDER,
        )
        self.service.delete(second_document.id, self.lawyer)
        self.assertIn(second_document.storage_public_id, self.storage.deleted)

        third_document = self.service.upload(
            self.case.id,
            self.lawyer,
            file_name="contract.pdf",
            content=b"%PDF-1.7 contract",
            document_type=DocumentType.CONTRACT,
        )
        self.service.delete(third_document.id, self.admin)
        self.assertIn(third_document.storage_public_id, self.storage.deleted)

    def test_rejects_disallowed_extensions_invalid_signatures_and_oversize(self) -> None:
        for file_name, content in (
            ("script.exe", b"MZ"),
            ("image.png", b"%PDF-1.7 document"),
            ("large.pdf", b"%PDF-" + b"x" * MAX_DOCUMENT_SIZE),
        ):
            with self.subTest(file_name=file_name):
                with self.assertRaises(CaseDocumentValidationError):
                    self.service.upload(
                        self.case.id,
                        self.client,
                        file_name=file_name,
                        content=content,
                        document_type=DocumentType.OTHER,
                    )

    def test_docx_requires_a_valid_word_archive(self) -> None:
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types/>")
            archive.writestr("word/document.xml", "<document/>")
        document = self.service.upload(
            self.case.id,
            self.client,
            file_name="petition.docx",
            content=stream.getvalue(),
            document_type=DocumentType.CONTRACT,
        )
        self.assertEqual(
            document.file_type,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


if __name__ == "__main__":
    unittest.main()
