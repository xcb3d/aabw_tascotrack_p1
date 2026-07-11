"""Internal Qwen3 cross-encoder-style reranker for authorized candidates."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RerankerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int
    model_id: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    execution: str
    max_input_tokens: int = Field(gt=0)
    instruction: str = Field(min_length=1)

    @property
    def is_production_pinned(self) -> bool:
        return self.revision != "PIN_BEFORE_PRODUCTION"


def load_reranker_config(path: str | Path) -> RerankerConfig:
    return RerankerConfig.model_validate_json(Path(path).read_text(encoding="utf-8"))


class Qwen3Reranker:
    def __init__(
        self, config: RerankerConfig, *, device: str = "auto", batch_size: int = 4
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        self.config = config
        self.requested_device = device
        self.batch_size = batch_size
        self._torch: Any = None
        self._tokenizer: Any = None
        self._model: Any = None
        self._device: str | None = None
        self._resolved_revision: str | None = None
        self._prefix_tokens: list[int] = []
        self._suffix_tokens: list[int] = []
        self._true_token_id: int | None = None
        self._false_token_id: int | None = None

    @property
    def resolved_revision(self) -> str:
        if self._resolved_revision is None:
            raise RuntimeError("reranker has not been loaded")
        return self._resolved_revision

    def load(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("reranking requires torch and transformers") from exc

        device = self.requested_device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested but is unavailable")
        if device not in {"cpu", "cuda"}:
            raise ValueError("device must be auto, cpu, or cuda")

        revision = self.config.revision if self.config.is_production_pinned else None
        revision_args = {"revision": revision} if revision is not None else {}
        tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_id, padding_side="left", **revision_args
        )
        dtype = torch.float32
        if device == "cuda":
            dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        model = AutoModelForCausalLM.from_pretrained(
            self.config.model_id,
            dtype=dtype,
            trust_remote_code=False,
            **revision_args,
        )
        model.eval()
        model.to(device)  # type: ignore[arg-type]

        prefix = (
            "<|im_start|>system\n"
            "Judge whether the Document meets the requirements based on the Query and the "
            "Instruct provided. Answer only yes or no.<|im_end|>\n<|im_start|>user\n"
        )
        suffix = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
        self._prefix_tokens = tokenizer.encode(prefix, add_special_tokens=False)
        self._suffix_tokens = tokenizer.encode(suffix, add_special_tokens=False)
        self._true_token_id = tokenizer.convert_tokens_to_ids("yes")
        self._false_token_id = tokenizer.convert_tokens_to_ids("no")
        if self._true_token_id == tokenizer.unk_token_id or self._false_token_id == tokenizer.unk_token_id:
            raise RuntimeError("reranker tokenizer does not expose yes/no score tokens")

        self._torch = torch
        self._tokenizer = tokenizer
        self._model = model
        self._device = device
        self._resolved_revision = (
            getattr(model.config, "_commit_hash", None)
            or revision
            or "UNRESOLVED_MODEL_REVISION"
        )

    def _format_pair(self, query: str, document: str) -> str:
        return (
            f"<Instruct>: {self.config.instruction}\n"
            f"<Query>: {query}\n<Document>: {document}"
        )

    async def score(self, query: str, documents: Sequence[str]) -> tuple[float, ...]:
        self.load()
        if not query.strip() or any(not document.strip() for document in documents):
            raise ValueError("query and reranker documents cannot be empty")
        if not documents:
            return ()
        torch = self._torch
        scores: list[float] = []
        content_limit = (
            self.config.max_input_tokens - len(self._prefix_tokens) - len(self._suffix_tokens)
        )
        for start in range(0, len(documents), self.batch_size):
            pairs = [self._format_pair(query, item) for item in documents[start : start + self.batch_size]]
            token_rows = self._tokenizer(
                pairs,
                add_special_tokens=False,
                truncation=True,
                max_length=content_limit,
            )["input_ids"]
            token_rows = [self._prefix_tokens + row + self._suffix_tokens for row in token_rows]
            batch = self._tokenizer.pad(
                {"input_ids": token_rows}, padding=True, return_tensors="pt"
            )
            batch = {key: value.to(self._device) for key, value in batch.items()}
            with torch.inference_mode():
                logits = self._model(**batch).logits[:, -1, :]
                pair_logits = torch.stack(
                    [logits[:, self._false_token_id], logits[:, self._true_token_id]], dim=1
                )
                batch_scores = torch.softmax(pair_logits.float(), dim=1)[:, 1]
            scores.extend(float(value) for value in batch_scores.cpu().tolist())
        return tuple(scores)
