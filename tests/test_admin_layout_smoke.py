import unittest
from pathlib import Path


class AdminLayoutSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_source = Path("app.py").read_text(encoding="utf-8")

    def test_email_settings_is_parent_section(self):
        self.assertIn('with st.expander("Email Settings", expanded=False):', self.app_source)
        self.assertIn('"Email Sending"', self.app_source)
        self.assertIn('"Email Bounce Processing"', self.app_source)
        self.assertIn('"Invalid / Bounced Email Cleanup"', self.app_source)
        self.assertIn('"Email Signature"', self.app_source)
        self.assertNotIn('with st.expander("Email Sending", expanded=False):', self.app_source)
        self.assertNotIn('with st.expander("Email Bounce Processing", expanded=False):', self.app_source)
        self.assertNotIn('with st.expander("Invalid / Bounced Email Cleanup", expanded=False):', self.app_source)
        self.assertNotIn('with st.expander("Email Signature", expanded=False):', self.app_source)

    def test_ui_scale_is_in_system_settings_not_sidebar(self):
        sidebar_start = self.app_source.index("with st.sidebar:")
        menu_start = self.app_source.index('page = st.radio(', sidebar_start)
        sidebar_before_menu = self.app_source[sidebar_start:menu_start]
        system_start = self.app_source.index('with st.expander("System Settings", expanded=False):')
        email_start = self.app_source.index('with st.expander("Email Settings", expanded=False):')
        system_section = self.app_source[system_start:email_start]

        self.assertNotIn('"UI Scale"', sidebar_before_menu)
        self.assertIn('"UI Scale"', system_section)

    def test_daily_capacity_is_in_crm_activation(self):
        system_start = self.app_source.index('with st.expander("System Settings", expanded=False):')
        email_start = self.app_source.index('with st.expander("Email Settings", expanded=False):')
        crm_start = self.app_source.index('with st.expander("CRM Activation", expanded=False):')
        followup_start = self.app_source.index("def show_follow_up_queue():")
        system_section = self.app_source[system_start:email_start]
        crm_section = self.app_source[crm_start:followup_start]

        self.assertNotIn('"Daily Outreach Capacity"', system_section)
        self.assertIn('"Daily Outreach Capacity"', crm_section)


if __name__ == "__main__":
    unittest.main()
