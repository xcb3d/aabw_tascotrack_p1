"""Internal embedding contracts and configuration."""

from modules.knowledge.src.embeddings.config import EmbeddingModelConfig, load_embedding_config
from modules.knowledge.src.embeddings.contracts import Embedder, EmbeddingRecord, TextToEmbed
from modules.knowledge.src.embeddings.qwen3 import Qwen3Embedder

__all__ = [
    "Embedder",
    "EmbeddingModelConfig",
    "EmbeddingRecord",
    "Qwen3Embedder",
    "TextToEmbed",
    "load_embedding_config",
]
