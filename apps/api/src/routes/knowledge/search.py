from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.config import Settings, get_settings
from apps.api.src.db.models import AgentRun, RunEvent, Session
from apps.api.src.dependencies import get_current_subject, get_db, get_request_id
from apps.api.src.routes.chat.runs import _envelope
from apps.api.src.schemas.chat import LegacyChatBody, LegacyChatEnvelope, LegacyChatRequest
from apps.api.src.schemas.common import Classification, RunStatus
from apps.api.src.schemas.page import PageInfo
from apps.api.src.schemas.search import SearchBody, SearchEnvelope, SearchHit, SearchRequest
from modules.agent.src.runtime import execute_run
from modules.identity.src.subject import SubjectContext
from modules.knowledge.src.retrieval import build_postgres_retriever
from modules.policy.src.engine import PolicyEngine

router = APIRouter(tags=["Knowledge"])


@router.post("/mytasco/v1/aiwsp/knowledge/search", operation_id="searchKnowledge", response_model=SearchEnvelope)
async def search_knowledge(body: SearchRequest, request_id: str = Depends(get_request_id), subject: SubjectContext = Depends(get_current_subject), db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)) -> SearchEnvelope:
    page_size = body.pageInfo.pageSize if body.pageInfo else 10
    current_page = body.pageInfo.currentPage if body.pageInfo else 0
    filters = body.filters
    hits = await build_postgres_retriever(settings).search(
        db, body.query, subject, top_k=min(20, page_size * (current_page + 1)),
        department=filters.department if filters else None,
        classification=filters.classification.value if filters and filters.classification else None,
    )
    page = hits[current_page * page_size:(current_page + 1) * page_size]
    return SearchEnvelope(body=SearchBody(
        result=[SearchHit(documentId=hit.document_id, chunkId=hit.chunk_id, title=hit.title, department=hit.department, classification=Classification(hit.classification), section=hit.section, snippet=hit.content[:500], score=hit.score, allowedReason="POLICY_ALLOW") for hit in page],
        pageInfo=PageInfo(currentPage=current_page, pageSize=page_size, totalRecord=len(hits)),
        permissionDecision="ALLOW" if page else "NO_AUTHORIZED_SOURCE", likelyPermissionDenied=False, deniedMatchCount=None,
        dlp={"allowed": True, "codes": []}, roleIdentifier={"subjectId": subject.subject_id},
    ), requestId=request_id)


@router.post("/mytasco/v1/aiwsp/assistant/chat", operation_id="legacyChat", response_model=LegacyChatEnvelope)
async def legacy_chat(body: LegacyChatRequest, request_id: str = Depends(get_request_id), subject: SubjectContext = Depends(get_current_subject), db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)) -> LegacyChatEnvelope:
    session = Session(tenant_id=subject.tenant_id, owner_id=subject.subject_id, locale="vi-VN", title="Legacy chat")
    db.add(session)
    await db.flush()
    run = AgentRun(tenant_id=subject.tenant_id, owner_id=subject.subject_id, session_id=session.id, trace_id=uuid.uuid4(), client_request_id=uuid.uuid4(), message=body.message, locale="vi-VN", mode="knowledge", status=RunStatus.RECEIVED.value)
    db.add(run)
    await db.flush()
    db.add(RunEvent(run_id=run.id, status=RunStatus.RECEIVED.value, payload={}))
    await execute_run(db, run.id, subject, settings)
    await db.commit()
    envelope = await _envelope(db, run, request_id)
    return LegacyChatEnvelope(body=LegacyChatBody(
        conversationId=str(session.id), answer=envelope.body.answer,
        citations=envelope.body.citations or [],
        permissionDecision=envelope.body.permissionDecision.value if envelope.body.permissionDecision else None,
        confidence=envelope.body.confidence.value if envelope.body.confidence else None,
        modelUsed=settings.OPENAI_MODEL if settings.OPENAI_ENABLED else "fake-responses-v1",
        redactionApplied=False, dlpCategories=[], retrieval={"route": envelope.body.route.value if envelope.body.route else None},
        roleIdentifier={"subjectId": subject.subject_id},
    ), requestId=request_id)
