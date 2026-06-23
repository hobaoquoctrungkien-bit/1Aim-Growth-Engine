import unittest

from database import get_connection, init_db
from knowledge_service import generate_answer, save_intelligence, search_intelligence


class KnowledgeIntelligenceSmokeTest(unittest.TestCase):
    def setUp(self):
        init_db()
        self.created_ids = []

    def tearDown(self):
        conn = get_connection()
        for item_id in self.created_ids:
            conn.execute("DELETE FROM knowledge_intelligence WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()

    def test_save_search_and_ai_context_for_intelligence(self):
        item_id = save_intelligence(
            {
                "intelligence_type": "Lessons Learned",
                "title": "__Smoke shipment delay lesson__",
                "entity_name": "Smoke Customer",
                "country": "Vietnam",
                "lane": "China - Vietnam",
                "commodity": "Router",
                "summary": "unique_shipment_delay_lesson",
                "details": "Always confirm import compliance documents before quoting urgent router shipments.",
                "source": "Smoke test",
                "source_type": "Opportunity",
                "source_id": 999001,
                "confidence": "High",
                "tags": "lessons learned, shipment history",
                "status": "Active",
            }
        )
        self.created_ids.append(item_id)

        rows = search_intelligence("unique_shipment_delay_lesson")
        self.assertTrue(any(row["id"] == item_id for row in rows))
        saved = next(row for row in rows if row["id"] == item_id)
        self.assertEqual(saved["source_type"], "Opportunity")
        self.assertEqual(saved["source_id"], 999001)

        answer = generate_answer("unique_shipment_delay_lesson")
        self.assertTrue(any(row["id"] == item_id for row in answer["intelligence"]))
        self.assertIn("Supporting knowledge", answer["conclusion"])


if __name__ == "__main__":
    unittest.main()
