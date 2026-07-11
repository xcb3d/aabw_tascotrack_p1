import unittest
from dataclasses import FrozenInstanceError

from modules.knowledge.contracts.retrieval import (
    AuthorizedRetrievalCandidate,
    AuthorizedRetrievalResult,
    RetrievalRequest,
)


class RetrievalContractTest(unittest.TestCase):
    def test_request_preserves_policy_binding(self):
        request = RetrievalRequest(
            tenant_id="tenant-1",
            subject_id="user-1",
            purpose="KNOWLEDGE_SEARCH",
            policy_decision_id="decision-1",
            query="quy định nghỉ phép",
        )

        self.assertEqual(request.tenant_id, "tenant-1")
        self.assertEqual(request.policy_decision_id, "decision-1")
        self.assertEqual(request.query_vector, ())
        with self.assertRaises(FrozenInstanceError):
            request.tenant_id = "tenant-2"

    def test_request_preserves_immutable_query_vector(self):
        request = RetrievalRequest(
            tenant_id="tenant-1",
            subject_id="user-1",
            purpose="KNOWLEDGE_SEARCH",
            policy_decision_id="decision-1",
            query="quy định nghỉ phép",
            query_vector=(0.6, 0.8),
        )

        self.assertEqual(request.query_vector, (0.6, 0.8))
        with self.assertRaises(FrozenInstanceError):
            request.query_vector = ()

    def test_result_keeps_candidates_bound_to_same_policy_decision(self):
        candidate = AuthorizedRetrievalCandidate(
            chunk_id="chunk-1",
            document_id="DOC001",
            source_version="v1",
            classification="Internal",
            content="Nội dung đã được policy cho phép.",
            policy_decision_id="decision-1",
        )
        result = AuthorizedRetrievalResult(
            tenant_id="tenant-1",
            policy_decision_id="decision-1",
            candidates=(candidate,),
        )

        self.assertEqual(result.candidates, (candidate,))
        self.assertEqual(result.candidates[0].policy_decision_id, result.policy_decision_id)
        with self.assertRaises(FrozenInstanceError):
            candidate.document_id = "DOC002"


if __name__ == "__main__":
    unittest.main()
