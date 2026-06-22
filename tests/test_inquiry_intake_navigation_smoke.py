import unittest
from pathlib import Path


class InquiryIntakeNavigationSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_source = Path("app.py").read_text(encoding="utf-8")

    def test_inquiry_intake_is_inside_opportunities_menu(self):
        menu_start = self.app_source.index('page = st.radio(')
        menu_end = self.app_source.index('previous_parent_page =', menu_start)
        menu_section = self.app_source[menu_start:menu_end]
        self.assertNotIn('"Inquiry Intake"', menu_section)

        opportunities_start = self.app_source.index("def show_opportunities():")
        opportunity_detail_start = self.app_source.index("def show_opportunity_detail", opportunities_start)
        opportunities_section = self.app_source[opportunities_start:opportunity_detail_start]
        self.assertIn("show_inquiry_intake()", opportunities_section)
        self.assertNotIn('st.subheader("Create Opportunity")', opportunities_section)


if __name__ == "__main__":
    unittest.main()
