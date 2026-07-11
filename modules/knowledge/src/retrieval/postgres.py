from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from modules.identity.src.subject import SubjectContext
from modules.policy.src.engine import PolicyEngine


class QueryEmbedder(Protocol):
    async def embed_query(self, query: str, *, tenant_id: str) -> tuple[float, ...]: ...


@dataclass(frozen=True)
class PostgresSearchHit:
    chunk_id: str
    document_id: str
    version_id: str
    title: str
    department: str
    classification: str
    section: str
    content: str
    score: float
    policy_decision_id: str


class PostgresHybridRetriever:
    """Tenant-filtered FTS + pgvector retrieval with deterministic policy recheck."""

    def __init__(self, policy: PolicyEngine, embedder: QueryEmbedder | None = None) -> None:
        self.policy = policy
        self.embedder = embedder

    async def search(
        self,
        session: AsyncSession,
        query: str,
        subject: SubjectContext,
        *,
        purpose: str = "KNOWLEDGE_SEARCH",
        top_k: int = 8,
        department: str | None = None,
        classification: str | None = None,
    ) -> tuple[PostgresSearchHit, ...]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        if not 1 <= top_k <= 20:
            raise ValueError("top_k must be between 1 and 20")
        query_vector = None
        terms = [term.replace("'", "") for term in re.findall(r"[^\W_]+", query.casefold(), flags=re.UNICODE) if len(term) > 1]
        tsquery = " | ".join(dict.fromkeys(terms)) or query
        if self.embedder is not None:
            vector = await self.embedder.embed_query(query, tenant_id=subject.tenant_id)
            if len(vector) != 512:
                raise ValueError("query embedding must contain 512 values")
            query_vector = "[" + ",".join(f"{value:.8g}" for value in vector) + "]"

        sql = text(
            """
            WITH authorized AS (
                SELECT c.*, d.title,
                       ts_rank_cd(to_tsvector('simple', c.content), to_tsquery('simple', :tsquery)) AS lexical_score,
                       CASE WHEN CAST(:query_vector AS text) IS NULL OR c.embedding IS NULL THEN 0.0
                            ELSE 1.0 - (c.embedding <=> CAST(:query_vector AS halfvec)) END AS vector_score
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                JOIN document_versions v ON v.id = c.version_id
                WHERE c.tenant_id = :tenant_id
                  AND d.status = 'active' AND v.status = 'active'
                  AND (v.effective_from IS NULL OR v.effective_from <= :now)
                  AND (v.effective_to IS NULL OR v.effective_to > :now)
                  AND (CAST(:department AS text) IS NULL OR c.department_id = CAST(:department AS text))
                  AND (CAST(:classification AS text) IS NULL OR c.classification = CAST(:classification AS text))
                  AND c.classification <> 'Secret'
            )
            SELECT *, LEAST(1.0, GREATEST(0.0,
                (lexical_score * 0.45 + vector_score * 0.55) *
                CASE WHEN COALESCE((annotations->>'promptInjection')::boolean, false) THEN 0.25 ELSE 1.0 END
            )) AS final_score
            FROM authorized
            WHERE lexical_score > 0 OR vector_score > 0
            ORDER BY final_score DESC, stable_id ASC
            LIMIT :candidate_limit
            """
        )
        rows = (
            await session.execute(
                sql,
                {
                    "query": query,
                    "tsquery": tsquery,
                    "query_vector": query_vector,
                    "tenant_id": subject.tenant_id,
                    "now": datetime.now(timezone.utc),
                    "department": department,
                    "classification": classification,
                    "candidate_limit": min(50, top_k * 4),
                },
            )
        ).mappings()
        hits: list[PostgresSearchHit] = []
        for row in rows:
            decision = await self.policy.decide(
                subject,
                {
                    "tenant_id": row["tenant_id"],
                    "department_id": row["department_id"],
                    "classification": row["classification"],
                    "allowed_access": row["allowed_access"],
                    "status": "active",
                },
                "knowledge:read",
                purpose,
            )
            if decision.decision.value != "ALLOW":
                continue
            hits.append(
                PostgresSearchHit(
                    chunk_id=row["stable_id"], document_id=str(row["document_id"]),
                    version_id=str(row["version_id"]), title=row["title"],
                    department=row["department_id"], classification=row["classification"],
                    section=row["section"], content=row["content"], score=float(row["final_score"]),
                    policy_decision_id=decision.decision_id or "",
                )
            )
            if len(hits) >= top_k:
                break
        return tuple(hits)
