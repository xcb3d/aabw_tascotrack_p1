from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from modules.knowledge.src.retrieval import offline_adapter
from tests.knowledge.test_offline_adapter import request, write_store


class OfflineRetrievalAclTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        write_store(self.directory)
        self.store = offline_adapter.load_offline_store(self.directory)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_denied_high_similarity_resource_is_not_scored_or_exported(self):
        scored = []
        original_similarity = offline_adapter._similarity

        def similarity(query_vector, resource):
            scored.append(resource.chunk_id)
            return original_similarity(query_vector, resource)

        with mock.patch.object(offline_adapter, "_similarity", side_effect=similarity):
            result = offline_adapter.retrieve_offline(
                request(query_vector=(0.0, 1.0)),
                self.store,
                lambda _, resource: resource.chunk_id == "chunk-a",
            )

        self.assertEqual(scored, ["chunk-a"])
        self.assertEqual(tuple(item.chunk_id for item in result.candidates), ("chunk-a",))
        self.assertNotIn("chunk-b", str(result))
        self.assertNotIn("DOC002", str(result))
        self.assertNotIn("second", str(result))

    def test_tenant_mismatch_skips_policy_and_scoring(self):
        policy_calls = []
        with mock.patch.object(offline_adapter, "_similarity") as similarity:
            result = offline_adapter.retrieve_offline(
                request(tenant_id="tenant-2"),
                self.store,
                lambda *_: policy_calls.append(True) or True,
            )

        self.assertEqual(result.candidates, ())
        self.assertEqual(policy_calls, [])
        similarity.assert_not_called()


if __name__ == "__main__":
    unittest.main()
