# Progress log — MiroShark Ralph loop

> Append-only. Une entrée par story complétée. Patterns/pièges en bas.

## Codebase Patterns (mise à jour continue)

### Frontend
- **baseURL axios** dans `frontend/src/api/index.js` doit rester relative (`''`) en prod pour passer par le reverse-proxy. La worktree dev utilise `.env.development` avec `VITE_API_TARGET` pointant vers la prod.
- **Compose détourné** : le service Vite dev tourne sur 0.0.0.0:3000 (`host: true` dans `vite.config.js`) avec `allowedHosts: true` pour accepter le hostname Cloudflare tunnel.
- **Design tokens** : `frontend/src/design-tokens.css` est la source de vérité unique des couleurs/spacing/radius. Le rebind legacy (`--color-orange` → `--ms-orange`) permet la migration progressive.

### Backend
- **Vue Compose Coolify** : les env vars de l'app Coolify sont **injectées dans tous les services du compose**, ce qui peut casser des images strict-validate (Neo4j 5 par défaut). Always validate `NEO4J_server_config_strict__validation_enabled=false` est en place.
- **Flask debug propagation** : `concurrently` tue le container quand Flask debug auto-reloader détecte un changement → cascade `restart: unless-stopped` Docker → restart loop. Toujours valider `FLASK_DEBUG=false` pour les déploiements stables.
- **DNS interne Docker** : avec Coolify, ne pas utiliser `container_name` dans le compose → préfix de Coolify casse les aliases de service.

### Infra
- **Tunnel Cloudflare** = `nahda-tunnel`, le service systemd s'appelle `cloudflared-nahda.service` (PAS `cloudflared.service`).
- **Reload après ajout sous-domaine** : `cloudflared tunnel route dns nahda-tunnel <sub>.ai-mpower.com` + ajout ingress + `sudo systemctl restart cloudflared-nahda`.

### Tests
- À documenter au fur et à mesure (pytest configs, Playwright fixtures, etc.).

## Pièges à éviter (déjà rencontrés)

- **Tunnel vers `https://...:port` côté Coolify Domains** crée des boucles HTTP redirect. Toujours utiliser `http://...:port` quand Cloudflare termine déjà le TLS.
- **Image GHCR privée** dans le compose upstream → toujours préférer `build: .` depuis le Dockerfile local sauf si l'image est publique.
- **`ports:` host-mode** dans le compose causent des conflits multi-app sur le même hôte Coolify. Utiliser `expose:` (réseau Docker interne).

## Log d'itérations

### 2026-04-29 — US-034 Security headers (HSTS, X-Frame-Options, CSP, Referrer-Policy, Permissions-Policy)
- **Statut** : passes: true
- **Fichiers** : backend/app/security_headers.py (nouveau), backend/app/__init__.py, backend/tests/test_unit_security_headers.py
- **Quality gates** : 8/8 tests security passent
- **Approche** :
  - Middleware Flask `after_request` → setdefault les headers (n'override pas si déjà posé)
  - `/share/*`, `/embed/*`, `/api/simulation/<id>/share-card.png|replay.gif` SANS X-Frame-Options ni CSP (pour social unfurl Slack/Discord/Twitter)
  - HSTS conditionnel à `FLASK_ENV != 'development'` (sinon dev local en HTTP foire)
  - CSP minimal qui tolère encore unsafe-inline + Google Fonts (à durcir post US-016)

### 2026-04-29 — US-031 + US-032 + US-033 Hardening prod minimal
- **Statut** : passes: true (3 stories en un seul commit, fichier config.py touché par les 3)
- **Fichiers** : backend/app/config.py, backend/app/__init__.py, backend/tests/test_unit_hardening.py
- **Quality gates** : 174 tests passed, 17 skipped (intégration), 0 régression
- **Changes** :
  - SECRET_KEY default → fallback per-process random (`secrets.token_hex(32)`) + flag `SECRET_KEY_FROM_ENV`
  - Config.validate() refuse de booter si SECRET_KEY absent + FLASK_ENV != 'development'
  - DEBUG default 'False' (était 'True')
  - CORS lit `CORS_ORIGINS` depuis env, defaults `https://prospectives.ai-mpower.com,http://localhost:3000,http://127.0.0.1:3000`
- **Learnings** :
  - importlib.reload(app.config) suffit pour tester monkeypatch.setenv sur Config classvars.
  - flask-cors gère bien les listes Python comme value de `origins`. Pas besoin d'array YAML.
  - Le sub-agent US-002 tourne en parallèle sans conflit (backend vs frontend).

### 2026-04-29 — US-001 Setup vue-i18n + structure locales
- **Statut** : passes: true
- **Fichiers** : frontend/src/i18n.js, frontend/src/locales/{fr,ar,en}.json, main.js, vite.config.js, package.json
- **Versions** : vue-i18n@^11.4.0 (et non v9 — v11 est maintenue actif)
- **Quality gates** : npm run build ✓ (199.89 kB main bundle / 66.10 kB gzip)
- **Learnings** :
  - vue-i18n 11 est la version maintenue (anciennement v9). API similaire (`createI18n`, `legacy: false`).
  - Le `@intlify/unplugin-vue-i18n` plugin Vite est obligatoire pour pré-compiler les JSON et activer `runtimeOnly: true` (bundle plus léger).
  - Détection 4 niveaux : URL `?lang=` → `localStorage` → `navigator.language` → fallback `fr`.
  - `applyDirection()` est appelé au chargement de l'instance i18n → pas besoin de toucher App.vue.

### 2026-04-29 — US-000 Sécuriser pytest pour quality gates Ralph
- **Statut** : passes: true
- **Fichiers touchés** : backend/pyproject.toml, backend/tests/test_unit_smoke.py, backend/tests/README.md
- **Durée** : ~10 min
- **Quality gates** : pytest 167 passed / 17 skipped intégration ✓ ; npm run build ✓
- **Learnings** :
  - Le repo avait déjà `conftest.py` avec markers + skip auto des integration. Bonne hygiène.
  - 17 fichiers `test_unit_*.py` déjà présents : le projet est plus mature qu'attendu côté tests.
  - Smoke tests minimaux (create_app, blueprints, Config.validate) suffisent pour US-000 car le reste de la suite valide déjà la majorité des composants.
