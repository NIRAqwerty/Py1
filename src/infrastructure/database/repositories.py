import uuid
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.entities import User, Source, Article, ArticleEmbedding, Publication, HumanReviewTask
from src.domain.repositories import (
    UserRepository,
    SourceRepository,
    ArticleRepository,
    ArticleEmbeddingRepository,
    PublicationRepository,
    HumanReviewTaskRepository,
)
from src.infrastructure.database.models import (
    UserModel,
    SourceModel,
    ArticleModel,
    ArticleEmbeddingModel,
    PublicationModel,
    HumanReviewTaskModel,
)

# Mappers
def to_user_entity(m: UserModel) -> User:
    return User(
        id=m.id,
        username=m.username,
        hashed_password=m.hashed_password,
        role=m.role,
        created_at=m.created_at,
    )

def to_source_entity(m: SourceModel) -> Source:
    return Source(
        id=m.id,
        name=m.name,
        type=m.type,
        config=m.config,
        status=m.status,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )

def to_article_entity(m: ArticleModel) -> Article:
    return Article(
        id=m.id,
        source_id=m.source_id,
        external_id=m.external_id,
        title=m.title,
        raw_text=m.raw_text,
        media_urls=m.media_urls.get("urls", []),
        status=m.status,
        fetched_at=m.fetched_at,
    )

def to_embedding_entity(m: ArticleEmbeddingModel) -> ArticleEmbedding:
    return ArticleEmbedding(
        article_id=m.article_id,
        embedding=m.embedding,
        created_at=m.created_at,
    )

def to_publication_entity(m: PublicationModel) -> Publication:
    return Publication(
        id=m.id,
        article_id=m.article_id,
        final_text=m.final_text,
        final_media_urls=m.final_media_urls.get("urls", []),
        telegram_message_id=m.telegram_message_id,
        published_at=m.published_at,
    )

def to_review_task_entity(m: HumanReviewTaskModel) -> HumanReviewTask:
    return HumanReviewTask(
        id=m.id,
        article_id=m.article_id,
        reasons=m.reasons.get("reasons", []),
        confidence_score=m.confidence_score,
        status=m.status,
        reviewer_id=m.reviewer_id,
        reviewed_at=m.reviewed_at,
        edited_text=m.edited_text,
        created_at=m.created_at,
    )


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, user: User) -> None:
        stmt = select(UserModel).filter(UserModel.id == user.id)
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        if not model:
            model = UserModel(
                id=user.id,
                username=user.username,
                hashed_password=user.hashed_password,
                role=user.role,
                created_at=user.created_at,
            )
            self.session.add(model)
        else:
            model.username = user.username
            model.hashed_password = user.hashed_password
            model.role = user.role

    async def find_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        stmt = select(UserModel).filter(UserModel.id == user_id)
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        return to_user_entity(model) if model else None

    async def find_by_username(self, username: str) -> Optional[User]:
        stmt = select(UserModel).filter(UserModel.username == username)
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        return to_user_entity(model) if model else None


class SqlAlchemySourceRepository(SourceRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, source: Source) -> None:
        stmt = select(SourceModel).filter(SourceModel.id == source.id)
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        if not model:
            model = SourceModel(
                id=source.id,
                name=source.name,
                type=source.type,
                config=source.config,
                status=source.status,
                created_at=source.created_at,
                updated_at=source.updated_at,
            )
            self.session.add(model)
        else:
            model.name = source.name
            model.type = source.type
            model.config = source.config
            model.status = source.status
            model.updated_at = source.updated_at

    async def find_by_id(self, source_id: uuid.UUID) -> Optional[Source]:
        stmt = select(SourceModel).filter(SourceModel.id == source_id)
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        return to_source_entity(model) if model else None

    async def find_all_active(self) -> List[Source]:
        stmt = select(SourceModel).filter(SourceModel.status == "ACTIVE")
        res = await self.session.execute(stmt)
        return [to_source_entity(m) for m in res.scalars().all()]


class SqlAlchemyArticleRepository(ArticleRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, article: Article) -> None:
        stmt = select(ArticleModel).filter(ArticleModel.id == article.id)
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        if not model:
            model = ArticleModel(
                id=article.id,
                source_id=article.source_id,
                external_id=article.external_id,
                title=article.title,
                raw_text=article.raw_text,
                media_urls={"urls": article.media_urls},
                status=article.status,
                fetched_at=article.fetched_at,
            )
            self.session.add(model)
        else:
            model.title = article.title
            model.raw_text = article.raw_text
            model.media_urls = {"urls": article.media_urls}
            model.status = article.status

    async def find_by_id(self, article_id: uuid.UUID) -> Optional[Article]:
        stmt = select(ArticleModel).filter(ArticleModel.id == article_id)
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        return to_article_entity(model) if model else None

    async def find_by_source_and_external_id(self, source_id: uuid.UUID, external_id: str) -> Optional[Article]:
        stmt = select(ArticleModel).filter(
            and_(ArticleModel.source_id == source_id, ArticleModel.external_id == external_id)
        )
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        return to_article_entity(model) if model else None

    async def find_by_status(self, status: str) -> List[Article]:
        stmt = select(ArticleModel).filter(ArticleModel.status == status)
        res = await self.session.execute(stmt)
        return [to_article_entity(m) for m in res.scalars().all()]


class SqlAlchemyArticleEmbeddingRepository(ArticleEmbeddingRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, embedding: ArticleEmbedding) -> None:
        stmt = select(ArticleEmbeddingModel).filter(ArticleEmbeddingModel.article_id == embedding.article_id)
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        if not model:
            model = ArticleEmbeddingModel(
                article_id=embedding.article_id,
                embedding=embedding.embedding,
                created_at=embedding.created_at,
            )
            self.session.add(model)
        else:
            model.embedding = embedding.embedding

    async def find_by_article_id(self, article_id: uuid.UUID) -> Optional[ArticleEmbedding]:
        stmt = select(ArticleEmbeddingModel).filter(ArticleEmbeddingModel.article_id == article_id)
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        return to_embedding_entity(model) if model else None

    async def find_similar(self, query_embedding: List[float], threshold: float, limit: int = 5) -> List[Tuple[Article, float]]:
        # Cosine distance = 1 - cosine similarity
        distance = ArticleEmbeddingModel.embedding.cosine_distance(query_embedding)
        # Cosine similarity threshold means distance < (1.0 - threshold)
        stmt = (
            select(ArticleModel, distance)
            .join(ArticleEmbeddingModel, ArticleModel.id == ArticleEmbeddingModel.article_id)
            .filter(distance < (1.0 - threshold))
            .order_by(distance)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        results = []
        for row in res.all():
            article_model, dist_val = row
            similarity = 1.0 - float(dist_val)
            results.append((to_article_entity(article_model), similarity))
        return results


class SqlAlchemyPublicationRepository(PublicationRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, publication: Publication) -> None:
        stmt = select(PublicationModel).filter(PublicationModel.id == publication.id)
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        if not model:
            model = PublicationModel(
                id=publication.id,
                article_id=publication.article_id,
                final_text=publication.final_text,
                final_media_urls={"urls": publication.final_media_urls},
                telegram_message_id=publication.telegram_message_id,
                published_at=publication.published_at,
            )
            self.session.add(model)
        else:
            model.final_text = publication.final_text
            model.final_media_urls = {"urls": publication.final_media_urls}
            model.telegram_message_id = publication.telegram_message_id

    async def find_by_id(self, publication_id: uuid.UUID) -> Optional[Publication]:
        stmt = select(PublicationModel).filter(PublicationModel.id == publication_id)
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        return to_publication_entity(model) if model else None

    async def find_by_article_id(self, article_id: uuid.UUID) -> Optional[Publication]:
        stmt = select(PublicationModel).filter(PublicationModel.article_id == article_id)
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        return to_publication_entity(model) if model else None


class SqlAlchemyHumanReviewTaskRepository(HumanReviewTaskRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, task: HumanReviewTask) -> None:
        stmt = select(HumanReviewTaskModel).filter(HumanReviewTaskModel.id == task.id)
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        if not model:
            model = HumanReviewTaskModel(
                id=task.id,
                article_id=task.article_id,
                reasons={"reasons": task.reasons},
                confidence_score=task.confidence_score,
                status=task.status,
                reviewer_id=task.reviewer_id,
                reviewed_at=task.reviewed_at,
                edited_text=task.edited_text,
                created_at=task.created_at,
            )
            self.session.add(model)
        else:
            model.status = task.status
            model.reasons = {"reasons": task.reasons}
            model.confidence_score = task.confidence_score
            model.reviewer_id = task.reviewer_id
            model.reviewed_at = task.reviewed_at
            model.edited_text = task.edited_text

    async def find_by_id(self, task_id: uuid.UUID) -> Optional[HumanReviewTask]:
        stmt = select(HumanReviewTaskModel).filter(HumanReviewTaskModel.id == task_id)
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        return to_review_task_entity(model) if model else None

    async def find_pending(self) -> List[HumanReviewTask]:
        stmt = select(HumanReviewTaskModel).filter(HumanReviewTaskModel.status == "PENDING").order_by(HumanReviewTaskModel.created_at.desc())
        res = await self.session.execute(stmt)
        return [to_review_task_entity(m) for m in res.scalars().all()]
