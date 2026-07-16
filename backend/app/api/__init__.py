"""
API Routes Module
"""

from flask import Blueprint

# Annotations explicites : sans elles, mypy ne peut pas résoudre le type de
# ces blueprints à travers le cycle d'import `from . import <module>` plus
# bas (chaque module de routes fait `from . import xxx_bp` en retour) —
# cause racine de l'essentiel des erreurs "Cannot determine type" (US-212).
graph_bp: Blueprint = Blueprint('graph', __name__)
simulation_bp: Blueprint = Blueprint('simulation', __name__)
report_bp: Blueprint = Blueprint('report', __name__)
templates_bp: Blueprint = Blueprint('templates', __name__)
settings_bp: Blueprint = Blueprint('settings', __name__)
observability_bp: Blueprint = Blueprint('observability', __name__)
mcp_bp: Blueprint = Blueprint('mcp', __name__)
docs_bp: Blueprint = Blueprint('docs', __name__)

from . import graph  # noqa: E402, F401
from . import simulation  # noqa: E402, F401
from . import pdf_export  # noqa: E402, F401  — US-024 branded PDF export
from . import report  # noqa: E402, F401
from . import templates  # noqa: E402, F401
from . import settings  # noqa: E402, F401
from . import observability  # noqa: E402, F401
from . import mcp  # noqa: E402, F401
from . import docs  # noqa: E402, F401

# share_bp is mounted at the root (no /api prefix) so the public landing
# URL stays clean — see api/share.py.
from .share import share_bp  # noqa: E402, F401

# calibration_bp serves the public Brier-score endpoint at
# /api/calibration/brier-score — see api/calibration.py.
from .calibration import calibration_bp  # noqa: E402, F401

# admin_bp serves the ops analytics endpoint at /api/admin/analytics
# (US-065). Gated on BASSIRA_ADMIN_TOKEN — see api/admin.py.
from .admin import admin_bp  # noqa: E402, F401

