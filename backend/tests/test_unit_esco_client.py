"""Tests unitaires US-228 — esco_client (cache Supabase + API ESCO, ADR-016).

Vérifie :
  - cache hit : zéro appel réseau (AC3)
  - cache miss : appel API 2 temps (search puis resource/occupation),
    écriture cache, contenu retourné conforme
  - échec réseau simulé : retourne None sans lever (AC4)
  - Supabase indisponible : le profil ESCO reste utilisable (best-effort cache)
  - requête vide : retourne None immédiatement, zéro appel
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.auth.supabase_client import SupabaseConfigError
from app.services import esco_client


def _fake_supabase_client(select_rows):
    """Client Supabase factice : select() renvoie `select_rows`, insert() capture le payload."""
    client = MagicMock()
    client.table.return_value = client
    client.select.return_value = client
    client.eq.return_value = client
    client.limit.return_value = client
    client.execute.return_value = SimpleNamespace(data=select_rows)
    return client


def _fake_urlopen_sequence(*json_bodies):
    """Retourne un mock urlopen renvoyant successivement chaque body JSON."""
    responses = []
    for body in json_bodies:
        resp = MagicMock()
        resp.__enter__.return_value = resp
        resp.__exit__.return_value = False
        resp.read.return_value = json.dumps(body).encode("utf-8")
        responses.append(resp)
    mock = MagicMock(side_effect=responses)
    return mock


_SEARCH_RESPONSE = {
    "_embedded": {
        "results": [
            {"title": "analyste financier/analyste financière", "uri": "http://data.europa.eu/esco/occupation/fake-1"},
        ]
    }
}

_AR_SEARCH_RESPONSE = {
    "_embedded": {
        "results": [
            {"title": "محلل مالي", "uri": "http://data.europa.eu/esco/occupation/fake-1"},
        ]
    }
}

_DETAIL_RESPONSE = {
    "title": "Financial analyst",
    "description": {"fr": {"literal": "Analyse la performance financière des organisations."}},
    "_links": {
        "hasEssentialSkill": [{"title": "analyse financière"}, {"title": "modélisation"}],
        "hasOptionalSkill": [{"title": "veille réglementaire"}],
    },
}


class TestCacheHit:
    def test_cache_hit_makes_zero_network_calls(self):
        cached_row = {
            "occupation_uri": "http://data.europa.eu/esco/occupation/fake-1",
            "label": "analyste financier",
            "lang": "fr",
            "definition": "Analyse la performance financière.",
            "essential_skills": ["analyse financière"],
            "optional_skills": [],
            "source": "esco",
        }
        client = _fake_supabase_client([cached_row])
        with patch("urllib.request.urlopen") as mock_urlopen:
            result = esco_client.get_occupation_profile(
                "Analyste Financier", lang="fr", client=client,
            )
            mock_urlopen.assert_not_called()
        assert result == cached_row


class TestCacheMiss:
    def test_fetches_from_api_and_writes_cache(self):
        client = _fake_supabase_client([])  # cache vide
        with patch(
            "urllib.request.urlopen",
            _fake_urlopen_sequence(_SEARCH_RESPONSE, _DETAIL_RESPONSE),
        ):
            result = esco_client.get_occupation_profile(
                "analyste financier", lang="fr", client=client,
            )

        assert result["occupation_uri"] == "http://data.europa.eu/esco/occupation/fake-1"
        assert result["label"] == "analyste financier"  # terme de recherche normalisé
        assert result["definition"] == "Analyse la performance financière des organisations."
        assert result["essential_skills"] == ["analyse financière", "modélisation"]
        assert result["optional_skills"] == ["veille réglementaire"]
        assert result["source"] == "esco"

        insert_call = client.insert.call_args
        assert insert_call is not None
        assert insert_call.args[0]["label"] == "analyste financier"

    def test_arabic_query_normalized_and_cached(self):
        client = _fake_supabase_client([])
        with patch(
            "urllib.request.urlopen",
            _fake_urlopen_sequence(_AR_SEARCH_RESPONSE, _DETAIL_RESPONSE),
        ):
            result = esco_client.get_occupation_profile("محلل مالي", lang="ar", client=client)
        assert result["label"] == "محلل مالي"
        assert result["lang"] == "ar"

    def test_rejects_non_exact_first_result_without_detail_or_cache_write(self):
        client = _fake_supabase_client([])
        false_positive = {
            "_embedded": {
                "results": [
                    {"title": "convoyeur de fonds/convoyeuse de fonds", "uri": "wrong-uri"},
                ]
            }
        }
        with patch("urllib.request.urlopen", _fake_urlopen_sequence(false_positive)) as urlopen:
            assert esco_client.get_occupation_profile("CTO et co-fondateur", lang="fr", client=client) is None

        assert urlopen.call_count == 1
        assert client.insert.call_args.args[0] == {"label": "cto et co-fondateur", "lang": "fr"}

    def test_uses_exact_second_result_after_rejecting_false_first_result(self):
        client = _fake_supabase_client([])
        search = {
            "_embedded": {
                "results": [
                    {"title": "convoyeur de fonds/convoyeuse de fonds", "uri": "wrong-uri"},
                    {"title": "analyste financier/analyste financière", "uri": "right-uri"},
                ]
            }
        }
        with patch("urllib.request.urlopen", _fake_urlopen_sequence(search, _DETAIL_RESPONSE)) as urlopen:
            result = esco_client.get_occupation_profile("analyste financier", lang="fr", client=client)

        assert urlopen.call_count == 2
        assert result["occupation_uri"] == "right-uri"
        assert client.insert.call_args.args[0]["occupation_uri"] == "right-uri"


class TestNetworkFailure:
    def test_search_network_error_returns_none_without_raising(self):
        import urllib.error

        client = _fake_supabase_client([])
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            result = esco_client.get_occupation_profile("analyste financier", lang="fr", client=client)
        assert result is None
        assert all(call.args != ("occupation_profile_unresolved",) for call in client.table.call_args_list)

    def test_occupation_not_found_returns_none(self):
        client = _fake_supabase_client([])
        empty_search = {"_embedded": {"results": []}}
        with patch("urllib.request.urlopen", _fake_urlopen_sequence(empty_search)):
            result = esco_client.get_occupation_profile("xyzzy-inexistant", lang="fr", client=client)
        assert result is None
        assert client.table.call_args_list[-1].args == ("occupation_profile_unresolved",)

    def test_unresolved_occupation_is_traced_without_network_dependency(self):
        client = _fake_supabase_client([])
        empty_search = {"_embedded": {"results": []}}
        with patch("urllib.request.urlopen", _fake_urlopen_sequence(empty_search)):
            assert esco_client.get_occupation_profile("role inconnu", lang="fr", client=client) is None

        assert client.table.call_args_list[-1].args == ("occupation_profile_unresolved",)
        assert client.insert.call_args.args[0] == {"label": "role inconnu", "lang": "fr"}

    def test_malformed_json_returns_none(self):
        resp = MagicMock()
        resp.__enter__.return_value = resp
        resp.__exit__.return_value = False
        resp.read.return_value = b"not valid json {{{"
        client = _fake_supabase_client([])
        with patch("urllib.request.urlopen", return_value=resp):
            result = esco_client.get_occupation_profile("analyste financier", lang="fr", client=client)
        assert result is None
        assert all(call.args != ("occupation_profile_unresolved",) for call in client.table.call_args_list)

    def test_unexpected_json_shape_is_unavailable_and_not_traced(self):
        client = _fake_supabase_client([])
        with patch("urllib.request.urlopen", _fake_urlopen_sequence(["not", "an", "object"])):
            result = esco_client.get_occupation_profile("analyste financier", lang="fr", client=client)

        assert result is None
        assert all(call.args != ("occupation_profile_unresolved",) for call in client.table.call_args_list)


class TestSupabaseUnavailable:
    def test_config_error_at_lookup_still_returns_fresh_profile(self, monkeypatch):
        monkeypatch.setattr(
            esco_client, "get_supabase_admin",
            lambda: (_ for _ in ()).throw(SupabaseConfigError("not configured")),
        )
        with patch(
            "urllib.request.urlopen",
            _fake_urlopen_sequence(_SEARCH_RESPONSE, _DETAIL_RESPONSE),
        ):
            result = esco_client.get_occupation_profile("analyste financier", lang="fr")
        assert result is not None
        assert result["source"] == "esco"

    def test_cache_write_failure_does_not_break_result(self):
        client = _fake_supabase_client([])
        client.insert.side_effect = RuntimeError("cache write failed")
        with patch(
            "urllib.request.urlopen",
            _fake_urlopen_sequence(_SEARCH_RESPONSE, _DETAIL_RESPONSE),
        ):
            result = esco_client.get_occupation_profile("analyste financier", lang="fr", client=client)
        assert result is not None
        assert result["definition"] == "Analyse la performance financière des organisations."


class TestEmptyQuery:
    def test_empty_string_returns_none_without_any_call(self):
        client = MagicMock()
        with patch("urllib.request.urlopen") as mock_urlopen:
            result = esco_client.get_occupation_profile("   ", lang="fr", client=client)
            mock_urlopen.assert_not_called()
        client.table.assert_not_called()
        assert result is None
