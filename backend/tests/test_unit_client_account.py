"""Tests unitaires Lot B — ensure_client_account (compte client multi-tenant).

Couvre :
  - Création complète (auth.users + organizations + org_members) si l'email
    est inconnu.
  - Idempotence : un email déjà membre d'une org retourne l'org existante,
    ne recrée rien, n'envoie pas de nouveau magic link.
  - Re-rattachement des quote_ownership de l'org de repli vers la nouvelle org.
  - Best-effort : toute exception interne est absorbée, jamais propagée.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.services import client_account_service as cas


class TestEnsureClientAccountIdempotence:
    def test_existing_member_returns_existing_org_without_recreating(self, monkeypatch):
        cli = MagicMock()

        monkeypatch.setattr(
            cas, "_find_user_by_email",
            lambda email, *, client: {"id": "user-existing-uuid", "email": email},
        )
        monkeypatch.setattr(
            cas, "_find_org_membership",
            lambda user_id, *, client: {"org_id": "org-existing-uuid", "role": "owner"},
        )
        create_org_mock = MagicMock()
        monkeypatch.setattr(cas, "_create_org_and_membership", create_org_mock)
        send_link_mock = MagicMock()
        monkeypatch.setattr(cas, "_send_magic_link", send_link_mock)

        result = cas.ensure_client_account(
            "karim@example.com", "Karim Bensaid", "Atlas Capital",
            source="calcom_booking", client=cli,
        )

        assert result == {
            "org_id": "org-existing-uuid",
            "user_id": "user-existing-uuid",
            "created": False,
        }
        create_org_mock.assert_not_called()
        send_link_mock.assert_not_called()

    def test_new_email_creates_org_and_sends_magic_link(self, monkeypatch):
        cli = MagicMock()
        monkeypatch.setattr(cas, "_find_user_by_email", lambda email, *, client: None)
        monkeypatch.setattr(
            cas, "_create_org_and_membership",
            lambda email, full_name, org_name, *, client: {
                "org_id": "org-new-uuid", "user_id": "user-new-uuid",
            },
        )
        reattach_mock = MagicMock()
        monkeypatch.setattr(cas, "_reattach_quote_ownership", reattach_mock)
        send_link_mock = MagicMock()
        monkeypatch.setattr(cas, "_send_magic_link", send_link_mock)

        result = cas.ensure_client_account(
            "nouveau@example.com", "Nouveau Client", "Nouvelle Org",
            source="quote_paid", client=cli,
        )

        assert result == {
            "org_id": "org-new-uuid",
            "user_id": "user-new-uuid",
            "created": True,
        }
        reattach_mock.assert_called_once_with(
            "org-new-uuid", "nouveau@example.com", client=cli,
        )
        send_link_mock.assert_called_once_with(
            "nouveau@example.com", "Nouveau Client", "fr", client=cli,
        )

    def test_locale_is_propagated_to_magic_link(self, monkeypatch):
        cli = MagicMock()
        monkeypatch.setattr(cas, "_find_user_by_email", lambda email, *, client: None)
        monkeypatch.setattr(
            cas, "_create_org_and_membership",
            lambda email, full_name, org_name, *, client: {
                "org_id": "org-2", "user_id": "user-2",
            },
        )
        monkeypatch.setattr(cas, "_reattach_quote_ownership", MagicMock())
        send_link_mock = MagicMock()
        monkeypatch.setattr(cas, "_send_magic_link", send_link_mock)

        cas.ensure_client_account(
            "ar-client@example.com", "عميل", "Org", source="quote_paid",
            locale="ar", client=cli,
        )

        send_link_mock.assert_called_once_with(
            "ar-client@example.com", "عميل", "ar", client=cli,
        )

    def test_never_raises_on_internal_error(self, monkeypatch):
        cli = MagicMock()

        def _boom(*a, **kw):
            raise RuntimeError("simulated Supabase outage")

        monkeypatch.setattr(cas, "_find_user_by_email", _boom)

        result = cas.ensure_client_account(
            "erreur@example.com", "X", None, source="calcom_booking", client=cli,
        )

        assert result == {"org_id": None, "user_id": None, "created": False}

    def test_invalid_email_returns_empty_without_calling_anything(self, monkeypatch):
        find_mock = MagicMock()
        monkeypatch.setattr(cas, "_find_user_by_email", find_mock)

        result = cas.ensure_client_account(
            "not-an-email", "X", None, source="calcom_booking", client=MagicMock(),
        )

        assert result == {"org_id": None, "user_id": None, "created": False}
        find_mock.assert_not_called()


class TestSlugify:
    def test_slugify_lowercases_and_strips_special_chars(self):
        assert cas._slugify("Atlas Capital Partners !") == "atlas-capital-partners"

    def test_slugify_empty_falls_back_to_org(self):
        assert cas._slugify("   ") == "org"


class TestUniqueSlug:
    def test_returns_base_slug_when_available(self):
        cli = MagicMock()
        cli.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

        result = cas._unique_slug("atlas-capital", client=cli)

        assert result == "atlas-capital"

    def test_suffixes_on_collision(self):
        cli = MagicMock()
        # Première vérification : collision (une ligne trouvée) ; ensuite libre.
        responses = [
            MagicMock(data=[{"id": "existing"}]),
            MagicMock(data=[]),
        ]
        cli.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = responses

        result = cas._unique_slug("atlas-capital", client=cli)

        assert result.startswith("atlas-capital-")
        assert result != "atlas-capital"
