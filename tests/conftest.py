import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from src.infrastructure.ai.orchestrator import AIOrchestrator

@pytest.fixture
def mock_ai_orchestrator() -> MagicMock:
    orchestrator = MagicMock(spec=AIOrchestrator)
    orchestrator.generate_text = AsyncMock(return_value="Mocked response text")
    orchestrator.get_embeddings = AsyncMock(return_value=[0.1] * 1536)
    orchestrator.analyze_image = AsyncMock(return_value='{"has_watermark_or_logo": false, "is_low_quality": false, "confidence_score": 0.9, "reason": "clean"}')
    orchestrator.generate_image = AsyncMock(return_value=b"fake_image_bytes")
    orchestrator.double_pass_rewrite = AsyncMock(return_value="This is a clean, factual, and rewritten Telegram post.")
    return orchestrator
