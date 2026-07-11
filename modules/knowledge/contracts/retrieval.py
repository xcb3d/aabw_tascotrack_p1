from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalRequest:
    tenant_id: str
    subject_id: str
    purpose: str
    policy_decision_id: str
    query: str
    query_vector: tuple[float, ...] = ()


@dataclass(frozen=True)
class AuthorizedRetrievalCandidate:
    chunk_id: str
    document_id: str
    source_version: str
    classification: str
    content: str
    policy_decision_id: str


@dataclass(frozen=True)
class AuthorizedRetrievalResult:
    tenant_id: str
    policy_decision_id: str
    candidates: tuple[AuthorizedRetrievalCandidate, ...]
