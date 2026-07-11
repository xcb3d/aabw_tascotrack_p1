"""Embed an AIE1 chunk JSONL dataset with the internal Qwen3 model."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from modules.knowledge.src.embeddings import TextToEmbed, load_embedding_config
from modules.knowledge.src.embeddings.qwen3 import Qwen3Embedder

DEFAULT_OUTPUT = Path("database/seeds/aie1/embeddings.jsonl")


def _read_chunks(path: Path, tenant_id: str) -> tuple[TextToEmbed, ...]:
    items: list[TextToEmbed] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value: dict[str, Any] = json.loads(line)
                chunk_id = str(value["chunk_id"])
                content = str(value["content"])
                version_id = str(value["version_id"])
                classification = str(value["classification"])
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                raise ValueError(f"invalid chunk record at {path}:{line_number}") from exc
            if chunk_id in seen:
                raise ValueError(f"duplicate chunk_id {chunk_id!r} at {path}:{line_number}")
            if not content.strip():
                raise ValueError(f"empty chunk content at {path}:{line_number}")
            seen.add(chunk_id)
            items.append(
                TextToEmbed(
                    chunk_id=chunk_id,
                    tenant_id=tenant_id,
                    document_version_id=version_id,
                    content=content,
                    content_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                    classification=classification,
                )
            )
    return tuple(items)


def _write_record(handle: Any, record: Any) -> None:
    value = {
        "chunk_id": record.chunk_id,
        "tenant_id": record.tenant_id,
        "document_version_id": record.document_version_id,
        "model_id": record.model_id,
        "model_revision": record.model_revision,
        "dimension": record.dimension,
        "normalized": record.normalized,
        "content_sha256": record.content_sha256,
        "embedding": list(record.values),
    }
    handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")


async def embed_dataset(args: argparse.Namespace) -> dict[str, Any]:
    config = load_embedding_config(args.model_config)
    items = _read_chunks(args.source, args.tenant_id)
    summary = {
        "source": args.source.as_posix(),
        "output": args.output.as_posix(),
        "tenant_id": args.tenant_id,
        "chunk_count": len(items),
        "model_id": config.model_id,
        "configured_revision": config.revision,
        "dimension": config.output_dimension,
        "device": args.device,
        "batch_size": args.batch_size,
        "dry_run": args.dry_run,
    }
    if args.dry_run:
        return summary
    if args.output.exists() and not args.overwrite:
        raise FileExistsError(f"output already exists: {args.output}; pass --overwrite to replace")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(f".{args.output.name}.{os.getpid()}.tmp")
    if not config.is_production_pinned:
        print(
            "warning: model revision is unpinned; this is permitted only for development",
            file=sys.stderr,
        )
    embedder = Qwen3Embedder(config, device=args.device, batch_size=args.batch_size)
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            total = len(items)
            for start in range(0, total, args.batch_size):
                batch = items[start : start + args.batch_size]
                records = await embedder.embed_documents(batch)
                for record in records:
                    _write_record(handle, record)
                print(f"embedded {min(start + len(batch), total)}/{total}", file=sys.stderr)
        temporary.replace(args.output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise

    summary["device"] = embedder.device
    summary["resolved_revision"] = embedder.resolved_revision
    summary["dry_run"] = False
    manifest = args.output.with_suffix(".manifest.json")
    manifest.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--model-config", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--tenant-id", default="demo-mytasco")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> None:
    args = _parser().parse_args()
    try:
        summary = asyncio.run(embed_dataset(args))
    except Exception as exc:
        print(f"embedding failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
