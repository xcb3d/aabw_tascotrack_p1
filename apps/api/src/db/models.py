from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import HALFVEC
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    BigInteger,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
    func
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Department(Base):
    """Bảng phòng ban (departments)."""
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    department_en: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    department_vi: Mapped[str] = mapped_column(String(128), nullable=False)
    knowledge_space: Mapped[str] = mapped_column(String(128), nullable=False)


class Role(Base):
    """Bảng vai trò (roles)."""
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_en: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    role_vi: Mapped[str] = mapped_column(String(64), nullable=False)
    company_knowledge: Mapped[str] = mapped_column(String(32), nullable=False)
    department_knowledge: Mapped[str] = mapped_column(String(32), nullable=False)
    executive_knowledge: Mapped[str] = mapped_column(String(32), nullable=False)


class Permission(Base):
    """Bảng phân quyền tĩnh tham chiếu (permissions)."""
    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    classification: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    employee: Mapped[str] = mapped_column(String(32), nullable=False)
    manager: Mapped[str] = mapped_column(String(32), nullable=False)
    director: Mapped[str] = mapped_column(String(32), nullable=False)
    executive: Mapped[str] = mapped_column(String(32), nullable=False)
    rule_description_vi: Mapped[str] = mapped_column(Text, nullable=False)


class User(Base):
    """Bảng nhân viên giả lập (users)."""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    department_id: Mapped[str] = mapped_column(
        String(32), 
        ForeignKey("departments.department_id", onupdate="CASCADE"), 
        nullable=False, 
        index=True
    )
    role_en: Mapped[str] = mapped_column(
        String(64), 
        ForeignKey("roles.role_en", onupdate="CASCADE"), 
        nullable=False, 
        index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="Active")
    password: Mapped[str] = mapped_column(String(255), nullable=False)


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    stable_id: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    department_id: Mapped[str] = mapped_column(String(128), nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    allowed_access: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (UniqueConstraint("tenant_id", "stable_id", name="uq_document_tenant_stable"),)


class DocumentVersion(Base, TimestampMixin):
    __tablename__ = "document_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    acl_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    classification_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    raw_content: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    quarantine_reasons: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    qa_metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    steward_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_document_version_number"),
        UniqueConstraint("document_id", "content_hash", name="uq_document_content_hash"),
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    stable_id: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    heading_path: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    section: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    department_id: Mapped[str] = mapped_column(String(128), nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    allowed_access: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    annotations: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    embedding = mapped_column(HALFVEC(512), nullable=True)


class PublicEvaluationCase(Base):
    """Các ca đánh giá kiểm thử chất lượng RAG (public_evaluation_cases)."""
    __tablename__ = "public_evaluation_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str] = mapped_column(
        String(32), 
        ForeignKey("users.user_id", onupdate="CASCADE"), 
        nullable=False, 
        index=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_permission: Mapped[str] = mapped_column(String(32), nullable=False)
    expected_document_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    answer_type: Mapped[str] = mapped_column(String(32), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(32), nullable=False)


class Session(Base, TimestampMixin):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    locale: Mapped[str] = mapped_column(String(32), nullable=False, default="vi-VN")
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)


class Message(Base):
    """Các tin nhắn trong phiên chat (messages)."""
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("sessions.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    client_request_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("role IN ('USER', 'ASSISTANT', 'SYSTEM')", name="chk_messages_role"),
    )


class AgentRun(Base, TimestampMixin):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    client_request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    locale: Mapped[str] = mapped_column(String(32), nullable=False, default="vi-VN")
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="auto")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="RECEIVED", index=True)
    route: Mapped[str | None] = mapped_column(String(64), nullable=True)
    purpose: Mapped[str | None] = mapped_column(String(64), nullable=True)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    claims: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    citations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    permission_decision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(32), nullable=True)
    degraded_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    budget: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cancelled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "owner_id", "client_request_id", name="uq_run_client_request"),
    )


class RunEvent(Base):
    __tablename__ = "run_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvidenceManifest(Base):
    __tablename__ = "evidence_manifests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    evidence_id: Mapped[str] = mapped_column(String(180), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str] = mapped_column(String(180), nullable=False)
    source_version: Mapped[str] = mapped_column(String(180), nullable=False)
    span_locator: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    span_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    policy_decision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    acl_scope_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose: Mapped[str] = mapped_column(String(64), nullable=False)
    sanitized_content: Mapped[str] = mapped_column(Text, nullable=False)
    integrity_tag: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("run_id", "evidence_id", name="uq_manifest_run_evidence"),)


class Action(Base, TimestampMixin):
    __tablename__ = "actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    action_type: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="WAITING_CONFIRMATION")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    confirmation_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_decision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False)
    operation: Mapped[str] = mapped_column(String(128), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "owner_id", "operation", "key_hash", name="uq_idempotency_scope"),
    )


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    queue: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    policy_decision_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditChainState(Base):
    """Bảng lưu trạng thái chuỗi kiểm toán (audit_chain_state)."""
    __tablename__ = "audit_chain_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    last_sequence_no: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_entry_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        CheckConstraint("id = 1", name="chk_audit_chain_state_single_row"),
    )


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvaluationRun(Base, TimestampMixin):
    __tablename__ = "evaluation_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(180), nullable=False)
    candidate_config_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    baseline_config_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
