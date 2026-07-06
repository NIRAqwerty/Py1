"""initial

Revision ID: 0001
Revises: None
Create Date: 2026-07-07 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from src.config import settings

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector;"))

    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    op.create_table(
        'sources',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'articles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source_id', sa.UUID(), nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('media_urls', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_id', 'external_id', name='uq_source_external')
    )
    op.create_index(op.f('ix_articles_external_id'), 'articles', ['external_id'], unique=False)
    op.create_index(op.f('ix_articles_fetched_at'), 'articles', ['fetched_at'], unique=False)
    op.create_index(op.f('ix_articles_status'), 'articles', ['status'], unique=False)

    op.create_table(
        'article_embeddings',
        sa.Column('article_id', sa.UUID(), nullable=False),
        sa.Column('embedding', Vector(dim=settings.db.embedding_dimension), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('article_id')
    )

    op.create_table(
        'publications',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('article_id', sa.UUID(), nullable=False),
        sa.Column('final_text', sa.Text(), nullable=False),
        sa.Column('final_media_urls', sa.JSON(), nullable=False),
        sa.Column('telegram_message_id', sa.String(length=100), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'human_review_tasks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('article_id', sa.UUID(), nullable=False),
        sa.Column('reasons', sa.JSON(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('reviewer_id', sa.UUID(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('edited_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('human_review_tasks')
    op.drop_table('publications')
    op.drop_table('article_embeddings')
    op.drop_index(op.f('ix_articles_status'), table_name='articles')
    op.drop_index(op.f('ix_articles_fetched_at'), table_name='articles')
    op.drop_index(op.f('ix_articles_external_id'), table_name='articles')
    op.drop_table('articles')
    op.drop_table('sources')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_table('users')
