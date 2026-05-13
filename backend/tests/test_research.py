"""US-B01 — Tests unitaires endpoints /api/research/*.

Couvre :
  - validation payload (SEED_REQUIRED, SEED_TOO_SHORT/LONG, LANG_UNSUPPORTED,
    DEPTH_HINT_INVALID, SESSION_ID_REQUIRED)
  - 401 sans JWT (héritage @require_auth)
  - 503 KAIROS_NOT_CONFIGURED quand env vide
  - succès POST + propagation 401/429/404 Kairos
  - cache hit (POST identique = pas de 2e appel HTTP)
  - cache 24h sur status=completed
  - fallback in-process si REDIS_URL absent (path par défaut des tests)

Aucun appel réseau réel : ``requests.post`` / ``requests.get`` sont
entièrement monkeypatchés.
"""

from __future__ import annotations

import time
from typing import Any, Dict
from unittest.mock import MagicMock

import jwt as pyjwt
import pytest
import requests

from app import create_app
from app.auth import jwt_verifier
from app.services import kairos_proxy as kx


# ─── Fixtures de base ─────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_jwt_cache():
    jwt_verifier._cache_clear()
    yield
    jwt_verifier._cache_clear()


@pytest.fixture(autouse=True)
def _reset_kairos_cache(monkeypatch):
    """Force la ré-init du singleton cache pour chaque test (les autres
    tests peuvent avoir laissé des entrées in-process)."""
    monkeypatch.setenv("REDIS_URL", "")
    monkeypatch.setattr(kx.Config, "REDIS_URL", "", raising=False)
    kx._reset_cache_for_tests()
    yield
    kx._reset_cache_for_tests()


@pytest.fixture
def jwt_secret(monkeypatch):
    secret = "research-tests-secret-zzz"
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    return secret


@pytest.fixture
def kairos_env(monkeypatch):
    """Pose des KAIROS_* valides pour les tests qui exercent la voie heureuse."""
    url = "https://kairos.test.local/functions/v1"
    key = "bsr_test_key_xxx"
    monkeypatch.setenv("KAIROS_API_URL", url)
    monkeypatch.setenv("KAIROS_API_KEY", key)
    monkeypatch.setattr(kx.Config, "KAIROS_API_URL", url, raising=False)
    monkeypatch.setattr(kx.Config, "KAIROS_API_KEY", key, raising=False)
    return {"url": url, "key": key}


@pytest.fixture
def app(monkeypatch):
    from app import storage as storage_pkg

    class _DummyStorage:
        def __init__(self, *a, **kw):
            pass

    monkeypatch.setattr(storage_pkg, "Neo4jStorage", _DummyStorage)
    app_obj = create_app()
    app_obj.config["TESTING"] = True
    return app_obj


@pytest.fixture
def client(app):
    return app.test_client()


def _make_token(secret: str, sub: str = "uid-research-001",
                email: str = "user@bassira.test") -> str:
    now = int(time.time())
    return pyjwt.encode(
        {
            "sub": sub, "email": email,
            "aud": "authenticated", "role": "authenticated",
            "iat": now, "exp": now + 3600,
        },
        secret,
        algorithm="HS256",
    )


def _auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _seed() -> str:
    return (
        "Réforme du Code du travail au Maroc 2026 : impact sur les "
        "employeurs informels et perception des syndicats."
    )


def _fake_response(status: int, body: Dict[str, Any]) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    resp.json.return_value = body
    return resp


# ─── 1. Auth + config gates ───────────────────────────────────────────────────


class TestResearchAuth:
    def test_post_without_token_is_401(self, client):
        resp = client.post("/api/research/from-seed", json={"seed": _seed(), "lang": "fr"})
        assert resp.status_code == 401
        assert resp.get_json()["error_code"] == "MISSING_AUTH"

    def test_get_without_token_is_401(self, client):
        resp = client.get("/api/research/status?session_id=abc")
        assert resp.status_code == 401

    def test_post_kairos_not_configured_returns_503(self, client, jwt_secret, monkeypatch):
        monkeypatch.setattr(kx.Config, "KAIROS_API_URL", "", raising=False)
        monkeypatch.setattr(kx.Config, "KAIROS_API_KEY", "", raising=False)
        token = _make_token(jwt_secret)
        resp = client.post(
            "/api/research/from-seed",
            json={"seed": _seed(), "lang": "fr"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 503
        assert resp.get_json()["error_code"] == "KAIROS_NOT_CONFIGURED"


# ─── 2. Validation payload ────────────────────────────────────────────────────


class TestResearchValidation:
    def test_seed_required(self, client, jwt_secret, kairos_env):
        token = _make_token(jwt_secret)
        resp = client.post(
            "/api/research/from-seed",
            json={"lang": "fr"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 400
        assert resp.get_json()["error_code"] == "SEED_REQUIRED"

    def test_seed_too_short(self, client, jwt_secret, kairos_env):
        token = _make_token(jwt_secret)
        resp = client.post(
            "/api/research/from-seed",
            json={"seed": "trop court", "lang": "fr"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 400
        assert resp.get_json()["error_code"] == "SEED_TOO_SHORT"

    def test_seed_too_long(self, client, jwt_secret, kairos_env):
        token = _make_token(jwt_secret)
        resp = client.post(
            "/api/research/from-seed",
            json={"seed": "a" * 3001, "lang": "fr"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 400
        assert resp.get_json()["error_code"] == "SEED_TOO_LONG"

    def test_lang_unsupported(self, client, jwt_secret, kairos_env):
        token = _make_token(jwt_secret)
        resp = client.post(
            "/api/research/from-seed",
            json={"seed": _seed(), "lang": "es"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 400
        assert resp.get_json()["error_code"] == "LANG_UNSUPPORTED"

    def test_depth_hint_invalid(self, client, jwt_secret, kairos_env):
        token = _make_token(jwt_secret)
        resp = client.post(
            "/api/research/from-seed",
            json={"seed": _seed(), "lang": "fr", "depth_hint": 5},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 400
        assert resp.get_json()["error_code"] == "DEPTH_HINT_INVALID"

    def test_status_missing_session_id(self, client, jwt_secret, kairos_env):
        token = _make_token(jwt_secret)
        resp = client.get(
            "/api/research/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert resp.get_json()["error_code"] == "SESSION_ID_REQUIRED"


# ─── 3. Voie heureuse + cache ─────────────────────────────────────────────────


class TestResearchHappyPath:
    def test_post_succeeds_and_returns_session_id(
        self, client, jwt_secret, kairos_env, monkeypatch
    ):
        token = _make_token(jwt_secret)
        fake = _fake_response(
            202,
            {"ok": True, "session_id": "sess-uuid-001", "status": "running", "message": "queued"},
        )
        mock_post = MagicMock(return_value=fake)
        monkeypatch.setattr(kx.requests, "post", mock_post)

        resp = client.post(
            "/api/research/from-seed",
            json={"seed": _seed(), "lang": "fr"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["data"]["session_id"] == "sess-uuid-001"
        assert body["data"]["status"] == "running"
        assert body["data"]["cached"] is False
        # Vérifie qu'on a bien envoyé x-api-key
        call_args = mock_post.call_args
        assert call_args.kwargs["headers"]["x-api-key"] == kairos_env["key"]

    def test_post_second_call_with_same_seed_hits_cache(
        self, client, jwt_secret, kairos_env, monkeypatch
    ):
        token = _make_token(jwt_secret)
        fake = _fake_response(
            202, {"ok": True, "session_id": "sess-uuid-002", "status": "running"},
        )
        mock_post = MagicMock(return_value=fake)
        monkeypatch.setattr(kx.requests, "post", mock_post)

        payload = {"seed": _seed(), "lang": "fr"}
        # 1er appel — hit Kairos
        client.post("/api/research/from-seed", json=payload, headers=_auth_headers(token))
        # 2e appel — devrait taper le cache, pas Kairos
        resp = client.post(
            "/api/research/from-seed", json=payload, headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["cached"] is True
        assert mock_post.call_count == 1  # un seul appel HTTP malgré 2 POST

    def test_get_status_running_returns_payload(
        self, client, jwt_secret, kairos_env, monkeypatch
    ):
        token = _make_token(jwt_secret)
        fake = _fake_response(
            200,
            {
                "ok": True,
                "session_id": "sess-uuid-003",
                "status": "running",
                "created_at": "2026-05-13T01:00:00Z",
            },
        )
        monkeypatch.setattr(kx.requests, "get", MagicMock(return_value=fake))
        resp = client.get(
            "/api/research/status?session_id=sess-uuid-003",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["status"] == "running"
        assert body["data"]["cached"] is False

    def test_get_status_completed_is_cached_24h(
        self, client, jwt_secret, kairos_env, monkeypatch
    ):
        token = _make_token(jwt_secret)
        result_payload = {
            "ok": True,
            "session_id": "sess-uuid-004",
            "status": "completed",
            "result": {"topics": [{"label": "Méfiance employeurs"}]},
            "completed_at": "2026-05-13T01:03:00Z",
        }
        mock_get = MagicMock(return_value=_fake_response(200, result_payload))
        monkeypatch.setattr(kx.requests, "get", mock_get)

        # 1er appel — hit Kairos
        r1 = client.get(
            "/api/research/status?session_id=sess-uuid-004",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r1.status_code == 200
        # 2e appel — cache
        r2 = client.get(
            "/api/research/status?session_id=sess-uuid-004",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r2.status_code == 200
        assert r2.get_json()["data"]["cached"] is True
        assert r2.get_json()["data"]["status"] == "completed"
        assert mock_get.call_count == 1


# ─── 4. Erreurs Kairos relayées ──────────────────────────────────────────────


class TestResearchKairosErrors:
    def test_kairos_401_returns_502_invalid_key(
        self, client, jwt_secret, kairos_env, monkeypatch
    ):
        token = _make_token(jwt_secret)
        monkeypatch.setattr(
            kx.requests, "post",
            MagicMock(return_value=_fake_response(401, {"error": "invalid_api_key"})),
        )
        resp = client.post(
            "/api/research/from-seed",
            json={"seed": _seed(), "lang": "fr"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 502
        assert resp.get_json()["error_code"] == "KAIROS_INVALID_KEY"

    def test_kairos_429_returns_429_rate_limited(
        self, client, jwt_secret, kairos_env, monkeypatch
    ):
        token = _make_token(jwt_secret)
        monkeypatch.setattr(
            kx.requests, "post",
            MagicMock(return_value=_fake_response(429, {"error": "rate_limited"})),
        )
        resp = client.post(
            "/api/research/from-seed",
            json={"seed": _seed(), "lang": "fr"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 429
        assert resp.get_json()["error_code"] == "KAIROS_RATE_LIMITED"

    def test_kairos_timeout_returns_504(
        self, client, jwt_secret, kairos_env, monkeypatch
    ):
        token = _make_token(jwt_secret)

        def _raise_timeout(*a, **kw):
            raise requests.exceptions.Timeout("simulated")

        monkeypatch.setattr(kx.requests, "post", _raise_timeout)
        resp = client.post(
            "/api/research/from-seed",
            json={"seed": _seed(), "lang": "fr"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 504
        assert resp.get_json()["error_code"] == "KAIROS_TIMEOUT"

    def test_kairos_connection_error_returns_502_unreachable(
        self, client, jwt_secret, kairos_env, monkeypatch
    ):
        token = _make_token(jwt_secret)

        def _raise_conn(*a, **kw):
            raise requests.exceptions.ConnectionError("dns down")

        monkeypatch.setattr(kx.requests, "post", _raise_conn)
        resp = client.post(
            "/api/research/from-seed",
            json={"seed": _seed(), "lang": "fr"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 502
        assert resp.get_json()["error_code"] == "KAIROS_UNREACHABLE"

    def test_get_status_404_returns_404_session_not_found(
        self, client, jwt_secret, kairos_env, monkeypatch
    ):
        token = _make_token(jwt_secret)
        monkeypatch.setattr(
            kx.requests, "get",
            MagicMock(return_value=_fake_response(404, {"error": "session_not_found"})),
        )
        resp = client.get(
            "/api/research/status?session_id=nope-uuid",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
        assert resp.get_json()["error_code"] == "SESSION_NOT_FOUND"


# ─── 5. Cache helpers unitaires ──────────────────────────────────────────────


class TestCacheKey:
    def test_same_inputs_same_hash(self):
        a = kx.cache_key_from_seed("hello world", "fr", "tech", 1)
        b = kx.cache_key_from_seed("hello world", "fr", "tech", 1)
        assert a == b

    def test_different_lang_differs(self):
        a = kx.cache_key_from_seed("hello world", "fr")
        b = kx.cache_key_from_seed("hello world", "en")
        assert a != b

    def test_depth_changes_hash(self):
        a = kx.cache_key_from_seed("hello world", "fr", depth_hint=0)
        b = kx.cache_key_from_seed("hello world", "fr", depth_hint=2)
        assert a != b


class TestInProcessCache:
    def test_set_get_roundtrip(self):
        cache = kx._TtlCache()
        cache.set("k1", {"hello": "world"}, ttl_s=60)
        assert cache.get("k1") == {"hello": "world"}

    def test_expired_entry_returns_none(self, monkeypatch):
        cache = kx._TtlCache()
        cache.set("k2", {"v": 1}, ttl_s=1)
        # Avance le temps de 2 s
        real_time = time.time
        monkeypatch.setattr(time, "time", lambda: real_time() + 2.0)
        assert cache.get("k2") is None

    def test_miss_returns_none(self):
        cache = kx._TtlCache()
        assert cache.get("not-there") is None
