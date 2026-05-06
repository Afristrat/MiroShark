"""Add US-137 Admin Users page to PRD."""
import json
from pathlib import Path

p = Path('.ralph/prd.json')
data = json.loads(p.read_text(encoding='utf-8'))

new = {
    "id": "US-137",
    "chantier": "AJ-admin-users",
    "title": "Page admin Users : liste cross-tenant des inscriptions avec filtre org + actions",
    "description": "Trou architectural identifie 2026-05-06 : aucune vue admin pour voir les utilisateurs qui s inscrivent sur la plateforme. Aujourd hui les users vont dans auth.users (Supabase managed) et members (notre table multitenant) mais aucune page Bassira ne permet a un super-admin de visualiser et gerer ces inscriptions. La consultation passe par Supabase Dashboard. Creer /admin/users qui agglomere auth.users + members + orgs.",
    "acceptanceCriteria": [
        "Endpoint GET /api/admin/users (super-admin OR org admin) avec query params org_id?, search?, limit, offset",
        "Backend : agglomere auth.users (id, email, created_at, last_sign_in_at, raw_user_meta_data) + LEFT JOIN members (org_id, role) + LEFT JOIN orgs (name, slug)",
        "Pour super-admin : retourne tous les users cross-tenant, filtrable par org_id",
        "Pour org admin : retourne uniquement les users de son org (via user_orgs())",
        "Endpoint GET /api/admin/users/<user_id>/simulations : list sims de ce user (via simulation_ownership.org_id IN user_orgs(user_id))",
        "Endpoint GET /api/admin/users/stats : total inscrits, actifs 7j, nouveaux 30j",
        "Frontend AdminUsersView.vue route /admin/users, meta.requiresSuperAdmin",
        "Tableau avec colonnes : Email, Org(s), Role, Date inscription, Dernier login, Status (actif/inactif), Actions (voir sims, voir profil)",
        "Filtres : par org (dropdown), par status, recherche email, periode inscription",
        "Tri : date inscription desc (default), dernier login desc, email asc",
        "Bouton Voir les sims pointe vers /admin/simulations?user_id=X (lien interne)",
        "Tokens --wi-* exclusivement, i18n FR/EN/AR (cles adminUsers.*)",
        "Tests pytest backend/tests/test_admin_users.py : RLS scenarios (super-admin all, org admin own org, member 403), endpoints + filtre + search",
        "Tests Playwright frontend/tests/e2e/admin-users.spec.ts : page accessible super-admin, redirect non-auth, filtre fonctionne"
    ],
    "passes": False,
    "dependencies": ["US-091", "US-092", "US-095"],
    "metadata": {
        "estimated_hours": 5,
        "priority": "P1",
        "files_to_create": [
            "backend/app/api/admin_users.py",
            "frontend/src/views/AdminUsersView.vue",
            "backend/tests/test_admin_users.py",
            "frontend/tests/e2e/admin-users.spec.ts"
        ],
        "files_to_modify": [
            "backend/app/__init__.py",
            "frontend/src/router/index.js",
            "frontend/src/components/AppHeader.vue",
            "frontend/src/api/client.js",
            "frontend/src/locales/fr.json",
            "frontend/src/locales/en.json",
            "frontend/src/locales/ar.json"
        ],
        "rationale": "Trou identifie par Amine 2026-05-06. Sans cette page, les super-admins doivent passer par Supabase Dashboard externe pour voir leurs users. Necessaire pour onboarding tracking + support client + audit RGPD."
    }
}

data['stories'].append(new)
p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(f"Added US-137. passes:false: {sum(1 for s in data['stories'] if not s['passes'])}")
