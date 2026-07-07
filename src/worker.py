import asyncio
import uuid
from datetime import datetime
from typing import List, Optional, Any
from sqlalchemy import select
from arq import cron
from src.config import settings
from src.infrastructure.database.session import async_session_maker
from src.infrastructure.database.models import HumanReviewTaskModel, PublicationModel
from src.infrastructure.database.repositories import (
    SqlAlchemySourceRepository,
    SqlAlchemyArticleRepository,
    SqlAlchemyArticleEmbeddingRepository,
    SqlAlchemyHumanReviewTaskRepository,
    SqlAlchemyPublicationRepository,
)
from src.infrastructure.plugins.manager import PluginManager
from src.infrastructure.ai.orchestrator import AIOrchestrator
from src.infrastructure.checkers.ad_spam import AdSpamChecker
from src.infrastructure.checkers.duplicate import DuplicateChecker
from src.infrastructure.checkers.fact_check import FactChecker
from src.infrastructure.checkers.grammar_readability import GrammarReadabilityChecker
from src.infrastructure.checkers.toxicity_nsfw import ToxicityNsfwChecker
from src.infrastructure.checkers.image_quality import ImageQualityChecker
from src.infrastructure.image_pipeline.pipeline import ImagePipeline
from src.infrastructure.telegram.publisher import TelegramPublisher
from src.infrastructure.queue.arq_config import redis_settings, enqueue_job
from src.infrastructure.logging import get_logger
from src.domain.entities import ArticleEmbedding, HumanReviewTask, Publication

logger = get_logger("QUEUE")
plugin_manager = PluginManager()
ai_orchestrator = AIOrchestrator()
image_pipeline = ImagePipeline(ai_orchestrator)
telegram_publisher = TelegramPublisher()

async def fetch_sources_task(ctx: Any) -> None:
    logger.info("Executing fetch_sources_task")
    async with async_session_maker() as session:
        source_repo = SqlAlchemySourceRepository(session)
        article_repo = SqlAlchemyArticleRepository(session)
        
        active_sources = await source_repo.find_all_active()
        logger.info(f"Found {len(active_sources)} active sources to scrape")
        
        for source in active_sources:
            try:
                plugin = plugin_manager.get_plugin(source.type)
                articles = await plugin.fetch_latest(source, limit=5)
                logger.info(f"Fetched {len(articles)} posts from source", source_name=source.name)
                
                for article in articles:
                    existing = await article_repo.find_by_source_and_external_id(
                        source_id=source.id,
                        external_id=article.external_id
                    )
                    if not existing:
                        logger.info("Saving new article", external_id=article.external_id)
                        await article_repo.save(article)
                        await session.commit()
                        await enqueue_job("process_article_task", str(article.id))
                    else:
                        logger.debug("Article already exists, skipping", external_id=article.external_id)
            except Exception as e:
                logger.error("Error in fetch_sources_task for source", source_id=source.id, error=str(e))

async def process_article_task(ctx: Any, article_id: str) -> None:
    logger.info("Executing process_article_task", article_id=article_id)
    article_uuid = uuid.UUID(article_id)
    
    async with async_session_maker() as session:
        article_repo = SqlAlchemyArticleRepository(session)
        embedding_repo = SqlAlchemyArticleEmbeddingRepository(session)
        review_repo = SqlAlchemyHumanReviewTaskRepository(session)
        publication_repo = SqlAlchemyPublicationRepository(session)
        
        article = await article_repo.find_by_id(article_uuid)
        if not article:
            logger.error("Article not found in database", article_id=article_id)
            return
            
        article.status = "PROCESSING"
        await article_repo.save(article)
        await session.commit()

        ad_spam_checker = AdSpamChecker(ai_orchestrator)
        toxicity_checker = ToxicityNsfwChecker(ai_orchestrator)
        duplicate_checker = DuplicateChecker(ai_orchestrator, embedding_repo)
        fact_checker = FactChecker(ai_orchestrator)
        grammar_checker = GrammarReadabilityChecker(ai_orchestrator)
        image_quality_checker = ImageQualityChecker(ai_orchestrator)

        logger.info("Running quality checks for article", article_id=article_id)
        
        ad_result = await ad_spam_checker.check(article)
        if not ad_result.passed:
            logger.info("Article failed AdSpamCheck, filtering out", article_id=article_id, reason=ad_result.reason)
            article.status = "FILTERED"
            await article_repo.save(article)
            await session.commit()
            return

        tox_result = await toxicity_checker.check(article)
        if not tox_result.passed:
            logger.info("Article failed ToxicityCheck, filtering out", article_id=article_id, reason=tox_result.reason)
            article.status = "FILTERED"
            await article_repo.save(article)
            await session.commit()
            return

        dup_result = await duplicate_checker.check(article)
        if not dup_result.passed:
            logger.info("Article failed DuplicateCheck, setting duplicate status", article_id=article_id, reason=dup_result.reason)
            article.status = "DUPLICATE"
            await article_repo.save(article)
            await session.commit()
            return

        fact_result = await fact_checker.check(article)
        if not fact_result.passed:
            logger.info("Article failed FactCheck, rejecting", article_id=article_id, reason=fact_result.reason)
            article.status = "REJECTED"
            await article_repo.save(article)
            await session.commit()
            return

        grammar_result = await grammar_checker.check(article)
        if not grammar_result.passed:
            logger.info("Article failed GrammarCheck, rejecting", article_id=article_id, reason=grammar_result.reason)
            article.status = "REJECTED"
            await article_repo.save(article)
            await session.commit()
            return

        image_result = await image_quality_checker.check(article)
        image_passed = image_result.passed

        # Compute and persist embedding
        try:
            vector = await ai_orchestrator.get_embeddings(article.raw_text)
            art_emb = ArticleEmbedding(
                article_id=article.id,
                embedding=vector,
                created_at=datetime.utcnow()
            )
            await embedding_repo.save(art_emb)
            await session.commit()
        except Exception as e:
            logger.error("Failed to compute and save embedding", error=str(e), article_id=article_id)

        confidence = (fact_result.confidence_score + grammar_result.confidence_score) / 2.0
        
        reasons = []
        if confidence < settings.thresholds.human_review_confidence:
            reasons.append(f"Low AI confidence score ({confidence:.2f})")
        if not image_passed:
            reasons.append(f"Image quality issues: {image_result.reason}")

        if reasons:
            logger.info("Routing article to Human Review", article_id=article_id, reasons=reasons)
            article.status = "REVIEW"
            await article_repo.save(article)
            
            draft_text = ""
            try:
                draft_text = await ai_orchestrator.double_pass_rewrite(article.raw_text)
            except Exception as e:
                logger.error("Failed to generate draft rewrite for review", error=str(e))
                draft_text = article.raw_text
                
            review_task = HumanReviewTask(
                id=uuid.uuid4(),
                article_id=article.id,
                reasons=reasons,
                confidence_score=confidence,
                status="PENDING",
                edited_text=draft_text,
                created_at=datetime.utcnow()
            )
            await review_repo.save(review_task)
            await session.commit()
        else:
            logger.info("Article passed all thresholds. Auto-publishing.", article_id=article_id)
            article.status = "READY"
            await article_repo.save(article)
            
            try:
                rewritten_text = await ai_orchestrator.double_pass_rewrite(article.raw_text)
                final_images = await image_pipeline.process(article, rewritten_text)
                
                publication = Publication(
                    id=uuid.uuid4(),
                    article_id=article.id,
                    final_text=rewritten_text,
                    final_media_urls=final_images,
                    telegram_message_id=None,
                    published_at=datetime.utcnow()
                )
                await publication_repo.save(publication)
                await session.commit()
                
                await enqueue_job("publish_post_task", str(article.id))
            except Exception as e:
                logger.error("Failed in auto-publication preprocessing", error=str(e), article_id=article_id)
                article.status = "REVIEW"
                await article_repo.save(article)
                review_task = HumanReviewTask(
                    id=uuid.uuid4(),
                    article_id=article.id,
                    reasons=[f"Auto-publish preprocess failed: {str(e)}"],
                    confidence_score=confidence,
                    status="PENDING",
                    edited_text=article.raw_text,
                    created_at=datetime.utcnow()
                )
                await review_repo.save(review_task)
                await session.commit()

async def publish_post_task(ctx: Any, article_id: str) -> None:
    logger.info("Executing publish_post_task", article_id=article_id)
    article_uuid = uuid.UUID(article_id)
    
    async with async_session_maker() as session:
        article_repo = SqlAlchemyArticleRepository(session)
        publication_repo = SqlAlchemyPublicationRepository(session)
        
        article = await article_repo.find_by_id(article_uuid)
        if not article:
            logger.error("Article not found for publishing", article_id=article_id)
            return

        final_text = ""
        media_urls = []
        
        # Check if there is an approved review task
        stmt = select(HumanReviewTaskModel).filter(
            HumanReviewTaskModel.article_id == article_uuid
        ).order_by(HumanReviewTaskModel.created_at.desc())
        res = await session.execute(stmt)
        task_model = res.scalars().first()
        
        if task_model and task_model.status in ["APPROVED", "EDITED"]:
            final_text = task_model.edited_text or article.raw_text
            pub_model = await publication_repo.find_by_article_id(article_uuid)
            if pub_model:
                media_urls = pub_model.final_media_urls.get("urls", [])
            else:
                try:
                    media_urls = await image_pipeline.process(article, final_text)
                except Exception as e:
                    logger.error("Image pipeline failed for reviewed article, publishing text only", error=str(e))
        else:
            pub_model = await publication_repo.find_by_article_id(article_uuid)
            if pub_model:
                final_text = pub_model.final_text
                media_urls = pub_model.final_media_urls.get("urls", [])
            else:
                logger.error("No publication draft found for auto-publishing article", article_id=article_id)
                return

        try:
            msg_id = await telegram_publisher.publish(final_text, media_urls)
            
            pub_stmt = select(PublicationModel).filter(PublicationModel.article_id == article_uuid)
            pub_res = await session.execute(pub_stmt)
            publication = pub_res.scalar_one_or_none()
            
            if not publication:
                publication = PublicationModel(
                    id=uuid.uuid4(),
                    article_id=article_uuid,
                    final_text=final_text,
                    final_media_urls={"urls": media_urls},
                    telegram_message_id=msg_id,
                    published_at=datetime.utcnow()
                )
                session.add(publication)
            else:
                publication.telegram_message_id = msg_id
                publication.published_at = datetime.utcnow()
                
            article.status = "PUBLISHED"
            await article_repo.save(article)
            await session.commit()
            logger.info("Successfully completed publish_post_task", article_id=article_id, telegram_msg_id=msg_id)
        except Exception as e:
            logger.error("Failed to publish post to telegram", error=str(e), article_id=article_id)
            raise


# Configure Cron scheduling interval dynamically (convert scraper interval seconds to minutes)
cron_interval_minutes = max(1, settings.scraper.check_interval // 60)
cron_minutes = {i for i in range(0, 60, cron_interval_minutes)}

class WorkerSettings:
    functions = [fetch_sources_task, process_article_task, publish_post_task]
    redis_settings = redis_settings
    cron_jobs = [
        cron(fetch_sources_task, second=0, minute=cron_minutes)
    ]
