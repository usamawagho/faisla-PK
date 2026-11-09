import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Time,
    Uuid,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    CLIENT = "client"
    LAWYER = "lawyer"
    ADMIN = "admin"


class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AppointmentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ConsultationType(str, enum.Enum):
    ONLINE = "online"
    IN_PERSON = "in_person"


class CaseStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_CLIENT = "waiting_client"
    ON_HOLD = "on_hold"
    CLOSED = "closed"


class CasePriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class DocumentType(str, enum.Enum):
    CONTRACT = "contract"
    EVIDENCE = "evidence"
    COURT_ORDER = "court_order"
    AGREEMENT = "agreement"
    ID_DOCUMENT = "id_document"
    OTHER = "other"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    full_name = Column(String(200), nullable=True)
    cnic = Column(String(32), nullable=True)
    city = Column(String(100), nullable=True)
    address = Column(String(500), nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
    )

    lawyer_profile = relationship(
        "LawyerProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        single_parent=True,
    )
    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Notification.created_at.desc()",
    )


class LawyerProfile(Base):
    __tablename__ = "lawyer_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_lawyer_profiles_user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )
    full_name = Column(String, nullable=False)
    license_number = Column(String, unique=True, nullable=False)
    bar_council = Column(String, nullable=False)
    bar_council_number = Column(String, unique=True, nullable=False)
    specialization = Column(String, nullable=True)
    city = Column(String, nullable=True)
    years_of_experience = Column(Integer, nullable=False, default=0, server_default=text("0"))
    consultation_fee = Column(Numeric(10, 2), nullable=True)
    languages = Column(JSON, nullable=False, default=list, server_default=text("'[]'"))
    office_address = Column(String, nullable=True)
    cnic = Column(String, unique=True, nullable=False)
    verification_status = Column(
        Enum(VerificationStatus),
        default=VerificationStatus.PENDING,
        nullable=False,
    )

    user = relationship("User", back_populates="lawyer_profile")

    @property
    def verified(self) -> bool:
        return self.verification_status == VerificationStatus.APPROVED


class LawyerAvailability(Base):
    __tablename__ = "lawyer_availabilities"
    __table_args__ = (
        CheckConstraint(
            "day_of_week >= 0 AND day_of_week <= 6",
            name="ck_lawyer_availability_day_of_week",
        ),
        CheckConstraint(
            "start_time < end_time",
            name="ck_lawyer_availability_time_range",
        ),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lawyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    lawyer = relationship("User", foreign_keys=[lawyer_id])


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint(
            "client_id <> lawyer_id",
            name="ck_appointment_distinct_client_lawyer",
        ),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    lawyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    appointment_date = Column(Date, nullable=False)
    appointment_time = Column(Time, nullable=False)
    consultation_type = Column(Enum(ConsultationType), nullable=False)
    notes = Column(String(2000), nullable=True)
    status = Column(
        Enum(AppointmentStatus),
        nullable=False,
        default=AppointmentStatus.PENDING,
        server_default=AppointmentStatus.PENDING.name,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
    )

    client = relationship("User", foreign_keys=[client_id])
    lawyer = relationship("User", foreign_keys=[lawyer_id])


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (
        CheckConstraint(
            "client_id <> lawyer_id",
            name="ck_cases_distinct_client_lawyer",
        ),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    lawyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(10000), nullable=False)
    case_type = Column(String(100), nullable=False)
    status = Column(
        Enum(CaseStatus),
        nullable=False,
        default=CaseStatus.OPEN,
        server_default=CaseStatus.OPEN.name,
        index=True,
    )
    priority = Column(
        Enum(CasePriority),
        nullable=False,
        default=CasePriority.MEDIUM,
        server_default=CasePriority.MEDIUM.name,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
    )

    client = relationship("User", foreign_keys=[client_id])
    lawyer = relationship("User", foreign_keys=[lawyer_id])
    notes = relationship(
        "CaseNote",
        back_populates="case",
        order_by="CaseNote.created_at",
    )
    status_history = relationship(
        "CaseStatusHistory",
        back_populates="case",
        order_by="CaseStatusHistory.created_at",
    )
    documents = relationship(
        "CaseDocument",
        back_populates="case",
        order_by="CaseDocument.uploaded_at",
    )


class CaseNote(Base):
    __tablename__ = "case_notes"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(Uuid(as_uuid=True), ForeignKey("cases.id"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    note = Column(String(10000), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
    )

    case = relationship("Case", back_populates="notes")
    author = relationship("User")


class CaseStatusHistory(Base):
    __tablename__ = "case_status_history"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(Uuid(as_uuid=True), ForeignKey("cases.id"), nullable=False, index=True)
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    previous_status = Column(Enum(CaseStatus), nullable=True)
    new_status = Column(Enum(CaseStatus), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
    )

    case = relationship("Case", back_populates="status_history")
    changed_by = relationship("User")


class CaseDocument(Base):
    __tablename__ = "case_documents"
    __table_args__ = (
        CheckConstraint(
            "file_size > 0 AND file_size <= 10485760",
            name="ck_case_documents_file_size",
        ),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("cases.id"),
        nullable=False,
        index=True,
    )
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_type = Column(Enum(DocumentType), nullable=False)
    file_name = Column(String(255), nullable=False)
    original_file_name = Column(String(255), nullable=False)
    file_type = Column(String(127), nullable=False)
    file_size = Column(Integer, nullable=False)
    storage_url = Column(String(2048), nullable=False)
    storage_public_id = Column(String(255), nullable=False, unique=True)
    description = Column(String(1000), nullable=True)
    uploaded_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
    )

    case = relationship("Case", back_populates="documents")
    uploader = relationship("User")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(String(1000), nullable=False)
    is_read = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
        index=True,
    )

    user = relationship("User", back_populates="notifications")


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True)
    token_family = Column(Uuid(as_uuid=True), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    replaced_by = Column(Uuid(as_uuid=True), ForeignKey("refresh_sessions.id"))
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
    )
