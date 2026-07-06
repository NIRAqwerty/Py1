from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
import uuid
from src.domain.entities import User, Source, Article, ArticleEmbedding, Publication, HumanReviewTask

class UserRepository(ABC):
    @abstractmethod
    async def save(self, user: User) -> None:
        pass

    @abstractmethod
    async def find_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        pass

    @abstractmethod
    async def find_by_username(self, username: str) -> Optional[User]:
        pass

class SourceRepository(ABC):
    @abstractmethod
    async def save(self, source: Source) -> None:
        pass

    @abstractmethod
    async def find_by_id(self, source_id: uuid.UUID) -> Optional[Source]:
        pass

    @abstractmethod
    async def find_all_active(self) -> List[Source]:
        pass

class ArticleRepository(ABC):
    @abstractmethod
    async def save(self, article: Article) -> None:
        pass

    @abstractmethod
    async def find_by_id(self, article_id: uuid.UUID) -> Optional[Article]:
        pass

    @abstractmethod
    async def find_by_source_and_external_id(self, source_id: uuid.UUID, external_id: str) -> Optional[Article]:
        pass

    @abstractmethod
    async def find_by_status(self, status: str) -> List[Article]:
        pass

class ArticleEmbeddingRepository(ABC):
    @abstractmethod
    async def save(self, embedding: ArticleEmbedding) -> None:
        pass

    @abstractmethod
    async def find_by_article_id(self, article_id: uuid.UUID) -> Optional[ArticleEmbedding]:
        pass

    @abstractmethod
    async def find_similar(self, query_embedding: List[float], threshold: float, limit: int = 5) -> List[Tuple[Article, float]]:
        """Returns articles matching semantic similarity with their score."""
        pass

class PublicationRepository(ABC):
    @abstractmethod
    async def save(self, publication: Publication) -> None:
        pass

    @abstractmethod
    async def find_by_id(self, publication_id: uuid.UUID) -> Optional[Publication]:
        pass

    @abstractmethod
    async def find_by_article_id(self, article_id: uuid.UUID) -> Optional[Publication]:
        pass

class HumanReviewTaskRepository(ABC):
    @abstractmethod
    async def save(self, task: HumanReviewTask) -> None:
        pass

    @abstractmethod
    async def find_by_id(self, task_id: uuid.UUID) -> Optional[HumanReviewTask]:
        pass

    @abstractmethod
    async def find_pending(self) -> List[HumanReviewTask]:
        pass
