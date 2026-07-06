from dataclasses import dataclass, field
from datetime import datetime
import uuid
from typing import List, Optional, Dict, Any

@dataclass
class User:
    id: uuid.UUID
    username: str
    hashed_password: str
    role: str  # "ADMIN", "OPERATOR"
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class Source:
    id: uuid.UUID
    name: str
    type: str  # "TELEGRAM", "RSS", etc.
    config: Dict[str, Any] = field(default_factory=dict)
    status: str = "ACTIVE"  # "ACTIVE", "INACTIVE"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class Article:
    id: uuid.UUID
    source_id: uuid.UUID
    external_id: str
    raw_text: str
    media_urls: List[str] = field(default_factory=list)
    status: str = "PENDING"  # "PENDING", "PROCESSING", "DUPLICATE", "FILTERED", "REJECTED", "REVIEW", "READY", "PUBLISHED"
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    title: Optional[str] = None

@dataclass
class ArticleEmbedding:
    article_id: uuid.UUID
    embedding: List[float]
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class Publication:
    id: uuid.UUID
    article_id: uuid.UUID
    final_text: str
    final_media_urls: List[str] = field(default_factory=list)
    telegram_message_id: Optional[str] = None
    published_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class HumanReviewTask:
    id: uuid.UUID
    article_id: uuid.UUID
    reasons: List[str]
    confidence_score: float
    status: str = "PENDING"  # "PENDING", "APPROVED", "REJECTED", "EDITED"
    reviewer_id: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    edited_text: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
