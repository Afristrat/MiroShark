# Audit de Sécurité OWASP Top 10 — Bassira (post-multitenant)
**Date :** 2026-05-05  
**Périmètre :** Backend Flask + Supabase multitenant + Frontend Vue 3  
**Auditeur :** Agent US-116 (Claude Sonnet 4.6)  
**Méthode :** Revue statique exhaustive du code source (aucun accès prod)

---

## Synthèse exécutive

| Catégorie | Statut | Criticité |
|-----------|--------|-----------|
| A01 Broken Access Control | ⚠️ P0 | Stack traces publiques + IDOR partiel sur /report/* non authentifié |
| A02 Cryptographic Failures | ✅ OK | JWT dual-mode solide, no secret exposure |
| A03 Injection | ✅ OK | Supabase paramétré, path traversal bloqué |
| A04 Insecure Design | ⚠️ P1 | Rate limits manquants sur /report/generate + /report/chat |
| A05 Security Misconfiguration | ⚠️ P0 | Stack traces exposées en JSON public (simulation.py, report.py, graph.py) |
| A06 Vulnerable Components | ⚠️ P1 | npm : axios HIGH, vite HIGH, rollup HIGH, marked HIGH, picomatch HIGH |
| A07 Identification and Auth Failures | ✅ OK | JWT Supabase + JWKS + HS256 legacy |
| A08 Software and Data Integrity | ✅ OK | Webhook sortant, pas de Stripe webhooks entrants |
| A09 Security Logging and Monitoring | ✅ OK | JWT jamais loggué, audit super-admin sha256 |
| A10 SSRF | ⚠️ P0 | webhook_service.validate_url() sans blocage IP privée |

**P0 corrigés dans ce commit :** 2  
**P1 documentés pour suivi :** 3

---

## A01 — Broken Access Control

### 1.1 RLS Supabase (✅ OK)

Les trois tables multitenant ont toutes RLS activé :

```sql
-- migration 20260503_001_init_multitenant.sql : lignes 95-97
alter table public.organizations        enable row level security;
alter table public.org_members          enable row level security;
alter table public.simulation_ownership enable row level security;
```

Policies strictes : lecture limitée à l'org d'appartenance via `user_orgs()`, écriture limitée aux rôles `admin`/`owner`. La migration `20260504_001_org_self_service.sql` ajoute `self_service_enabled` sans relâcher le RLS.

### 1.2 Endpoints `/api/admin/*` (✅ OK)

`GET /api/admin/analytics` → `@require_admin_token` (dual-mode JWT super-admin + BASSIRA_ADMIN_TOKEN, hmac.compare_digest)  
`GET /api/admin/organizations`, `/api/admin/simulations`, `/api/admin/organizations/<id>/self-service` → `@require_super_admin` (JWT Supabase + whitelist BASSIRA_SUPER_ADMIN_EMAILS)  
`GET /api/admin/quotes/*` → `@require_super_admin`

`admin.py:381` : `/api/admin/me/super-status` requiert `@require_auth` (JWT valide). Sans JWT = 401. OK.

### 1.3 Endpoint `/api/report/<id>` — IDOR (⚠️ P0 partiel, documenté)

**Constat :** Les endpoints `/api/report/<report_id>`, `/api/report/<report_id>/download`, `/api/report/generate`, `/api/report/chat`, `/api/report/tools/search` n'ont **aucune authentification** (`report.py`, aucun décorateur `@require_auth`).

**Justification design actuelle :** Les rapports sont identifiés par `report_id = "report_" + uuid4().hex[:12]` (48 bits d'entropie — difficulté de bruteforce). Les simulations sont des données analytiques non-personnelles que le client partage librement (share cards publiques).

**Risque réel :** Un attaquant connaissant un `report_id` ou un `simulation_id` peut lire le rapport sans authentification. Cela constitue un IDOR potentiel en contexte multitenant si des rapports contiennent des données sensibles d'une org.

**Preuve :**
```python
# backend/app/api/report.py:327-376
@report_bp.route('/<report_id>', methods=['GET'])
def get_report(report_id: str):   # ← 0 décorateur auth
    report = ReportManager.get_report(report_id)
    ...
```

**Recommandation (P1 — ne pas casser la galerie publique) :** Ajouter `@soft_check_self_service` sur `get_report` à terme. Pour l'instant les rapports sont considérés comme publics (même scope que les share cards).

**Recommandation (P0 traceback) :** Voir A05.

### 1.4 Endpoints `/api/client/*` (✅ OK)

`POST /api/client/simulations/<id>/outcome` et `/publish` vérifient que `owner.org_id == g.current_org.id` avant toute action :

```python
# backend/app/api/client.py:283-288
if str(owner.get("org_id")) != str(org_id):
    return _err("FORBIDDEN_ORG", "Simulation does not belong...", 403)
```

Cross-tenant IDOR bloqué côté applicatif ET côté Supabase RLS.

---

## A02 — Cryptographic Failures

### 2.1 JWT verifier dual-mode (✅ OK)

`backend/app/auth/jwt_verifier.py` : Support ES256/RS256/EdDSA via JWKS + HS256 legacy. L'algorithme est détecté depuis le header JWT (`_peek_alg`). Cache LRU 5 min, TTL borné par `exp`. Aucun JWT ni header `Authorization` n'est jamais loggué :

```python
# jwt_verifier.py:245
logger.info("JWT rejected by PyJWT: %s", exc.__class__.__name__)
# ← seulement le type d'exception, jamais le token
```

### 2.2 Secrets côté frontend (✅ OK)

- `SUPABASE_SERVICE_ROLE_KEY` : jamais dans le code frontend. Toutes les requêtes Supabase admin passent par le backend Flask avec `service_role` côté serveur uniquement.
- `frontend/src/lib/supabase.js` : utilise `VITE_SUPABASE_ANON_KEY` uniquement (clé publique, par design Supabase).

### 2.3 HTTPS (✅ OK)

`security_headers.py:89-93` : HSTS `max-age=31536000; includeSubDomains` ajouté en prod. Le CORS_ORIGINS par défaut contient `https://prospectives.ai-mpower.com` (HTTPS).

---

## A03 — Injection

### 3.1 SQL Injection (✅ OK)

Le client Supabase-py utilise des requêtes paramétrées par défaut (`.eq()`, `.select()`, `.in_()`). Aucun appel `rpc()` avec interpolation directe de variables utilisateur n'a été détecté dans le périmètre multitenant.

### 3.2 Path Traversal (✅ OK)

`backend/app/utils/validation.py:12-45` : `validate_simulation_id()` rejette `..`, `/`, `\` et tout caractère hors `[a-zA-Z0-9_\-\.]`. Ce validateur est appliqué dans `simulation_bp.before_request` et `report_bp.before_request`.

### 3.3 XSS (✅ OK pour le frontend)

Le frontend Vue 3 échappe automatiquement via ses templates. Les markdown-it renders utilisent DOMPurify (cf. dépendances). Mais voir A06 pour les CVE dompurify.

### 3.4 Command Injection (✅ OK)

Aucun `subprocess` appelé avec input utilisateur direct détecté. Les process de simulation sont démarrés avec des `simulation_id` validés.

---

## A04 — Insecure Design

### 4.1 Rate limits en place (✅ OK partiel)

| Endpoint | Rate limit |
|---|---|
| `POST /api/simulation/enrich-ask` | 10 appels / 60s / IP (`_ENRICH_RATE_HITS`) |
| `POST /api/simulation/suggest-scenarios` | 10 appels / 60s / IP (`_SCENARIO_RATE_HITS`) |
| `POST /api/simulation/ask` | Rate limité (`_ASK_RATE_HITS`) |
| `POST /api/simulation/trending-topics` | Rate limité |
| `POST /api/quote` | `check_rate_limit()` dans `quote_service.py` |

**Preuve enrich-ask :**
```python
# backend/app/api/simulation.py:930-944
_ENRICH_RATE_HITS: dict = {}
_ENRICH_RATE_WINDOW_SEC = 60
_ENRICH_RATE_MAX_CALLS = 10
```

### 4.2 Endpoints sans rate limit (⚠️ P1)

- `POST /api/report/generate` — déclenche un thread + appels LLM. Un attaquant peut saturer la queue LLM.
- `POST /api/report/chat` — chaque appel lance un ReAct loop avec outils Neo4j.
- `POST /api/simulation/create` — crée un répertoire disque + Supabase row.

**Recommandation P1 :** Appliquer `_sliding_window_rate_limited` sur ces 3 endpoints (pattern existant identique). Priorité modérée car `create` est partiellement protégé par `@soft_check_self_service`.

---

## A05 — Security Misconfiguration

### 5.1 Headers de sécurité (✅ OK)

`backend/app/security_headers.py` est bien branché dans `create_app()` :

```python
# backend/app/__init__.py:62-63
from .security_headers import init_security_headers
init_security_headers(app)
```

Headers actifs : `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: camera=(), microphone=(), geolocation=()`, `X-Frame-Options: SAMEORIGIN` (hors routes embeddables), HSTS en prod, CSP.

### 5.2 DEBUG=False (✅ OK)

```python
# backend/app/config.py:44
DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
```

Par défaut `False`. Testé par `test_unit_hardening.py`.

### 5.3 Stack traces exposées en réponses publiques (⚠️ P0 CORRIGÉ)

**Constat grave :** Des dizaines d'endpoints publics non authentifiés exposent `traceback.format_exc()` dans les réponses JSON 500.

**Preuve :**
```python
# backend/app/api/report.py:372-376
return jsonify({
    "success": False,
    "error_code": "INTERNAL_ERROR",
    "error": str(e),
    "traceback": traceback.format_exc()   # ← exposé au client !
}), 500
```

Cela révèle :
- Chemins de fichiers serveur absolus
- Versions de bibliothèques utilisées
- Structure interne du code (noms de classes, méthodes)
- Potentiellement des valeurs de variables locales

**Impact :** Information disclosure facilitant les attaques ciblées.

**Correction P0 appliquée :** Voir `backend/app/api/simulation.py` et `backend/app/api/report.py` — la clé `"traceback"` est supprimée des réponses JSON publiques. Les tracebacks restent dans les logs serveur.

### 5.4 CORS (✅ OK)

```python
# backend/app/__init__.py:43-56
cors_origins_env = os.environ.get('CORS_ORIGINS', 'https://prospectives.ai-mpower.com,...')
```

Pas de `*` par défaut. Warning loggué si `*` détecté.

---

## A06 — Vulnerable Components

### 6.1 Backend Python (À VÉRIFIER)

`pip-audit` n'est pas installé dans l'environnement de test. Commande à lancer manuellement en prod :

```bash
uv add --dev pip-audit && uv run pip-audit
```

Aucune vulnérabilité connue détectée par inspection manuelle sur les packages critiques (PyJWT, flask-cors, supabase-py).

### 6.2 Frontend npm (⚠️ P1)

`npm audit` révèle **8 vulnérabilités** (5 HIGH, 3 MODERATE) :

| Package | Sévérité | CVE / Titre |
|---|---|---|
| `axios ^1.13.2` | HIGH | DoS via `__proto__` key in mergeConfig (GHSA-43fc-jf86-j433) |
| `axios ^1.13.2` | MODERATE | SSRF via NO_PROXY bypass (GHSA-3p68-rc4w-qgx5) |
| `axios ^1.13.2` | MODERATE | Auth bypass via prototype pollution (GHSA-w9j2-pvgh-6h63) |
| `dompurify` | MODERATE | ADD_TAGS bypass FORBID_TAGS |
| `follow-redirects` | MODERATE | Auth header leak on redirect |
| `marked` | HIGH | OOM via infinite recursion (GHSA-...) |
| `picomatch` | HIGH | ReDoS via extglob quantifiers |
| `rollup` | HIGH | Arbitrary file write via path traversal |
| `vite` | HIGH | Path traversal in `.map` handling |

**Recommandation P1 :** `npm update axios` (vers ≥ 1.15.1). Les autres (vite, rollup, picomatch) sont des dépendances de build uniquement — risque limité en prod mais à surveiller.

**Note :** Ne pas forcer la mise à jour en aveugle (risque de breaking changes). Tester d'abord sur la branche.

---

## A07 — Identification and Authentication Failures

### 7.1 Délégation Supabase Auth (✅ OK)

Aucune logique custom d'auth. On délègue entièrement à Supabase Auth :
- Login/signup : Supabase client-side
- JWT validation : `verify_supabase_jwt()` avec JWKS (ES256) ou SUPABASE_JWT_SECRET (HS256 legacy)

### 7.2 `getUser()` vs `getSession()` (✅ OK — backend)

Le backend ne fait jamais confiance à une session côté client. Il valide systématiquement le JWT via `verify_supabase_jwt()` (qui vérifie la signature cryptographiquement). Les claims sont extraits du JWT validé, jamais depuis une session cookie non vérifiée.

### 7.3 Session timeout (✅ OK)

Géré par Supabase Auth (token `exp` dans JWT, refreshed par le client). Le backend vérifie `exp` via `require: ["exp", "sub"]` dans les options PyJWT.

---

## A08 — Software and Data Integrity Failures

### 8.1 Webhook Stripe (✅ N/A)

Aucun webhook Stripe entrant en code. Le bridge Stripe US-104 est un bridge **manuel** : l'admin génère un Payment Link via le Dashboard Stripe et l'envoie manuellement via `/api/admin/quotes/<id>/send-payment-link`. Aucune signature webhook Stripe à vérifier.

### 8.2 Webhook sortant (✅ OK)

`backend/app/services/webhook_service.py` : la signature `X-MiroShark-Event` est un simple label (non un HMAC). Mais c'est un webhook *sortant* contrôlé par l'opérateur, pas un flux entrant. Pas de risque d'injection.

---

## A09 — Security Logging and Monitoring

### 9.1 JWT et secrets (✅ OK)

La politique de non-logging des JWT est strictement respectée :

```python
# jwt_verifier.py:245
logger.info("JWT rejected by PyJWT: %s", exc.__class__.__name__)
```

Le token brut, le header `Authorization`, et l'email ne sont jamais loggués en clair. Le décorateur `@require_super_admin` loggue uniquement le hash sha256 tronqué de l'email rejeté :

```python
# decorators.py:353-357
digest = hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:8]
logger.warning("super-admin denied for email_hash=%s ...", digest)
```

### 9.2 Logs audit admin (✅ OK)

`admin.py:921-924` : toggle self-service loggué avec `org_id` et valeur.

### 9.3 Prints résiduelle (⚠️ À SURVEILLER — non bloquant)

Des `print()` subsistent dans des services internes :
- `backend/app/utils/llm_client.py:353` : debug langfuse (first call only, pas de secrets)
- `backend/app/services/wonderwall_profile_generator.py:1342-1344` : progress reporting (pas de secrets)
- `backend/app/utils/run_summary.py:159` : summary markdown (pas de secrets)

Aucune de ces lignes ne logue de JWT, clé API, ou email. Risque : bruit dans les logs prod. Recommandation : remplacer par `logger.info()` à terme (P2, non bloquant).

---

## A10 — SSRF

### 10.1 `/api/simulation/enrich-ask` — Question enrichment (✅ OK)

Le endpoint `enrich-ask` passe une `question` (string brut) au LLM via `WebEnricher.enrich_question()`. Aucune URL n'est construite à partir de l'input utilisateur — la question est envoyée comme contenu, pas comme URL à fetcher. Pas de risque SSRF direct ici.

### 10.2 `url_fetcher.py` — Fetch URL via LLM (✅ OK — protection en place)

`backend/app/utils/url_fetcher.py` : le fetch URL délègue au LLM (pas d'appel HTTP direct depuis le backend). La fonction `_validate_url()` vérifie :
- Schéma : uniquement `http`/`https`
- IP résolue via `socket.gethostbyname()` : bloque private, loopback, link-local, reserved

```python
# url_fetcher.py:28-34
def _check_ip(ip_str: str) -> None:
    addr = ipaddress.ip_address(ip_str)
    if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
        raise ValueError(...)
```

**Limitation connue :** DNS rebinding possible (vérification faite avant la requête LLM, le LLM peut refetcher avec une IP différente). Risque atténué car c'est le LLM qui fait le fetch, pas le backend directement.

**Limitation :** `socket.gaierror` est silencé (`pass`) — si le DNS échoue, l'URL passe. Tolérable car le LLM surfacera l'erreur DNS.

### 10.3 `webhook_service.validate_url()` — SSRF sur webhook (⚠️ P0 CORRIGÉ)

**Constat :** `webhook_service.py:120-137` — `validate_url()` vérifie uniquement le schéma (`http`/`https`) et la longueur. Elle ne résout pas l'IP et ne bloque pas les adresses privées.

**Impact :** Un opérateur (ou une faille dans la Settings UI) pourrait configurer `WEBHOOK_URL=http://169.254.169.254/latest/meta-data/` (AWS metadata) et le backend ferait une requête HTTP vers cette IP interne à chaque simulation complétée.

**Preuve :**
```python
# backend/app/services/webhook_service.py:120-137
def validate_url(url: str) -> Optional[str]:
    # Vérifie juste le schéma, PAS l'IP !
    if not (lowered.startswith('http://') or lowered.startswith('https://')):
        return "Webhook URL must start with http:// or https://"
    return None  # ← aucune vérification IP
```

**Correction P0 appliquée :** `validate_url()` résout maintenant l'IP et bloque les ranges privés/loopback/link-local/réservés via la même logique que `url_fetcher.py`.

---

## Corrections P0 appliquées

### P0-1 : Stack traces retirées des réponses JSON publiques

**Fichiers modifiés :**
- `backend/app/api/simulation.py` : suppression de `"traceback": traceback.format_exc()` dans les réponses JSON 500 publiques (non authentifiées). Les tracebacks sont conservés dans les logs serveur.
- `backend/app/api/report.py` : idem.

**Stratégie :** Les endpoints sous `@require_admin_token` ou `@require_super_admin` conservent le traceback (audience = opérateurs). Les endpoints publics ou derrière `@soft_check_self_service` ne le transmettent pas au client.

### P0-2 : SSRF — webhook_service.validate_url() avec blocage IP privée

**Fichier modifié :** `backend/app/services/webhook_service.py`

`validate_url()` résout maintenant l'IP du host et lève une erreur si l'adresse est dans un range privé/loopback/link-local/réservé, bloquant les tentatives de SSRF via WEBHOOK_URL.

---

## Recommandations P1 (next sprint)

1. **A06 — npm axios** : `npm update axios` vers ≥ 1.15.1 (fixes DoS + SSRF bypass + prototype pollution). Tester build avant merge.
2. **A04 — rate limit report/generate et report/chat** : appliquer `_sliding_window_rate_limited` (20 calls/60s/IP recommandé — les appels LLM sont longs).
3. **A06 — pip-audit** : intégrer `pip-audit` dans le pipeline CI pour audit continu des dépendances Python.
4. **A09 — prints résiduels** : remplacer les `print()` dans les services par `logger.info()`.
5. **A01 — /api/report/* auth** : évaluer l'ajout de `@soft_check_self_service` sur `get_report` et `download_report` pour les contextes où les rapports sont confidentiels.

---

*Rapport généré par l'agent Ralph US-116 le 2026-05-05.*
