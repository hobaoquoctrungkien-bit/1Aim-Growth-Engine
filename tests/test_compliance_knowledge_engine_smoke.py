import unittest

from database import get_connection, init_db
from knowledge_service import (
    generate_compliance_answer,
    generate_compliance_rule_candidates,
    save_candidate_compliance_rules,
    save_compliance_note,
    save_compliance_rule,
    save_document,
    save_sop,
    search_compliance_rules,
    update_compliance_rule_status,
)


class ComplianceKnowledgeEngineSmokeTest(unittest.TestCase):
    def setUp(self):
        init_db()
        self.group_code = "__TEST_CKE__"
        conn = get_connection()
        conn.execute(
            """
            INSERT OR IGNORE INTO compliance_product_groups (
                name, code, description, managing_authority, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 'Active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            ("Test Compliance Group", self.group_code, "Smoke test only", "Test Authority"),
        )
        self.group_id = conn.execute(
            "SELECT id FROM compliance_product_groups WHERE code = ?",
            (self.group_code,),
        ).fetchone()["id"]
        conn.commit()
        conn.close()
        self.document_ids = []
        self.rule_ids = []
        self.note_ids = []
        self.sop_ids = []

    def tearDown(self):
        conn = get_connection()
        for rule_id in self.rule_ids:
            conn.execute("DELETE FROM compliance_rules WHERE id = ?", (rule_id,))
        for note_id in self.note_ids:
            conn.execute("DELETE FROM compliance_notes WHERE id = ?", (note_id,))
        for sop_id in self.sop_ids:
            conn.execute("DELETE FROM knowledge_sops WHERE id = ?", (sop_id,))
        for document_id in self.document_ids:
            conn.execute("DELETE FROM knowledge_document_tags WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM knowledge_chunks WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM knowledge_documents WHERE id = ?", (document_id,))
        conn.execute("DELETE FROM compliance_keywords WHERE product_group_id = ?", (self.group_id,))
        conn.execute("DELETE FROM compliance_product_groups WHERE id = ?", (self.group_id,))
        conn.commit()
        conn.close()

    def test_missing_approved_legal_basis_returns_insufficient(self):
        note_id = save_compliance_note(
            {
                "title": "__Smoke pending interpretation__",
                "topic": "Firewall",
                "product_group_id": self.group_id,
                "summary": "Firewall may need review.",
                "interpretation": "Interpretation only.",
                "approval_status": "Approved",
            }
        )
        self.note_ids.append(note_id)

        answer = generate_compliance_answer("unique firewall classification", self.group_code)

        self.assertEqual(answer["conclusion"], "Insufficient approved basis in the system.")
        self.assertIn("approved compliance rules", answer["risk_notes"].lower())

    def test_pending_and_rejected_sources_are_ignored(self):
        pending_rule_id = save_compliance_rule(
            {
                "product_group_id": self.group_id,
                "rule_title": "__Smoke pending legal rule__",
                "content": "unique_pending_legal_basis",
                "approval_status": "pending_review",
            }
        )
        rejected_note_id = save_compliance_note(
            {
                "title": "__Smoke rejected note__",
                "product_group_id": self.group_id,
                "summary": "unique_rejected_interpretation",
                "approval_status": "Rejected",
            }
        )
        self.rule_ids.append(pending_rule_id)
        self.note_ids.append(rejected_note_id)

        answer = generate_compliance_answer("unique_pending_legal_basis", self.group_code)

        self.assertEqual(answer["conclusion"], "Insufficient approved basis in the system.")
        self.assertFalse(answer["sources_used"])

    def test_approved_legal_rule_supplies_document_and_article_clause(self):
        document_id = save_document(
            {
                "title": "__Smoke MMDS Decree__",
                "document_no": "SMOKE-MMDS-001",
                "document_type": "Decree",
                "issuing_authority": "Test Authority",
                "effective_date": "2026-06-24",
                "status": "Active",
                "category": "SP_MMDS",
                "summary": "Approved legal basis for smoke firewall import.",
                "related_product_group": self.group_code,
                "approval_status": "Approved",
            },
            chunks=[
                {
                    "article_no": "7",
                    "clause_no": "2",
                    "heading": "Article 7",
                    "content": "unique_approved_firewall_basis requires import permit review.",
                    "keywords": "firewall, permit",
                    "status": "Approved",
                }
            ],
        )
        self.document_ids.append(document_id)
        rule_id = save_compliance_rule(
            {
                "product_group_id": self.group_id,
                "rule_title": "__Smoke firewall permit rule__",
                "legal_document_id": document_id,
                "article_no": "7",
                "clause_no": "2",
                "content": "unique_approved_firewall_basis requires import permit review.",
                "required_documents": "Technical datasheet\nImport permit if applicable",
                "approval_status": "Approved",
            }
        )
        self.rule_ids.append(rule_id)

        answer = generate_compliance_answer("unique_approved_firewall_basis", self.group_code)

        self.assertIn("Approved legal basis", answer["conclusion"])
        self.assertIn("SMOKE-MMDS-001", answer["document_number"])
        self.assertIn("7", answer["article_clause"])
        self.assertIn("2", answer["article_clause"])
        self.assertIn("Technical datasheet", answer["required_documents"])

    def test_generated_rules_default_pending_then_approved_rule_is_used_with_source(self):
        parsed = {
            "issuing_authority": "Test Authority",
            "effective_date": "2026-06-24",
            "confidence_score": "High",
            "key_clauses": [
                {
                    "article_no": "9",
                    "clause_no": "1",
                    "heading": "Article 9",
                    "content": "unique_generated_rule_source requires import license for firewall products.",
                    "keywords": "firewall, import license",
                }
            ],
        }
        candidates = generate_compliance_rule_candidates(parsed, self.group_code)
        self.assertEqual(candidates[0]["approval_status"], "pending_review")

        document_id = save_document(
            {
                "title": "__Smoke Generated Rule Legal__",
                "document_no": "SMOKE-GEN-001",
                "document_type": "Circular",
                "issuing_authority": "Test Authority",
                "category": self.group_code,
                "summary": "Generated rule source.",
                "related_product_group": self.group_code,
                "approval_status": "Approved",
            },
            chunks=[
                {
                    "article_no": "9",
                    "clause_no": "1",
                    "heading": "Article 9",
                    "content": "unique_generated_rule_source requires import license for firewall products.",
                    "keywords": "firewall, import license",
                    "status": "Approved",
                }
            ],
        )
        self.document_ids.append(document_id)
        rule_ids = save_candidate_compliance_rules(document_id, self.group_code, candidates)
        self.rule_ids.extend(rule_ids)

        pending_rules = search_compliance_rules(self.group_code, "unique_generated_rule_source", approved_only=False)
        self.assertEqual(pending_rules[0]["approval_status"], "pending_review")
        self.assertTrue(pending_rules[0]["source_chunk_id"])

        rejected_answer = generate_compliance_answer("unique_generated_rule_source", self.group_code)
        self.assertEqual(rejected_answer["conclusion"], "Insufficient approved basis in the system.")

        update_compliance_rule_status(rule_ids[0], "Approved")
        approved_answer = generate_compliance_answer("unique_generated_rule_source", self.group_code)
        self.assertIn("Approved legal basis", approved_answer["conclusion"])
        self.assertTrue(approved_answer["sources_used"][0]["source_chunk_id"])
        self.assertIn("unique_generated_rule_source", approved_answer["sources_used"][0]["source_content"])

    def test_legal_source_overrides_internal_sop_guidance(self):
        document_id = save_document(
            {
                "title": "__Smoke Override Legal__",
                "document_no": "SMOKE-OVERRIDE-001",
                "document_type": "Circular",
                "issuing_authority": "Test Authority",
                "category": "SP_MMDS",
                "summary": "Legal source says permit is required.",
                "related_product_group": self.group_code,
                "approval_status": "Approved",
            }
        )
        self.document_ids.append(document_id)
        rule_id = save_compliance_rule(
            {
                "product_group_id": self.group_id,
                "rule_title": "__Smoke legal override rule__",
                "legal_document_id": document_id,
                "content": "unique_override_question permit is required by legal source.",
                "approval_status": "Approved",
            }
        )
        sop_id = save_sop(
            {
                "title": "__Smoke conflicting SOP__",
                "purpose": "unique_override_question says permit is not required.",
                "procedure_steps": "Do not follow this if legal source conflicts.",
                "status": "Active",
                "approval_status": "Approved",
            }
        )
        self.rule_ids.append(rule_id)
        self.sop_ids.append(sop_id)

        answer = generate_compliance_answer("unique_override_question", self.group_code)

        self.assertIn("SMOKE-OVERRIDE-001", answer["document_number"])
        self.assertIn("Legal documents override", answer["risk_notes"])


if __name__ == "__main__":
    unittest.main()
