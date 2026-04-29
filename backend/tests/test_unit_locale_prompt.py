"""Unit tests for locale_prompt helpers (US-043)."""

import pytest
from flask import Flask

from app.utils.locale_prompt import (
    DEFAULT_LOCALE,
    LOCALE_FULL_NAMES,
    get_request_locale,
    localize_system_prompt,
)


@pytest.fixture
def app():
    """Lightweight Flask app pour les tests qui ont besoin d'un request context.

    On ne charge pas l'app complète Bassira (lourde, dépendances Neo4j et
    LLM). Un Flask vide suffit pour tester `get_request_locale` qui ne lit
    qu'un header.
    """
    return Flask(__name__)


# ── localize_system_prompt ────────────────────────────────────────────────


def test_localize_default_appends_french_instruction():
    out = localize_system_prompt("You are a designer.")
    assert "français" in out
    assert "code `fr`" in out
    assert "You are a designer." in out  # original preserved


def test_localize_arabic_uses_arabic_label():
    out = localize_system_prompt("You are a designer.", locale="ar")
    assert "arabe" in out
    assert "العربية" in out
    assert "code `ar`" in out


def test_localize_english_uses_english_label():
    out = localize_system_prompt("You are a designer.", locale="en")
    assert "English" in out
    assert "code `en`" in out


def test_localize_invalid_locale_falls_back_to_default():
    out = localize_system_prompt("Test prompt.", locale="zz")
    assert "français" in out  # default fr
    assert "code `fr`" in out


def test_localize_is_idempotent():
    once = localize_system_prompt("Original prompt.", locale="fr")
    twice = localize_system_prompt(once, locale="fr")
    assert once == twice  # second call is a no-op


def test_localize_preserves_schema_identifier_exception():
    out = localize_system_prompt("Some prompt.", locale="fr")
    # The instruction must explicitly carve out technical identifiers
    assert "PascalCase" in out
    assert "UPPER_SNAKE_CASE" in out
    assert "snake_case" in out
    assert "JSON" in out


def test_localize_translation_directive_present():
    out = localize_system_prompt("Some prompt.", locale="fr")
    assert "traduis-le mentalement" in out


# ── get_request_locale (out of Flask context) ─────────────────────────────


def test_get_request_locale_outside_flask_returns_default():
    assert get_request_locale() == DEFAULT_LOCALE


def test_get_request_locale_outside_flask_with_custom_default():
    assert get_request_locale(default="ar") == "ar"


# ── get_request_locale (inside Flask context) ─────────────────────────────


def test_get_request_locale_inside_flask_reads_header(app):
    """Use the existing `app` fixture from backend/tests/conftest.py."""
    with app.test_request_context(headers={"X-Bassira-Locale": "ar"}):
        assert get_request_locale() == "ar"


def test_get_request_locale_inside_flask_invalid_falls_back(app):
    with app.test_request_context(headers={"X-Bassira-Locale": "zz"}):
        assert get_request_locale() == DEFAULT_LOCALE


def test_get_request_locale_inside_flask_missing_header_falls_back(app):
    with app.test_request_context():  # no headers
        assert get_request_locale() == DEFAULT_LOCALE


def test_get_request_locale_inside_flask_case_insensitive(app):
    with app.test_request_context(headers={"X-Bassira-Locale": "FR"}):
        assert get_request_locale() == "fr"


# ── Constants sanity ──────────────────────────────────────────────────────


def test_supported_locales_includes_fr_ar_en():
    assert "fr" in LOCALE_FULL_NAMES
    assert "ar" in LOCALE_FULL_NAMES
    assert "en" in LOCALE_FULL_NAMES


def test_default_locale_is_supported():
    assert DEFAULT_LOCALE in LOCALE_FULL_NAMES
