import unittest

from typography import DEFAULT_UI_SCALE, get_typography_tokens
from ui_helpers import status_badge_html


class UiHelpersSmokeTest(unittest.TestCase):
    def test_typography_preserves_large_font_default(self):
        tokens = get_typography_tokens(DEFAULT_UI_SCALE)

        self.assertGreaterEqual(tokens["sm"], 20)
        self.assertGreater(tokens["xl"], tokens["lg"])
        self.assertGreater(tokens["xxl"], tokens["xl"])

    def test_status_badge_escapes_label_text(self):
        html = status_badge_html("<script>alert('x')</script>", "red")

        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertIn("ui-status-badge", html)

    def test_status_badge_falls_back_to_neutral_tone(self):
        html = status_badge_html("Unknown", "missing-tone")

        self.assertIn("#1c2636", html)
        self.assertIn("Unknown", html)


if __name__ == "__main__":
    unittest.main()
