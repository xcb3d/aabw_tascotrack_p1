import unittest
from pathlib import Path

from modules.governance.src.evaluation.public_harness import evaluate_public_cases
from modules.governance.src.evaluation.xlsm_dataset import load_public_evaluation_dataset


WORKBOOK = Path(__file__).resolve().parents[3] / "package" / "ai_workspace_dataset_vietnamese_participants.xlsm"


class AclNoUnauthorizedEvidenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = evaluate_public_cases(load_public_evaluation_dataset(WORKBOOK))

    def test_denied_cases_export_no_document_ids(self):
        for result in self.results:
            if result.actual_permission == "Deny":
                with self.subTest(question_id=result.question_id):
                    self.assertEqual(result.expected_document_ids, ())
                    self.assertEqual(result.allowed_document_ids, ())

    def test_every_exported_document_was_expected_and_authorized(self):
        for result in self.results:
            with self.subTest(question_id=result.question_id):
                self.assertTrue(set(result.allowed_document_ids).issubset(result.expected_document_ids))
                if result.actual_permission == "Allow":
                    self.assertEqual(result.allowed_document_ids, result.expected_document_ids)


if __name__ == "__main__":
    unittest.main()
