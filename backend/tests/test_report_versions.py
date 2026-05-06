"""Tests unitaires US-127 — Versionning + commentaires rapport.

Couvre (≥ 12 tests) :
  Endpoints HTTP :
    1.  GET  /api/admin/reports/<id>/versions          — liste vide
    2.  GET  /api/admin/reports/<id>/versions          — liste avec données
    3.  POST /api/admin/reports/<id>/versions          — création version OK
    4.  POST /api/admin/reports/<id>/versions          — corps invalide → 400
    5.  GET  /api/admin/reports/<id>/versions/<v>/diff/<other> — diff OK
    6.  GET  /api/admin/reports/<id>/versions/<v>/diff/<other> — version introuvable → 404
    7.  GET  /api/admin/reports/<id>/comments          — liste commentaires vide
    8.  GET  /api/admin/reports/<id>/comments          — filtre resolved=false
    9.  POST /api/admin/reports/<id>/comments          — création OK
    10. POST /api/admin/reports/<id>/comments          — corps vide → 400
    11. PATCH /api/admin/reports/<id>/comments/<cid>   — résolution OK
    12. PATCH /api/admin/reports/<id>/comments/<cid>   — absent → 404
    13. RLS : accès refusé non-admin → 403
    14. Accès non-authentifié → 401

  Service _compute_diff :
    15. Lignes identiques → op=equal
    16. Lignes ajoutées → op=insert
    17. Lignes supprimées → op=delete
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest

from app import create_app
from app.auth import jwt_verifier
from app.api.admin_report_versions import _compute_diff


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures de base
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def _reset_jwt_cache():
    jwt_verifier._cache_clear()
    yield
    jwt_verifier._cache_clear()


@pytest.fixture
def jwt_secret(monkeypatch):
    secret = "versions-test-secret-us127"
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    return secret


@pytest.fixture
def super_admin_email() -> str:
    return "superadmin@bassira-test.com"


@pytest.fixture
def regular_user_email() -> str:
    return "regular@acme-test.com"


@pytest.fixture
def whitelist_env(monkeypatch, super_admin_email):
    monkeypatch.setenv("BASSIRA_SUPER_ADMIN_EMAILS", super_admin_email)
    yield


def _make_token(secret: str, sub: str, email: str) -> str:
    now = int(time.time())
    return pyjwt.encode(
        {
            "sub":   sub,
            "email": email,
            "aud":   "authenticated",
            "role":  "authenticated",
            "iat":   now,
            "exp":   now + 3600,
        },
        secret,
        algorithm="HS256",
    )


@pytest.fixture
def app(monkeypatch):
    from app import storage as storage_pkg
    monkeypatch.setattr(storage_pkg, "Neo4jStorage", MagicMock())
    _app = create_app()
    _app.config["TESTING"] = True
    return _app


@pytest.fixture
def client(app):
    return app.test_client()


# ─── Helpers mock Supabase ───────────────────────────────────────────────────


_REPORT_ID = "report_us127_test00"
_ORG_ID    = "org-uuid-us127"
_VERSION_ID_A = str(uuid.uuid4())
_VERSION_ID_B = str(uuid.uuid4())
_COMMENT_ID   = str(uuid.uuid4())


def _resp(data):
    r = MagicMock()
    r.data = data
    return r


def _chain(default_rows: List[Dict[str, Any]], insert_returns: Optional[List[Dict[str, Any]]] = None):
    c = MagicMock()
    c.select.return_value = c
    c.insert.return_value = c
    c.update.return_value = c
    c.eq.return_value     = c
    c.lte.return_value    = c
    c.order.return_value  = c
    c.limit.return_value  = c
    c.offset.return_value = c
    c.execute.return_value = _resp(insert_returns if insert_returns is not None else default_rows)
    return c


def _version_row(
    version_id: str = _VERSION_ID_A,
    report_id: str = _REPORT_ID,
    version_number: int = 1,
    markdown_content: str = "# Rapport\n\nPremière version.",
    comment: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "version_id":       version_id,
        "report_id":        report_id,
        "version_number":   version_number,
        "markdown_content": markdown_content,
        "created_by":       "actor-uuid-001",
        "created_at":       "2026-05-06T10:00:00+00:00",
        "comment":          comment,
    }


def _comment_row(
    comment_id: str = _COMMENT_ID,
    report_id: str = _REPORT_ID,
    resolved: bool = False,
    body: str = "Ceci est un commentaire test.",
) -> Dict[str, Any]:
    return {
        "comment_id":       comment_id,
        "report_id":        report_id,
        "version_id":       None,
        "paragraph_anchor": "section-1",
        "author_id":        "actor-uuid-001",
        "body":             body,
        "resolved":         resolved,
        "created_at":       "2026-05-06T10:00:00+00:00",
    }


def _state_row(
    report_id: str = _REPORT_ID,
    state: str = "DRAFT",
    org_id: str = _ORG_ID,
) -> Dict[str, Any]:
    return {
        "report_id":           report_id,
        "state":               state,
        "current_version":     1,
        "last_transition_at":  "2026-05-06T10:00:00+00:00",
        "last_transition_by":  "actor-uuid-001",
        "locked_by":           None,
        "locked_at":           None,
        "org_id":              org_id,
        "created_at":          "2026-05-06T09:00:00+00:00",
        "updated_at":          "2026-05-06T10:00:00+00:00",
    }


def _make_supabase_mock(
    state_rows: Optional[List[Dict[str, Any]]] = None,
    version_rows: Optional[List[Dict[str, Any]]] = None,
    comment_rows: Optional[List[Dict[str, Any]]] = None,
    version_insert_returns: Optional[List[Dict[str, Any]]] = None,
    comment_insert_returns: Optional[List[Dict[str, Any]]] = None,
    comment_update_returns: Optional[List[Dict[str, Any]]] = None,
) -> MagicMock:
    """Mock Supabase configurable par scénario."""
    state_rows             = state_rows             or []
    version_rows           = version_rows           or []
    comment_rows           = comment_rows           or []

    cli = MagicMock()

    def _table(name: str):
        if name == "report_states":
            return _chain(state_rows)
        if name == "report_versions":
            ir = version_insert_returns
            return _chain(version_rows, insert_returns=ir)
        if name == "report_comments":
            if comment_update_returns is not None:
                return _chain(comment_rows, insert_returns=comment_update_returns)
            ir = comment_insert_returns
            return _chain(comment_rows, insert_returns=ir)
        return _chain([])

    cli.table.side_effect = _table
    return cli


# ═══════════════════════════════════════════════════════════════════════════════
# Tests du service _compute_diff
# ═══════════════════════════════════════════════════════════════════════════════


class TestComputeDiff:
    """Tests unitaires du service diff interne."""

    def test_equal_lines_produce_equal_ops(self):
        """Deux textes identiques → toutes les ops sont 'equal'."""
        text = "Ligne 1\nLigne 2\nLigne 3\n"
        ops = _compute_diff(text, text)
        assert all(op["op"] == "equal" for op in ops)
        assert len(ops) > 0

    def test_added_lines_produce_insert_ops(self):
        """Texte plus long → contient des ops 'insert'."""
        old = "Ligne A\n"
        new = "Ligne A\nLigne B\n"
        ops = _compute_diff(old, new)
        insert_ops = [o for o in ops if o["op"] == "insert"]
        assert len(insert_ops) >= 1
        assert any("Ligne B" in o["text"] for o in insert_ops)

    def test_deleted_lines_produce_delete_ops(self):
        """Texte plus court → contient des ops 'delete'."""
        old = "Ligne A\nLigne B\n"
        new = "Ligne A\n"
        ops = _compute_diff(old, new)
        delete_ops = [o for o in ops if o["op"] == "delete"]
        assert len(delete_ops) >= 1
        assert any("Ligne B" in o["text"] for o in delete_ops)

    def test_empty_old_all_inserts(self):
        """Texte vide ancien → tout est insert."""
        ops = _compute_diff("", "Nouveau contenu\n")
        assert all(op["op"] == "insert" for op in ops if op["text"].strip())

    def test_empty_new_all_deletes(self):
        """Texte vide nouveau → tout est delete."""
        ops = _compute_diff("Ancien contenu\n", "")
        assert all(op["op"] == "delete" for op in ops if op["text"].strip())


# ═══════════════════════════════════════════════════════════════════════════════
# Tests HTTP — Versions
# ═══════════════════════════════════════════════════════════════════════════════


class TestListVersions:
    """GET /api/admin/reports/<id>/versions"""

    def test_list_versions_empty(
        self, client, jwt_secret, whitelist_env, super_admin_email
    ):
        """Liste vide retourne success:true avec tableau vide."""
        token = _make_token(jwt_secret, "actor-uuid-001", super_admin_email)
        mock_cli = _make_supabase_mock(
            state_rows=[_state_row()],
            version_rows=[],
        )

        with patch("app.api.admin_report_versions.get_supabase_admin", return_value=mock_cli), \
             patch("app.services.report_workflow.get_supabase_admin", return_value=mock_cli):
            resp = client.get(
                f"/api/admin/reports/{_REPORT_ID}/versions",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["versions"] == []
        assert data["data"]["count"] == 0

    def test_list_versions_with_data(
        self, client, jwt_secret, whitelist_env, super_admin_email
    ):
        """Liste avec versions existantes retourne les rows."""
        token = _make_token(jwt_secret, "actor-uuid-001", super_admin_email)
        v1 = _version_row(version_id=_VERSION_ID_A, version_number=1)
        v2 = _version_row(version_id=_VERSION_ID_B, version_number=2, comment="révision 2")
        mock_cli = _make_supabase_mock(
            state_rows=[_state_row()],
            version_rows=[v2, v1],  # ordre DESC
        )

        with patch("app.api.admin_report_versions.get_supabase_admin", return_value=mock_cli), \
             patch("app.services.report_workflow.get_supabase_admin", return_value=mock_cli):
            resp = client.get(
                f"/api/admin/reports/{_REPORT_ID}/versions",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["count"] == 2
        assert data["data"]["versions"][0]["version_number"] == 2


class TestCreateVersion:
    """POST /api/admin/reports/<id>/versions"""

    def test_create_version_ok(
        self, client, jwt_secret, whitelist_env, super_admin_email
    ):
        """Création d'une version avec markdown valide → 201."""
        token = _make_token(jwt_secret, "actor-uuid-001", super_admin_email)
        new_v = _version_row(version_id=str(uuid.uuid4()), version_number=1, comment="v1 initiale")
        mock_cli = _make_supabase_mock(
            state_rows=[_state_row()],
            version_rows=[],
            version_insert_returns=[new_v],
        )

        with patch("app.api.admin_report_versions.get_supabase_admin", return_value=mock_cli), \
             patch("app.services.report_workflow.get_supabase_admin", return_value=mock_cli):
            resp = client.post(
                f"/api/admin/reports/{_REPORT_ID}/versions",
                headers={"Authorization": f"Bearer {token}"},
                json={"markdown_content": "# Rapport v1\n\nContenu.", "comment": "v1 initiale"},
            )

        assert resp.status_code == 201
        data = resp.get_json()
        assert data["success"] is True
        assert "version" in data["data"]

    def test_create_version_invalid_body(
        self, client, jwt_secret, whitelist_env, super_admin_email
    ):
        """Corps sans markdown_content → 400."""
        token = _make_token(jwt_secret, "actor-uuid-001", super_admin_email)
        mock_cli = _make_supabase_mock(state_rows=[_state_row()])

        with patch("app.api.admin_report_versions.get_supabase_admin", return_value=mock_cli), \
             patch("app.services.report_workflow.get_supabase_admin", return_value=mock_cli):
            resp = client.post(
                f"/api/admin/reports/{_REPORT_ID}/versions",
                headers={"Authorization": f"Bearer {token}"},
                json={"comment": "sans contenu"},
            )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error_code"] == "INVALID_BODY"


class TestDiffVersions:
    """GET /api/admin/reports/<id>/versions/<v>/diff/<other>"""

    def test_diff_versions_ok(
        self, client, jwt_secret, whitelist_env, super_admin_email
    ):
        """Diff entre deux versions existantes → ops JSON."""
        token = _make_token(jwt_secret, "actor-uuid-001", super_admin_email)
        v1 = _version_row(
            version_id=_VERSION_ID_A,
            version_number=1,
            markdown_content="# V1\n\nAncien contenu.\n",
        )
        v2 = _version_row(
            version_id=_VERSION_ID_B,
            version_number=2,
            markdown_content="# V2\n\nNouveau contenu.\n",
        )

        # Le mock doit retourner la bonne version selon l'ID interrogé
        mock_cli = MagicMock()

        def _table(name: str):
            if name == "report_states":
                return _chain([_state_row()])
            if name == "report_versions":
                # Le mock retourne la bonne version selon l'ordre d'appel
                c = MagicMock()
                c.select.return_value = c
                c.eq.return_value     = c
                c.order.return_value  = c
                c.limit.return_value  = c
                c.offset.return_value = c
                # Premier appel → v1, deuxième → v2
                c.execute.side_effect = [
                    _resp([v1]),
                    _resp([v2]),
                ]
                return c
            return _chain([])

        mock_cli.table.side_effect = _table

        with patch("app.api.admin_report_versions.get_supabase_admin", return_value=mock_cli), \
             patch("app.services.report_workflow.get_supabase_admin", return_value=mock_cli):
            resp = client.get(
                f"/api/admin/reports/{_REPORT_ID}/versions/{_VERSION_ID_A}/diff/{_VERSION_ID_B}",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "diff" in data["data"]
        diff = data["data"]["diff"]
        ops = {op["op"] for op in diff}
        assert ops  # au moins un op

    def test_diff_version_not_found(
        self, client, jwt_secret, whitelist_env, super_admin_email
    ):
        """Version inexistante → 404."""
        token = _make_token(jwt_secret, "actor-uuid-001", super_admin_email)
        mock_cli = MagicMock()

        def _table(name: str):
            if name == "report_states":
                return _chain([_state_row()])
            if name == "report_versions":
                c = MagicMock()
                c.select.return_value = c
                c.eq.return_value     = c
                c.order.return_value  = c
                c.limit.return_value  = c
                c.offset.return_value = c
                c.execute.return_value = _resp([])  # vide → version introuvable
                return c
            return _chain([])

        mock_cli.table.side_effect = _table

        with patch("app.api.admin_report_versions.get_supabase_admin", return_value=mock_cli), \
             patch("app.services.report_workflow.get_supabase_admin", return_value=mock_cli):
            resp = client.get(
                f"/api/admin/reports/{_REPORT_ID}/versions/bad-vid/diff/also-bad",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error_code"] == "VERSION_NOT_FOUND"


# ═══════════════════════════════════════════════════════════════════════════════
# Tests HTTP — Commentaires
# ═══════════════════════════════════════════════════════════════════════════════


class TestListComments:
    """GET /api/admin/reports/<id>/comments"""

    def test_list_comments_empty(
        self, client, jwt_secret, whitelist_env, super_admin_email
    ):
        """Liste vide → success:true."""
        token = _make_token(jwt_secret, "actor-uuid-001", super_admin_email)
        mock_cli = _make_supabase_mock(
            state_rows=[_state_row()],
            comment_rows=[],
        )

        with patch("app.api.admin_report_versions.get_supabase_admin", return_value=mock_cli), \
             patch("app.services.report_workflow.get_supabase_admin", return_value=mock_cli):
            resp = client.get(
                f"/api/admin/reports/{_REPORT_ID}/comments",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["comments"] == []

    def test_list_comments_resolved_filter(
        self, client, jwt_secret, whitelist_env, super_admin_email
    ):
        """Filtre resolved=false retourne les bons commentaires."""
        token = _make_token(jwt_secret, "actor-uuid-001", super_admin_email)
        open_comment = _comment_row(resolved=False)
        mock_cli = _make_supabase_mock(
            state_rows=[_state_row()],
            comment_rows=[open_comment],
        )

        with patch("app.api.admin_report_versions.get_supabase_admin", return_value=mock_cli), \
             patch("app.services.report_workflow.get_supabase_admin", return_value=mock_cli):
            resp = client.get(
                f"/api/admin/reports/{_REPORT_ID}/comments?resolved=false",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["count"] == 1
        assert data["data"]["comments"][0]["resolved"] is False


class TestCreateComment:
    """POST /api/admin/reports/<id>/comments"""

    def test_create_comment_ok(
        self, client, jwt_secret, whitelist_env, super_admin_email
    ):
        """Création commentaire valide → 201."""
        token = _make_token(jwt_secret, "actor-uuid-001", super_admin_email)
        new_comment = _comment_row()
        mock_cli = _make_supabase_mock(
            state_rows=[_state_row()],
            comment_rows=[],
            comment_insert_returns=[new_comment],
        )

        with patch("app.api.admin_report_versions.get_supabase_admin", return_value=mock_cli), \
             patch("app.services.report_workflow.get_supabase_admin", return_value=mock_cli):
            resp = client.post(
                f"/api/admin/reports/{_REPORT_ID}/comments",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "paragraph_anchor": "section-1",
                    "body": "Excellent point, à développer.",
                },
            )

        assert resp.status_code == 201
        data = resp.get_json()
        assert data["success"] is True
        assert "comment" in data["data"]

    def test_create_comment_empty_body(
        self, client, jwt_secret, whitelist_env, super_admin_email
    ):
        """Commentaire sans contenu → 400."""
        token = _make_token(jwt_secret, "actor-uuid-001", super_admin_email)
        mock_cli = _make_supabase_mock(state_rows=[_state_row()])

        with patch("app.api.admin_report_versions.get_supabase_admin", return_value=mock_cli), \
             patch("app.services.report_workflow.get_supabase_admin", return_value=mock_cli):
            resp = client.post(
                f"/api/admin/reports/{_REPORT_ID}/comments",
                headers={"Authorization": f"Bearer {token}"},
                json={"paragraph_anchor": "section-1", "body": ""},
            )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error_code"] == "INVALID_BODY"


class TestPatchComment:
    """PATCH /api/admin/reports/<id>/comments/<cid>"""

    def test_resolve_comment_ok(
        self, client, jwt_secret, whitelist_env, super_admin_email
    ):
        """Résoudre un commentaire existant → 200."""
        token = _make_token(jwt_secret, "actor-uuid-001", super_admin_email)
        resolved_comment = _comment_row(resolved=True)
        mock_cli = _make_supabase_mock(
            state_rows=[_state_row()],
            comment_update_returns=[resolved_comment],
        )

        with patch("app.api.admin_report_versions.get_supabase_admin", return_value=mock_cli), \
             patch("app.services.report_workflow.get_supabase_admin", return_value=mock_cli):
            resp = client.patch(
                f"/api/admin/reports/{_REPORT_ID}/comments/{_COMMENT_ID}",
                headers={"Authorization": f"Bearer {token}"},
                json={"resolved": True},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["comment"]["resolved"] is True

    def test_patch_comment_not_found(
        self, client, jwt_secret, whitelist_env, super_admin_email
    ):
        """Commentaire inexistant → 404."""
        token = _make_token(jwt_secret, "actor-uuid-001", super_admin_email)
        mock_cli = _make_supabase_mock(
            state_rows=[_state_row()],
            comment_update_returns=[],  # update retourne vide
        )

        with patch("app.api.admin_report_versions.get_supabase_admin", return_value=mock_cli), \
             patch("app.services.report_workflow.get_supabase_admin", return_value=mock_cli):
            resp = client.patch(
                f"/api/admin/reports/{_REPORT_ID}/comments/non-existent-id",
                headers={"Authorization": f"Bearer {token}"},
                json={"resolved": True},
            )

        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error_code"] == "COMMENT_NOT_FOUND"


# ═══════════════════════════════════════════════════════════════════════════════
# Tests RLS / Auth
# ═══════════════════════════════════════════════════════════════════════════════


class TestAccessControl:
    """Vérification contrôle d'accès."""

    def test_unauthenticated_returns_401(self, client, jwt_secret, whitelist_env):
        """Sans token → 401."""
        resp = client.get(f"/api/admin/reports/{_REPORT_ID}/versions")
        assert resp.status_code == 401

    def test_non_admin_user_denied(
        self, client, jwt_secret, whitelist_env, regular_user_email
    ):
        """User non-admin de l'org → 403."""
        token = _make_token(jwt_secret, "regular-user-uuid", regular_user_email)
        # L'org du rapport ne correspond à aucune org de l'user
        mock_cli = _make_supabase_mock(state_rows=[_state_row()])

        with patch("app.api.admin_report_versions.get_supabase_admin", return_value=mock_cli), \
             patch("app.services.report_workflow.get_supabase_admin", return_value=mock_cli), \
             patch("app.api.admin_report_versions.get_user_orgs", return_value=[]):
            resp = client.get(
                f"/api/admin/reports/{_REPORT_ID}/versions",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 403
        data = resp.get_json()
        assert data["error_code"] == "ACCESS_DENIED"
