"""init_rag_schema_and_triggers

Revision ID: 4ca8265f06fd
Revises: 
Create Date: 2026-07-12 00:10:08.560553

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '4ca8265f06fd'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Đảm bảo extension pgvector được cài đặt
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 1. Tạo các bảng tĩnh tham chiếu
    op.create_table(
        'departments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('department_id', sa.String(length=32), nullable=False),
        sa.Column('department_en', sa.String(length=128), nullable=False),
        sa.Column('department_vi', sa.String(length=128), nullable=False),
        sa.Column('knowledge_space', sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('department_id'),
        sa.UniqueConstraint('department_en')
    )
    
    op.create_table(
        'roles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('role_en', sa.String(length=64), nullable=False),
        sa.Column('role_vi', sa.String(length=64), nullable=False),
        sa.Column('company_knowledge', sa.String(length=32), nullable=False),
        sa.Column('department_knowledge', sa.String(length=32), nullable=False),
        sa.Column('executive_knowledge', sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role_en')
    )

    op.create_table(
        'permissions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('classification', sa.String(length=32), nullable=False),
        sa.Column('employee', sa.String(length=32), nullable=False),
        sa.Column('manager', sa.String(length=32), nullable=False),
        sa.Column('director', sa.String(length=32), nullable=False),
        sa.Column('executive', sa.String(length=32), nullable=False),
        sa.Column('rule_description_vi', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('classification')
    )

    # 2. Tạo bảng Users
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.String(length=32), nullable=False),
        sa.Column('full_name', sa.String(length=200), nullable=False),
        sa.Column('department_id', sa.String(length=32), nullable=False),
        sa.Column('role_en', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='Active'),
        sa.Column('password', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
        sa.UniqueConstraint('email'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.department_id'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['role_en'], ['roles.role_en'], onupdate='CASCADE')
    )
    op.create_index('ix_users_department_id', 'users', ['department_id'])
    op.create_index('ix_users_role_en', 'users', ['role_en'])

    # 3. Tạo bảng Documents kèm cột tự sinh allowed_access
    op.create_table(
        'documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.String(length=32), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('department_id', sa.String(length=32), nullable=False),
        sa.Column('classification', sa.String(length=32), nullable=False),
        sa.Column('owner', sa.String(length=128), nullable=False),
        sa.Column(
            'allowed_access',
            sa.String(length=32),
            sa.Computed(
                "CASE classification "
                "WHEN 'Public' THEN 'All' "
                "WHEN 'Internal' THEN 'All Employees' "
                "WHEN 'Confidential' THEN 'Own Department' "
                "WHEN 'Restricted' THEN 'Executive Only' "
                "ELSE 'Executive Only' END",
                persisted=True
            ),
            nullable=False
        ),
        sa.Column('last_updated', sa.Date(), nullable=False),
        sa.Column('tags', sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column('language', sa.String(length=16), nullable=False, server_default='vi'),
        sa.Column('word_count', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='Active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.department_id'], onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['classification'], ['permissions.classification'], onupdate='CASCADE')
    )
    op.create_index('ix_documents_department_id', 'documents', ['department_id'])
    op.create_index('ix_documents_classification', 'documents', ['classification'])

    # 4. Tạo bảng Chunks
    op.create_table(
        'chunks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('section', sa.String(length=256), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('document_id', 'chunk_index', name='uq_document_chunk_index')
    )
    op.create_index('ix_chunks_document_id', 'chunks', ['document_id'])

    # 5. Tạo bảng PublicEvaluationCase
    op.create_table(
        'public_evaluation_cases',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('question_id', sa.String(length=32), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.String(length=32), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('expected_permission', sa.String(length=32), nullable=False),
        sa.Column('expected_document_ids', sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column('answer_type', sa.String(length=32), nullable=False),
        sa.Column('difficulty', sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('question_id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], onupdate='CASCADE')
    )
    op.create_index('ix_public_evaluation_cases_user_id', 'public_evaluation_cases', ['user_id'])

    # 6. Tạo bảng Sessions
    op.create_table(
        'sessions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('principal_type', sa.String(length=16), nullable=False, server_default='ANONYMOUS'),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='ACTIVE'),
        sa.Column('locale', sa.String(length=32), nullable=False, server_default='vi-VN'),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.CheckConstraint(
            "(principal_type = 'ANONYMOUS' AND user_id IS NULL) OR (principal_type = 'USER' AND user_id IS NOT NULL)",
            name='chk_sessions_principal'
        ),
        sa.CheckConstraint("status IN ('ACTIVE', 'EXPIRED', 'REVOKED')", name='chk_sessions_status')
    )
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'])

    # 7. Tạo bảng Messages
    op.create_table(
        'messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=16), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('client_request_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('client_request_id'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.CheckConstraint("role IN ('USER', 'ASSISTANT', 'SYSTEM')", name='chk_messages_role')
    )
    op.create_index('ix_messages_session_id', 'messages', ['session_id'])

    # 8. Tạo bảng AgentRuns
    op.create_table(
        'agent_runs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('input_message_id', sa.UUID(), nullable=False),
        sa.Column('trace_id', sa.UUID(), nullable=False),
        sa.Column('idempotency_key', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=64), nullable=False, server_default='RECEIVED'),
        sa.Column('route', sa.String(length=64), nullable=True),
        sa.Column('answer', sa.Text(), nullable=True),
        sa.Column('claims', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('citations', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('input_message_id'),
        sa.UniqueConstraint('idempotency_key'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['input_message_id'], ['messages.id'], ondelete='CASCADE')
    )
    op.create_index('ix_agent_runs_session_id', 'agent_runs', ['session_id'])

    # 9. Tạo bảng Actions
    op.create_table(
        'actions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('agent_run_id', sa.UUID(), nullable=False),
        sa.Column('action_type', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=64), nullable=False, server_default='DRAFT'),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('parameters', sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column('confirmation_token_hash', sa.String(length=64), nullable=True),
        sa.Column('idempotency_key', sa.String(length=128), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('confirmation_token_hash'),
        sa.UniqueConstraint('idempotency_key'),
        sa.ForeignKeyConstraint(['agent_run_id'], ['agent_runs.id'], ondelete='CASCADE'),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'WAITING_CONFIRMATION', 'CONFIRMED', 'EXECUTING', 'COMPLETED', 'REJECTED', 'EXPIRED', 'FAILED')",
            name='chk_actions_status'
        )
    )
    op.create_index('ix_actions_agent_run_id', 'actions', ['agent_run_id'])

    # 10. Tạo bảng AuditEvents
    op.create_table(
        'audit_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('sequence_no', sa.BigInteger(), nullable=True),
        sa.Column('run_id', sa.UUID(), nullable=True),
        sa.Column('event_type', sa.String(length=128), nullable=False),
        sa.Column('actor_user_id', sa.UUID(), nullable=True),
        sa.Column('request_id', sa.String(length=64), nullable=True),
        sa.Column('payload', sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column('prev_hash', sa.String(length=64), nullable=True),
        sa.Column('entry_hash', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sequence_no'),
        sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL')
    )
    op.create_index('ix_audit_events_run_id', 'audit_events', ['run_id'])
    op.create_index('ix_audit_events_actor_user_id', 'audit_events', ['actor_user_id'])
    op.create_index('ix_audit_events_request_id', 'audit_events', ['request_id'])

    # 11. Tạo bảng AuditChainState
    op.create_table(
        'audit_chain_state',
        sa.Column('id', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('last_sequence_no', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('last_entry_hash', sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('id = 1', name='chk_audit_chain_state_single_row')
    )
    # Khởi tạo bản ghi trạng thái duy nhất cho ledger
    op.execute("INSERT INTO audit_chain_state (id, last_sequence_no, last_entry_hash) VALUES (1, 0, NULL)")

    # 12. Triển khai trigger chống giả mạo Hash-Chain trên audit_events
    op.execute("""
    CREATE OR REPLACE FUNCTION process_audit_event_hash()
    RETURNS TRIGGER AS $$
    DECLARE
        v_prev_hash VARCHAR(64);
        v_seq_no BIGINT;
        v_entry_hash VARCHAR(64);
        v_canonical_data TEXT;
    BEGIN
        -- Khóa bản ghi trạng thái để tuần tự hóa việc tạo chuỗi hash
        SELECT last_sequence_no, last_entry_hash
        INTO v_seq_no, v_prev_hash
        FROM audit_chain_state
        WHERE id = 1
        FOR UPDATE;

        -- Tăng số thứ tự
        v_seq_no := v_seq_no + 1;

        -- Gán thời gian cố định
        NEW.created_at := COALESCE(NEW.created_at, NOW());

        -- Tạo chuỗi băm chuẩn hóa (Canonical String)
        v_canonical_data := COALESCE(v_prev_hash, '') || '|' ||
                            v_seq_no::TEXT || '|' ||
                            COALESCE(NEW.run_id::TEXT, '') || '|' ||
                            NEW.event_type || '|' ||
                            COALESCE(NEW.actor_user_id::TEXT, '') || '|' ||
                            COALESCE(NEW.request_id, '') || '|' ||
                            NEW.payload::TEXT || '|' ||
                            NEW.created_at::TEXT;

        -- Tính toán Hash SHA-256 mã hóa thập lục phân
        v_entry_hash := encode(sha256(v_canonical_data::bytea), 'hex');

        -- Cập nhật trạng thái
        UPDATE audit_chain_state
        SET last_sequence_no = v_seq_no,
            last_entry_hash = v_entry_hash
        WHERE id = 1;

        -- Gán các giá trị sinh tự động vào bản ghi đang chèn
        NEW.sequence_no := v_seq_no;
        NEW.prev_hash := v_prev_hash;
        NEW.entry_hash := v_entry_hash;

        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_audit_events_hash_chain
    BEFORE INSERT ON audit_events
    FOR EACH ROW
    EXECUTE FUNCTION process_audit_event_hash();
    """)


def downgrade() -> None:
    # Gỡ bỏ trigger và hàm băm
    op.execute("DROP TRIGGER IF EXISTS trg_audit_events_hash_chain ON audit_events;")
    op.execute("DROP FUNCTION IF EXISTS process_audit_event_hash();")

    # Xóa các bảng theo thứ tự đảo ngược
    op.drop_table('audit_chain_state')
    op.drop_table('audit_events')
    op.drop_table('actions')
    op.drop_table('agent_runs')
    op.drop_table('messages')
    op.drop_table('sessions')
    op.drop_table('public_evaluation_cases')
    op.drop_table('chunks')
    op.drop_table('documents')
    op.drop_table('users')
    op.drop_table('permissions')
    op.drop_table('roles')
    op.drop_table('departments')
