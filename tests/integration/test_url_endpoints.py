"""
Integration tests for URL endpoints (shorten, redirect, deactivate, list).
Uses in-memory SQLite + fakeredis via conftest fixtures.
"""

import pytest


class TestShortenEndpoint:
    """POST /api/v1/shorten"""

    def test_shorten_creates_url(self, client, auth_headers):
        resp = client.post(
            "/api/v1/shorten",
            json={"original_url": "https://example.com"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "short_code" in data
        assert "short_url" in data
        assert data["original_url"] == "https://example.com"
        assert data["is_active"] is True

    def test_shorten_with_custom_code(self, client, auth_headers):
        resp = client.post(
            "/api/v1/shorten",
            json={"original_url": "https://custom.com", "custom_code": "mycode"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["short_code"] == "mycode"

    def test_shorten_custom_code_conflict(self, client, auth_headers):
        client.post(
            "/api/v1/shorten",
            json={"original_url": "https://a.com", "custom_code": "same"},
            headers=auth_headers,
        )
        resp = client.post(
            "/api/v1/shorten",
            json={"original_url": "https://b.com", "custom_code": "same"},
            headers=auth_headers,
        )
        assert resp.status_code == 409

    def test_shorten_without_api_key_is_401(self, client):
        resp = client.post(
            "/api/v1/shorten",
            json={"original_url": "https://noauth.com"},
        )
        assert resp.status_code == 422  # missing header → validation error

    def test_shorten_invalid_api_key_is_401(self, client):
        resp = client.post(
            "/api/v1/shorten",
            json={"original_url": "https://noauth.com"},
            headers={"X-API-Key": "badkey"},
        )
        assert resp.status_code == 401

    def test_shorten_invalid_url_is_422(self, client, auth_headers):
        resp = client.post(
            "/api/v1/shorten",
            json={"original_url": "not-a-url"},
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestRedirectEndpoint:
    """GET /{short_code}"""

    def test_redirect_follows_to_original(self, client, auth_headers):
        create = client.post(
            "/api/v1/shorten",
            json={"original_url": "https://redirect-target.com"},
            headers=auth_headers,
        )
        code = create.json()["short_code"]
        resp = client.get(f"/{code}", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["location"] == "https://redirect-target.com"

    def test_redirect_unknown_code_is_404(self, client):
        resp = client.get("/zzz999", follow_redirects=False)
        assert resp.status_code == 404

    def test_redirect_records_click(self, client, auth_headers, db):
        create = client.post(
            "/api/v1/shorten",
            json={"original_url": "https://click-test.com"},
            headers=auth_headers,
        )
        code = create.json()["short_code"]
        client.get(f"/{code}", follow_redirects=False)

        from app.models.click import ClickEvent
        clicks = db.query(ClickEvent).all()
        assert len(clicks) >= 1


class TestDeactivateEndpoint:
    """DELETE /api/v1/urls/{short_code}"""

    def test_deactivate_own_url(self, client, auth_headers):
        create = client.post(
            "/api/v1/shorten",
            json={"original_url": "https://todeactivate.com"},
            headers=auth_headers,
        )
        code = create.json()["short_code"]

        resp = client.delete(f"/api/v1/urls/{code}", headers=auth_headers)
        assert resp.status_code == 204

        # Redirect should now be 410
        redirect = client.get(f"/{code}", follow_redirects=False)
        assert redirect.status_code == 410

    def test_deactivate_nonexistent_is_404(self, client, auth_headers):
        resp = client.delete("/api/v1/urls/doesnotexist", headers=auth_headers)
        assert resp.status_code == 404


class TestListURLsEndpoint:
    """GET /api/v1/urls"""

    def test_list_urls_returns_own_urls(self, client, auth_headers):
        for i in range(3):
            client.post(
                "/api/v1/shorten",
                json={"original_url": f"https://example{i}.com"},
                headers=auth_headers,
            )
        resp = client.get("/api/v1/urls", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 3
        assert isinstance(data["items"], list)

    def test_pagination(self, client, auth_headers):
        resp = client.get("/api/v1/urls?page=1&page_size=2", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 2
