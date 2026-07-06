"""
Integration tests for the analytics endpoint.
GET /api/v1/analytics/{short_code}
"""

import pytest


class TestAnalyticsEndpoint:
    def _create_url(self, client, auth_headers, url="https://analytics-test.com"):
        resp = client.post(
            "/api/v1/shorten",
            json={"original_url": url},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        return resp.json()["short_code"]

    def test_analytics_returns_summary(self, client, auth_headers):
        code = self._create_url(client, auth_headers)
        # Generate some clicks
        for _ in range(3):
            client.get(f"/{code}", follow_redirects=False)

        resp = client.get(f"/api/v1/analytics/{code}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["short_code"] == code
        assert data["total_clicks"] >= 3
        assert "daily_breakdown" in data
        assert "top_referers" in data

    def test_analytics_unknown_code_is_404(self, client, auth_headers):
        resp = client.get("/api/v1/analytics/unknownxyz", headers=auth_headers)
        assert resp.status_code == 404

    def test_analytics_wrong_owner_is_404(self, client, auth_headers, db):
        """A URL owned by key A should not be readable by key B."""
        from app.models.api_key import APIKey

        # Create a second API key
        raw_b = APIKey.generate_raw_key()
        key_b = APIKey(key_hash=APIKey.hash_key(raw_b), owner="other", is_active=True)
        db.add(key_b)
        db.commit()
        headers_b = {"X-API-Key": raw_b}

        code = self._create_url(client, auth_headers)
        resp = client.get(f"/api/v1/analytics/{code}", headers=headers_b)
        assert resp.status_code == 404

    def test_analytics_zero_clicks(self, client, auth_headers):
        code = self._create_url(client, auth_headers, url="https://zero-clicks.com")
        resp = client.get(f"/api/v1/analytics/{code}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total_clicks"] == 0
