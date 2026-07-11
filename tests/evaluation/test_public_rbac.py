import unittest

from modules.governance.contracts.evaluation import DocumentRecord, UserRecord
from modules.governance.src.evaluation.public_rbac import allows


class PublicRbacTest(unittest.TestCase):
    def user(self, role="Employee", department="Finance", status="Active"):
        return UserRecord("U001", role, department, status)

    def document(self, classification, department="Finance"):
        return DocumentRecord("DOC001", "Title", department, classification, "All")

    def test_public_and_internal_allow_active_personas(self):
        for classification in ("Public", "Internal"):
            with self.subTest(classification=classification):
                self.assertTrue(allows(self.user(), self.document(classification, "Engineering")))

    def test_confidential_requires_same_department_except_executive(self):
        document = self.document("Confidential", "Engineering")

        self.assertFalse(allows(self.user(), document))
        self.assertTrue(allows(self.user("Executive"), document))

    def test_restricted_allows_executive_only(self):
        document = self.document("Restricted", "Engineering")

        self.assertFalse(allows(self.user("Director", "Engineering"), document))
        self.assertTrue(allows(self.user("Executive", "Finance"), document))

    def test_inactive_and_unknown_personas_deny(self):
        document = self.document("Public")

        self.assertFalse(allows(self.user(status="Inactive"), document))
        self.assertFalse(allows(self.user(role="Contractor"), document))


if __name__ == "__main__":
    unittest.main()
