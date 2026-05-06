"""
MiroShark Backend - Flask application factory
"""

import os
import warnings

# Suppress multiprocessing resource_tracker warnings (from third-party libraries like transformers)
# Must be set before all other imports
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, request
from flask_cors import CORS
from flask_compress import Compress

from .config import Config
from .utils.logger import setup_logger, get_logger


def create_app(config_class=Config):
    """Flask application factory function"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Set JSON encoding: ensure non-ASCII characters are displayed directly (instead of \uXXXX format)
    # Flask >= 2.3 uses app.json.ensure_ascii, older versions use JSON_AS_ASCII config
    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False
    
    # Set up logging
    logger = setup_logger('miroshark')
    
    # Only print startup info in the reloader subprocess (avoid printing twice in debug mode)
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process
    
    if should_log_startup:
        logger.info("=" * 50)
        logger.info("MiroShark Backend starting...")
        logger.info("=" * 50)
    
    # Enable CORS — whitelist from CORS_ORIGINS env (comma-separated).
    # Defaults to the production tunnel + local dev server.
    cors_origins_env = os.environ.get(
        'CORS_ORIGINS',
        'https://prospectives.ai-mpower.com,http://localhost:3000,http://127.0.0.1:3000',
    )
    cors_origins = [o.strip() for o in cors_origins_env.split(',') if o.strip()]
    # The literal '*' is still honoured (no whitelist) but emits a warning.
    if '*' in cors_origins:
        logger.warning(
            "CORS_ORIGINS contains '*' — every origin is allowed. "
            "Set CORS_ORIGINS to an explicit comma-separated list in production."
        )
    CORS(app, resources={r"/api/*": {"origins": cors_origins}})

    # Enable gzip/brotli response compression
    Compress(app)

    # Security headers (X-Frame-Options, X-Content-Type-Options, HSTS, CSP)
    from .security_headers import init_security_headers
    init_security_headers(app)

    # --- Initialize Neo4jStorage singleton (DI via app.extensions) ---
    from .storage import Neo4jStorage
    try:
        neo4j_storage = Neo4jStorage()
        app.extensions['neo4j_storage'] = neo4j_storage
        if should_log_startup:
            logger.info("Neo4jStorage initialized (connected to %s)", Config.NEO4J_URI)
    except Exception as e:
        logger.error("Neo4jStorage initialization failed: %s", e)
        # Store None so endpoints can return 503 gracefully
        app.extensions['neo4j_storage'] = None

    # Register simulation process cleanup function (ensure all simulation processes are terminated when server shuts down)
    from .services.simulation_runner import SimulationRunner
    SimulationRunner.register_cleanup()
    if should_log_startup:
        logger.info("Simulation process cleanup function registered")
    
    # Request logging middleware
    @app.before_request
    def log_request():
        logger = get_logger('miroshark.request')
        logger.debug(f"Request: {request.method} {request.path}")
        if request.content_type and 'json' in request.content_type:
            logger.debug(f"Request body: {request.get_json(silent=True)}")
    
    @app.after_request
    def log_response(response):
        logger = get_logger('miroshark.request')
        logger.debug(f"Response: {response.status_code}")
        return response
    
    # Register blueprints
    from .api import graph_bp, simulation_bp, report_bp, templates_bp, settings_bp, observability_bp, mcp_bp, docs_bp, share_bp, calibration_bp, admin_bp
    app.register_blueprint(graph_bp, url_prefix='/api/graph')
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    app.register_blueprint(report_bp, url_prefix='/api/report')
    app.register_blueprint(templates_bp, url_prefix='/api/templates')
    app.register_blueprint(settings_bp, url_prefix='/api/settings')
    app.register_blueprint(observability_bp, url_prefix='/api/observability')
    app.register_blueprint(mcp_bp, url_prefix='/api/mcp')
    # docs_bp serves Swagger UI + the OpenAPI spec at /api/docs,
    # /api/openapi.yaml, /api/openapi.json (no extra sub-prefix — the spec
    # URL is the developer-facing surface so we keep it short).
    app.register_blueprint(docs_bp, url_prefix='/api')
    # share_bp serves the public OG-tag landing page at /share/<sim_id>
    # (no prefix — keeps the social share URL short).
    app.register_blueprint(share_bp)
    # calibration_bp serves the public Brier-score / calibration-plot
    # endpoint at /api/calibration/brier-score (no auth — calibration
    # numbers are the commercial argument).
    app.register_blueprint(calibration_bp, url_prefix='/api/calibration')
    # admin_bp serves the ops analytics dashboard endpoint at
    # /api/admin/analytics (US-065). Gated on BASSIRA_ADMIN_TOKEN —
    # internal-only, never expose to unauthenticated clients.
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    # quote_bp serves the commercial-form receiver at POST /api/quote
    # (US-025) — public, rate-limited, fires a notification email.
    # admin_quote_bp expose la console super-admin /api/admin/quotes
    # (US-102/103/104) — workflow statut + envoi Resend.
    from .api.quote import quote_bp, admin_quote_bp
    app.register_blueprint(quote_bp, url_prefix='/api/quote')
    app.register_blueprint(admin_quote_bp, url_prefix='/api/admin/quotes')
    # models_bp serves the public branded-brief PDF endpoint at
    # GET /api/models/<slug>/pdf-brief?lang=<fr|en|ar> (US-088).
    from .api.models import models_bp
    app.register_blueprint(models_bp, url_prefix='/api/models')
    # client_bp expose les endpoints multitenant authentifiés Supabase
    # (US-092) : /api/client/auth/me, /api/client/simulations[+outcome+publish].
    # Tous les endpoints sont protégés par JWT Supabase et rôle org.
    from .api.client import client_bp
    app.register_blueprint(client_bp, url_prefix='/api/client')

    # invitations_bp + admin_invitations_bp — système d'invitation
    # user → org via email magic link (US-115).
    #   /api/admin/invitations          — POST/GET/DELETE (org admin OR super-admin)
    #   /api/invitations/<token>/accept — public metadata pour pré-remplir signup
    #   /api/invitations/<token>/redeem — auth requis, crée la row org_members
    from .api.invitations import admin_invitations_bp, invitations_bp
    app.register_blueprint(admin_invitations_bp, url_prefix='/api/admin/invitations')
    app.register_blueprint(invitations_bp, url_prefix='/api/invitations')

    # admin_branding_bp — gestion du branding PDF par org (US-120).
    #   /api/admin/branding          — GET / POST
    #   /api/admin/branding/<id>     — PATCH
    #   /api/admin/branding/<id>/preview — POST (aperçu SVG)
    from .api.admin_branding import admin_branding_bp
    app.register_blueprint(admin_branding_bp, url_prefix='/api/admin/branding')

    # admin_reports_bp — workflow états + Approve & Sign (US-126 + US-128).
    #   /api/admin/reports/<id>/state      — GET état courant + audit log (US-126)
    #   /api/admin/reports/<id>/transition — POST effectue une transition (US-126)
    #   /api/admin/reports/<id>/lock       — POST acquiert le lock IN_REVIEW (US-126)
    #   /api/admin/reports/<id>/unlock     — POST relâche le lock (US-126)
    #   /api/admin/reports/<id>/approve    — POST (super-admin only, snapshot+watermark+sign) (US-128)
    from .api.admin_reports import admin_reports_bp
    app.register_blueprint(admin_reports_bp, url_prefix='/api/admin/reports')

    # admin_report_versions_bp — versioning + commentaires rapport (US-127).
    #   /api/admin/reports/<id>/versions                         — GET/POST
    #   /api/admin/reports/<id>/versions/<vid>/diff/<other_vid>  — GET diff
    #   /api/admin/reports/<id>/comments                         — GET/POST
    #   /api/admin/reports/<id>/comments/<cid>                   — PATCH
    from .api.admin_report_versions import admin_report_versions_bp
    app.register_blueprint(admin_report_versions_bp, url_prefix='/api/admin/reports')

    # pdf_generation_bp — génération PDF hybride sync/async (US-129).
    #   POST /api/admin/reports/<id>/preview  — preview sync 1 page
    #   POST /api/admin/reports/<id>/generate — enqueue async RQ
    #   GET  /api/admin/reports/<id>/jobs/<job_id> — polling status
    from .api.pdf_generation import pdf_generation_bp
    app.register_blueprint(pdf_generation_bp, url_prefix='/api/admin/reports')
    
    # Health check
    @app.route('/health')
    def health():
        return {'status': 'ok', 'service': 'MiroShark Backend'}
    
    if should_log_startup:
        logger.info("MiroShark Backend startup complete")
    
    return app

