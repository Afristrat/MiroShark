"""Tests unitaires US-IQ-04 — CTA de confirmation + templates email localisés."""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.services import intake_service as svc  # noqa: E402


class TestBuildConfirmationCta:
    def test_self_service_fr(self):
        result = svc._build_confirmation_cta("self_service", "fr", None)
        assert "package" in result["cta_html"].lower() or "offre" in result["cta_html"].lower()
        assert result["next_step_label"]

    def test_quote_48h_fr(self):
        result = svc._build_confirmation_cta("quote_48h", "fr", None)
        assert "48" in result["cta_html"]

    def test_meeting_confirms_without_rebooking_link_fr(self):
        """Depuis ADR-IQ-10 bis, l'email meeting part APRÈS réservation
        vérifiée — il ne doit plus jamais contenir de lien de RÉSERVATION
        (Cal.com envoie déjà sa propre confirmation native avec le lien
        Google Meet)."""
        result = svc._build_confirmation_cta("meeting", "fr")
        assert "agenda.ai-mpower.com" not in result["cta_html"]
        assert "Réservez" not in result["cta_html"]
        assert "confirmé" in result["next_step_label"]

    def test_meeting_ignores_calcom_link_argument(self):
        """calcom_link est accepté pour compatibilité de signature mais
        n'est plus utilisé par aucune branche de copy."""
        link = "https://agenda.ai-mpower.com/a.mansouri/entretien-bassira-20-min?intake_session_id=abc"
        result = svc._build_confirmation_cta("meeting", "fr", link)
        assert link not in result["cta_html"]

    def test_meeting_en_locale(self):
        result = svc._build_confirmation_cta("meeting", "en")
        assert "confirmed" in result["next_step_label"].lower()
        assert "book" not in result["cta_html"].lower()

    def test_meeting_ar_locale(self):
        result = svc._build_confirmation_cta("meeting", "ar")
        assert "مؤكَّد" in result["next_step_label"]
        assert "احجز" not in result["cta_html"]

    def test_unknown_route_falls_back_to_quote_48h_copy(self):
        """Filet de sécurité : une route inattendue ne doit jamais lever, ni
        produire un CTA vide — le générique 'devis 48h' est le repli sûr."""
        result = svc._build_confirmation_cta("unexpected_value", "fr", None)
        assert result["cta_html"]


class TestBuildCalcomBookingLink:
    def test_includes_event_type_slug_and_username(self, monkeypatch):
        monkeypatch.setattr(svc.Config, "CALCOM_BOOKER_USERNAME", "a.mansouri")
        monkeypatch.setattr(svc.Config, "CALCOM_EVENT_TYPE_SLUG", "entretien-bassira-20-min")
        link = svc._build_calcom_booking_link("sess-abc-123", "fr")
        assert link.startswith("https://agenda.ai-mpower.com/a.mansouri/entretien-bassira-20-min")
        assert "intake_session_id=sess-abc-123" in link

    def test_locale_propagated_as_query_param(self):
        link_en = svc._build_calcom_booking_link("sess-1", "en")
        link_ar = svc._build_calcom_booking_link("sess-1", "ar")
        assert "lang=en" in link_en
        assert "lang=ar" in link_ar

    def test_fr_locale_maps_to_fr_query_param(self):
        link = svc._build_calcom_booking_link("sess-1", "fr")
        assert "lang=fr" in link

    def test_session_id_url_encoded(self):
        link = svc._build_calcom_booking_link("sess with space", "fr")
        assert "sess with space" not in link
        assert "sess+with+space" in link or "sess%20with%20space" in link
