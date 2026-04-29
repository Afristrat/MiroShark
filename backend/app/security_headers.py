"""Middleware Flask qui ajoute les headers de sécurité standards.

Compromis production-ready :
- X-Frame-Options: SAMEORIGIN par défaut (anti-clickjacking)
- /share/* et /embed/* SANS X-Frame-Options (social unfurl Slack/Discord/Twitter)
- X-Content-Type-Options: nosniff (anti-MIME-sniffing)
- Referrer-Policy: strict-origin-when-cross-origin (limite la fuite de l'URL référente)
- Strict-Transport-Security: 1 an (uniquement quand FLASK_ENV != 'development')
- Content-Security-Policy minimal qui n'empêche pas Vite/Tailwind/CDN Google Fonts

Le but est de remonter le score Lighthouse Best Practices > 90 sans casser
les fonctionnalités existantes (galerie publique, embed iframe, MCP).
"""

from __future__ import annotations

import logging
import os
from typing import Iterable

from flask import Flask, request

logger = logging.getLogger(__name__)

# Routes qui DOIVENT pouvoir être embarquées dans des iframes tierces
# pour que les share cards / GIFs / embeds fonctionnent correctement
# (Slack, Discord, Twitter unfurl ; embed.html iframe).
_EMBEDDABLE_PREFIXES: tuple[str, ...] = (
    '/share',
    '/embed',
    '/api/simulation/',  # /api/simulation/<id>/share-card.png et /replay.gif
)

# CSP minimal : autorise inline scripts/styles (Vue dev hot-reload + d3 inline),
# Google Fonts, et les images data: URI. À durcir une fois la migration tokens
# terminée (US-016) — on retirera unsafe-inline.
_DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data: blob: https:; "
    "connect-src 'self' https: wss:; "
    "frame-ancestors 'self'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


def _is_embeddable(path: str, embeddable_prefixes: Iterable[str]) -> bool:
    return any(path.startswith(prefix) for prefix in embeddable_prefixes)


def init_security_headers(
    app: Flask,
    *,
    embeddable_prefixes: Iterable[str] = _EMBEDDABLE_PREFIXES,
    csp: str = _DEFAULT_CSP,
) -> None:
    """Branche le hook ``after_request`` pour ajouter les headers."""

    is_production = os.environ.get('FLASK_ENV', 'production').lower() != 'development'

    @app.after_request
    def _add_security_headers(response):  # type: ignore[no-untyped-def]
        path = request.path or '/'
        embeddable = _is_embeddable(path, embeddable_prefixes)

        # Anti-MIME-sniffing : toujours actif.
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')

        # Referrer policy : toujours actif.
        response.headers.setdefault(
            'Referrer-Policy', 'strict-origin-when-cross-origin'
        )

        # Permissions-Policy : on bloque par défaut camera/microphone/geolocation
        # car aucune feature MiroShark ne les utilise.
        response.headers.setdefault(
            'Permissions-Policy', 'camera=(), microphone=(), geolocation=()'
        )

        # X-Frame-Options : SAMEORIGIN sauf pour les routes embeddables.
        if not embeddable:
            response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')

        # HSTS : uniquement en prod (HTTPS) — en dev, le navigateur doit
        # pouvoir basculer entre HTTPS et HTTP sans persister.
        if is_production:
            response.headers.setdefault(
                'Strict-Transport-Security',
                'max-age=31536000; includeSubDomains',
            )

        # CSP : on évite de l'imposer aux endpoints embeddables (les iframes
        # qui hébergent un share card peuvent casser sinon).
        if not embeddable:
            response.headers.setdefault('Content-Security-Policy', csp)

        return response

    logger.info(
        "security_headers initialized (production=%s, embeddable_prefixes=%s)",
        is_production,
        list(embeddable_prefixes),
    )
