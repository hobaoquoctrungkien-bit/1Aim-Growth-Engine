import unittest

from database import get_connection, init_db
from document_parser_service import parse_document
from knowledge_service import generate_answer, save_document, search_documents


class LegalMetadataIngestionSmokeTest(unittest.TestCase):
    def setUp(self):
        init_db()
        self.document_ids = []

    def tearDown(self):
        conn = get_connection()
        for document_id in self.document_ids:
            conn.execute("DELETE FROM knowledge_document_tags WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM knowledge_chunks WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM knowledge_documents WHERE id = ?", (document_id,))
        conn.commit()
        conn.close()

    def test_law_is_not_misclassified_as_circular_and_missing_authority_needs_review(self):
        text = """
LUAT AN NINH MANG
So: 24/2018/QH14

Dieu 1. Pham vi dieu chinh
Luat nay quy dinh ve an ninh mang.
"""
        parsed = parse_document(text, "random_filename_circular.txt", provider="Regex")

        self.assertEqual(parsed["document_type"], "LAW")
        self.assertNotEqual(parsed["document_type"], "CIRCULAR")
        self.assertEqual(parsed["issuing_authority"], "")
        self.assertTrue(parsed["parsed_fields"]["issuing_authority"]["needs_review"])
        self.assertEqual(parsed["parsed_fields"]["issuing_authority"]["confidence"], "low")
        self.assertIn("LUAT AN NINH MANG", parsed["parsed_fields"]["title"]["evidence_text"])
        self.assertFalse(parsed["parsed_fields"]["title"]["needs_review"])

    def test_document_not_used_by_ai_until_admin_verified(self):
        text = "LAW SAMPLE\nSo: META-001\nunique_unverified_legal_basis"
        document_id = save_document(
            {
                "title": "Unverified Smoke Legal",
                "document_no": "META-001",
                "document_type": "LAW",
                "issuing_authority": "",
                "category": "Import Compliance",
                "summary": "unique_unverified_legal_basis",
                "approval_status": "Approved",
                "extracted_text": text,
                "metadata_review_status": "needs_review",
            },
            chunks=[
                {
                    "heading": "Unverified",
                    "content": "unique_unverified_legal_basis",
                    "keywords": "unique_unverified_legal_basis",
                    "status": "Approved",
                }
            ],
        )
        self.document_ids.append(document_id)

        answer = generate_answer("unique_unverified_legal_basis")

        self.assertEqual(answer["conclusion"], "Insufficient verified legal basis in the system.")

    def test_admin_verified_document_is_searchable_and_used_by_ai(self):
        text = "LAW SAMPLE\nSo: META-002\nunique_verified_legal_basis"
        document_id = save_document(
            {
                "title": "Verified Smoke Legal",
                "document_no": "META-002",
                "document_type": "LAW",
                "issuing_authority": "QUOC HOI",
                "category": "Import Compliance",
                "summary": "unique_verified_legal_basis",
                "approval_status": "Approved",
                "extracted_text": text,
                "metadata_review_status": "admin_verified",
            },
            chunks=[
                {
                    "heading": "Verified",
                    "content": "unique_verified_legal_basis",
                    "keywords": "unique_verified_legal_basis",
                    "status": "Approved",
                }
            ],
        )
        self.document_ids.append(document_id)

        rows = search_documents("unique_verified_legal_basis")
        answer = generate_answer("unique_verified_legal_basis")

        self.assertTrue(any(row["id"] == document_id for row in rows))
        self.assertIn("Verified legal basis", answer["conclusion"])
        self.assertTrue(any(row.get("document_no") == "META-002" for row in answer["relevant_documents"]))


if __name__ == "__main__":
    unittest.main()
