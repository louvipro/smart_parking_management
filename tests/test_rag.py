import os

import pytest

from src.infrastructure.ml_agents.ai import get_rag_response
from src.shared.utils import logger
from src.config.settings_env import settings

logger.info(f" working directory is {os.getcwd()}")


# @pytest.mark.skipif(
#     not settings.ENABLE_AZURE_SEARCH, reason="requires env ENABLE_AZURE_SEARCH=True"
# )
# def test_get_related_document_ai_search():
#     user_input = "What is the capital of France?"
#     question_context = get_related_document_ai_search(user_input)

#     assert type(question_context) == str


@pytest.mark.skipif(
    not settings.ENABLE_AZURE_SEARCH, reason="requires env ENABLE_AZURE_SEARCH=True"
)
def test_get_rag_response():
    res = get_rag_response("What is the capital of France?")
    assert type(res) == str


# @pytest.mark.skipif(
#     not settings.ENABLE_AZURE_SEARCH, reason="requires env ENABLE_AZURE_SEARCH=True"
# )
# def test_run_azure_ai_search_indexer():
#     assert run_azure_ai_search_indexer().status_code == 202


@pytest.mark.skipif(
    not settings.ENABLE_AZURE_SEARCH, reason="requires env ENABLE_AZURE_SEARCH=True"
)
def test_get_rag_response_with_real_data():
    res = get_rag_response("What is the grace period for exiting the parking lot?")
    assert type(res) == str
    logger.info(f"RAG response is {res}")
    assert "grace period" in res.lower()