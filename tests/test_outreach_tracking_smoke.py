import unittest

from database import (
    find_outreach_reply_match,
    get_connection,
    init_db,
    record_outreach_open,
)


class OutreachTrackingSmokeTest(unittest.TestCase):
    def setUp(self):
        init_db()
        self.created = {"organizations": [], "contacts": [], "leads": [], "campaigns": [], "messages": []}
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO organizations (name, country, created_at, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)", ("__Tracking Org__", "China"))
            org_id = cur.lastrowid
            cur.execute(
                "INSERT INTO contacts (organization_id, name, full_name, email, created_at, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                (org_id, "__Tracking Contact__", "__Tracking Contact__", "tracking@example.com"),
            )
            contact_id = cur.lastrowid
            cur.execute(
                "INSERT INTO leads (organization_id, contact_id, campaign, lead_status, created_at, updated_at) VALUES (?, ?, ?, 'Contacted', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                (org_id, contact_id, "__Tracking Campaign__"),
            )
            lead_id = cur.lastrowid
            cur.execute(
                "INSERT INTO outreach_campaigns (campaign_name, status, created_at, updated_at) VALUES (?, 'Sent', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                ("__Tracking Campaign__",),
            )
            campaign_id = cur.lastrowid
            cur.execute(
                """
                INSERT INTO outreach_messages (
                    campaign_id, lead_id, organization_id, contact_id, email, subject,
                    message_body, tracking_token, status, delivery_status, sent_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Sent', 'Sent', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (
                    campaign_id,
                    lead_id,
                    org_id,
                    contact_id,
                    "tracking@example.com",
                    "Vietnam logistics support",
                    "Hello",
                    "0123456789abcdef0123456789abcdef",
                ),
            )
            message_id = cur.lastrowid
            conn.commit()
        finally:
            conn.close()
        self.created["organizations"].append(org_id)
        self.created["contacts"].append(contact_id)
        self.created["leads"].append(lead_id)
        self.created["campaigns"].append(campaign_id)
        self.created["messages"].append(message_id)

    def tearDown(self):
        conn = get_connection()
        for message_id in self.created["messages"]:
            conn.execute("DELETE FROM outreach_messages WHERE id = ?", (message_id,))
        for campaign_id in self.created["campaigns"]:
            conn.execute("DELETE FROM outreach_campaigns WHERE id = ?", (campaign_id,))
        for lead_id in self.created["leads"]:
            conn.execute("DELETE FROM activities WHERE lead_id = ?", (lead_id,))
            conn.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
        for contact_id in self.created["contacts"]:
            conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        for org_id in self.created["organizations"]:
            conn.execute("DELETE FROM organizations WHERE id = ?", (org_id,))
        conn.commit()
        conn.close()

    def test_open_tracking_sets_opened_at(self):
        result = record_outreach_open("0123456789abcdef0123456789abcdef")
        self.assertTrue(result["ok"])
        conn = get_connection()
        row = conn.execute(
            "SELECT opened_at, delivery_status FROM outreach_messages WHERE tracking_token = ?",
            ("0123456789abcdef0123456789abcdef",),
        ).fetchone()
        conn.close()
        self.assertTrue(row["opened_at"])
        self.assertEqual(row["delivery_status"], "Delivered")

    def test_reply_match_uses_tracking_token_header(self):
        conn = get_connection()
        matched = find_outreach_reply_match(
            conn.cursor(),
            "tracking@example.com",
            "Re: Vietnam logistics support",
            "",
            "<0123456789abcdef0123456789abcdef@1aimgrowthengine.local>",
        )
        conn.close()
        self.assertIsNotNone(matched)
        self.assertEqual(matched["tracking_token"], "0123456789abcdef0123456789abcdef")


if __name__ == "__main__":
    unittest.main()
