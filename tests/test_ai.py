import pytest
import asyncio
from src.infrastructure.ml_agents.ai import get_rag_response

@pytest.mark.asyncio
async def test_get_rag_response():
    """Test that get_rag_response returns the expected placeholder message."""
    response = await get_rag_response("test query")
    assert response == "The AI assistant is currently under development. Please check back later."
