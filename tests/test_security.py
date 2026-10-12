"""Verify security headers and CORS behavior."""
from unittest import TestCase
from service import app


class TestSecurity(TestCase):
    """Security configuration tests."""

    def setUp(self):
        self.client = app.test_client()

    def test_security_headers(self):
        """Return security headers on normal responses."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "SAMEORIGIN")
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])

    def test_https_hsts(self):
        """Return HSTS on HTTPS responses."""
        response = self.client.get("/", base_url="https://localhost")
        self.assertIn("max-age=", response.headers["Strict-Transport-Security"])

    def test_cors_origin(self):
        """Allow browser origins without credential sharing."""
        response = self.client.get("/", headers={"Origin": "https://example.com"})
        self.assertEqual(response.headers["Access-Control-Allow-Origin"], "https://example.com")
        self.assertNotIn("Access-Control-Allow-Credentials", response.headers)

    def test_cors_preflight(self):
        """Allow a JSON update preflight."""
        response = self.client.options("/accounts/1", headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "Content-Type",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("PUT", response.headers["Access-Control-Allow-Methods"])
        self.assertIn("content-type", response.headers["Access-Control-Allow-Headers"].lower())
