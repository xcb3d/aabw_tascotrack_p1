"""secure backend and agentic RAG core

Revision ID: 0001_secure_core
Revises:
"""

from alembic import op

from apps.api.src.db.models import Base

revision = "0001_secure_core"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    op.execute("CREATE INDEX IF NOT EXISTS ix_chunks_embedding_hnsw ON chunks USING hnsw (embedding halfvec_cosine_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_chunks_content_fts ON chunks USING gin (to_tsvector('simple', content))")


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
