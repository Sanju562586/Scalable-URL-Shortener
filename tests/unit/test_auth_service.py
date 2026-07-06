"""Unit tests for AuthService — API key creation lifecycle."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.services.auth_service import AuthService
from app.schemas.api_key import APIKeyCreateRequest, APIKeyResponse
from app.models.api_key import APIKey


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def mock_db():
    return MagicMock()


@pytest.fixture()
def service(mock_db):
    svc = AuthService(mock_db)
    svc._repo = MagicMock()
    return svc


def _make_persisted_api_key(id=1, owner="tester", key_hash="abc123") -> APIKey:
    """Build a fake persisted APIKey (simulating what the repo returns after create)."""
    key = APIKey()
    key.id = id
    key.key_hash = key_hash
    key.owner = owner
    key.is_active = True
    key.created_at = datetime.now(tz=timezone.utc)
    return key


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestCreateAPIKey:
    """AuthService.create_api_key() — generates, hashes, and persists an API key."""

    def test_returns_api_key_response(self, service):
        """create_api_key should return an APIKeyResponse schema."""
        persisted = _make_persisted_api_key()
        service._repo.create.return_value = persisted

        req = APIKeyCreateRequest(owner="alice")
        result = service.create_api_key(req)

        assert isinstance(result, APIKeyResponse)

    def test_raw_key_is_64_hex_chars(self, service):
        """The raw key must be 64-character hex (32 bytes → hex)."""
        persisted = _make_persisted_api_key()
        service._repo.create.return_value = persisted

        req = APIKeyCreateRequest(owner="alice")
        result = service.create_api_key(req)

        assert len(result.raw_key) == 64
        assert all(c in "0123456789abcdef" for c in result.raw_key)

    def test_raw_key_is_not_stored(self, service):
        """The APIKey object passed to repo.create should NOT contain the raw key."""
        persisted = _make_persisted_api_key()
        service._repo.create.return_value = persisted

        req = APIKeyCreateRequest(owner="alice")
        result = service.create_api_key(req)

        # Grab the APIKey object passed to repo.create
        created_obj: APIKey = service._repo.create.call_args[0][0]
        # The stored hash should differ from the raw key
        assert created_obj.key_hash != result.raw_key

    def test_stored_hash_matches_sha256_of_raw_key(self, service):
        """The key_hash stored in the DB must be SHA-256 of the raw key."""
        persisted = _make_persisted_api_key()
        service._repo.create.return_value = persisted

        req = APIKeyCreateRequest(owner="bob")
        result = service.create_api_key(req)

        created_obj: APIKey = service._repo.create.call_args[0][0]
        expected_hash = APIKey.hash_key(result.raw_key)
        assert created_obj.key_hash == expected_hash

    def test_owner_is_set_correctly(self, service):
        """The persisted APIKey should have the correct owner name."""
        persisted = _make_persisted_api_key(owner="carol")
        service._repo.create.return_value = persisted

        req = APIKeyCreateRequest(owner="carol")
        result = service.create_api_key(req)

        assert result.owner == "carol"

    def test_api_key_is_active_on_creation(self, service):
        """Newly created API keys must be active."""
        persisted = _make_persisted_api_key()
        service._repo.create.return_value = persisted

        req = APIKeyCreateRequest(owner="dave")
        result = service.create_api_key(req)

        assert result.is_active is True

    def test_repo_commit_is_called(self, service):
        """AuthService must commit the transaction after persisting the key."""
        persisted = _make_persisted_api_key()
        service._repo.create.return_value = persisted

        req = APIKeyCreateRequest(owner="eve")
        service.create_api_key(req)

        service._repo.commit.assert_called_once()

    def test_two_keys_have_different_raw_values(self, service):
        """Each call should produce a unique raw key (cryptographically random)."""
        persisted = _make_persisted_api_key()
        service._repo.create.return_value = persisted

        req = APIKeyCreateRequest(owner="frank")
        r1 = service.create_api_key(req)
        r2 = service.create_api_key(req)

        assert r1.raw_key != r2.raw_key

    def test_response_id_matches_persisted_id(self, service):
        """The response `id` should come from the persisted object, not a placeholder."""
        persisted = _make_persisted_api_key(id=42)
        service._repo.create.return_value = persisted

        req = APIKeyCreateRequest(owner="grace")
        result = service.create_api_key(req)

        assert result.id == 42


# ── Tests: APIKey model helpers ───────────────────────────────────────────────

class TestAPIKeyModelHelpers:
    """Test the static helpers on the APIKey model used by AuthService."""

    def test_generate_raw_key_is_64_chars(self):
        raw = APIKey.generate_raw_key()
        assert len(raw) == 64

    def test_generate_raw_key_is_hex(self):
        raw = APIKey.generate_raw_key()
        int(raw, 16)  # raises ValueError if not valid hex

    def test_hash_key_is_64_char_hex(self):
        hashed = APIKey.hash_key("some_raw_key")
        assert len(hashed) == 64
        assert all(c in "0123456789abcdef" for c in hashed)

    def test_hash_key_is_deterministic(self):
        """Same raw key must always produce the same hash."""
        raw = "my-test-key"
        assert APIKey.hash_key(raw) == APIKey.hash_key(raw)

    def test_different_raw_keys_produce_different_hashes(self):
        assert APIKey.hash_key("key-a") != APIKey.hash_key("key-b")
