import unittest
from pathlib import Path

from modules.governance.src.evaluation.public_harness import evaluate_public_cases
from modules.governance.src.evaluation.xlsm_dataset import load_public_evaluation_dataset


WORKBOOK = next(
    parent / "ai_workspace_dataset_vietnamese_participants (1).xlsm"
    for parent in Path(__file__).resolve().parents
    if (parent / "ai_workspace_dataset_vietnamese_participants (1).xlsm").is_file()
)


class PublicHarnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = evaluate_public_cases(load_public_evaluation_dataset(WORKBOOK))

    def test_matches_all_public_evaluation_permissions(self):
        self.assertEqual(len(self.results), 50)
        self.assertEqual(sum(result.expected_permission == "Allow" for result in self.results), 44)
        self.assertEqual(sum(result.expected_permission == "Deny" for result in self.results), 6)
        self.assertTrue(all(result.actual_permission == result.expected_permission for result in self.results))

    def test_multi_document_case_requires_every_document(self):
        result = next(item for item in self.results if item.question_id == "P031")

        self.assertEqual(result.actual_permission, "Allow")
        self.assertEqual(result.allowed_document_ids, ("DOC001", "DOC011"))

    def test_denied_results_reveal_no_authorized_document_ids(self):
        for result in self.results:
            if result.actual_permission == "Deny":
                with self.subTest(question_id=result.question_id):
                    self.assertEqual(result.allowed_document_ids, ())


if __name__ == "__main__":
    unittest.main()
