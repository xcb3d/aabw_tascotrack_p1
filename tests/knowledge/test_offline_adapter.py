from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from modules.knowledge.contracts.retrieval import RetrievalRequest
from modules.knowledge.src.retrieval.offline_adapter import (
    load_offline_store,
    retrieve_offline,
)


def write_store(directory: Path, *, chunks=None, embeddings=None, manifest=None):
    chunks = chunks or [
        {
            "chunk_id": "chunk-a",
            "document_id": "DOC001",
            "version_id": "DOC001-v1",
            "classification": "Internal",
            "department": "HR",
            "allowed_access": "All Employees",
            "content": "first",
        },
        {
            "chunk_id": "chunk-b",
            "document_id": "DOC002",
            "version_id": "DOC002-v1",
            "classification": "Confidential",
            "department": "Finance",
            "allowed_access": "Own Department",
            "content": "second",
        },
    ]
    embeddings = embeddings or [
        {
            "chunk_id": chunk["chunk_id"],
            "tenant_id": "tenant-1",
            "document_version_id": chunk["version_id"],
            "model_id": "model-1",
            "model_revision": "revision-1",
            "dimension": 2,
            "normalized": True,
            "content_sha256": sha256(chunk["content"].encode()).hexdigest(),
            "embedding": [1.0, 0.0] if chunk["chunk_id"] == "chunk-a" else [0.0, 1.0],
        }
        for chunk in chunks
    ]
    manifest = manifest or {
        "tenant_id": "tenant-1",
        "model_id": "model-1",
        "configured_revision": "revision-1",
        "resolved_revision": "revision-1",
        "dimension": 2,
        "chunk_count": len(chunks),
    }
    (directory / "chunks.jsonl").write_text(
        "\n".join(json.dumps(row) for row in chunks), encoding="utf-8"
    )
    (directory / "embeddings.jsonl").write_text(
        "\n".join(json.dumps(row) for row in embeddings), encoding="utf-8"
    )
    (directory / "embeddings.manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )


def request(**overrides):
    values = {
        "tenant_id": "tenant-1",
        "subject_id": "subject-1",
        "purpose": "KNOWLEDGE_SEARCH",
        "policy_decision_id": "decision-1",
        "query": "query",
        "query_vector": (1.0, 0.0),
    }
    values.update(overrides)
    return RetrievalRequest(**values)


class OfflineAdapterTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        write_store(self.directory)
        self.store = load_offline_store(self.directory)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_loads_immutable_resources_and_maps_result(self):
        self.assertEqual(len(self.store.resources), 2)
        result = retrieve_offline(request(), self.store, lambda _, resource: resource.chunk_id == "chunk-a")

        self.assertEqual(result.tenant_id, "tenant-1")
        self.assertEqual(result.policy_decision_id, "decision-1")
        self.assertEqual(result.candidates[0].chunk_id, "chunk-a")
        self.assertEqual(result.candidates[0].source_version, "DOC001-v1")

    def test_loader_rejects_invalid_artifact_contracts(self):
        cases = (
            ("duplicate chunk", {"chunks": [
                {"chunk_id": "chunk-a", "document_id": "DOC001", "version_id": "v1", "classification": "Internal", "department": "HR", "allowed_access": "All", "content": "a"},
                {"chunk_id": "chunk-a", "document_id": "DOC002", "version_id": "v2", "classification": "Internal", "department": "HR", "allowed_access": "All", "content": "b"},
            ]}),
            ("manifest count", {"manifest": {"tenant_id": "tenant-1", "model_id": "model-1", "configured_revision": "revision-1", "resolved_revision": "revision-1", "dimension": 2, "chunk_count": 3}}),
        )
        for name, overrides in cases:
            with self.subTest(name=name), TemporaryDirectory() as temporary_directory:
                directory = Path(temporary_directory)
                write_store(directory, **overrides)
                with self.assertRaises(ValueError):
                    load_offline_store(directory)

    def test_loader_rejects_tampered_embedding_data(self):
        cases = (
            ("bad hash", {"content_sha256": "bad"}),
            ("wrong version", {"document_version_id": "other"}),
            ("wrong dimension", {"dimension": 3}),
            ("non-normalized", {"embedding": [2.0, 0.0]}),
            ("non-finite", {"embedding": [float("inf"), 0.0]}),
            ("model mismatch", {"model_id": "other"}),
        )
        for name, changes in cases:
            with self.subTest(name=name), TemporaryDirectory() as temporary_directory:
                directory = Path(temporary_directory)
                chunks = None
                embeddings = None
                manifest = None
                if name == "model mismatch":
                    manifest = {"tenant_id": "tenant-1", "model_id": "model-1", "configured_revision": "revision-1", "resolved_revision": "revision-1", "dimension": 2, "chunk_count": 2}
                    write_store(directory, manifest=manifest)
                    embeddings = [json.loads(line) for line in (directory / "embeddings.jsonl").read_text(encoding="utf-8").splitlines()]
                    embeddings[0].update(changes)
                else:
                    write_store(directory)
                    embeddings = [json.loads(line) for line in (directory / "embeddings.jsonl").read_text(encoding="utf-8").splitlines()]
                    embeddings[0].update(changes)
                write_store(directory, chunks=chunks, embeddings=embeddings, manifest=manifest)
                with self.assertRaises(ValueError):
                    load_offline_store(directory)

    def test_retrieval_validates_query_vector_and_limit(self):
        for query_vector in ((), (1.0,), (0.0, 0.0), (float("inf"), 0.0)):
            with self.subTest(query_vector=query_vector):
                with self.assertRaises(ValueError):
                    retrieve_offline(request(query_vector=query_vector), self.store, lambda *_: True)
        with self.assertRaises(ValueError):
            retrieve_offline(request(), self.store, lambda *_: True, limit=0)

    def test_uses_injected_policy_and_rechecks_before_export(self):
        calls = {"chunk-a": 0, "chunk-b": 0}

        def permitted(_, resource):
            calls[resource.chunk_id] += 1
            return resource.chunk_id == "chunk-b" and calls[resource.chunk_id] == 1

        result = retrieve_offline(request(query_vector=(0.0, 1.0)), self.store, permitted)

        self.assertEqual(result.candidates, ())
        self.assertGreaterEqual(calls["chunk-b"], 2)

    def test_returns_empty_without_policy_on_tenant_mismatch_or_policy_error(self):
        policy_calls = []
        mismatch = retrieve_offline(
            request(tenant_id="tenant-2"), self.store, lambda *_: policy_calls.append(True) or True
        )
        unavailable = retrieve_offline(request(), self.store, None)
        failed = retrieve_offline(request(), self.store, lambda *_: (_ for _ in ()).throw(RuntimeError()))

        self.assertEqual(mismatch.candidates, ())
        self.assertEqual(unavailable.candidates, ())
        self.assertEqual(failed.candidates, ())
        self.assertEqual(policy_calls, [])

    def test_ties_sort_by_chunk_id(self):
        result = retrieve_offline(
            request(query_vector=(1.0, 1.0)),
            self.store,
            lambda *_: True,
            limit=2,
        )
        self.assertEqual(tuple(item.chunk_id for item in result.candidates), ("chunk-a", "chunk-b"))


if __name__ == "__main__":
    unittest.main()
