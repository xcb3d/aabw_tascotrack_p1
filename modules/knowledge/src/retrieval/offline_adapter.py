from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path

from modules.knowledge.contracts.retrieval import (
    AuthorizedRetrievalCandidate,
    AuthorizedRetrievalResult,
    RetrievalRequest,
)


@dataclass(frozen=True)
class RetrievalResource:
    tenant_id: str
    chunk_id: str
    document_id: str
    source_version: str
    classification: str
    department: str
    allowed_access: str
    content: str
    vector: tuple[float, ...]


@dataclass(frozen=True)
class OfflineRetrievalStore:
    tenant_id: str
    dimension: int
    model_id: str
    model_revision: str
    resources: tuple[RetrievalResource, ...]


PolicyPredicate = Callable[[RetrievalRequest, RetrievalResource], bool]


def _read_json(path: Path):
    try:
        with path.open(encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("invalid retrieval artifact") from error


def _read_jsonl(path: Path) -> tuple[dict, ...]:
    try:
        with path.open(encoding="utf-8") as file:
            rows = tuple(json.loads(line) for line in file if line.strip())
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("invalid retrieval artifact") from error
    if not all(type(row) is dict for row in rows):
        raise ValueError("invalid retrieval artifact")
    return rows


def _text(row: dict, name: str) -> str:
    value = row.get(name)
    if type(value) is not str or not value:
        raise ValueError("invalid retrieval artifact")
    return value


def _positive_int(row: dict, name: str) -> int:
    value = row.get(name)
    if type(value) is not int or value <= 0:
        raise ValueError("invalid retrieval artifact")
    return value


def _vector(value, dimension: int) -> tuple[float, ...]:
    if type(value) is not list or len(value) != dimension:
        raise ValueError("invalid retrieval artifact")
    if any(type(item) not in (int, float) or not math.isfinite(item) for item in value):
        raise ValueError("invalid retrieval artifact")
    vector = tuple(float(item) for item in value)
    if abs(math.sqrt(sum(item * item for item in vector)) - 1) > 1e-6:
        raise ValueError("invalid retrieval artifact")
    return vector


def load_offline_store(artifact_directory: Path) -> OfflineRetrievalStore:
    directory = Path(artifact_directory)
    manifest = _read_json(directory / "embeddings.manifest.json")
    if type(manifest) is not dict:
        raise ValueError("invalid retrieval artifact")
    tenant_id = _text(manifest, "tenant_id")
    model_id = _text(manifest, "model_id")
    model_revision = _text(manifest, "resolved_revision")
    if _text(manifest, "configured_revision") != model_revision:
        raise ValueError("invalid retrieval artifact")
    dimension = _positive_int(manifest, "dimension")
    chunk_count = _positive_int(manifest, "chunk_count")

    chunks = _read_jsonl(directory / "chunks.jsonl")
    embeddings = _read_jsonl(directory / "embeddings.jsonl")
    if len(chunks) != chunk_count or len(embeddings) != chunk_count:
        raise ValueError("invalid retrieval artifact")

    chunks_by_id = {}
    for chunk in chunks:
        chunk_id = _text(chunk, "chunk_id")
        if chunk_id in chunks_by_id:
            raise ValueError("invalid retrieval artifact")
        chunks_by_id[chunk_id] = chunk

    embeddings_by_id = {}
    for embedding in embeddings:
        chunk_id = _text(embedding, "chunk_id")
        if chunk_id in embeddings_by_id:
            raise ValueError("invalid retrieval artifact")
        if (
            _text(embedding, "tenant_id") != tenant_id
            or _text(embedding, "model_id") != model_id
            or _text(embedding, "model_revision") != model_revision
            or _positive_int(embedding, "dimension") != dimension
            or embedding.get("normalized") is not True
        ):
            raise ValueError("invalid retrieval artifact")
        embeddings_by_id[chunk_id] = embedding

    if set(chunks_by_id) != set(embeddings_by_id):
        raise ValueError("invalid retrieval artifact")

    resources = []
    for chunk_id, chunk in chunks_by_id.items():
        embedding = embeddings_by_id[chunk_id]
        source_version = _text(chunk, "version_id")
        if _text(embedding, "document_version_id") != source_version:
            raise ValueError("invalid retrieval artifact")
        content = _text(chunk, "content")
        if _text(embedding, "content_sha256") != sha256(content.encode()).hexdigest():
            raise ValueError("invalid retrieval artifact")
        resources.append(RetrievalResource(
            tenant_id,
            chunk_id,
            _text(chunk, "document_id"),
            source_version,
            _text(chunk, "classification"),
            _text(chunk, "department"),
            _text(chunk, "allowed_access"),
            content,
            _vector(embedding.get("embedding"), dimension),
        ))
    return OfflineRetrievalStore(tenant_id, dimension, model_id, model_revision, tuple(resources))


def _query_vector(value, dimension: int) -> tuple[float, ...]:
    if type(value) is not tuple or not value or len(value) != dimension:
        raise ValueError("invalid query vector")
    if any(type(item) not in (int, float) or not math.isfinite(item) for item in value):
        raise ValueError("invalid query vector")
    vector = tuple(float(item) for item in value)
    if not any(vector):
        raise ValueError("invalid query vector")
    return vector


def _similarity(query_vector: tuple[float, ...], resource: RetrievalResource) -> float:
    return sum(left * right for left, right in zip(query_vector, resource.vector)) / math.sqrt(
        sum(item * item for item in query_vector)
    )


def _empty_result(request: RetrievalRequest) -> AuthorizedRetrievalResult:
    return AuthorizedRetrievalResult(request.tenant_id, request.policy_decision_id, ())


def retrieve_offline(
    request: RetrievalRequest,
    store: OfflineRetrievalStore,
    permitted: PolicyPredicate | None,
    *,
    limit: int = 5,
) -> AuthorizedRetrievalResult:
    if type(limit) is not int or limit <= 0:
        raise ValueError("limit must be a positive integer")
    query_vector = _query_vector(request.query_vector, store.dimension)
    if request.tenant_id != store.tenant_id or permitted is None:
        return _empty_result(request)

    try:
        authorized = tuple(resource for resource in store.resources if permitted(request, resource))
    except Exception:
        return _empty_result(request)
    ranked = sorted(
        ((_similarity(query_vector, resource), resource) for resource in authorized),
        key=lambda item: (-item[0], item[1].chunk_id),
    )

    candidates = []
    try:
        for _, resource in ranked:
            if not permitted(request, resource):
                continue
            candidates.append(AuthorizedRetrievalCandidate(
                resource.chunk_id,
                resource.document_id,
                resource.source_version,
                resource.classification,
                resource.content,
                request.policy_decision_id,
            ))
            if len(candidates) == limit:
                break
    except Exception:
        return _empty_result(request)
    return AuthorizedRetrievalResult(request.tenant_id, request.policy_decision_id, tuple(candidates))
