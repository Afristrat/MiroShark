# -*- coding: utf-8 -*-
"""US-203 — payload riche des devis dans Supabase (source de vérité).

Couvre :
  * ``link_quote_to_org(payload=...)`` transmet le payload à l'insert.
  * ``get_quote_payload_from_supabase`` : trouvé / vide / erreur.
  * ``list_quotes_with_payload`` : page + total, fail-soft → None.
  * ``read_quote_payload`` : Supabase d'abord, filesystem en repli.
  * ``list_quotes`` : Supabase d'abord, repli filesystem legacy.
  * ``submit_quote`` : double persistance — 500 UNIQUEMENT si les deux
    échouent ; le fichier n'est plus bloquant quand Supabase a réussi.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import quote_admin_service as qa
from app.services import quote_ownership as qo
from app.services import quote_service as qs


# ─── Stubs Supabase dédiés (chaînes fluent minimales) ────────────────────────


class _Resp:
    def __init__(self, data: Any, count: Optional[int] = None) -> None:
        self.data = data
        self.count = count


class _Chain:
    """Chaîne fluent qui absorbe select/eq/order/range/limit/insert et
    renvoie une réponse préconfigurée à ``execute()``."""

    def __init__(self, resp: _Resp, sink: Optional[Dict[str, Any]] = None,
                 raises: Optional[Exception] = None) -> None:
        self._resp = resp
        self._sink = sink if sink is not None else {}
        self._raises = raises

    def __call__(self, *args, **kwargs):  # table('quote_ownership')
        return self

    def select(self, *a, **kw):
        self._sink["select"] = a
        self._sink["count"] = kw.get("count")
        return self

    def insert(self, row):
        self._sink["insert"] = row
        return self

    def eq(self, col, val):
        self._sink.setdefault("eq", []).append((col, val))
        return self

    def order(self, *a, **kw):
        return self

    def range(self, lo, hi):
        self._sink["range"] = (lo, hi)
        return self

    def limit(self, n):
        return self

    def execute(self):
        if self._raises is not None:
            raise self._raises
        return self._resp


class _Client:
    def __init__(self, chain: _Chain) -> None:
        self._chain = chain

    def table(self, name):
        return self._chain


_PAYLOAD = {
    "quote_id": "q_deadbeef",
    "full_name": "Karim Bensaid",
    "email": "karim@example.com",
    "company": "Banque Populaire MA",
    "package": "crisis_drill_24h",
    "message": "Stress-test avant lancement.",
    "submitted_at": "2026-07-07T12:00:00+00:00",
}


# ─── link_quote_to_org : payload transmis ────────────────────────────────────


class TestLinkWithPayload:
    def test_payload_present_dans_insert(self):
        sink: Dict[str, Any] = {}
        cli = _Client(_Chain(_Resp([{"quote_id": "q_deadbeef"}]), sink))
        ok = qo.link_quote_to_org(
            "q_deadbeef", "org-uuid-001",
            customer_email="karim@example.com",
            package_id="crisis_drill_24h",
            payload=_PAYLOAD,
            client=cli,
        )
        assert ok is True
        assert sink["insert"]["payload"] == _PAYLOAD

    def test_sans_payload_colonne_absente(self):
        sink: Dict[str, Any] = {}
        cli = _Client(_Chain(_Resp([{}]), sink))
        qo.link_quote_to_org("q_deadbeef", "org-uuid-001", client=cli)
        assert "payload" not in sink["insert"]


# ─── get_quote_payload_from_supabase ─────────────────────────────────────────


class TestGetQuotePayload:
    def test_trouve(self):
        cli = _Client(_Chain(_Resp([{"payload": _PAYLOAD}])))
        assert qo.get_quote_payload_from_supabase("q_deadbeef", client=cli) == _PAYLOAD

    def test_payload_vide_retourne_none(self):
        cli = _Client(_Chain(_Resp([{"payload": {}}])))
        assert qo.get_quote_payload_from_supabase("q_deadbeef", client=cli) is None

    def test_ligne_absente_retourne_none(self):
        cli = _Client(_Chain(_Resp([])))
        assert qo.get_quote_payload_from_supabase("q_x", client=cli) is None

    def test_erreur_retourne_none(self):
        cli = _Client(_Chain(_Resp([]), raises=RuntimeError("boom")))
        assert qo.get_quote_payload_from_supabase("q_x", client=cli) is None


# ─── list_quotes_with_payload ────────────────────────────────────────────────


class TestListQuotesWithPayload:
    def _rows(self) -> List[Dict[str, Any]]:
        return [{
            "quote_id": "q_deadbeef",
            "org_id": "org-uuid-001",
            "customer_email": "karim@example.com",
            "package_id": "crisis_drill_24h",
            "status": "received",
            "created_at": "2026-07-07T12:00:01+00:00",
            "payload": _PAYLOAD,
        }]

    def test_page_et_total(self):
        sink: Dict[str, Any] = {}
        cli = _Client(_Chain(_Resp(self._rows(), count=7), sink))
        page = qo.list_quotes_with_payload(limit=10, offset=0, client=cli)
        assert page is not None
        assert page["total"] == 7
        assert page["items"][0]["payload"] == _PAYLOAD
        assert sink["count"] == "exact"

    def test_filtre_statut_applique(self):
        sink: Dict[str, Any] = {}
        cli = _Client(_Chain(_Resp(self._rows(), count=1), sink))
        qo.list_quotes_with_payload(status_filter="received", client=cli)
        assert ("status", "received") in sink.get("eq", [])

    def test_erreur_retourne_none(self):
        cli = _Client(_Chain(_Resp([]), raises=RuntimeError("boom")))
        assert qo.list_quotes_with_payload(client=cli) is None


# ─── read_quote_payload : Supabase d'abord, filesystem en repli ─────────────


class TestReadQuotePayloadSupabaseFirst:
    def test_supabase_prioritaire(self, monkeypatch):
        monkeypatch.setattr(
            qo, "get_quote_payload_from_supabase", lambda qid, **kw: _PAYLOAD,
        )
        # Le filesystem ne doit même pas être consulté.
        monkeypatch.setattr(
            qa, "quotes_dir",
            lambda: (_ for _ in ()).throw(AssertionError("fs consulté")),
        )
        assert qa.read_quote_payload("q_deadbeef") == _PAYLOAD

    def test_repli_filesystem(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            qo, "get_quote_payload_from_supabase", lambda qid, **kw: None,
        )
        qdir = tmp_path / "quotes"
        qdir.mkdir()
        (qdir / "quote_20260707T120000_deadbeef.json").write_text(
            json.dumps(_PAYLOAD), encoding="utf-8",
        )
        monkeypatch.setattr(qa, "quotes_dir", lambda: qdir)
        assert qa.read_quote_payload("q_deadbeef") == _PAYLOAD


# ─── list_quotes : Supabase d'abord, repli legacy ────────────────────────────


class TestListQuotesSupabaseFirst:
    def test_supabase_prioritaire_shape_identique(self, tmp_path, monkeypatch):
        page = {
            "items": [{
                "quote_id": "q_deadbeef",
                "org_id": "org-uuid-001",
                "customer_email": "karim@example.com",
                "package_id": "crisis_drill_24h",
                "status": "quoted",
                "created_at": "2026-07-07T12:00:01+00:00",
                "payload": _PAYLOAD,
            }],
            "total": 1,
        }
        monkeypatch.setattr(qo, "list_quotes_with_payload", lambda **kw: page)
        monkeypatch.setattr(qa, "quotes_dir", lambda: tmp_path / "quotes")
        items, total = qa.list_quotes(limit=50, offset=0)
        assert total == 1
        item = items[0]
        assert item["quote_id"] == "q_deadbeef"
        assert item["payload"] == _PAYLOAD
        assert item["status"]["status"] == "quoted"
        assert item["status"]["history"] == []

    def test_repli_filesystem_si_supabase_indisponible(self, tmp_path, monkeypatch):
        monkeypatch.setattr(qo, "list_quotes_with_payload", lambda **kw: None)
        monkeypatch.setattr(qa, "quotes_dir", lambda: tmp_path / "quotes")
        items, total = qa.list_quotes()
        assert items == [] and total == 0


# ─── submit_quote : double persistance ───────────────────────────────────────


def _valid_submission() -> Dict[str, Any]:
    return {
        "full_name": "Karim Bensaid",
        "company": "Banque Populaire MA",
        "email": "karim@example.com",
        "package": "crisis_drill_24h",
        "consent_rgpd": True,
        "message": "Stress-test avant lancement.",
    }


@pytest.fixture
def _mute_emails(monkeypatch):
    monkeypatch.setattr(qs, "_send_email", lambda record: None)
    monkeypatch.setattr(qs, "_send_client_confirmation", lambda record: None)


class TestSubmitQuoteDualPersistence:
    def test_supabase_ok_fichier_ko_reste_200(self, monkeypatch, _mute_emails):
        monkeypatch.setattr(qs, "_persist_quote_supabase", lambda *a, **kw: True)
        def _boom(record):
            raise OSError("disk full")
        monkeypatch.setattr(qs, "_write_record", _boom)
        status, body = qs.submit_quote(_valid_submission())
        assert status == 200 and body["success"] is True

    def test_les_deux_ko_500(self, monkeypatch, _mute_emails):
        monkeypatch.setattr(qs, "_persist_quote_supabase", lambda *a, **kw: False)
        def _boom(record):
            raise OSError("disk full")
        monkeypatch.setattr(qs, "_write_record", _boom)
        status, body = qs.submit_quote(_valid_submission())
        assert status == 500 and body["error_code"] == "STORAGE_ERROR"

    def test_supabase_ko_fichier_ok_reste_200(self, tmp_path, monkeypatch, _mute_emails):
        monkeypatch.setattr(qs, "_persist_quote_supabase", lambda *a, **kw: False)
        written: Dict[str, Any] = {}
        monkeypatch.setattr(qs, "_write_record", lambda record: written.update(record) or tmp_path / "q.json")
        status, body = qs.submit_quote(_valid_submission())
        assert status == 200 and written["full_name"] == "Karim Bensaid"

    def test_payload_transmis_a_supabase(self, monkeypatch, _mute_emails):
        captured: Dict[str, Any] = {}
        def _persist(quote_id, record, org_id):
            captured["record"] = record
            return True
        monkeypatch.setattr(qs, "_persist_quote_supabase", _persist)
        monkeypatch.setattr(qs, "_write_record", lambda record: None)
        qs.submit_quote(_valid_submission())
        assert captured["record"]["email"] == "karim@example.com"
        assert captured["record"]["consent_rgpd"] is True


# ─── US-IQ-04 audit R1 : échappement HTML du contenu prospect ───────────────


class TestSendClientConfirmationHtmlEscaping:
    def test_full_name_html_escaped(self, monkeypatch):
        import app.services.email_service as email_svc

        captured = {}
        monkeypatch.setattr(
            email_svc, "send_email",
            lambda *, to_email, subject, html_body, **kw: captured.update(
                {"html_body": html_body}
            ) or True,
        )
        record = {
            "email": "prospect@example.com",
            "full_name": "<script>alert(1)</script>",
            "company": "Acme & Co",
            "package": "custom",
            "industry": "<b>tech</b>",
            "quote_id": "q_test123",
        }
        qs._send_client_confirmation(record)
        assert "<script>alert(1)</script>" not in captured["html_body"]
        assert "&lt;script&gt;" in captured["html_body"]
        assert "Acme &amp; Co" in captured["html_body"]
        assert "&lt;b&gt;tech&lt;/b&gt;" in captured["html_body"]
