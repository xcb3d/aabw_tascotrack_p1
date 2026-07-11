"""ingestion QA and steward review metadata

Revision ID: 0002_ingestion_qa
Revises: 0001_secure_core
"""

from alembic import op

revision = "0002_ingestion_qa"
down_revision = "0001_secure_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE document_versions ADD COLUMN IF NOT EXISTS qa_metrics jsonb NOT NULL DEFAULT '{}'::jsonb")
    op.execute("ALTER TABLE document_versions ADD COLUMN IF NOT EXISTS steward_review_required boolean NOT NULL DEFAULT false")


def downgrade() -> None:
    op.execute("ALTER TABLE document_versions DROP COLUMN IF EXISTS steward_review_required")
    op.execute("ALTER TABLE document_versions DROP COLUMN IF EXISTS qa_metrics")
