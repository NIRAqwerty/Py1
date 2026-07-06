from typing import Any
from src.domain.entities import Article
from src.domain.repositories import ArticleEmbeddingRepository
from src.infrastructure.checkers.base import BaseChecker, CheckResult
from src.config import settings
from src.infrastructure.logging import get_logger

logger = get_logger("AI")

class DuplicateChecker(BaseChecker):
    def __init__(self, ai_orchestrator: Any, embedding_repo: ArticleEmbeddingRepository) -> None:
        super().__init__(ai_orchestrator)
        self.embedding_repo = embedding_repo

    async def check(self, article: Article) -> CheckResult:
        try:
            # 1. Compute embedding vector
            embedding_vector = await self.ai.get_embeddings(article.raw_text)
            
            # 2. Search for similar articles in DB
            similar_articles = await self.embedding_repo.find_similar(
                query_embedding=embedding_vector,
                threshold=settings.thresholds.duplicate_cosine,
                limit=1
            )
            
            if similar_articles:
                matched_article, similarity = similar_articles[0]
                if matched_article.id != article.id and matched_article.external_id != article.external_id:
                    logger.info(
                        "Semantic duplicate detected",
                        article_id=article.id,
                        duplicate_of=matched_article.id,
                        similarity=similarity,
                    )
                    return CheckResult(
                        passed=False,
                        confidence_score=similarity,
                        reason=f"Semantic duplicate of article '{matched_article.id}' (similarity: {similarity:.2f})"
                    )

            return CheckResult(passed=True, confidence_score=1.0)
        except Exception as e:
            logger.error("DuplicateChecker failed", error=str(e), article_id=article.id)
            return CheckResult(passed=True, confidence_score=0.0, reason=f"Checker failed: {str(e)}")


