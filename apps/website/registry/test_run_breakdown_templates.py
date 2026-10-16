from django.template.loader import render_to_string
from django.test import SimpleTestCase


class RunBreakdownTemplateTests(SimpleTestCase):
    def test_shared_shell_preserves_labels_close_controls_and_content(self):
        for name in ("temperature", "kill-delta", "weight", "weapon-kills",
                     "broken-weapons", "activity", "skills", "landmarks", "outpost"):
            with self.subTest(dialog=name):
                html = render_to_string(f"registry/includes/run_breakdowns/{name}.html", {
                    "dialog_id": "example-dialog", "title_id": "example-title",
                    "title": "Example title", "section": "Challenge progress",
                    "description": "Example description", "skills_close": name == "skills",
                    "detail": {"id": "activity-example", "label": "Fish caught", "total": 2},
                })
                self.assertIn('aria-labelledby="example-title"', html)
                self.assertIn('<h2 id="example-title">Example title</h2>', html)
                self.assertIn('aria-label="Close example title"', html)
                self.assertIn("run-breakdown-section-bar", html)
                self.assertIn("data-skills-dialog-close" if name == "skills" else "data-outpost-dialog-close", html)
                self.assertEqual(html.count("<dialog "), 1)
                self.assertEqual(html.count("</dialog>"), 1)

    def test_optional_description_and_escaping(self):
        html = render_to_string("registry/includes/run_breakdowns/base.html", {
            "title": "<script>example</script>", "section": "Activity",
        })
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<p></p>", html)

    def test_footer_keeps_totals_and_coverage_out_of_the_header(self):
        for total, litres, expected in ((0, False, "0 recorded."), (63.75, True, "63.75 L recorded.")):
            with self.subTest(total=total):
                html = render_to_string("registry/includes/run_breakdowns/activity.html", {
                    "detail": {"total": total, "litres": litres, "partial": True},
                })
                header, remainder = html.split("</header>", 1)
                self.assertNotIn(expected, header)
                footer = remainder.split('<footer class="run-breakdown-footer">', 1)[1]
                self.assertIn(expected, footer)
                self.assertIn("Highest amounts first.", footer)
                self.assertIn("Earlier records may be missing.", footer)
                self.assertEqual(html.count("<footer"), 1)

    def test_empty_footer_and_unknown_total_are_not_invented(self):
        self.assertNotIn("<footer", render_to_string("registry/includes/run_breakdowns/footer.html", {}))
        html = render_to_string("registry/includes/run_breakdowns/activity.html", {
            "detail": {"total": None, "partial": True},
        })
        self.assertNotIn("recorded.", html)
        self.assertIn("Earlier records may be missing.", html)
