"""Frontend static contract and accessibility tests for RA NEXUS portal."""

import re
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


class TestFrontendContract(unittest.TestCase):
    """Verifies that frontend static files adhere to security, accessibility, and DOM contracts."""

    def setUp(self):
        self.client = TestClient(app)

    def test_index_html_serving(self):
        """Test that index.html is served at the root URL with proper branding."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        self.assertIn("Sapthagiri NPS University", response.text)
        self.assertIn("RA NEXUS", response.text)

    def test_static_assets_serving(self):
        """Test that style.css and app.js are served correctly."""
        res_css = self.client.get("/style.css")
        self.assertEqual(res_css.status_code, 200)
        self.assertIn("text/css", res_css.headers.get("content-type", ""))

        res_js = self.client.get("/app.js")
        self.assertEqual(res_js.status_code, 200)
        js_type = res_js.headers.get("content-type", "")
        self.assertTrue(
            "javascript" in js_type,
            f"Expected javascript content type, got {js_type}"
        )

    def test_csp_compliance_no_inline_scripts_or_styles(self):
        """Strict CSP compliance: index.html must not contain inline scripts, styles, or inline handlers."""
        html_path = FRONTEND_DIR / "index.html"
        self.assertTrue(html_path.exists(), "index.html must exist")
        content = html_path.read_text(encoding="utf-8")

        # No inline <script> tags with content
        inline_scripts = re.findall(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", content, re.DOTALL | re.IGNORECASE)
        non_empty_scripts = [s.strip() for s in inline_scripts if s.strip()]
        self.assertEqual(non_empty_scripts, [], "index.html contains forbidden inline script blocks violating CSP")

        # No inline <style> blocks
        inline_styles = re.findall(r"<style[^>]*>(.*?)</style>", content, re.DOTALL | re.IGNORECASE)
        self.assertEqual(inline_styles, [], "index.html contains forbidden inline <style> blocks violating CSP")

        # No inline event handler attributes (e.g. onclick=, onload=)
        inline_handlers = re.findall(r"\son\w+\s*=", content, re.IGNORECASE)
        self.assertEqual(inline_handlers, [], f"index.html contains inline event handlers: {inline_handlers}")

    def test_app_js_dom_ids_exist_in_index_html(self):
        """Verify that every getElementById call in app.js points to an existing element in index.html."""
        js_path = FRONTEND_DIR / "app.js"
        html_path = FRONTEND_DIR / "index.html"
        self.assertTrue(js_path.exists())
        self.assertTrue(html_path.exists())

        js_content = js_path.read_text(encoding="utf-8")
        html_content = html_path.read_text(encoding="utf-8")

        # Extract all IDs referenced via document.getElementById("...")
        referenced_ids = set(re.findall(r'document\.getElementById\(["\']([^"\']+)["\']\)', js_content))
        self.assertGreater(len(referenced_ids), 10, "Expected multiple getElementById calls")

        # Extract all id="..." in index.html
        html_ids = set(re.findall(r'id=["\']([^"\']+)["\']', html_content))

        missing_ids = referenced_ids - html_ids
        self.assertEqual(
            missing_ids,
            set(),
            f"app.js queries IDs that do not exist in index.html: {missing_ids}"
        )

    def test_navigation_views_coherence(self):
        """Verify that all data-view buttons have a matching <view>View section in index.html."""
        html_path = FRONTEND_DIR / "index.html"
        content = html_path.read_text(encoding="utf-8")

        nav_views = set(re.findall(r'data-view=["\']([^"\']+)["\']', content))
        self.assertGreater(len(nav_views), 3)

        for view in nav_views:
            expected_panel_id = f"{view}View"
            self.assertIn(
                f'id="{expected_panel_id}"',
                content,
                f"Missing view panel for navigation tab '{view}'"
            )

    def test_accessibility_landmarks_and_announcers(self):
        """Verify essential accessibility components: skip link, main landmark, live announcer."""
        html_path = FRONTEND_DIR / "index.html"
        content = html_path.read_text(encoding="utf-8")

        self.assertIn('class="skip-link"', content, "Missing skip to main content link")
        self.assertIn('href="#main-content"', content, "Skip link must point to #main-content")
        self.assertIn('id="main-content"', content, "Missing #main-content landmark")
        self.assertIn('id="liveAnnouncer"', content, "Missing screen reader live announcer")
        self.assertIn('aria-live="polite"', content, "Live announcer must have aria-live='polite'")
        self.assertIn('role="log"', content, "Chat messages container must have role='log'")

    def test_quick_action_queries_validity(self):
        """Verify that every chip-card data-query is answered meaningfully by POST /chat."""
        html_path = FRONTEND_DIR / "index.html"
        content = html_path.read_text(encoding="utf-8")
        queries = re.findall(r'data-query=["\']([^"\']+)["\']', content)
        self.assertGreater(len(queries), 3)

        for query in queries:
            response = self.client.post("/chat", json={
                "message": query,
                "student_context": {"branch": "ECE", "section": "1ECE02"}
            })
            self.assertEqual(response.status_code, 200, f"Query '{query}' failed")
            data = response.json()
            self.assertIn("response", data)
            self.assertTrue(len(data["response"]) > 0)

    def test_directory_api_rendered_structure(self):
        """Verify that /api/campus/facilities provides all fields required by directory cards."""
        res = self.client.get("/api/campus/facilities")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        facilities = data.get("facilities", [])
        self.assertGreater(len(facilities), 0)
        for fac in facilities:
            self.assertIn("title", fac)
            self.assertIn("location", fac)
            self.assertIn("category", fac)
            self.assertEqual(fac.get("verification_status"), "verified")

    def test_next_class_simulation_workflow(self):
        """Simulate timetable next-class button click flow."""
        res = self.client.get("/api/timetable/next-class?section=1ECE02&client_time=2026-10-12T10:15:00")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["section"], "1ECE02")
        self.assertFalse(data["can_determine"])
        self.assertIn("missing_information", data)


    def test_ra_tech_branding(self):
        """Verify that RA TECH brand identity is present in index.html and headers."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("RA TECH", response.text, "index.html must display RA TECH brand identity")

    def test_about_view_structure(self):
        """Verify that the About RA NEXUS panel has architecture, capabilities, and honest limitations."""
        html_path = FRONTEND_DIR / "index.html"
        content = html_path.read_text(encoding="utf-8")
        self.assertIn('id="aboutView"', content)
        self.assertIn("Deterministic Intent Router", content)
        self.assertIn("Section-Isolated Timetable Engine", content)
        self.assertIn("AST-Sandboxed Safe Calculator", content)
        self.assertIn("Grounded Campus Knowledge Store", content)
        self.assertIn("Isolated Staging Pipeline", content)
        self.assertIn("Honest Operational Disclosures", content)

    def test_staging_status_banner_and_isolation_notice(self):
        """Verify that the timetable portal contains a clear, non-authoritative Stage 5B staging advisory."""
        html_path = FRONTEND_DIR / "index.html"
        content = html_path.read_text(encoding="utf-8")
        self.assertIn('id="timetableStagingBanner"', content)
        self.assertIn("DEVELOPMENT PREVIEW", content)
        self.assertIn("Stage 5B", content)
        self.assertIn("Pending Review", content)


if __name__ == "__main__":
    unittest.main()
