import unittest

from database import get_connection, init_db
from knowledge_service import generate_answer, parse_legal_document_text, save_document, search_chunks


class KnowledgeParserSmokeTest(unittest.TestCase):
    def setUp(self):
        init_db()
        self.created_document_ids = []

    def tearDown(self):
        if not self.created_document_ids:
            return
        conn = get_connection()
        for document_id in self.created_document_ids:
            conn.execute("DELETE FROM knowledge_document_tags WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM knowledge_chunks WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM knowledge_documents WHERE id = ?", (document_id,))
        conn.commit()
        conn.close()

    def test_vietnamese_legal_txt_parser(self):
        sample = """
CHÍNH PHỦ
Số: 69/2018/NĐ-CP

NGHỊ ĐỊNH
Về quản lý ngoại thương, nhập khẩu, xuất khẩu và giấy phép

Hà Nội, ngày 15 tháng 5 năm 2018
Nghị định này có hiệu lực từ ngày 15/05/2018.

Điều 1. Phạm vi điều chỉnh
1. Tổ chức nhập khẩu phải chuẩn bị hồ sơ, giấy phép và thực hiện thủ tục hải quan theo quy định.
"""

        parsed = parse_legal_document_text(sample, "sample_legal.txt")

        self.assertEqual(parsed["document_no"], "69/2018/NĐ-CP")
        self.assertIn("NGHỊ ĐỊNH", parsed["title"])
        self.assertIn("nhập khẩu", parsed["title"])
        self.assertEqual(parsed["document_type"], "Nghị định")
        self.assertEqual(parsed["issuing_authority"], "CHÍNH PHỦ")
        self.assertEqual(parsed["issue_date"], "2018-05-15")
        self.assertEqual(parsed["effective_date"], "2018-05-15")
        self.assertIn("customs", parsed["tags"])
        self.assertTrue(parsed["chunks"])
        self.assertEqual(parsed["chunks"][0]["status"], "pending_review")

    def test_pending_review_chunks_are_ignored_by_ai_search(self):
        document_id = save_document(
            {
                "title": "__Pending Review Smoke__",
                "document_no": "SMOKE-001",
                "document_type": "Official Letter",
                "issuing_authority": "TEST",
                "issue_date": "2026-06-22",
                "effective_date": "2026-06-22",
                "expiry_date": "",
                "status": "Active",
                "category": "Customs",
                "source_url": "",
                "file_path": "",
                "summary": "Smoke test only.",
            },
            chunks=[
                {
                    "heading": "Pending only",
                    "content": "unique_pending_clause_for_ai_ignore",
                    "keywords": "unique_pending_clause_for_ai_ignore",
                    "status": "pending_review",
                }
            ],
            tag_names=["customs"],
        )
        self.created_document_ids.append(document_id)

        self.assertFalse(
            any(row["document_id"] == document_id for row in search_chunks("unique_pending_clause_for_ai_ignore"))
        )
        answer = generate_answer("unique_pending_clause_for_ai_ignore")
        self.assertEqual(answer["conclusion"], "Insufficient information in knowledge base.")


if __name__ == "__main__":
    unittest.main()
