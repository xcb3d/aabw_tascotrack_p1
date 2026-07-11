"""Validated document ingestion primitives owned by AIE1."""

from modules.knowledge.src.ingestion.chunking import chunk_document
from modules.knowledge.src.ingestion.workbook import load_workbook_corpus

__all__ = ["chunk_document", "load_workbook_corpus"]
