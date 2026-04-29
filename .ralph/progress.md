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
