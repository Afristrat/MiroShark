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

### YYYY-MM-DD HH:MM — US-XXX [titre]
- **Statut** : passes: true / passes: false (avec raison)
- **Fichiers touchés** : ...
- **Durée** : ...
- **Commit** : ...
- **Learnings** : (si pattern intéressant ou piège évité)

(à compléter par chaque itération)
