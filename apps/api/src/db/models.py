from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    String,
    Text,
    func,
    Integer,
    BigInteger,
    ForeignKey,
    Computed,
    UniqueConstraint,
    CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for API-owned tables."""
    pass


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


class Document(Base):
    """Tài liệu tri thức và siêu dữ liệu (documents)."""
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    department_id: Mapped[str] = mapped_column(
        String(32), 
        ForeignKey("departments.department_id", onupdate="CASCADE"), 
        nullable=False, 
        index=True
    )
    classification: Mapped[str] = mapped_column(
        String(32), 
        ForeignKey("permissions.classification", onupdate="CASCADE"), 
        nullable=False, 
        index=True
    )
    owner: Mapped[str] = mapped_column(String(128), nullable=False)
    
    # Cột tự sinh đồng bộ tĩnh theo classification
    allowed_access: Mapped[str] = mapped_column(
        String(32),
        Computed(
            "CASE classification "
            "WHEN 'Public' THEN 'All' "
            "WHEN 'Internal' THEN 'All Employees' "
            "WHEN 'Confidential' THEN 'Own Department' "
            "WHEN 'Restricted' THEN 'Executive Only' "
            "ELSE 'Executive Only' END",
            persisted=True
        ),
        nullable=False
    )
    
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="vi")
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="Active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Chunk(Base):
    """Phân mảnh văn bản (chunks)."""
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("documents.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),
    )


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


class Session(Base):
    """Phiên hội thoại (sessions)."""
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="SET NULL"), 
        nullable=True, 
        index=True
    )
    principal_type: Mapped[str] = mapped_column(String(16), nullable=False, default="ANONYMOUS")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    locale: Mapped[str] = mapped_column(String(32), nullable=False, default="vi-VN")
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "(principal_type = 'ANONYMOUS' AND user_id IS NULL) OR (principal_type = 'USER' AND user_id IS NOT NULL)",
            name="chk_sessions_principal"
        ),
        CheckConstraint("status IN ('ACTIVE', 'EXPIRED', 'REVOKED')", name="chk_sessions_status"),
    )


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


class AgentRun(Base):
    """Phiên chạy của Agent State Machine (agent_runs)."""
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("sessions.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    input_message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("messages.id", ondelete="CASCADE"), 
        unique=True, 
        nullable=False
    )
    trace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="RECEIVED")
    route: Mapped[str | None] = mapped_column(String(64), nullable=True)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    claims: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    citations: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Action(Base):
    """Các hành động cần xác nhận (actions)."""
    __tablename__ = "actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("agent_runs.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    action_type: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="DRAFT")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    confirmation_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'WAITING_CONFIRMATION', 'CONFIRMED', 'EXECUTING', 'COMPLETED', 'REJECTED', 'EXPIRED', 'FAILED')",
            name="chk_actions_status"
        ),
    )


class AuditEvent(Base):
    """Nhật ký hệ thống chống sửa đổi (audit_events)."""
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sequence_no: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("agent_runs.id", ondelete="SET NULL"), 
        nullable=True, 
        index=True
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="SET NULL"), 
        nullable=True, 
        index=True
    )
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entry_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
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
