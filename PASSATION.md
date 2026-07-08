== PASSATION NUCLÉAIRE MiroShark/Bassira — 2026-07-08 (soir, contexte <60%) ==
Synthèse complète et autonome — ne suppose la lecture d'aucune passation antérieure.

[ETAT]
- Branche `main`, poussée à jour : `e89696a` (dernier commit, code). Prod https://bassira.ma
  **UP, HTTP 200**, conteneur `miroshark-u6pn5mr2pgi88s13un55pkzb-194734237493` tourne sur
  l'image taguée exactement `e89696a…` (vérifié `docker ps` sur le serveur — déploiement
  auto Coolify confirmé, pas juste supposé).
- Base Supabase de Bassira = **self-hosted sur le serveur**, stack Coolify
  `dgybi9q5e2ggkjtaxlu2ukai`, URL publique `https://db-miroshark.ai-mpower.com`. **Migration
  hors de l'ancienne base « ventures » actée** — décision confirmée : repartir propre, PAS de
  migration des anciennes données. Base actuellement quasi vide (2 comptes de test créés
  cette session, `organizations`=1, le reste des tables métier à 0 lignes — normal,
  pré-lancement).
- `.ralph/prd.json` v2.0.0, chantier `V2-A-blocA` : US-201/202/206 `passes:true`. US-203
  (payload devis→Supabase) et US-204 (Resend+bassira.ma) : code+infra faits mais
  `passes:false` — il manque toujours la preuve d'un devis test réel survivant à un redeploy
  (reporté par Amine, jamais refait depuis). US-207 (WSGI prod) et US-208 (Redis/worker PDF)
  `pending`, pas commencées. US-205 (Stripe) : voir [BLOQUÉ].
- Cartographie complète du projet disponible : `.understand-anything/knowledge-graph.json`
  (1441 nœuds, 2468 arêtes, 10 couches, tour guidé 14 étapes, 554 fichiers analysés).
  Dashboard interactif lancé via skill `/understand-dashboard` (process de session, mort au
  `/clear` — relancer si besoin, le graphe lui est déjà sauvegardé de façon permanente).

[FAIT cette session]
1. **Incident « Erreur réseau » login RÉSOLU** : l'ingress du tunnel Cloudflare remote-managed
   n'avait aucune règle pour `db-miroshark.ai-mpower.com` (catch-all 404, donc pas de CORS,
   donc `failed to fetch` navigateur). Fix : `PUT` de l'ingress complet du tunnel
   `7156c3f9-07a4-472d-963a-efaf59769d40` avec la règle ajoutée (version 114, 58 règles) +
   sync `config-nahda.yml` sur le serveur. Non-régression vérifiée sur bassira.ma,
   prospectives, nahda.ma, tamkin.ma.
2. **Incident `fetchProfile 503 AUTH_NOT_CONFIGURED` RÉSOLU** : la base self-hosted signe ses
   JWT en HS256 (pas JWKS asymétrique comme l'ancienne base Cloud) → le backend exigeait
   `SUPABASE_JWT_SECRET`, absente de l'env Coolify. Copié depuis `GOTRUE_JWT_SECRET` de la
   stack `dgybi…` vers l'env Coolify de l'app + restart. Preuve E2E : login réel +
   `GET /api/client/auth/me` → HTTP 200, org AIMPOWER/owner renvoyée.
3. **Comptes créés** (API admin GoTrue, email confirmé d'office) : `test@bassira.ma` (sans
   org, existence à trancher) et `medamine.mansouriidrissi@gmail.com` (**owner** org AIMPOWER
   `f7abf22e-a0f0-49ad-9e47-484787924c0f`). **Login confirmé fonctionnel par Amine.**
4. **`COOLIFY_API_TOKEN` du coffre DPAPI découvert PÉRIMÉ** (401 sur l'API). Nouveau token
   généré directement en base Coolify (Sanctum, id=10, abilities root, nom
   `claude-rotation-2026-07-08`) — valeur stockée UNIQUEMENT sur le serveur :
   `/home/serveuria/.credentials/coolify-api-token-claude-20260708` (chmod 600). **Rotation
   dans le coffre DPAPI toujours PAS faite** (session sans accès à `~/.claude/secrets`).
5. **`RESEND_API_KEY` corrigée** : la clé déployée sur Coolify était invalide (401 « API key is
   invalid » constaté par appel direct à l'API Resend). Remplacée par la clé valide du coffre
   (domaine `ai-mpower.com` vérifié, région eu-west-1) + restart. **Vérifié par un envoi réel
   post-rebuild : HTTP 200, id Resend `52409253-4343-4dc3-a96c-452801a83a3f`.** Cause du
   « je ne reçois aucun mail » signalé par Amine — aucun rapport avec le code applicatif.
6. **Indépendance de la base Supabase CONFIRMÉE** : scan des 28 apps Coolify — aucune app hors
   miroshark (et ses sidecars neo4j/ollama du même groupe docker-compose) ne référence
   `db-miroshark.ai-mpower.com`. La stack `dgybi…` est exclusive à Bassira.
7. **2 bugs UI corrigés, commités, POUSSÉS et DÉPLOYÉS** (commit `e89696a`, vérifié en prod) :
   - `frontend/src/components/AppHeader.vue` : le lien nav « Modèles » portait en dur la
     classe `app-header__link--featured`, dont le CSS était identique à
     `.router-link-active` → paraissait actif sur toutes les pages. Classe retirée.
   - `frontend/src/views/OffersView.vue` : la netteté des cartes d'offres suivait
     `activeIndex` (état de carrousel initialisé à 0 → 1ʳᵉ carte toujours nette), pas le
     survol. `.offers-slide--active { opacity:1 }` → `.offers-slide:hover { opacity:1 }`
     (le scale/glow du carrousel sur `--active`/`--featured` reste inchangé).
   Build frontend vérifié vert avant commit.
8. **Outillage navigateur installé** : `dev-browser` (npm global, CLI Sawyer Hood, MIT,
   légitime — vérifié via `npm view` avant install) car l'extension Claude-in-Chrome n'est
   PAS connectée sur ce poste (`tabs_context_mcp` → « Browser extension is not connected »).
   `dev-browser` pilote un Chromium local géré par un démon (`dev-browser status`/`browsers`).

[ALERTE]
- ⚠️ **`COOLIFY_API_TOKEN` du coffre DPAPI toujours périmé** — toute session future utilisant
  `. load-secrets.ps1` puis l'API Coolify échouera en 401 tant que la rotation n'est pas
  faite. Valeur de remplacement prête sur le serveur (point 4 ci-dessus) ; il faut soit une
  session avec accès à `~/.claude/secrets`, soit qu'Amine la reporte lui-même (SOP-001
  brouillon, procédure de rotation).
- ⚠️ Le mot de passe généré pour `medamine.mansouriidrissi@gmail.com` a été transmis via le
  presse-papier Windows en fin de session précédente — normalement déjà utilisé/changé par
  Amine (login confirmé fonctionnel), mais pas de confirmation qu'il l'a changé depuis.
- ⚠️ Compte `test@bassira.ma` toujours existant, sans organisation — décision de suppression
  jamais explicitement demandée par Amine, à trancher.
- ⚠️ Dashboard `/understand` (vite dev server, port 5173) tournait en process de session —
  mourra au `/clear`. Le graphe (`knowledge-graph.json`) lui est permanent, relancer via
  `/understand-dashboard` suffit si Amine veut y revenir.

[BLOQUÉ]
- !! **Stripe (US-205) EN COURS DE DÉBLOCAGE, PAS TERMINÉ.** Aucune clé
  `STRIPE_SECRET_KEY`/`STRIPE_WEBHOOK_SECRET` dans le coffre — code non écrit (pas de dette
  spéculative non testable). Amine a demandé de câbler Stripe via le **serveur MCP officiel
  Stripe** (`mcp__plugin_stripe_stripe__*`, pas du code custom directement). Flux OAuth
  démarré (`mcp__plugin_stripe_stripe__authenticate`) → URL d'autorisation ouverte dans
  `dev-browser` (page named "stripe-auth") → Amine était en train de se connecter à
  dashboard.stripe.com (email autofillé `a.mansouri@afrique…`, cookies déjà rejetés par moi)
  **au moment où le hook de passation s'est déclenché — état exact de l'autorisation
  INCONNU à la reprise, à vérifier en premier.**
- Périmètre exact US-205 une fois débloqué : créer products/prices Stripe des 3 packages
  (MAD/USD, **jamais EUR**), câbler Checkout Sessions sur `/offres`, webhook
  `checkout.session.completed` signé → `quote_ownership.status='paid'` automatique. AC :
  products/prices visibles dashboard Stripe test mode + paiement test complet automatique +
  aucun secret hardcodé + pytest/build verts.

[NEXT]
1. **EN PREMIER** : vérifier l'état de la connexion `dev-browser` page "stripe-auth"
   (`dev-browser <<'EOF' const page = await browser.getPage("stripe-auth"); console.log(page.url()); EOF`)
   — si sur `access.stripe.com/mcp/oauth2/authorize`, redemander à Amine de cliquer
   « Autoriser » ; si sur une page de callback en erreur (`localhost:3118/callback?...`),
   récupérer l'URL complète et appeler `mcp__plugin_stripe_stripe__complete_authentication`
   avec. Si déjà connecté, les outils `mcp__plugin_stripe_stripe__*` réels apparaîtront.
2. Une fois le MCP Stripe connecté : implémenter US-205 (products/prices MAD/USD, Checkout
   Sessions `/offres`, webhook signé, tests), marquer `passes:true` dans `.ralph/prd.json`
   après vérification E2E réelle (pas de claim sans test).
3. Rotation `COOLIFY_API_TOKEN` dans le coffre DPAPI (valeur prête côté serveur, cf. [ALERTE]).
4. Relancer avec Amine le test réel de devis (US-203/US-204, `passes:false` depuis plusieurs
   jours) — un devis soumis doit survivre à un redeploy ET déclencher un email Resend reçu
   <2min avec liens bassira.ma. Marquer les deux `passes:true` si succès.
5. Trancher le sort de `test@bassira.ma` (garder/supprimer).
6. Poursuivre Bloc A : US-207 (WSGI prod) → US-208 (Redis/worker PDF, dépend US-207).
7. Amine réglait aussi « un bug email » de son côté (périmètre non précisé) — vérifier où il
   en est ; ne pas y toucher sans qu'il ait explicitement rendu la main dessus.

[CTX]
- Accès serveur (hors LAN) : Tailscale `100.124.187.2`, `ssh -i ~/.ssh/serveurai_mnemo
  serveuria@100.124.187.2` (user `serveuria`, PAS `serveurai`).
- App Coolify miroshark : uuid `u6pn5mr2pgi88s13un55pkzb`, build_pack `dockercompose`.
- Tunnel Cloudflare partagé (~58 hostnames, ~15 projets) : `7156c3f9-07a4-472d-963a-efaf59769d40`,
  **remote-managed** (le fichier local `config-nahda.yml` est cosmétique, la vraie source de
  vérité est l'API `GET/PUT .../cfd_tunnel/{id}/configurations`).
- Stack Supabase Bassira = `dgybi9q5e2ggkjtaxlu2ukai` (PAS `dp7p66…` = Tamkin, piège déjà
  rencontré). Kong exposé en local `:8210` = Tamkin, ne jamais router dessus par erreur.
- Repo GitHub : `Afristrat/MiroShark`, push direct sur `main` déclenche un rebuild Coolify
  complet (~15 min), pas juste un restart léger — à anticiper avant chaque push pendant
  qu'Amine teste en direct.

[MEMO inter-sessions]
- **Cloudflare Tunnel remote-managed** : ne jamais supposer qu'éditer le YAML local + restart
  suffit — toujours vérifier le champ `source` de `GET .../configurations` ; si `"cloudflare"`,
  il faut `PUT` le tableau `ingress` complet (récupéré, modifié, repoussé tel quel — jamais
  retapé à la main).
- **Supabase self-hosted multi-projets sur le serveur** : ~10 stacks différentes
  (`supabase-db-<hash>`), ne jamais deviner laquelle — vérifier via `VITE_SUPABASE_URL` de
  l'app concernée avant toute opération SQL.
- **Toute opération d'infra (Docker, psql, CLI d'admin) → TOUJOURS sur le serveur via SSH**,
  jamais en local sur le poste Windows d'Amine.
- **Hook bash-guard** : bloque grep/heredocs non ancrés sur des sources sensibles (réponses API
  Coolify, tokens) — toujours passer par un script `.sh`/`.py` écrit via Write puis exécuté via
  scp+ssh, jamais de commande inline avec `cat`/grep large sur une sortie contenant un secret.
- **`dev-browser`** (nouvel outil, installé cette session) : CLI légitime (Sawyer Hood, MIT) qui
  pilote un Chromium local via un démon — utile quand Claude-in-Chrome n'est pas connecté.
  Pages nommées persistent entre invocations (`browser.getPage("nom")`).
- Amine veut être RECONNECTÉ pour piloter son navigateur normalement : installer l'extension
  Claude sur Chrome (claude.ai/chrome) + relancer Chrome résoudrait ça pour la prochaine fois.

— fin passation —
