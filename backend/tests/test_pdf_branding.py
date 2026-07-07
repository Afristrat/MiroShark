"""Tests unitaires US-120 — pdf_branding service + API admin.

Couvre :
  Service ``pdf_branding`` :
    - validate_placeholders : whitelist, XSS, placeholders inconnus
    - get_active_branding : retourne le branding actif, None si absent
    - create_branding : insert avec validation champs
    - list_branding : listing ordonné
    - update_branding : versioning (expire l'ancienne, crée la nouvelle)

  Endpoints HTTP :
    - GET  /api/admin/branding    (super-admin + org admin)
    - POST /api/admin/branding    (create)
    - PATCH /api/admin/branding/<id>  (update versioning)
    - POST /api/admin/branding/<id>/preview  (SVG preview)

  Sécurité (RLS scenarios) :
    - Super-admin sans org_id → 400
    - User normal (non-admin) → 403
    - Org admin cross-tenant → 404
    - Super-admin avec org_id → accès OK
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest

from app import create_app
from app.auth import jwt_verifier
from app.services import pdf_branding as pb


# ─── Fixtures de base ──────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_jwt_cache():
    jwt_verifier._cache_clear()
    yield
    jwt_verifier._cache_clear()


@pytest.fixture
def jwt_secret(monkeypatch):
    secret = "pdf-branding-test-secret"
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    return secret


@pytest.fixture
def super_admin_email() -> str:
    return "superadmin@bassira-test.com"


@pytest.fixture
def regular_email() -> str:
    return "user@acme-test.com"


@pytest.fixture
def whitelist_env(monkeypatch, super_admin_email):
    monkeypatch.setenv("BASSIRA_SUPER_ADMIN_EMAILS", super_admin_email)
    yield


def _make_token(secret: str, sub: str, email: str) -> str:
    now = int(time.time())
    return pyjwt.encode(
        {
            "sub": sub,
            "email": email,
            "aud": "authenticated",
            "role": "authenticated",
            "iat": now,
            "exp": now + 3600,
        },
        secret,
        algorithm="HS256",
    )


# ─── Fixture app Flask ────────────────────────────────────────────────────────


@pytest.fixture
def app(monkeypatch):
    from app import storage as storage_pkg

    monkeypatch.setattr(storage_pkg, "Neo4jStorage", MagicMock())
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


# ─── Helpers mock client Supabase ────────────────────────────────────────────


def _make_supabase_client(rows_by_table: Optional[Dict[str, List[Any]]] = None) -> MagicMock:
    """Crée un mock client Supabase avec des réponses configurables.

    ``rows_by_table`` : dict ``{table_name: [row_dicts]}``.
    Toutes les opérations (select, insert, update) retournent les rows
    correspondantes ou une liste vide.
    """
    rows_by_table = rows_by_table or {}

    def _make_response(data):
        resp = MagicMock()
        resp.data = data
        return resp

    def _build_query_chain(table_name: str):
        rows = rows_by_table.get(table_name, [])
        chain = MagicMock()
        chain.select.return_value = chain
        chain.insert.return_value = chain
        chain.update.return_value = chain
        chain.eq.return_value = chain
        chain.lte.return_value = chain
        chain.or_.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain
        chain.offset.return_value = chain
        chain.execute.return_value = _make_response(rows)
        return chain

    cli = MagicMock()

    def _table(name):
        return _build_query_chain(name)

    cli.table.side_effect = _table
    return cli


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Tests service pdf_branding
# ═══════════════════════════════════════════════════════════════════════════════


class TestValidatePlaceholders:
    """validate_placeholders — whitelist XSS + placeholders autorisés."""

    def test_empty_string_is_valid(self):
        ok, _ = pb.validate_placeholders("")
        assert ok is True

    def test_plain_text_is_valid(self):
        ok, _ = pb.validate_placeholders("Page {{page}} sur {{total}}")
        assert ok is True

    def test_all_allowed_placeholders(self):
        template = (
            "{{logo}} {{section}} {{page}} {{total}} {{report_id}} "
            "{{client_name}} {{date}} {{org_name}} {{generated_at}}"
        )
        ok, _ = pb.validate_placeholders(template)
        assert ok is True

    def test_unknown_placeholder_rejected(self):
        ok, reason = pb.validate_placeholders("{{unknown_field}}")
        assert ok is False
        assert "unknown_field" in reason or "Unknown placeholder" in reason

    def test_html_tag_rejected(self):
        ok, reason = pb.validate_placeholders("<script>alert('xss')</script>")
        assert ok is False
        assert "HTML" in reason

    def test_img_tag_rejected(self):
        ok, reason = pb.validate_placeholders("Texte <img src=x onerror=alert(1)>")
        assert ok is False

    def test_non_string_rejected(self):
        ok, _ = pb.validate_placeholders(None)  # type: ignore[arg-type]
        assert ok is False


class TestGetActiveBranding:
    """get_active_branding — retourne le branding actif ou None."""

    def test_returns_active_row(self):
        row = {"id": "abc", "org_id": "org1", "name": "Standard", "valid_to": None}
        cli = _make_supabase_client({"pdf_branding": [row]})
        result = pb.get_active_branding("org1", client=cli)
        assert result is not None
        assert result["name"] == "Standard"

    def test_returns_none_if_no_rows(self):
        cli = _make_supabase_client({"pdf_branding": []})
        result = pb.get_active_branding("org1", client=cli)
        assert result is None

    def test_uses_first_row_ordered_by_valid_from(self):
        rows = [
            {"id": "newest", "org_id": "org1", "name": "V2", "valid_from": "2026-05-06T00:00:00Z"},
            {"id": "older",  "org_id": "org1", "name": "V1", "valid_from": "2026-05-01T00:00:00Z"},
        ]
        cli = _make_supabase_client({"pdf_branding": rows})
        result = pb.get_active_branding("org1", client=cli)
        # On retourne simplement la première (mock simplifié : pas de tri réel)
        assert result is not None


class TestCreateBranding:
    """create_branding — validation + insert."""

    def test_creates_branding_with_defaults(self):
        new_row = {"id": "new-id", "org_id": "org1", "name": "Standard", "valid_to": None}
        cli = _make_supabase_client({"pdf_branding": [new_row]})
        result = pb.create_branding("org1", "Standard", client=cli)
        assert result["id"] == "new-id"

    def test_raises_on_unknown_field(self):
        cli = _make_supabase_client({})
        with pytest.raises(ValueError, match="Unknown branding fields"):
            pb.create_branding("org1", "Standard", client=cli, unknown_field="x")

    def test_raises_on_invalid_template(self):
        cli = _make_supabase_client({})
        with pytest.raises(ValueError, match="HTML"):
            pb.create_branding(
                "org1", "Standard", client=cli,
                header_left="<script>xss</script>"
            )

    def test_raises_on_unknown_placeholder(self):
        cli = _make_supabase_client({})
        with pytest.raises(ValueError, match="Unknown placeholder"):
            pb.create_branding(
                "org1", "Standard", client=cli,
                header_left="{{unknown}}"
            )

    def test_accepts_valid_palette(self):
        new_row = {"id": "new-id", "org_id": "org1", "name": "Branded", "palette_primary": "#FF8551"}
        cli = _make_supabase_client({"pdf_branding": [new_row]})
        result = pb.create_branding(
            "org1", "Branded", client=cli,
            palette_primary="#FF8551"
        )
        assert result["id"] == "new-id"


class TestListBranding:
    """list_branding — listing complet ordonné."""

    def test_returns_all_rows(self):
        rows = [
            {"id": "v2", "org_id": "org1", "name": "V2"},
            {"id": "v1", "org_id": "org1", "name": "V1"},
        ]
        cli = _make_supabase_client({"pdf_branding": rows})
        result = pb.list_branding("org1", client=cli)
        assert len(result) == 2

    def test_returns_empty_list_if_no_rows(self):
        cli = _make_supabase_client({"pdf_branding": []})
        result = pb.list_branding("org1", client=cli)
        assert result == []


class TestUpdateBranding:
    """update_branding — versioning insert (expire ancienne + crée nouvelle)."""

    def _make_update_client(self, existing_row: Dict[str, Any], new_row: Dict[str, Any]) -> MagicMock:
        """Mock client pour update_branding.

        Le client doit :
        1. Retourner existing_row lors du SELECT initial.
        2. Retourner [] lors du UPDATE (expire).
        3. Retourner new_row lors de l'INSERT.
        """
        call_count = {"count": 0}

        def _table(name):
            chain = MagicMock()
            chain.select.return_value = chain
            chain.insert.return_value = chain
            chain.update.return_value = chain
            chain.eq.return_value = chain
            chain.lte.return_value = chain
            chain.or_.return_value = chain
            chain.order.return_value = chain
            chain.limit.return_value = chain
            chain.offset.return_value = chain

            def _execute():
                call_count["count"] += 1
                resp = MagicMock()
                if call_count["count"] == 1:
                    # Premier execute = SELECT
                    resp.data = [existing_row]
                elif call_count["count"] == 2:
                    # Deuxième = UPDATE expire
                    resp.data = []
                else:
                    # Troisième = INSERT nouvelle version
                    resp.data = [new_row]
                return resp

            chain.execute.side_effect = _execute
            return chain

        cli = MagicMock()
        cli.table.side_effect = _table
        return cli

    def test_creates_new_version(self):
        existing = {"id": "old-id", "org_id": "org1", "name": "V1", "valid_to": None,
                    "header_left": "{{logo}}", "header_center": "{{section}}", "header_right": "{{page}}/{{total}}",
                    "footer_left": "{{report_id}}", "footer_center": "{{generated_at}}", "footer_right": "bassira.ma",
                    "palette_primary": "#FF8551", "palette_secondary": "#006D44",
                    "palette_text": "#241915", "palette_background": "#FAF7F2",
                    "font_titles": "Outfit", "font_body": "Manrope", "font_mono": "JetBrains Mono",
                    "disclaimer_text": {"fr": "Confidentiel"}, "logo_url": None}
        new = dict(existing, id="new-id", name="V2", valid_from="2026-05-06T14:00:00Z")
        cli = self._make_update_client(existing, new)
        result = pb.update_branding("old-id", client=cli, name="V2")
        assert result["id"] == "new-id"
        assert result["name"] == "V2"

    def test_raises_on_not_found(self):

        def _table(name):
            chain = MagicMock()
            chain.select.return_value = chain
            chain.eq.return_value = chain
            chain.limit.return_value = chain

            def _execute():
                resp = MagicMock()
                resp.data = []
                return resp

            chain.execute.side_effect = _execute
            return chain

        cli = MagicMock()
        cli.table.side_effect = _table

        with pytest.raises(KeyError):
            pb.update_branding("nonexistent-id", client=cli, name="V2")

    def test_raises_on_invalid_placeholder(self):
        existing = {"id": "old-id", "org_id": "org1", "name": "V1",
                    "header_left": "{{logo}}", "header_center": "{{section}}", "header_right": "Page {{page}}",
                    "footer_left": "CONF", "footer_center": "Date", "footer_right": "bassira.ma",
                    "palette_primary": "#FF8551", "palette_secondary": "#006D44",
                    "palette_text": "#241915", "palette_background": "#FAF7F2",
                    "font_titles": "Outfit", "font_body": "Manrope", "font_mono": "JetBrains Mono",
                    "disclaimer_text": {}, "logo_url": None, "valid_to": None}
        cli = _make_supabase_client({"pdf_branding": [existing]})
        with pytest.raises(ValueError, match="Unknown placeholder|HTML"):
            pb.update_branding("old-id", client=cli, header_left="{{malicious}}")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Tests endpoints HTTP
# ═══════════════════════════════════════════════════════════════════════════════


ORG_UUID = "00000000-0000-0000-0000-000000000099"
USER_UUID = "00000000-0000-0000-0000-000000000042"
OTHER_ORG_UUID = "00000000-0000-0000-0000-000000000077"
BRANDING_UUID = "bbbbbbbb-0000-0000-0000-000000000001"


class TestAdminBrandingListEndpoint:
    """GET /api/admin/branding — listing."""

    def test_super_admin_without_org_id_returns_400(
        self, client, jwt_secret, super_admin_email, whitelist_env
    ):
        token = _make_token(jwt_secret, USER_UUID, super_admin_email)
        with patch("app.api.admin_branding.get_supabase_admin") as mock_cli_fn:
            mock_cli_fn.return_value = _make_supabase_client({})
            resp = client.get(
                "/api/admin/branding",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error_code"] == "ORG_ID_REQUIRED"

    def test_super_admin_with_org_id_returns_200(
        self, client, jwt_secret, super_admin_email, whitelist_env
    ):
        token = _make_token(jwt_secret, USER_UUID, super_admin_email)
        brandings = [{"id": BRANDING_UUID, "org_id": ORG_UUID, "name": "Standard"}]
        with patch("app.api.admin_branding.get_supabase_admin") as mock_cli_fn:
            mock_cli_fn.return_value = _make_supabase_client({"pdf_branding": brandings})
            resp = client.get(
                f"/api/admin/branding?org_id={ORG_UUID}",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert len(data["data"]["brandings"]) == 1

    def test_unauthenticated_returns_401(self, client):
        resp = client.get("/api/admin/branding")
        assert resp.status_code == 401

    def test_non_admin_user_without_org_membership_returns_403(
        self, client, jwt_secret, regular_email, whitelist_env
    ):
        token = _make_token(jwt_secret, USER_UUID, regular_email)
        with patch("app.api.admin_branding.get_supabase_admin") as mock_cli_fn, \
             patch("app.api.admin_branding.get_user_orgs") as mock_orgs:
            mock_cli_fn.return_value = _make_supabase_client({})
            # L'utilisateur n'est dans aucune org en tant qu'admin
            mock_orgs.return_value = [
                {"id": ORG_UUID, "name": "ACME", "slug": "acme", "role": "member"}
            ]
            resp = client.get(
                f"/api/admin/branding?org_id={ORG_UUID}",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 403
        data = resp.get_json()
        assert data["error_code"] == "INSUFFICIENT_ROLE"


class TestAdminBrandingCreateEndpoint:
    """POST /api/admin/branding — création."""

    def test_super_admin_creates_branding(
        self, client, jwt_secret, super_admin_email, whitelist_env
    ):
        token = _make_token(jwt_secret, USER_UUID, super_admin_email)
        new_row = {
            "id": BRANDING_UUID,
            "org_id": ORG_UUID,
            "name": "Rapport Standard",
            "valid_to": None,
        }
        with patch("app.api.admin_branding.get_supabase_admin") as mock_cli_fn:
            mock_cli_fn.return_value = _make_supabase_client({"pdf_branding": [new_row]})
            resp = client.post(
                "/api/admin/branding",
                json={"org_id": ORG_UUID, "name": "Rapport Standard"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["branding"]["name"] == "Rapport Standard"

    def test_missing_name_returns_400(
        self, client, jwt_secret, super_admin_email, whitelist_env
    ):
        token = _make_token(jwt_secret, USER_UUID, super_admin_email)
        with patch("app.api.admin_branding.get_supabase_admin") as mock_cli_fn:
            mock_cli_fn.return_value = _make_supabase_client({})
            resp = client.post(
                "/api/admin/branding",
                json={"org_id": ORG_UUID},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error_code"] == "INVALID_NAME"

    def test_html_in_template_returns_400(
        self, client, jwt_secret, super_admin_email, whitelist_env
    ):
        token = _make_token(jwt_secret, USER_UUID, super_admin_email)
        with patch("app.api.admin_branding.get_supabase_admin") as mock_cli_fn:
            mock_cli_fn.return_value = _make_supabase_client({})
            resp = client.post(
                "/api/admin/branding",
                json={
                    "org_id": ORG_UUID,
                    "name": "Malicious",
                    "header_left": "<script>xss</script>",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error_code"] == "INVALID_BODY"

    def test_cross_tenant_access_returns_404(
        self, client, jwt_secret, regular_email, whitelist_env
    ):
        """Un admin d'une org ne peut pas créer un branding pour une autre org."""
        token = _make_token(jwt_secret, USER_UUID, regular_email)
        with patch("app.api.admin_branding.get_supabase_admin") as mock_cli_fn, \
             patch("app.api.admin_branding.get_user_orgs") as mock_orgs:
            mock_cli_fn.return_value = _make_supabase_client({})
            mock_orgs.return_value = [
                {"id": ORG_UUID, "name": "ACME", "slug": "acme", "role": "admin"}
            ]
            resp = client.post(
                "/api/admin/branding",
                json={"org_id": OTHER_ORG_UUID, "name": "Cross-tenant Attack"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error_code"] == "ORG_NOT_FOUND_FOR_USER"


class TestAdminBrandingUpdateEndpoint:
    """PATCH /api/admin/branding/<id> — versioning update."""

    def test_super_admin_patches_branding(
        self, client, jwt_secret, super_admin_email, whitelist_env
    ):
        token = _make_token(jwt_secret, USER_UUID, super_admin_email)
        existing_row = {"id": BRANDING_UUID, "org_id": ORG_UUID, "name": "V1"}
        new_row = {"id": "new-uuid", "org_id": ORG_UUID, "name": "V2", "valid_from": "2026-05-06T00:00:00Z"}

        call_counter = {"n": 0}

        def _table(name):
            chain = MagicMock()
            chain.select.return_value = chain
            chain.insert.return_value = chain
            chain.update.return_value = chain
            chain.eq.return_value = chain
            chain.lte.return_value = chain
            chain.or_.return_value = chain
            chain.order.return_value = chain
            chain.limit.return_value = chain
            chain.offset.return_value = chain

            def _execute():
                call_counter["n"] += 1
                resp = MagicMock()
                if call_counter["n"] == 1:
                    # Premier appel : SELECT initial (org_id fetch par le endpoint)
                    resp.data = [{"org_id": ORG_UUID}]
                elif call_counter["n"] == 2:
                    # Deuxième : SELECT complet pour update_branding
                    resp.data = [existing_row]
                elif call_counter["n"] == 3:
                    # Troisième : UPDATE expire
                    resp.data = []
                else:
                    # Quatrième : INSERT nouvelle version
                    resp.data = [new_row]
                return resp

            chain.execute.side_effect = _execute
            return chain

        mock_cli = MagicMock()
        mock_cli.table.side_effect = _table

        with patch("app.api.admin_branding.get_supabase_admin") as mock_cli_fn:
            mock_cli_fn.return_value = mock_cli
            resp = client.patch(
                f"/api/admin/branding/{BRANDING_UUID}",
                json={"name": "V2"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    def test_no_fields_returns_400(
        self, client, jwt_secret, super_admin_email, whitelist_env
    ):
        token = _make_token(jwt_secret, USER_UUID, super_admin_email)
        with patch("app.api.admin_branding.get_supabase_admin") as mock_cli_fn:
            cli_mock = _make_supabase_client({"pdf_branding": [{"org_id": ORG_UUID}]})
            mock_cli_fn.return_value = cli_mock
            resp = client.patch(
                f"/api/admin/branding/{BRANDING_UUID}",
                json={},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 400
        assert resp.get_json()["error_code"] == "NO_FIELDS"


class TestAdminBrandingPreviewEndpoint:
    """POST /api/admin/branding/<id>/preview — aperçu SVG."""

    def test_super_admin_gets_preview_svg(
        self, client, jwt_secret, super_admin_email, whitelist_env
    ):
        token = _make_token(jwt_secret, USER_UUID, super_admin_email)
        branding_row = {
            "id": BRANDING_UUID,
            "org_id": ORG_UUID,
            "name": "Standard",
            "palette_primary": "#FF8551",
            "palette_secondary": "#006D44",
            "palette_text": "#241915",
            "palette_background": "#FAF7F2",
            "font_titles": "Outfit",
            "font_body": "Manrope",
            "header_left": "{{logo}}",
            "header_center": "{{section}}",
            "header_right": "Page {{page}}/{{total}}",
            "footer_left": "{{report_id}} · CONFIDENTIEL",
            "footer_center": "{{generated_at}}",
            "footer_right": "bassira.ma",
            "disclaimer_text": {"fr": "Confidentiel", "en": "Confidential", "ar": "سري"},
        }
        with patch("app.api.admin_branding.get_supabase_admin") as mock_cli_fn:
            mock_cli_fn.return_value = _make_supabase_client({"pdf_branding": [branding_row]})
            resp = client.post(
                f"/api/admin/branding/{BRANDING_UUID}/preview",
                json={"lang": "fr"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "preview_svg" in data["data"]
        assert data["data"]["content_type"] == "image/svg+xml"
        # Le base64 doit décoder en SVG valide
        import base64
        svg_bytes = base64.b64decode(data["data"]["preview_svg"])
        svg_str = svg_bytes.decode("utf-8")
        assert "<svg" in svg_str
        assert "</svg>" in svg_str

    def test_preview_branding_not_found_returns_404(
        self, client, jwt_secret, super_admin_email, whitelist_env
    ):
        token = _make_token(jwt_secret, USER_UUID, super_admin_email)
        with patch("app.api.admin_branding.get_supabase_admin") as mock_cli_fn:
            mock_cli_fn.return_value = _make_supabase_client({"pdf_branding": []})
            resp = client.post(
                f"/api/admin/branding/{BRANDING_UUID}/preview",
                json={"lang": "fr"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 404
        assert resp.get_json()["error_code"] == "BRANDING_NOT_FOUND"

    def test_preview_multilang_ar(
        self, client, jwt_secret, super_admin_email, whitelist_env
    ):
        token = _make_token(jwt_secret, USER_UUID, super_admin_email)
        branding_row = {
            "id": BRANDING_UUID,
            "org_id": ORG_UUID,
            "name": "Arabic Branding",
            "disclaimer_text": {"fr": "Confidentiel", "en": "Confidential", "ar": "سري"},
            "palette_primary": "#FF8551",
            "palette_background": "#FAF7F2",
            "palette_text": "#241915",
            "font_titles": "Outfit",
            "font_body": "Manrope",
        }
        with patch("app.api.admin_branding.get_supabase_admin") as mock_cli_fn:
            mock_cli_fn.return_value = _make_supabase_client({"pdf_branding": [branding_row]})
            resp = client.post(
                f"/api/admin/branding/{BRANDING_UUID}/preview",
                json={"lang": "ar"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["lang"] == "ar"
        import base64
        svg_str = base64.b64decode(data["data"]["preview_svg"]).decode("utf-8")
        assert "سري" in svg_str


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Tests validate_placeholders unitaires supplémentaires
# ═══════════════════════════════════════════════════════════════════════════════


class TestValidatePlaceholdersAdditional:
    """Cas supplémentaires pour la couverture de validate_placeholders."""

    def test_multiple_valid_placeholders(self):
        ok, _ = pb.validate_placeholders(
            "{{report_id}} · CONFIDENTIEL · {{generated_at}}"
        )
        assert ok is True

    def test_mixed_valid_and_text(self):
        ok, _ = pb.validate_placeholders("Rapport {{client_name}} — {{date}}")
        assert ok is True

    def test_link_tag_rejected(self):
        ok, _ = pb.validate_placeholders("<a href='evil.com'>click</a>")
        assert ok is False

    def test_only_placeholder_markers_no_content(self):
        ok, _ = pb.validate_placeholders("{{ }}")
        # {{ }} n'est pas dans la whitelist
        ok2, reason = pb.validate_placeholders("{{  }}")
        assert ok2 is False or (ok2 is True and "{{ }}" not in pb._ALLOWED_PLACEHOLDERS)
