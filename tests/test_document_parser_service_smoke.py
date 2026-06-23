import unittest

from database import init_db
from document_parser_service import GeminiParserProvider, OpenAIParserProvider, RegexParserProvider, get_parser_provider, parse_document


class DocumentParserServiceSmokeTest(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_legal_document_structured_output(self):
        text = """
CHINH PHU
So: 69/2018/ND-CP

NGHI DINH
Ve quan ly ngoai thuong, nhap khau, xuat khau va giay phep

Ha Noi, ngay 15 thang 5 nam 2018
Nghi dinh nay co hieu luc tu ngay 15/05/2018.

Dieu 1. Pham vi dieu chinh
1. To chuc nhap khau phai chuan bi ho so, giay phep va thuc hien thu tuc hai quan theo quy dinh.
"""
        parsed = parse_document(text, "sample_decree.txt", provider="Regex")

        self.assertEqual(parsed["document_type"], "DECREE")
        self.assertEqual(parsed["document_no"], "69/2018/ND-CP")
        self.assertEqual(parsed["issue_date"], "2018-05-15")
        self.assertEqual(parsed["effective_date"], "2018-05-15")
        self.assertIn("customs", parsed["tags"])
        self.assertTrue(parsed["key_clauses"])
        self.assertIn(parsed["field_confidence"]["document_type"], ["High", "Medium"])

    def test_commercial_invoice_structured_output(self):
        text = """
COMMERCIAL INVOICE
Invoice No: INV-2026-001
Invoice Date: 2026-06-23
Shipper: Shenzhen Sample Logistics Co., Ltd.
Consignee: 1Aim Logistics
Description of Goods: Cisco firewall model ASA-5506
Total Value: USD 12500
"""
        parsed = parse_document(text, "invoice.txt", provider="Regex")

        self.assertEqual(parsed["document_type"], "COMMERCIAL INVOICE")
        self.assertEqual(parsed["invoice_number"], "INV-2026-001")
        self.assertEqual(parsed["invoice_date"], "2026-06-23")
        self.assertEqual(parsed["currency"], "USD")
        self.assertEqual(parsed["value"], "12500")
        self.assertIn("civil cryptography", parsed["possible_compliance_topics"])
        self.assertEqual(parsed["parser_engine"], "regex")

    def test_provider_abstraction_and_ai_stub_fallback(self):
        self.assertIsInstance(get_parser_provider("Regex"), RegexParserProvider)
        self.assertIsInstance(get_parser_provider("OpenAI"), OpenAIParserProvider)
        self.assertIsInstance(get_parser_provider("Gemini"), GeminiParserProvider)

        parsed = parse_document("COMMERCIAL INVOICE\nInvoice No: INV-1", "invoice.txt", provider="OpenAI")
        self.assertEqual(parsed["document_type"], "COMMERCIAL INVOICE")
        self.assertIn("openai", parsed["parser_engine"])
        self.assertIn("fallback", parsed["parser_engine"])


if __name__ == "__main__":
    unittest.main()
