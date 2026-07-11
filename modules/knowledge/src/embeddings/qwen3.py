"""Internal Qwen3 embedding implementation with lazy ML dependencies."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from modules.knowledge.src.embeddings.config import EmbeddingModelConfig
from modules.knowledge.src.embeddings.contracts import EmbeddingRecord, TextToEmbed


class Qwen3Embedder:
    """Run Qwen3 embedding inference on a local CPU or CUDA device."""

    def __init__(
        self,
        config: EmbeddingModelConfig,
        *,
        device: str = "auto",
        batch_size: int = 16,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        self.config = config
        self.batch_size = batch_size
        self._requested_device = device
        self._torch: Any = None
        self._tokenizer: Any = None
        self._model: Any = None
        self._device: str | None = None
        self._resolved_revision: str | None = None

    @property
    def resolved_revision(self) -> str:
        if self._resolved_revision is None:
            raise RuntimeError("model has not been loaded")
        return self._resolved_revision

    @property
    def device(self) -> str:
        if self._device is None:
            raise RuntimeError("model has not been loaded")
        return self._device

    def load(self) -> None:
        """Load model weights locally; the model hub may download a missing snapshot."""

        if self._model is not None:
            return
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError as exc:  # pragma: no cover - depends on worker environment
            raise RuntimeError(
                "Qwen embedding requires torch and transformers in the worker environment"
            ) from exc

        device = self._requested_device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested but is not available")
        if device not in {"cpu", "cuda"}:
            raise ValueError("device must be auto, cpu, or cuda")

        revision = None if not self.config.is_production_pinned else self.config.revision
        load_kwargs: dict[str, Any] = {"trust_remote_code": False}
        if revision is not None:
            load_kwargs["revision"] = revision
        if device == "cuda":
            load_kwargs["dtype"] = (
                torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
            )
        else:
            load_kwargs["dtype"] = torch.float32

        tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_id,
            padding_side="left",
            **({"revision": revision} if revision is not None else {}),
        )
        model = AutoModel.from_pretrained(self.config.model_id, **load_kwargs)
        model.eval()
        model.to(device)

        self._torch = torch
        self._tokenizer = tokenizer
        self._model = model
        self._device = device
        self._resolved_revision = (
            getattr(model.config, "_commit_hash", None)
            or revision
            or "UNRESOLVED_MODEL_REVISION"
        )

    def _encode(self, texts: Sequence[str], *, is_query: bool) -> tuple[tuple[float, ...], ...]:
        self.load()
        if not texts:
            return ()
        if any(not text.strip() for text in texts):
            raise ValueError("embedding input cannot be empty")

        torch = self._torch
        values = list(texts)
        if is_query:
            values = [
                f"Instruct: {self.config.query_instruction}\nQuery: {text}" for text in values
            ]

        result: list[tuple[float, ...]] = []
        for start in range(0, len(values), self.batch_size):
            batch = values[start : start + self.batch_size]
            encoded = self._tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=self.config.max_input_tokens,
                return_tensors="pt",
            )
            encoded = {name: value.to(self.device) for name, value in encoded.items()}
            with torch.inference_mode():
                output = self._model(**encoded)
                attention_mask = encoded["attention_mask"]
                if attention_mask[:, -1].sum() == attention_mask.shape[0]:
                    embeddings = output.last_hidden_state[:, -1]
                else:
                    sequence_lengths = attention_mask.sum(dim=1) - 1
                    rows = torch.arange(output.last_hidden_state.shape[0], device=self.device)
                    embeddings = output.last_hidden_state[rows, sequence_lengths]
                embeddings = embeddings[:, : self.config.output_dimension].float()
                embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            result.extend(tuple(float(item) for item in row) for row in embeddings.cpu().tolist())
        return tuple(result)

    async def embed_documents(
        self, items: Sequence[TextToEmbed]
    ) -> tuple[EmbeddingRecord, ...]:
        for item in items:
            action = self.config.classification_policy.get(item.classification)
            if action != "embed_internal":
                raise ValueError(f"classification {item.classification!r} cannot be embedded")
        vectors = self._encode([item.content for item in items], is_query=False)
        return tuple(
            EmbeddingRecord(
                chunk_id=item.chunk_id,
                tenant_id=item.tenant_id,
                document_version_id=item.document_version_id,
                model_id=self.config.model_id,
                model_revision=self.resolved_revision,
                dimension=self.config.output_dimension,
                normalized=self.config.normalize,
                values=vector,
                content_sha256=item.content_sha256,
            )
            for item, vector in zip(items, vectors, strict=True)
        )

    async def embed_query(self, query: str, *, tenant_id: str) -> tuple[float, ...]:
        del tenant_id  # Tenant remains an authorization/filter input, not embedding text.
        return self._encode([query], is_query=True)[0]
