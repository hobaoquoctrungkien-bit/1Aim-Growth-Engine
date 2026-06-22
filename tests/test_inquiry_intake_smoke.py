import shutil
import unittest
from pathlib import Path

from database import create_inquiry_opportunity, get_connection, init_db
from inquiry_intake import build_inquiry_notes, parse_inquiry_text, save_inquiry_files


class InquiryIntakeSmokeTest(unittest.TestCase):
    def setUp(self):
        init_db()
        self.created = {}
        self.created_folder = None

    def tearDown(self):
        conn = get_connection()
        if self.created.get("opportunity_id"):
            conn.execute("DELETE FROM tasks WHERE opportunity_id = ?", (self.created["opportunity_id"],))
            conn.execute("DELETE FROM activities WHERE opportunity_id = ?", (self.created["opportunity_id"],))
            conn.execute("DELETE FROM opportunities WHERE id = ?", (self.created["opportunity_id"],))
        if self.created.get("contact_id"):
            conn.execute("DELETE FROM contacts WHERE id = ?", (self.created["contact_id"],))
        if self.created.get("organization_id"):
            conn.execute("DELETE FROM organizations WHERE id = ?", (self.created["organization_id"],))
        conn.commit()
        conn.close()

        if self.created_folder:
            shutil.rmtree(self.created_folder, ignore_errors=True)

    def test_inquiry_parse_save_files_and_create_opportunity(self):
        raw_email = """
From: Alex Tran <alex@example-forwarder.com>
Subject: Vietnam to Los Angeles air freight quotation

Company: Example Forwarder Ltd
Origin: Ho Chi Minh City
Destination: Los Angeles
Commodity: machine parts
Volume: 560 kg
Please quote air freight and customs clearance.
"""
        attachment_texts = [
            {
                "filename": "packing_list.txt",
                "text": "Cargo: spare parts\nQuantity: 3 pallets",
            }
        ]

        parsed = parse_inquiry_text(raw_email, attachment_texts)

        self.assertEqual(parsed["company_name"], "Example Forwarder Ltd")
        self.assertEqual(parsed["contact_person"], "Alex Tran")
        self.assertEqual(parsed["email"], "alex@example-forwarder.com")
        self.assertEqual(parsed["service_type"], "Air Freight")
        self.assertIn("Ho Chi Minh City", parsed["trade_lane"])
        self.assertEqual(parsed["commodity"], "machine parts")

        folder, saved_files = save_inquiry_files(
            parsed["opportunity_name"],
            [{"filename": "packing list.txt", "content": b"test attachment"}],
        )
        self.created_folder = folder

        self.assertTrue(Path(folder).exists())
        self.assertEqual(len(saved_files), 1)
        self.assertTrue(Path(saved_files[0]).exists())

        record = dict(parsed)
        record["stage"] = "Quote Requested"
        record["attachment_folder"] = folder
        record["attachment_files"] = "\n".join(saved_files)
        record["notes"] = build_inquiry_notes(record, saved_files)

        self.created = create_inquiry_opportunity(record)

        conn = get_connection()
        opportunity = conn.execute(
            "SELECT * FROM opportunities WHERE id = ?",
            (self.created["opportunity_id"],),
        ).fetchone()
        task = conn.execute(
            "SELECT * FROM tasks WHERE opportunity_id = ? AND task_type = 'prepare_quote'",
            (self.created["opportunity_id"],),
        ).fetchone()
        conn.close()

        self.assertIsNotNone(opportunity)
        self.assertEqual(opportunity["stage"], "Quote Requested")
        self.assertEqual(opportunity["service_type"], "Air Freight")
        self.assertIsNotNone(task)
        self.assertEqual(task["status"], "open")


if __name__ == "__main__":
    unittest.main()
