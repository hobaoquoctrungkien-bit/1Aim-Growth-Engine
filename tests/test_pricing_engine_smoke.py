import unittest

from database import (
    apply_pricing_summary_to_opportunity,
    calculate_suggested_sell_rate,
    create_inquiry_opportunity,
    get_connection,
    get_pricing_summary,
    init_db,
    save_vendor_rate,
)


class PricingEngineSmokeTest(unittest.TestCase):
    def setUp(self):
        init_db()
        self.created = create_inquiry_opportunity(
            {
                "opportunity_name": "Pricing Smoke Test",
                "company_name": "Pricing Test Forwarder",
                "contact_person": "Alex Pricing",
                "email": "pricing-smoke@example.com",
                "trade_lane": "Ho Chi Minh City to Los Angeles",
                "service_type": "Air Freight",
                "stage": "Quote Requested",
                "next_action": "Prepare quotation",
            }
        )

    def tearDown(self):
        conn = get_connection()
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

    def test_rate_lines_margin_comparison_and_apply_to_opportunity(self):
        calculated = calculate_suggested_sell_rate(1000, 15, 50)
        self.assertEqual(calculated["cost_amount"], 1000)
        self.assertEqual(calculated["margin_amount"], 200)
        self.assertEqual(calculated["suggested_sell_amount"], 1200)

        opportunity_id = self.created["opportunity_id"]
        carrier_rate_id = save_vendor_rate(
            {
                "opportunity_id": opportunity_id,
                "vendor_type": "Carrier",
                "vendor_name": "Carrier A",
                "charge_type": "Freight",
                "charge_name": "Main freight",
                "currency": "USD",
                "cost_amount": 1000,
                "margin_percent": 15,
                "margin_amount": 50,
                "transit_time": "12 days",
            }
        )
        agent_rate_id = save_vendor_rate(
            {
                "opportunity_id": opportunity_id,
                "vendor_type": "Agent",
                "vendor_name": "Agent B",
                "charge_type": "Freight",
                "charge_name": "Agent all-in",
                "currency": "USD",
                "cost_amount": 1100,
                "margin_percent": 10,
                "margin_amount": 0,
                "transit_time": "10 days",
            }
        )
        local_charge_id = save_vendor_rate(
            {
                "opportunity_id": opportunity_id,
                "vendor_type": "Local Charge",
                "vendor_name": "",
                "charge_type": "Origin",
                "charge_name": "Origin docs",
                "currency": "USD",
                "cost_amount": 40,
                "margin_percent": 25,
            }
        )

        self.assertIsNotNone(carrier_rate_id)
        self.assertIsNotNone(agent_rate_id)
        self.assertIsNotNone(local_charge_id)

        summary = get_pricing_summary(opportunity_id)
        self.assertEqual(len(summary["rates"]), 3)
        self.assertEqual(summary["best_by_currency"]["USD"]["vendor_name"], "Carrier A")
        self.assertEqual(summary["best_by_currency"]["USD"]["suggested_sell_total"], 1250)

        self.assertTrue(apply_pricing_summary_to_opportunity(opportunity_id, "USD"))
        conn = get_connection()
        opportunity = conn.execute(
            "SELECT potential_revenue, potential_profit FROM opportunities WHERE id = ?",
            (opportunity_id,),
        ).fetchone()
        conn.close()

        self.assertEqual(opportunity["potential_revenue"], 1250)
        self.assertEqual(opportunity["potential_profit"], 210)


if __name__ == "__main__":
    unittest.main()
