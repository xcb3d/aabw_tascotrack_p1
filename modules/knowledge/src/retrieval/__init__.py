from __future__ import annotations

from apps.api.src.schemas.search import SearchRequest


async def search(request: SearchRequest, subject_id: str) -> list[dict]:
    """Search authorized knowledge chunks.

    # TODO: apply policy filtering, vector retrieval, reranking, and DLP.
    """
    raise NotImplementedError("knowledge.search")
