import unittest
from pathlib import Path
from unittest import mock

from modules.governance.src.evaluation.xlsm_dataset import _table, load_public_evaluation_dataset


WORKBOOK = Path(__file__).resolve().parents[2] / "package" / "ai_workspace_dataset_vietnamese_participants.xlsm"


class XlsmDatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = load_public_evaluation_dataset(WORKBOOK)

    def test_loads_expected_dataset_shape(self):
        self.assertEqual(len(self.dataset.documents), 40)
        self.assertEqual(len(self.dataset.users), 32)
        self.assertEqual(len(self.dataset.scenarios), 50)

    def test_finds_expected_headers_when_xml_row_numbers_have_gaps(self):
        class Archive:
            pass

        rows = {1: {"A": "banner"}, 3: {"A": "document_id"}, 4: {"A": "DOC001"}}
        with mock.patch("modules.governance.src.evaluation.xlsm_dataset._rows", return_value=rows):
            records = _table(Archive(), "ignored", (), ("document_id",))

        self.assertEqual(records, ({"document_id": "DOC001"},))

    def test_loaded_record_mappings_are_immutable(self):
        with self.assertRaises(TypeError):
            self.dataset.documents["DOC999"] = self.dataset.documents["DOC001"]

    def test_normalizes_hr_and_splits_multi_document_expectation(self):
        self.assertEqual(self.dataset.documents["DOC006"].department, "Human Resources")
        scenario = next(item for item in self.dataset.scenarios if item.question_id == "P031")
        self.assertEqual(scenario.expected_document_ids, ("DOC001", "DOC011"))

    def test_uses_evaluation_persona_not_profile_role(self):
        scenario = next(item for item in self.dataset.scenarios if item.question_id == "P003")

        self.assertEqual(self.dataset.users[scenario.user_id].role, "Manager")
        self.assertEqual(scenario.role, "Employee")


if __name__ == "__main__":
    unittest.main()
