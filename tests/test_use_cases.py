import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from src.domain.entities import Article
from src.worker import process_article_task

@pytest.mark.asyncio
@patch("src.worker.async_session_maker")
@patch("src.worker.ai_orchestrator")
@patch("src.worker.image_pipeline")
@patch("src.worker.enqueue_job")
async def test_process_article_task_auto_publish(
    mock_enqueue: MagicMock,
    mock_img_pipe: MagicMock,
    mock_ai: MagicMock,
    mock_session_maker: MagicMock,
) -> None:
    # 1. Mock DB Session
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session_maker.return_value.__aenter__.return_value = mock_session
    
    # 2. Mock Article entity
    article_id = uuid.uuid4()
    mock_article = Article(
        id=article_id,
        source_id=uuid.uuid4(),
        external_id="ext_001",
        raw_text="Google announces Gemini 1.5 Flash.",
        fetched_at=datetime.utcnow(),
        status="PENDING"
    )
    
    # 3. Mock Repositories
    mock_article_repo = MagicMock()
    mock_article_repo.find_by_id = AsyncMock(return_value=mock_article)
    mock_article_repo.save = AsyncMock()
    
    mock_emb_repo = MagicMock()
    mock_emb_repo.save = AsyncMock()
    
    mock_pub_repo = MagicMock()
    mock_pub_repo.save = AsyncMock()

    mock_review_repo = MagicMock()
    mock_review_repo.save = AsyncMock()
    
    # 4. Patch SQLAlchemy repo instantiation inside the worker
    with patch("src.worker.SqlAlchemyArticleRepository", return_value=mock_article_repo), \
         patch("src.worker.SqlAlchemyArticleEmbeddingRepository", return_value=mock_emb_repo), \
         patch("src.worker.SqlAlchemyPublicationRepository", return_value=mock_pub_repo), \
         patch("src.worker.SqlAlchemyHumanReviewTaskRepository", return_value=mock_review_repo):
             
        # Mock sequence of generate_text calls for checkers and rewriters
        mock_ai.generate_text = AsyncMock()
        mock_ai.generate_text.side_effect = [
            '{"is_ad_or_spam": false, "confidence_score": 0.01, "reason": "clean"}', # AdSpam check
            '{"is_toxic_or_nsfw": false, "toxicity_score": 0.01, "reason": "clean"}', # Toxicity check
            '{"is_verifiable_and_consistent": true, "contradiction_score": 0.01, "reason": "clean"}', # Fact check
            '{"is_comprehensible_and_correct": true, "readability_score": 0.95, "error_count": 0, "reason": "clean"}', # Readability check
        ]
        mock_ai.double_pass_rewrite = AsyncMock(return_value="Final rewritten copy")
        mock_ai.get_embeddings = AsyncMock(return_value=[0.1] * 1536)
        
        # Mock duplicate finder to return no duplicates
        mock_emb_repo.find_similar = AsyncMock(return_value=[])
        
        # Mock image processor returning an illustration path
        mock_img_pipe.process = AsyncMock(return_value=["/app/artifacts/generated_images/illus.jpg"])
        
        # Run worker task
        await process_article_task(None, str(article_id))
        
        # 5. Assertions
        assert mock_article.status == "READY"
        mock_article_repo.save.assert_called()
        mock_pub_repo.save.assert_called()
        mock_enqueue.assert_called_with("publish_post_task", str(article_id))
