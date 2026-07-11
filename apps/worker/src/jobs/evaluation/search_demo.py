"""Run one ACL-filtered hybrid retrieval query against AIE1 artifacts."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from modules.knowledge.src.embeddings import Qwen3Embedder, load_embedding_config
from modules.knowledge.src.retrieval.artifacts import load_artifact_index
from modules.knowledge.src.retrieval.filters import RetrievalSubject
from modules.knowledge.src.retrieval.hybrid import HybridRetriever
from modules.knowledge.src.retrieval.reranker import Qwen3Reranker, load_reranker_config


def build_retriever(args: argparse.Namespace) -> HybridRetriever:
    embedding_config = load_embedding_config(args.embedding_config)
    index = load_artifact_index(
        chunks_path=args.chunks,
        documents_path=args.documents,
        embeddings_path=args.embeddings,
    )
    if (
        index.model_id != embedding_config.model_id
        or index.model_revision != embedding_config.revision
        or index.dimension != embedding_config.output_dimension
    ):
        raise ValueError("embedding artifact does not match the active model registry")
    embedder = Qwen3Embedder(
        embedding_config, device=args.device, batch_size=args.embedding_batch_size
    )
    reranker = None
    if not args.no_reranker:
        reranker = Qwen3Reranker(
            load_reranker_config(args.reranker_config),
            device=args.device,
            batch_size=args.reranker_batch_size,
        )
    return HybridRetriever(index, embedder, reranker=reranker)


async def run(args: argparse.Namespace) -> list[dict]:
    retriever = build_retriever(args)
    subject = RetrievalSubject(
        tenant_id=args.tenant_id,
        user_id=args.user_id,
        department=args.user_department,
        role=args.user_role,
    )
    hits = await retriever.search(
        args.query,
        subject,
        top_k=args.top_k,
        department=args.filter_department,
        classification=args.filter_classification,
    )
    return [
        {
            "rank": hit.final_rank,
            "chunkId": hit.chunk.chunk_id,
            "documentId": hit.chunk.document_id,
            "documentVersionId": hit.chunk.document_version_id,
            "title": hit.chunk.title,
            "department": hit.chunk.department,
            "classification": hit.chunk.classification,
            "headingPath": list(hit.chunk.heading_path),
            "snippet": hit.chunk.content[:500],
            "scores": asdict(hit.scores),
        }
        for hit in hits
    ]


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--query", required=True)
    value.add_argument("--user-id", default="U001")
    value.add_argument("--user-role", default="Employee")
    value.add_argument("--user-department", default="Human Resources")
    value.add_argument("--tenant-id", default="demo-mytasco")
    value.add_argument("--top-k", type=int, default=8)
    value.add_argument("--filter-department")
    value.add_argument("--filter-classification")
    value.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    value.add_argument("--embedding-batch-size", type=int, default=16)
    value.add_argument("--reranker-batch-size", type=int, default=4)
    value.add_argument("--no-reranker", action="store_true")
    value.add_argument("--chunks", type=Path, default=Path("database/seeds/aie1/chunks.jsonl"))
    value.add_argument(
        "--documents", type=Path, default=Path("database/seeds/aie1/documents.jsonl")
    )
    value.add_argument(
        "--embeddings", type=Path, default=Path("database/seeds/aie1/embeddings.jsonl")
    )
    value.add_argument(
        "--embedding-config",
        type=Path,
        default=Path("config/models/embedding-qwen3-0.6b.json"),
    )
    value.add_argument(
        "--reranker-config",
        type=Path,
        default=Path("config/models/reranker-qwen3-0.6b.json"),
    )
    return value


def main() -> None:
    args = parser().parse_args()
    try:
        result = asyncio.run(run(args))
    except Exception as exc:
        print(f"search failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps({"query": args.query, "hits": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
