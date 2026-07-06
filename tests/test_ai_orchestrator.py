import pytest
from unittest.mock import AsyncMock, MagicMock
from src.infrastructure.ai.orchestrator import AIOrchestrator

@pytest.mark.asyncio
async def test_double_pass_rewrite_calls_correct_steps() -> None:
    # Setup the actual orchestrator
    orchestrator = AIOrchestrator()
    
    # Mock the active adapter to return specific values sequentially
    mock_adapter = MagicMock()
    mock_adapter.generate_text = AsyncMock(side_effect=[
        "- Google announced Gemini 1.5 Flash.\n- Features 1M context.", # Step 1 output
        "Google has launched Gemini 1.5 Flash, featuring a large 1M token context." # Step 2 output
    ])
    orchestrator.adapters = {"gemini": mock_adapter}
    
    result = await orchestrator.double_pass_rewrite("Raw input post about Google's new model.")
    
    assert "Gemini 1.5 Flash" in result
    assert mock_adapter.generate_text.call_count == 2
