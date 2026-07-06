"""
Integration tests for the auth endpoint.
POST /api/v1/auth/api-keys
"""

import pytest


class TestAuthEndpoint:
    def test_create_api_key_returns_201(self, client):
        resp = client.post(
            "/api/v1/auth/api-keys",
            json={"owner": "test-user"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "raw_key" in data
        assert len(data["raw_key"]) == 64  # 32 bytes → 64 hex chars
        assert data["owner"] == "test-user"
        assert data["is_active"] is True

    def test_raw_key_is_usable_as_api_key(self, client):
        """A freshly issued key should authenticate successfully on /shorten."""
        create_resp = client.post(
            "/api/v1/auth/api-keys",
            json={"owner": "fresh-user"},
        )
        raw_key = create_resp.json()["raw_key"]

        shorten_resp = client.post(
            "/api/v1/shorten",
            json={"original_url": "https://authenticated.com"},
            headers={"X-API-Key": raw_key},
        )
        assert shorten_resp.status_code == 201

    def test_missing_owner_is_422(self, client):
        resp = client.post("/api/v1/auth/api-keys", json={})
        assert resp.status_code == 422

    def test_empty_owner_is_422(self, client):
        resp = client.post("/api/v1/auth/api-keys", json={"owner": ""})
        assert resp.status_code == 422

    def test_health_check(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
