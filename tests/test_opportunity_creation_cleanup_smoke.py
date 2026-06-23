import unittest

from database import (
    create_opportunity,
    delete_test_opportunities,
    get_connection,
    get_test_opportunity_candidates,
    init_db,
)


class OpportunityCreationCleanupSmokeTest(unittest.TestCase):
    def setUp(self):
        init_db()
        self.created_ids = []

    def tearDown(self):
        conn = get_connection()
        for opportunity_id in self.created_ids:
            conn.execute("DELETE FROM tasks WHERE opportunity_id = ?", (opportunity_id,))
            conn.execute("DELETE FROM activities WHERE opportunity_id = ?", (opportunity_id,))
            conn.execute("DELETE FROM vendor_rates WHERE opportunity_id = ?", (opportunity_id,))
            conn.execute("DELETE FROM opportunities WHERE id = ?", (opportunity_id,))
        conn.commit()
        conn.close()

    def test_create_opportunity_shared_function_saves_quote_prep_fields(self):
        result = create_opportunity(
            {
                "opportunity_name": "__Shared Create Smoke__",
                "stage": "Interested",
                "trade_lane": "Ho Chi Minh -> Los Angeles",
                "service_type": "Air Freight",
                "cargo_description": "machine parts",
                "origin": "Ho Chi Minh",
                "destination": "Los Angeles",
                "volume": "3 cbm",
                "weight": "560 kg",
                "container_type": "",
                "quantity": "3 pallets",
                "incoterm": "FOB",
                "quotation_status": "Not Started",
            }
        )
        self.created_ids.append(result["opportunity_id"])

        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM opportunities WHERE id = ?",
            (result["opportunity_id"],),
        ).fetchone()
        conn.close()

        self.assertEqual(row["cargo_description"], "machine parts")
        self.assertEqual(row["origin"], "Ho Chi Minh")
        self.assertEqual(row["destination"], "Los Angeles")
        self.assertEqual(row["weight"], "560 kg")
        self.assertEqual(row["quantity"], "3 pallets")
        self.assertEqual(row["incoterm"], "FOB")
        self.assertEqual(row["quotation_status"], "Not Started")

    def test_clean_test_opportunities_only_deletes_strict_candidates(self):
        test_result = create_opportunity(
            {
                "opportunity_name": "__Need rate test cleanup smoke__",
                "stage": "Interested",
                "potential_revenue": "0",
            }
        )
        keep_result = create_opportunity(
            {
                "opportunity_name": "__Need rate real revenue smoke__",
                "stage": "Interested",
                "potential_revenue": "100",
            }
        )
        self.created_ids.extend([test_result["opportunity_id"], keep_result["opportunity_id"]])

        candidates = get_test_opportunity_candidates()
        candidate_ids = [row["id"] for row in candidates]
        self.assertIn(test_result["opportunity_id"], candidate_ids)
        self.assertNotIn(keep_result["opportunity_id"], candidate_ids)

        deleted = delete_test_opportunities([test_result["opportunity_id"], keep_result["opportunity_id"]])
        self.assertEqual(deleted, 1)
        self.created_ids.remove(test_result["opportunity_id"])

        conn = get_connection()
        deleted_row = conn.execute("SELECT id FROM opportunities WHERE id = ?", (test_result["opportunity_id"],)).fetchone()
        kept_row = conn.execute("SELECT id FROM opportunities WHERE id = ?", (keep_result["opportunity_id"],)).fetchone()
        conn.close()

        self.assertIsNone(deleted_row)
        self.assertIsNotNone(kept_row)


if __name__ == "__main__":
    unittest.main()
