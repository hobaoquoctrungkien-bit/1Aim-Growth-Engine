import unittest

from database import (
    create_inquiry_opportunity,
    create_quotation_from_opportunity,
    create_quotation_version,
    get_connection,
    get_quotation_detail,
    init_db,
    save_vendor_rate,
    update_quotation_status,
)
from quotation_engine import build_quotation_excel, build_quotation_pdf


class QuotationEngineSmokeTest(unittest.TestCase):
    def setUp(self):
        init_db()
        self.created = create_inquiry_opportunity(
            {
                "opportunity_name": "Quotation Smoke Test",
                "company_name": "Quote Test Forwarder",
                "contact_person": "Alex Quote",
                "email": "quote-smoke@example.com",
                "trade_lane": "Ho Chi Minh City to Los Angeles",
                "service_type": "Air Freight",
                "stage": "Quote Requested",
                "next_action": "Prepare quotation",
            }
        )
        self.quotation_ids = []

    def tearDown(self):
        conn = get_connection()
        for quotation_id in self.quotation_ids:
            conn.execute("DELETE FROM quotation_items WHERE quotation_id = ?", (quotation_id,))
            conn.execute("DELETE FROM activities WHERE quotation_id = ?", (quotation_id,))
            conn.execute("DELETE FROM quotations WHERE id = ?", (quotation_id,))
        opportunity_id = self.created.get("opportunity_id")
        if opportunity_id:
            conn.execute("DELETE FROM vendor_rates WHERE opportunity_id = ?", (opportunity_id,))
            conn.execute("DELETE FROM tasks WHERE opportunity_id = ?", (opportunity_id,))
            conn.execute("DELETE FROM activities WHERE opportunity_id = ?", (opportunity_id,))
            conn.execute("DELETE FROM opportunities WHERE id = ?", (opportunity_id,))
        if self.created.get("contact_id"):
            conn.execute("DELETE FROM contacts WHERE id = ?", (self.created["contact_id"],))
        if self.created.get("organization_id"):
            conn.execute("DELETE FROM organizations WHERE id = ?", (self.created["organization_id"],))
        conn.commit()
        conn.close()

    def test_create_export_version_and_approve_quotation(self):
        opportunity_id = self.created["opportunity_id"]
        save_vendor_rate(
            {
                "opportunity_id": opportunity_id,
                "vendor_type": "Carrier",
                "vendor_name": "Carrier A",
                "charge_type": "Freight",
                "charge_name": "Main freight",
                "basis": "Shipment",
                "currency": "USD",
                "cost_amount": 1000,
                "margin_percent": 20,
            }
        )

        quotation_id = create_quotation_from_opportunity(opportunity_id, currency="USD")
        self.quotation_ids.append(quotation_id)
        quotation = get_quotation_detail(quotation_id)

        self.assertIsNotNone(quotation)
        self.assertEqual(quotation["status"], "Draft")
        self.assertEqual(len(quotation["items"]), 1)
        self.assertEqual(quotation["sell_amount"], 1200)
        self.assertGreater(len(build_quotation_excel(quotation)), 1000)
        self.assertTrue(build_quotation_pdf(quotation).startswith(b"%PDF-1.4"))

        new_version_id = create_quotation_version(quotation_id)
        self.quotation_ids.append(new_version_id)
        new_version = get_quotation_detail(new_version_id)
        self.assertEqual(new_version["version"], 2)
        self.assertEqual(new_version["parent_quotation_id"], quotation_id)

        self.assertTrue(update_quotation_status(new_version_id, "Approved"))
        approved = get_quotation_detail(new_version_id)
        self.assertEqual(approved["status"], "Approved")
        self.assertTrue(approved["approved_at"])

        conn = get_connection()
        opportunity = conn.execute(
            "SELECT stage, status FROM opportunities WHERE id = ?",
            (opportunity_id,),
        ).fetchone()
        conn.close()
        self.assertEqual(opportunity["stage"], "Quoted")
        self.assertEqual(opportunity["status"], "quoted")


if __name__ == "__main__":
    unittest.main()
