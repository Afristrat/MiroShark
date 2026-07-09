== PASSATION NUCLÉAIRE MiroShark/Bassira — 2026-07-09 ==
Synthèse complète et autonome — ne suppose la lecture d'aucune passation antérieure.

[ETAT]
- Commit `b729078` poussé sur `main` (câblage Stripe complet) — **DÉPLOIEMENT CONFIRMÉ** :
  conteneur `miroshark-u6pn5mr2pgi88s13un55pkzb-000517664243` tourne sur l'image taguée
  exactement `b729078ca528ba44f8906569aa7e2d1abf018f0c`, `STRIPE_SECRET_KEY` et
  `STRIPE_WEBHOOK_SECRET` présentes dans son env, `bassira.ma` HTTP 200 (vérifié
  post-rebuild). Les routes `/api/stripe/create-checkout-session` et `/api/stripe/webhook`
  sont donc en prod, MAIS le test E2E réel (Checkout Session + webhook) n'est PAS encore
  fait (cf. [BLOQUÉ]).
- Base Supabase de Bassira = **self-hosted sur le serveur**, stack Coolify
  `dgybi9q5e2ggkjtaxlu2ukai`, URL publique `https://db-miroshark.ai-mpower.com`. Migration
  hors de l'ancienne base « ventures » actée par Amine — repartir propre, pas de migration
  des anciennes données. Base quasi vide (2 comptes de test, `organizations`=1, reste à 0
  lignes — normal, pré-lancement).
- **Stripe connecté en MODE LIVE** (compte `acct_1PHxGdHM2FpoSxES`, « AI-MPower, L.L.C. »)
  — décision explicite d'Amine après échec répété de bascule en sandbox via MCP (cf.
  [MEMO]). Aucune boutique live active actuellement (confirmé par Amine), risque accepté.
- `.ralph/prd.json` v2.0.0, chantier `V2-A-blocA` : US-201/202/206 `passes:true`. US-203
  (payload devis→Supabase) et US-204 (Resend+bassira.ma) : code+infra faits mais
  `passes:false` — il manque toujours la preuve d'un devis test réel survivant à un
  redeploy (reporté par Amine il y a plusieurs jours, jamais refait depuis). US-205
  (Stripe) : code fait, `passes:false` en attente de vérification E2E (cf. [BLOQUÉ]).
  US-207 (WSGI prod) et US-208 (Redis/worker PDF) : `pending`, pas commencées.
- Cartographie complète du projet disponible : `.understand-anything/knowledge-graph.json`
  (1441 nœuds, 2468 arêtes, 10 couches, tour guidé 14 étapes, 554 fichiers analysés).
  Dashboard relançable via skill `/understand-dashboard` (process de session, mort au
  `/clear` — le graphe lui est permanent).

[FAIT — session 2026-07-09 (Stripe)]
1. Connexion Stripe MCP établie (`mcp__plugin_stripe_stripe__*`) après plusieurs
   déblocages (extension Claude-in-Chrome non connectée → repli `dev-browser` → retour
   Chrome natif via `/mcp` de Claude Code, tapé par Amine). `dev-browser` (npm, CLI Sawyer
   Hood, MIT, légitime) installé sur ce poste — **réservé aux tâches non sensibles**,
   Chrome/Claude-in-Chrome reste la référence pour banques/paiements (préférence Amine,
   mémoire `feedback_browser_tool_choice.md`).
2. ADR-014 rédigée (`docs/08-decisions-log.md`) : Stripe self-service limité aux 3
   packages d'entrée (PMF Discovery, Crisis Drill 24h, Adcheck Lite) — les 6 paliers
   supérieurs restent sur le circuit devis manuel (confirme/resserre ADR-007, ne le
   contredit pas). Ajout d'une 3e devise EUR (contredit consciemment le « jamais EUR »
   d'ADR-007 pour CES 3 packages uniquement) — montants EUR = parité nominale avec l'USD
   (1000/2000/1500), décision explicite Amine.
3. Catalogue Stripe créé et VÉRIFIÉ (mode live) — 3 produits, chacun un seul objet Price
   portant les 3 devises en `currency_options` :
   - PMF Discovery `prod_UqkLY0kI0DSQJy` / Price actif `price_1Tr4hBHM2FpoSxESlmb3WXlR` —
     10 000 MAD / 1 000 USD / 1 000 EUR
   - Crisis Drill 24h `prod_UqmDV3PoJTKwtD` / Price actif `price_1Tr4hCHM2FpoSxESlD4heCqI` —
     20 000 MAD / 2 000 USD / 2 000 EUR
   - Adcheck Lite `prod_UqmDJa4ZnBnc8M` / Price actif `price_1Tr4hEHM2FpoSxESig2ZeeD1` —
     15 000 MAD / 1 500 USD / 1 500 EUR
   Incident corrigé en cours de route : 1ʳᵉ tentative avait mis le même montant sur les 3
   devises (MAD 10× trop bas) — repéré par Amine, corrigé par remplacement des Price (les
   anciens désactivés, pas supprimés — Stripe interdit de modifier `unit_amount`/`currency`
   d'un Price existant).
4. Backend écrit et vérifié techniquement (build + `uv run pytest -m "not integration"` →
   **1689 passed, 0 failed** ; `py_compile` + boot Flask + `url_map` confirmant les 2
   routes) :
   - `backend/app/services/stripe_service.py` — `create_checkout_session()` (devise
     explicite via param `currency` sur la Session) + `verify_webhook_signature()`
     (HMAC-SHA256 stdlib, PAS le SDK `stripe` — `requests` déjà dépendance).
   - `backend/app/api/stripe_checkout.py` — `POST /api/stripe/create-checkout-session`
     (public) + `POST /api/stripe/webhook` (signature vérifiée) → sur
     `checkout.session.completed`, insère `quote_ownership` avec `status='paid'`
     directement (quote_id = `stripe_<checkout_session_id>`, org = fallback interne
     `aimpower-bassira`, résolue par slug).
5. Frontend câblé (`frontend/src/views/OffersView.vue`) : les 3 packages d'entrée ont
   `selfService:true` → clic CTA appelle `createCheckoutSession()` et redirige vers l'URL
   Stripe hébergée. Toggle devise étendu à 3 boutons MAD/USD/EUR (`displayCurrency(pkg)`
   avec repli gracieux sur USD pour les 7 packages sans `priceEUR`). États loading/erreur
   scopés par carte.
6. Secrets posés en env Coolify (jamais affichés, presse-papier → script stdin → purge
   immédiate) : `STRIPE_SECRET_KEY` (clé RESTREINTE, Checkout Sessions write uniquement,
   créée par Amine) et `STRIPE_WEBHOOK_SECRET` (endpoint `https://bassira.ma/api/stripe/webhook`
   sur `checkout.session.completed`, créé par Amine). Les deux confirmés HTTP 201.
7. i18n polyglotte respecté : 4 clés d'erreur (`UNKNOWN_PACKAGE`, `INVALID_REQUEST`,
   `STRIPE_NOT_CONFIGURED`, `STRIPE_API_ERROR`) + `offers.checkout.loading` ajoutées en
   fr/en/ar, JSON validé. `docs/02-data-dictionary.md` mis à jour (format `quote_id`
   étendu).

[FAIT — session 2026-07-08 (infra + UI, tout déployé et vérifié)]
1. Incident « Erreur réseau » login résolu : ingress du tunnel Cloudflare remote-managed
   sans règle pour `db-miroshark.ai-mpower.com` (catch-all 404 → pas de CORS → `failed to
   fetch`). Fix : `PUT` de l'ingress complet (version 114, 58 règles) + sync
   `config-nahda.yml`. Non-régression vérifiée sur 4 hostnames du tunnel partagé.
2. Incident `fetchProfile 503 AUTH_NOT_CONFIGURED` résolu : la base self-hosted signe ses
   JWT en HS256 (pas JWKS comme l'ancienne base Cloud) → `SUPABASE_JWT_SECRET` copiée
   depuis `GOTRUE_JWT_SECRET` de la stack `dgybi…` vers l'env Coolify. Preuve E2E : login
   réel + `GET /api/client/auth/me` → HTTP 200.
3. Comptes créés (API admin GoTrue) : `test@bassira.ma` (sans org) et
   `medamine.mansouriidrissi@gmail.com` (owner org AIMPOWER `f7abf22e-…`). Login confirmé
   fonctionnel par Amine.
4. `RESEND_API_KEY` corrigée : celle déployée était invalide (401 « API key is invalid »
   direct API Resend). Remplacée par la clé valide du coffre + restart. Vérifié par un
   envoi réel post-rebuild : HTTP 200, id Resend `52409253-…`.
5. Indépendance de la base Supabase confirmée : scan des 28 apps Coolify, aucune hors
   miroshark (et ses sidecars neo4j/ollama) ne référence `db-miroshark.ai-mpower.com`.
6. 2 bugs UI corrigés, déployés (commit `e89696a`, vérifié en prod) : lien nav « Modèles »
   qui gardait un style actif permanent (classe `--featured` codée en dur, retirée) ;
   netteté des cartes `/offres` pilotée par `activeIndex` au lieu du survol
   (`.offers-slide:hover` remplace `.offers-slide--active` pour l'opacité).

[ALERTE]
- ⚠️ **`COOLIFY_API_TOKEN` du coffre DPAPI toujours périmé** (401 constaté). Nouveau token
  généré directement en base Coolify (Sanctum id=10, root), stocké UNIQUEMENT sur le
  serveur : `/home/serveuria/.credentials/coolify-api-token-claude-20260708` (chmod 600).
  **Rotation dans le coffre DPAPI toujours pas faite** — nécessite une session avec accès
  à `~/.claude/secrets`, ou qu'Amine la fasse lui-même (SOP-001 brouillon).
- ⚠️ Stripe en mode live sans sandbox fonctionnel — tout test doit utiliser de vraies
  Checkout Sessions (jamais complétées avec une vraie carte) plutôt que des cartes de
  test, qui n'existent qu'en sandbox.
- ⚠️ Compte `test@bassira.ma` toujours existant, sans organisation — décision de
  suppression jamais explicitement demandée par Amine.
- ⚠️ Mot de passe de `medamine.mansouriidrissi@gmail.com` transmis via presse-papier
  Windows il y a plusieurs jours — login confirmé fonctionnel depuis, probablement changé
  par Amine mais pas reconfirmé.

[BLOQUÉ / EN COURS]
- !! **Test E2E Stripe réel PAS fait** (déploiement lui CONFIRMÉ, cf. [ETAT]) : appeler
  `/api/stripe/create-checkout-session` pour un des 3 packages → vérifier une vraie URL
  Stripe renvoyée (NE PAS compléter le paiement avec une vraie carte, mode live). Pour le
  webhook : calculer la signature HMAC ENTIÈREMENT côté serveur (lire
  `STRIPE_WEBHOOK_SECRET` de l'env du conteneur, ne jamais la faire transiter par le chat)
  sur un payload `checkout.session.completed` synthétique, curler
  `/api/stripe/webhook` en local sur le serveur, vérifier la ligne `quote_ownership`
  insérée avec `status='paid'`.
- !! **Devis test réel US-203/US-204 PAS fait** (reporté par Amine il y a plusieurs
  jours) : soumettre un devis via le formulaire public → vérifier (a) la row apparaît
  dans `quote_ownership` avec `payload` rempli, (b) email Resend reçu <2min avec liens
  bassira.ma, idéalement (c) survie à un redeploy entre les deux. Clôt US-203 ET US-204
  d'un coup si succès.
- ! US-205 pas encore marquée `passes:true` dans `.ralph/prd.json` — attendre la
  vérification E2E réelle avant (jamais de claim sans preuve).

[NEXT]
1. **EN PREMIER** : test E2E Stripe réel (Checkout Session + webhook signé, cf. [BLOQUÉ])
   → si succès, marquer US-205 `passes:true` dans `.ralph/prd.json`.
2. Rotation `COOLIFY_API_TOKEN` dans le coffre DPAPI (valeur prête côté serveur).
3. Relancer avec Amine le devis test réel US-203/US-204 (cf. [BLOQUÉ]).
4. Trancher le sort de `test@bassira.ma` (garder/supprimer).
5. Poursuivre Bloc A : US-207 (WSGI prod) → US-208 (Redis/worker PDF, dépend US-207).

[CTX]
- Accès serveur (hors LAN) : Tailscale `100.124.187.2`,
  `ssh -i ~/.ssh/serveurai_mnemo serveuria@100.124.187.2` (user `serveuria`, PAS
  `serveurai`).
- App Coolify miroshark : uuid `u6pn5mr2pgi88s13un55pkzb`, build_pack `dockercompose`.
- Tunnel Cloudflare partagé (~58 hostnames, ~15 projets) :
  `7156c3f9-07a4-472d-963a-efaf59769d40`, **remote-managed** (le fichier local
  `config-nahda.yml` est cosmétique, la vraie source de vérité est l'API
  `GET/PUT .../cfd_tunnel/{id}/configurations`).
- Stack Supabase Bassira = `dgybi9q5e2ggkjtaxlu2ukai` (PAS `dp7p66…` = Tamkin, piège déjà
  rencontré). Kong exposé en local `:8210` = Tamkin, ne jamais router dessus par erreur.
- Repo GitHub : `Afristrat/MiroShark`, push direct sur `main` déclenche un rebuild Coolify
  complet (~15 min), pas juste un restart léger — à anticiper avant chaque push pendant
  qu'Amine teste en direct.
- Compte Stripe : `acct_1PHxGdHM2FpoSxES` (« AI-MPower, L.L.C. »), mode live.

[MEMO inter-sessions]
- **Cloudflare Tunnel remote-managed** : ne jamais supposer qu'éditer le YAML local +
  restart suffit — toujours vérifier le champ `source` de `GET .../configurations` ; si
  `"cloudflare"`, `PUT` le tableau `ingress` complet (récupéré, modifié, repoussé tel
  quel — jamais retapé à la main).
- **Supabase self-hosted multi-projets sur le serveur** : ~10 stacks différentes
  (`supabase-db-<hash>`), ne jamais deviner laquelle — vérifier via `VITE_SUPABASE_URL`
  de l'app concernée avant toute opération SQL.
- **Toute opération d'infra (Docker, psql, CLI d'admin) → TOUJOURS sur le serveur via
  SSH**, jamais en local sur le poste Windows d'Amine.
- **Hook bash-guard** : bloque grep/heredocs non ancrés sur des sources sensibles —
  toujours passer par un script `.sh`/`.py` écrit via Write puis exécuté via scp+ssh,
  jamais de commande inline avec `cat`/grep large sur une sortie contenant un secret. Idem
  pour un `git commit -m` avec heredoc `<<'EOF'` dans le message : passer par
  `git commit -F <fichier>`.
- **`dev-browser`** : CLI légitime (Sawyer Hood, MIT) qui pilote un Chromium local via un
  démon — utile quand Claude-in-Chrome n'est pas connecté, mais réservé aux tâches NON
  sensibles (jamais banques/paiements — préférence Amine). Pages nommées persistent entre
  invocations (`browser.getPage("nom")`).
- **OAuth Stripe MCP et mode sandbox** : l'autorisation se scope au mode (live/sandbox)
  actif dans le dashboard Stripe au moment du clic « Autoriser » — la bascule vers sandbox
  a échoué plusieurs fois malgré la procédure documentée (Amine a tranché : rester en
  live). Piège : après révocation d'une session OAuth
  (dashboard.stripe.com/settings/user), l'outil `authenticate` peut disparaître de la
  liste d'outils sans revenir — la commande native Claude Code **`/mcp`** (tapée par
  Amine) force la reconnexion.
- **Stripe Price = immuable sur `unit_amount`/`currency`** : pour corriger un montant,
  créer un NOUVEAU Price, le poser en `default_price` du Product, désactiver l'ancien
  (jamais de suppression possible si déjà attaché).
- **`currency_options` sur un Price** : un seul objet Price peut porter plusieurs devises
  (`default_price_data.currency_options[usd][unit_amount]=...`). La Checkout Session
  choisit la devise effective via son paramètre top-level `currency=` — sinon Stripe
  auto-détecte via la géoloc du client (Adaptive Pricing).

— fin passation —
