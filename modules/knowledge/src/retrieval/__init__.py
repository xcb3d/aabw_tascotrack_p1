from .postgres import PostgresHybridRetriever, PostgresSearchHit


def build_postgres_retriever(settings, policy=None):
    from modules.policy.src.engine import PolicyEngine
    embedder = None
    if settings.INTERNAL_EMBEDDINGS_ENABLED:
        from pathlib import Path
        from modules.knowledge.src.embeddings import Qwen3Embedder, load_embedding_config
        embedder = Qwen3Embedder(load_embedding_config(Path("config/models/embedding-qwen3-0.6b.json")))
    return PostgresHybridRetriever(policy or PolicyEngine(), embedder)

__all__ = ["PostgresHybridRetriever", "PostgresSearchHit", "build_postgres_retriever"]
