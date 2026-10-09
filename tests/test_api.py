"""Integration tests for FastAPI endpoints, security headers, CORS, rate limiting, and validation rules."""

import unittest
from fastapi.testclient import TestClient
from backend.main import app, reset_rate_limiter, RateLimitMiddleware


class TestAPI(unittest.TestCase):
    """Integration test suite for the HTTP API."""

    def setUp(self):
        reset_rate_limiter()
        self.client = TestClient(app)

    def tearDown(self):
        reset_rate_limiter()


    def test_health_check(self):
        """Test the /health status endpoint."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "online")
        self.assertEqual(data["name"], "RA NEXUS")

    def test_security_headers_present(self):
        """Test that essential HTTP security headers are returned without unsafe-inline."""
        response = self.client.get("/health")
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(response.headers.get("X-XSS-Protection"), "1; mode=block")
        csp = response.headers.get("Content-Security-Policy", "")
        self.assertIn("default-src 'self'", csp)
        self.assertNotIn("'unsafe-inline'", csp)

    def test_cors_allowed_origin(self):
        """Test CORS headers on preflight OPTIONS request for authorized origin."""
        response = self.client.options(
            "/chat",
            headers={
                "Origin": "http://127.0.0.1:5500",
                "Access-Control-Request-Method": "POST",
            }
        )
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://127.0.0.1:5500")
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")

    def test_cors_unauthorized_origin_rejected(self):
        """Test that unauthorized origin does not receive access-control-allow-origin."""
        response = self.client.options(
            "/chat",
            headers={
                "Origin": "http://unauthorized-attacker.example.com",
                "Access-Control-Request-Method": "POST",
            }
        )
        self.assertNotIn("access-control-allow-origin", response.headers)


    def test_chat_valid_message(self):
        """Test sending a valid chat message."""
        response = self.client.post("/chat", json={"message": "Where is the library?"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertIn("response", data)

    def test_chat_calculator_query(self):
        """Test sending a calculation through the API."""
        response = self.client.post("/chat", json={"message": "Calculate 15 plus 30"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["type"], "calculator")
        self.assertIn("45", data["response"])

    def test_chat_empty_message_validation(self):
        """Test validation error for empty message payload."""
        response = self.client.post("/chat", json={"message": ""})
        self.assertEqual(response.status_code, 422)

    def test_chat_whitespace_message_validation(self):
        """Test validation error for whitespace-only message."""
        response = self.client.post("/chat", json={"message": "    "})
        self.assertEqual(response.status_code, 422)

    def test_chat_missing_message_field(self):
        """Test validation error when 'message' key is omitted."""
        response = self.client.post("/chat", json={})
        self.assertEqual(response.status_code, 422)

    def test_chat_message_exceeds_max_length(self):
        """Test validation error when message exceeds 2000 characters."""
        long_message = "A" * 2001
        response = self.client.post("/chat", json={"message": long_message})
        self.assertEqual(response.status_code, 422)

    def test_rate_limiter_exceeded(self):
        """Test that exceeding the rate limit window triggers a 429 response."""
        # Find the RateLimitMiddleware instance on app to test limit triggering
        for middleware in app.user_middleware:
            if middleware.cls == RateLimitMiddleware:
                # Send requests from a test client until limit or verify 429 logic
                break

        # Simulate burst exceeding limit on /chat with a specific header/client
        client = TestClient(app)
        got_429 = False
        for _ in range(70):
            res = client.post("/chat", json={"message": "system status"})
            if res.status_code == 429:
                got_429 = True
                break
        self.assertTrue(got_429, "Expected 429 Too Many Requests after burst exceeding 60 requests/min")

    def test_frontend_serving(self):
        """Test that index.html is served at the root URL."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("RA NEXUS", response.text)


if __name__ == "__main__":
    unittest.main()
