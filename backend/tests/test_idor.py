"""Tests de sécurité — US-116 — Contrôles d'accès et SSRF (A01 + A10 OWASP).

Couvre :
- A01 : IDOR — les endpoints admin requièrent bien auth (401/403 sans token)
- A01 : Stack trace absente des réponses 500 publiques (A05 info disclosure)
- A10 : SSRF — webhook validate_url() bloque les IP privées
"""

from __future__ import annotations

import importlib

import pytest


@pytest.fixture(scope="module")
def client():
    import app as flask_app_module
    importlib.reload(flask_app_module)
    flask_app = flask_app_module.create_app()
    return flask_app.test_client()


# ─── A01 — Broken Access Control : endpoints admin ─────────────────────────


def test_admin_analytics_requires_auth(client):
    """A01 — GET /api/admin/analytics sans token → 401 ou 503 (pas 200)."""
    r = client.get("/api/admin/analytics")
    assert r.status_code in (401, 503), (
        f"Attendu 401 ou 503 sans token admin, obtenu {r.status_code}"
    )


def test_admin_organizations_requires_super_admin(client):
    """A01 — GET /api/admin/organizations sans JWT → 401."""
    r = client.get("/api/admin/organizations")
    assert r.status_code == 401, (
        f"Attendu 401 sans JWT sur /api/admin/organizations, obtenu {r.status_code}"
    )


def test_admin_simulations_requires_super_admin(client):
    """A01 — GET /api/admin/simulations sans JWT → 401."""
    r = client.get("/api/admin/simulations")
    assert r.status_code == 401, (
        f"Attendu 401 sans JWT sur /api/admin/simulations, obtenu {r.status_code}"
    )


def test_admin_quotes_requires_super_admin(client):
    """A01 — GET /api/admin/quotes sans JWT → 401."""
    r = client.get("/api/admin/quotes")
    assert r.status_code == 401, (
        f"Attendu 401 sans JWT sur /api/admin/quotes, obtenu {r.status_code}"
    )


def test_admin_quotes_patch_requires_super_admin(client):
    """A01 — PATCH /api/admin/quotes/<id>/status sans JWT → 401."""
    r = client.patch(
        "/api/admin/quotes/quote_test123/status",
        json={"status": "reviewing"},
    )
    assert r.status_code == 401, (
        f"Attendu 401 sans JWT sur PATCH /api/admin/quotes/<id>/status, obtenu {r.status_code}"
    )


def test_admin_self_service_patch_requires_super_admin(client):
    """A01 — PATCH /api/admin/organizations/<id>/self-service sans JWT → 401."""
    r = client.patch(
        "/api/admin/organizations/00000000-0000-0000-0000-000000000001/self-service",
        json={"enabled": True},
    )
    assert r.status_code == 401, (
        f"Attendu 401 sans JWT sur PATCH /api/admin/organizations/*/self-service, "
        f"obtenu {r.status_code}"
    )


def test_client_auth_me_requires_jwt(client):
    """A01 — GET /api/client/auth/me sans JWT → 401."""
    r = client.get("/api/client/auth/me")
    assert r.status_code == 401, (
        f"Attendu 401 sans JWT sur /api/client/auth/me, obtenu {r.status_code}"
    )


def test_client_simulations_requires_jwt(client):
    """A01 — GET /api/client/simulations sans JWT → 401."""
    r = client.get("/api/client/simulations")
    assert r.status_code == 401, (
        f"Attendu 401 sans JWT sur /api/client/simulations, obtenu {r.status_code}"
    )


def test_publish_endpoint_requires_admin_token(client):
    """A01 — POST /api/simulation/<id>/publish sans token admin → 401 ou 503."""
    r = client.post(
        "/api/simulation/sim_test123abc/publish",
        json={},
    )
    assert r.status_code in (401, 503), (
        f"Attendu 401/503 sans admin token sur POST /api/simulation/<id>/publish, "
        f"obtenu {r.status_code}"
    )


# ─── A05 — Pas de stack trace dans les réponses publiques ───────────────────


def test_report_404_has_no_traceback(client):
    """A05 — Une réponse 404 sur /api/report/* ne doit pas exposer de traceback."""
    r = client.get("/api/report/report_nonexistent_for_test")
    data = r.get_json() or {}
    assert "traceback" not in data, (
        f"Traceback exposé dans la réponse 404 report : {list(data.keys())}"
    )


def test_report_by_simulation_404_has_no_traceback(client):
    """A05 — Réponse 404 sur /api/report/by-simulation/* sans traceback."""
    r = client.get("/api/report/by-simulation/sim_nonexistent_test")
    data = r.get_json() or {}
    assert "traceback" not in data, (
        f"Traceback exposé dans la réponse : {list(data.keys())}"
    )


def test_simulation_invalid_id_400_has_no_traceback(client):
    """A05 — Un simulation_id invalide retourne 400 sans traceback.

    Le validateur before_request intercepte les IDs avec caractères spéciaux.
    Note : les séquences '../..' sont normalisées par Flask/Werkzeug AVANT
    que before_request soit appelé (protection du routeur). On teste donc
    un ID contenant des caractères invalides selon _SAFE_ID_PATTERN.
    """
    # ID contenant des caractères interdits (espaces, $, !)
    r = client.get("/api/simulation/sim_invalid$id!/config/realtime")
    # Le before_request doit retourner 400 avant d'atteindre le handler
    assert r.status_code == 400, (
        f"Attendu 400 pour un simulation_id invalide, obtenu {r.status_code}"
    )
    data = r.get_json() or {}
    assert "traceback" not in data, (
        f"Traceback exposé dans la réponse 400 : {list(data.keys())}"
    )
    assert data.get("error_code") == "INVALID_SIMULATION_ID"


# ─── A10 — SSRF : webhook validate_url bloque les IP privées ────────────────


def test_webhook_validate_url_blocks_localhost():
    """A10 — validate_url() rejette http://localhost/ (loopback)."""
    from app.services.webhook_service import validate_url
    err = validate_url("http://localhost/path")
    assert err is not None, "validate_url devrait rejeter localhost"
    assert "private" in err.lower() or "internal" in err.lower(), (
        f"Message d'erreur inattendu : {err!r}"
    )


def test_webhook_validate_url_blocks_loopback_ip():
    """A10 — validate_url() rejette http://127.0.0.1/ (loopback IP)."""
    from app.services.webhook_service import validate_url
    err = validate_url("http://127.0.0.1/secret")
    assert err is not None, "validate_url devrait rejeter 127.0.0.1"


def test_webhook_validate_url_blocks_private_10_range():
    """A10 — validate_url() rejette http://10.0.0.1/ (RFC 1918 privé)."""
    from app.services.webhook_service import validate_url
    err = validate_url("http://10.0.0.1/internal")
    assert err is not None, "validate_url devrait rejeter 10.0.0.1"


def test_webhook_validate_url_blocks_private_192_range():
    """A10 — validate_url() rejette http://192.168.1.1/ (RFC 1918 privé)."""
    from app.services.webhook_service import validate_url
    err = validate_url("http://192.168.1.1/")
    assert err is not None, "validate_url devrait rejeter 192.168.1.1"


def test_webhook_validate_url_allows_public_url():
    """A10 — validate_url() accepte une URL publique valide."""
    from app.services.webhook_service import validate_url
    # hooks.slack.com est une IP publique — doit passer la validation schéma
    # (le blocage IP n'intervient que si l'hôte résout vers une IP privée)
    err = validate_url("https://hooks.slack.com/services/test/test/test")
    # On accepte None (OK) ou un message non lié aux IP privées
    if err is not None:
        assert "private" not in err.lower() and "internal" not in err.lower(), (
            f"validate_url rejette à tort une URL publique : {err!r}"
        )


def test_webhook_validate_url_allows_empty():
    """A10 — validate_url('') retourne None (désactivation du webhook)."""
    from app.services.webhook_service import validate_url
    err = validate_url("")
    assert err is None, f"validate_url('') devrait retourner None, obtenu {err!r}"


def test_webhook_validate_url_rejects_non_http():
    """A10 — validate_url() rejette les schémas non-HTTP (ftp://, file://, etc.)."""
    from app.services.webhook_service import validate_url
    for bad_url in ["ftp://example.com", "file:///etc/passwd", "data:text/html,x"]:
        err = validate_url(bad_url)
        assert err is not None, f"validate_url devrait rejeter {bad_url!r}"


# ─── A10 — SSRF : url_fetcher validate_url bloque les IP privées ─────────────


def test_url_fetcher_blocks_private_ips():
    """A10 — url_fetcher._validate_url() rejette les URLs internes."""
    from app.utils.url_fetcher import _validate_url
    import pytest

    for bad_url in [
        "http://127.0.0.1/test",
        "http://10.0.0.1/api",
        "http://192.168.1.100/secret",
    ]:
        with pytest.raises(ValueError, match="private|internal"):
            _validate_url(bad_url)


def test_url_fetcher_blocks_non_http_schemes():
    """A10 — url_fetcher._validate_url() rejette les schémas non-HTTP."""
    from app.utils.url_fetcher import _validate_url
    import pytest

    for bad_url in ["ftp://example.com", "file:///etc/passwd"]:
        with pytest.raises(ValueError):
            _validate_url(bad_url)


# ─── US-206 — IDOR /api/report/* fermé (SECURITY_AUDIT §1.3) ────────────────


from types import SimpleNamespace


SIM_ID = "sim_" + "a" * 12
OWNED_ROW = {"simulation_id": SIM_ID, "org_id": "org-uuid-001", "is_published": False}
PUBLISHED_ROW = {"simulation_id": SIM_ID, "org_id": "org-uuid-001", "is_published": True}


def _fake_report():
    return SimpleNamespace(
        report_id="report_deadbeef1234",
        simulation_id=SIM_ID,
        markdown_content="# fake",
        to_dict=lambda: {"report_id": "report_deadbeef1234", "simulation_id": SIM_ID},
    )


@pytest.fixture
def _report_lookup(monkeypatch):
    """ReportManager résout toujours un rapport factice lié à SIM_ID."""
    from app.services.report_agent import ReportManager

    fake = _fake_report()
    monkeypatch.setattr(ReportManager, "get_report", staticmethod(lambda rid: fake))
    monkeypatch.setattr(
        ReportManager, "get_report_by_simulation", staticmethod(lambda sid: fake),
    )
    return fake


def _patch_owner(monkeypatch, row_or_exc):
    from app.auth import supabase_client as sbc

    if isinstance(row_or_exc, Exception):
        def _raise(sim_id, client=None):
            raise row_or_exc
        monkeypatch.setattr(sbc, "get_simulation_owner", _raise)
    else:
        monkeypatch.setattr(
            sbc, "get_simulation_owner", lambda sim_id, client=None: row_or_exc,
        )


class TestReportIdorClosed:
    """Sim possédée et NON publiée → accès anonyme refusé partout."""

    def test_get_report_anonymous_401(self, client, monkeypatch, _report_lookup):
        _patch_owner(monkeypatch, OWNED_ROW)
        r = client.get("/api/report/report_deadbeef1234")
        assert r.status_code == 401
        assert r.get_json()["error_code"] == "AUTH_REQUIRED"

    def test_download_anonymous_401(self, client, monkeypatch, _report_lookup):
        _patch_owner(monkeypatch, OWNED_ROW)
        r = client.get("/api/report/report_deadbeef1234/download")
        assert r.status_code == 401

    def test_by_simulation_anonymous_401(self, client, monkeypatch, _report_lookup):
        _patch_owner(monkeypatch, OWNED_ROW)
        r = client.get(f"/api/report/by-simulation/{SIM_ID}")
        assert r.status_code == 401

    def test_generate_anonymous_401(self, client, monkeypatch):
        _patch_owner(monkeypatch, OWNED_ROW)
        r = client.post("/api/report/generate", json={"simulation_id": SIM_ID})
        assert r.status_code == 401

    def test_chat_anonymous_401(self, client, monkeypatch):
        _patch_owner(monkeypatch, OWNED_ROW)
        r = client.post(
            "/api/report/chat",
            json={"simulation_id": SIM_ID, "message": "hello"},
        )
        assert r.status_code == 401

    def test_jwt_invalide_401(self, client, monkeypatch, _report_lookup):
        _patch_owner(monkeypatch, OWNED_ROW)
        r = client.get(
            "/api/report/report_deadbeef1234",
            headers={"Authorization": "Bearer not-a-jwt"},
        )
        assert r.status_code == 401
        assert r.get_json()["error_code"] == "INVALID_TOKEN"

    def test_jwt_valide_non_membre_403(self, client, monkeypatch, _report_lookup):
        from app.auth import jwt_verifier
        from app.auth import supabase_client as sbc

        _patch_owner(monkeypatch, OWNED_ROW)
        monkeypatch.setattr(
            jwt_verifier, "verify_supabase_jwt",
            lambda token: {"sub": "user-123", "email": "intrus@example.com"},
        )
        monkeypatch.setattr(
            sbc, "get_user_role_in_org", lambda uid, oid, client=None: None,
        )
        r = client.get(
            "/api/report/report_deadbeef1234",
            headers={"Authorization": "Bearer x.y.z"},
        )
        assert r.status_code == 403
        assert r.get_json()["error_code"] == "FORBIDDEN"

    def test_jwt_membre_200(self, client, monkeypatch, _report_lookup):
        from app.auth import jwt_verifier
        from app.auth import supabase_client as sbc

        _patch_owner(monkeypatch, OWNED_ROW)
        monkeypatch.setattr(
            jwt_verifier, "verify_supabase_jwt",
            lambda token: {"sub": "user-123", "email": "membre@example.com"},
        )
        monkeypatch.setattr(
            sbc, "get_user_role_in_org", lambda uid, oid, client=None: "member",
        )
        r = client.get(
            "/api/report/report_deadbeef1234",
            headers={"Authorization": "Bearer x.y.z"},
        )
        assert r.status_code == 200


class TestReportPublicPathsPreserved:
    """La galerie publique et le mode OSS/legacy ne sont PAS cassés."""

    def test_sim_publiee_lecture_anonyme_ok(self, client, monkeypatch, _report_lookup):
        _patch_owner(monkeypatch, PUBLISHED_ROW)
        r = client.get("/api/report/report_deadbeef1234")
        assert r.status_code == 200

    def test_sim_publiee_generate_reste_ferme(self, client, monkeypatch):
        _patch_owner(monkeypatch, PUBLISHED_ROW)
        r = client.post("/api/report/generate", json={"simulation_id": SIM_ID})
        assert r.status_code == 401

    def test_sim_non_trackee_legacy_ok(self, client, monkeypatch, _report_lookup):
        _patch_owner(monkeypatch, None)
        r = client.get("/api/report/report_deadbeef1234")
        assert r.status_code == 200

    def test_supabase_non_configure_legacy_ok(self, client, monkeypatch, _report_lookup):
        from app.auth.supabase_client import SupabaseConfigError

        _patch_owner(monkeypatch, SupabaseConfigError("not configured"))
        r = client.get("/api/report/report_deadbeef1234")
        assert r.status_code == 200
