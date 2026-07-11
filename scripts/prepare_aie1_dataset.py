"""Prepare deterministic AIE1 seed artifacts from the participant workbook."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from modules.knowledge.src.ingestion import chunk_document, load_workbook_corpus

DEFAULT_SOURCE = Path("package/ai_workspace_dataset_vietnamese_participants.xlsm")
DEFAULT_OUTPUT = Path("database/seeds/aie1")


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def prepare(source: Path, output: Path) -> dict[str, Any]:
    result = load_workbook_corpus(source)
    chunks = tuple(chunk for document in result.documents for chunk in chunk_document(document))
    output.mkdir(parents=True, exist_ok=True)

    _write_jsonl(output / "documents.jsonl", (item.as_dict() for item in result.documents))
    _write_jsonl(output / "chunks.jsonl", (item.as_dict() for item in chunks))
    _write_jsonl(output / "quarantine.jsonl", (item.as_dict() for item in result.quarantined))

    profile = {
        "source": source.as_posix(),
        "document_count": len(result.documents),
        "chunk_count": len(chunks),
        "quarantine_count": len(result.quarantined),
        "classification_counts": dict(sorted(Counter(d.classification for d in result.documents).items())),
        "department_counts": dict(sorted(Counter(d.department for d in result.documents).items())),
        "allowed_access_counts": dict(sorted(Counter(d.allowed_access for d in result.documents).items())),
        "language_counts": dict(sorted(Counter(d.language for d in result.documents).items())),
        "chunk_character_count": sum(len(chunk.content) for chunk in chunks),
    }
    (output / "corpus_profile.json").write_text(
        json.dumps(profile, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return profile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
