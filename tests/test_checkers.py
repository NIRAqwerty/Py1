import pytest
import uuid
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock
from src.domain.entities import Article
from src.infrastructure.checkers.ad_spam import AdSpamChecker
from src.infrastructure.checkers.fact_check import FactChecker
from src.infrastructure.checkers.grammar_readability import GrammarReadabilityChecker
from src.infrastructure.checkers.toxicity_nsfw import ToxicityNsfwChecker

@pytest.mark.asyncio
async def test_ad_spam_checker_detects_ad(mock_ai_orchestrator: Any) -> None:
    mock_ai_orchestrator.generate_text = AsyncMock(
        return_value='{"is_ad_or_spam": true, "confidence_score": 0.95, "reason": "referral discount"}'
    )
    
    checker = AdSpamChecker(mock_ai_orchestrator)
    article = Article(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        external_id="123",
        raw_text="Use code PYCOURSE to get 50% discount! Click: http://ref.com",
        fetched_at=datetime.utcnow()
    )
    res = await checker.check(article)
    assert res.passed is False
    assert res.confidence_score == 0.95
    assert "referral" in res.reason

@pytest.mark.asyncio
async def test_ad_spam_checker_passes_clean(mock_ai_orchestrator: Any) -> None:
    mock_ai_orchestrator.generate_text = AsyncMock(
        return_value='{"is_ad_or_spam": false, "confidence_score": 0.05, "reason": "clean news report"}'
    )
    
    checker = AdSpamChecker(mock_ai_orchestrator)
    article = Article(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        external_id="124",
        raw_text="FastAPI version 0.111.0 is released, introducing performance fixes.",
        fetched_at=datetime.utcnow()
    )
    res = await checker.check(article)
    assert res.passed is True
    assert res.confidence_score == 0.05

@pytest.mark.asyncio
async def test_toxicity_checker_rejects_toxic(mock_ai_orchestrator: Any) -> None:
    mock_ai_orchestrator.generate_text = AsyncMock(
        return_value='{"is_toxic_or_nsfw": true, "toxicity_score": 0.90, "reason": "hate speech"}'
    )
    
    checker = ToxicityNsfwChecker(mock_ai_orchestrator)
    article = Article(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        external_id="125",
        raw_text="Some hateful comments online...",
        fetched_at=datetime.utcnow()
    )
    res = await checker.check(article)
    assert res.passed is False
    assert "hate speech" in res.reason

@pytest.mark.asyncio
async def test_fact_checker_detects_contradictions(mock_ai_orchestrator: Any) -> None:
    mock_ai_orchestrator.generate_text = AsyncMock(
        return_value='{"is_verifiable_and_consistent": false, "contradiction_score": 0.85, "reason": "clashing numbers"}'
    )
    
    checker = FactChecker(mock_ai_orchestrator)
    article = Article(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        external_id="126",
        raw_text="First sentence says 10 people died. Next says 50 people died.",
        fetched_at=datetime.utcnow()
    )
    res = await checker.check(article)
    assert res.passed is False
    assert res.confidence_score == 1.0 - 0.85


