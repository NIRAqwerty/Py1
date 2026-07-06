import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    ForeignKey,
    String,
    Text,
    DateTime,
    Float,
    JSON,
    UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from src.config import settings

class Base(DeclarativeBase):
    pass

class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="OPERATOR", nullable=False)  # "ADMIN", "OPERATOR"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    review_tasks: Mapped[List["HumanReviewTaskModel"]] = relationship(
        back_populates="reviewer", cascade="all, delete-orphan"
    )

class SourceModel(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # "TELEGRAM", "RSS", etc.
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)  # "ACTIVE", "INACTIVE"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    articles: Mapped[List["ArticleModel"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )

class ArticleModel(Base):
    __tablename__ = "articles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    media_urls: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False, index=True)
    # Statuses: "PENDING", "PROCESSING", "DUPLICATE", "FILTERED", "REJECTED", "REVIEW", "READY", "PUBLISHED"
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_source_external"),
    )

    source: Mapped["SourceModel"] = relationship(back_populates="articles")
    embedding_relation: Mapped[Optional["ArticleEmbeddingModel"]] = relationship(
        back_populates="article", cascade="all, delete-orphan", uselist=False
    )
    publication: Mapped[Optional["PublicationModel"]] = relationship(
        back_populates="article", cascade="all, delete-orphan", uselist=False
    )
    review_task: Mapped[Optional["HumanReviewTaskModel"]] = relationship(
        back_populates="article", cascade="all, delete-orphan", uselist=False
    )

class ArticleEmbeddingModel(Base):
    __tablename__ = "article_embeddings"

    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True
    )
    # The dimension is loaded dynamically from configuration settings (default 1536)
    embedding: Mapped[List[float]] = mapped_column(Vector(settings.db.embedding_dimension), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    article: Mapped["ArticleModel"] = relationship(back_populates="embedding_relation")

class PublicationModel(Base):
    __tablename__ = "publications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    article_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    final_text: Mapped[str] = mapped_column(Text, nullable=False)
    final_media_urls: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    telegram_message_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    article: Mapped["ArticleModel"] = relationship(back_populates="publication")

class HumanReviewTaskModel(Base):
    __tablename__ = "human_review_tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    article_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    reasons: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)  # "PENDING", "APPROVED", "REJECTED", "EDITED"
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    edited_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    article: Mapped["ArticleModel"] = relationship(back_populates="review_task")
    reviewer: Mapped[Optional["UserModel"]] = relationship(back_populates="review_tasks")
