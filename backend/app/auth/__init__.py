"""Authentification multitenant Supabase Cloud (US-092).

Ce package isole toute la logique liée à l'authentification JWT Supabase
et à la résolution d'appartenance organisationnelle pour les endpoints
client (`/api/client/*`) du backend Bassira.

Module map :
    - jwt_verifier      : décodage + vérification d'un JWT Supabase Auth
    - supabase_client   : singleton client admin (service_role) + helpers
                          ownership / membership
    - decorators        : @require_auth, @require_org_membership,
                          @require_owner_or_admin

Aucun secret n'est embarqué : `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
et `SUPABASE_JWT_SECRET` sont lus exclusivement via `os.getenv` à l'usage,
afin que les tests pytest puissent monkeypatcher l'environnement et que
les déploiements Coolify gardent leurs variables strictement côté serveur.
"""

from .jwt_verifier import verify_supabase_jwt, InvalidTokenError  # noqa: F401
from .decorators import (  # noqa: F401
    require_auth,
    require_org_membership,
    require_owner_or_admin,
)

__all__ = [
    "verify_supabase_jwt",
    "InvalidTokenError",
    "require_auth",
    "require_org_membership",
    "require_owner_or_admin",
]
