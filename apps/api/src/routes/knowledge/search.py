from __future__ import annotations

from fastapi import APIRouter, Depends

from apps.api.src.dependencies import get_request_id
from apps.api.src.schemas.chat import LegacyChatEnvelope, LegacyChatRequest
from apps.api.src.schemas.search import SearchEnvelope, SearchRequest

router = APIRouter(tags=["Legacy"])


@router.post(
    "/mytasco/v1/aiwsp/knowledge/search",
    operation_id="searchKnowledge",
    response_model=SearchEnvelope,
)
async def search_knowledge(
    body: SearchRequest,
    request_id: str = Depends(get_request_id),
) -> SearchEnvelope:
    """searchKnowledge — POST /mytasco/v1/aiwsp/knowledge/search

    ACL-aware enterprise knowledge search.
    """
    # TODO: call modules.knowledge retrieval with ACL + DLP filters.
    raise NotImplementedError("searchKnowledge")


@router.post(
    "/mytasco/v1/aiwsp/assistant/chat",
    operation_id="legacyChat",
    response_model=LegacyChatEnvelope,
)
async def legacy_chat(
    body: LegacyChatRequest,
    request_id: str = Depends(get_request_id),
) -> LegacyChatEnvelope:
    """legacyChat — POST /mytasco/v1/aiwsp/assistant/chat

    Deprecated: compatibility endpoint for synchronous secure RAG chat.
    New clients should use chat sessions and runs.
    """
    # TODO: implement legacy chat flow with retrieval + validation.
    raise NotImplementedError("legacyChat")
