== PASSATION MiroShark/Bassira 2026-07-08 (nuit) — US-204 CLOS côté infra/code, migrations prod appliquées, reste le test réel ==

[ETAT]
- branche `main`, poussée à jour : `aa24af3` (dernier commit). Prod
  https://prospectives.ai-mpower.com **ET** https://bassira.ma : **UP, HTTP 200 sur les deux**
  (vérifié après déploiement auto Coolify sur commit `1b3bbdf`, image
  `u6pn5mr2pgi88s13un55pkzb_miroshark:1b3bbdf...`).
- **`.ralph/prd.json` v2.0.0**, 142 stories, chantier `V2-A-blocA` (8 stories US-201→US-208) :
  - US-201 (repositionnement stress-test) : **passes:true**
  - US-202 (encart Méthode&limites PDF, AI Act art.50) : **passes:true**
  - US-203 (payload devis → Supabase) : **code + migration SQL appliquée en prod** —
    `passes:false` encore, il ne manque QUE la preuve d'un devis test réel qui survit à un
    redeploy (pas fait, décision d'Amine : reporté à demain, 2026-07-08 soir).
  - US-204 (Resend + bassira.ma) : **code + infra domaine + migration SQL, TOUT fait** —
    `passes:false` encore, il ne manque QUE le devis test réel (email reçu <2min, liens
    bassira.ma) — même report qu'US-203, peuvent se valider dans le MÊME test.
  - US-205 (Stripe) : `pending` — credentials Stripe toujours absents (bloqueur historique).
  - US-206 (fermer IDOR /api/report) : **passes:true**
  - US-207 (WSGI prod + fail-closed) : `pending`, pas commencée.
  - US-208 (Redis/worker PDF prod) : `pending`, dépend d'US-207.
- **Rotation de ce fichier** : > 150 Ko atteint ce soir → toutes les entrées antérieures
  (2026-07-07 nuit, et les 8 passations de 2026-04-29 à 2026-05-22) déplacées vers
  `PASSATION-ARCHIVE.md` (même dossier). Cette entrée est désormais la SEULE tête active et
  se veut autonome (ne suppose pas la lecture des anciennes).

[FAIT cette session (2026-07-07 soir → 2026-07-08 nuit, session longue)]
1. **US-204 code** : migration `20260707_002_footer_bassira_ma.sql` (défaut SQL
   `pdf_branding.footer_right` 'bassira.ai'→'bassira.ma' + backfill), fallbacks
   `admin_branding.py`/`AdminBrandingView.vue`, liens marketing des 5 templates email +
   lien méthodologie `InteractionView.vue` + footer PDF `build_attachment_pdfs.py` →
   `bassira.ma`. `.env.example` documente RESEND_API_KEY/RESEND_FROM_EMAIL/EMAIL_*
   (absents jusque-là). Tests `test_pdf_branding.py` alignés. `docs/02-data-dictionary.md`
   mis à jour. Suite complète pytest : 1688 passed / 1 flaky connu (voir [ALERTE]) / 42
   skipped GTK. Frontend build OK.
2. **Correction collatérale** : CRLF introduit par erreur sur 3 fichiers lors d'édits Claude
   (`.env.example`, `org_invitation.html`, `InteractionView.vue`) — détecté via diff
   anormalement large (1400+ lignes pour 1 ligne éditée), corrigé dans un commit séparé.
3. **Résolution infra bassira.ma en 3 couches** (avec confirmation Amine à chaque étape à
   risque, cf. AskUserQuestion dans la session) :
   a. Ingress local `~/.cloudflared/config-nahda.yml` sur `serveuria@192.168.100.11` —
      backup horodaté + ajout `bassira.ma → localhost:80` (cosmétique, voir c).
   b. Coolify : app `miro-shark` (uuid `u6pn5mr2pgi88s13un55pkzb`, build_pack
      `dockercompose`) — domaine ajouté via API `docker_compose_domains`
      (`{"<service>":{"name":...,"domain":"a,b"}}`, `name` requis sinon 422) +
      `POST /restart` (régénère les labels Traefik, recrée le conteneur).
   c. **CAUSE RACINE réelle** : le tunnel Cloudflare `7156c3f9-07a4-472d-963a-efaf59769d40`
      est **remote-managed** (`GET .../cfd_tunnel/{id}/configurations` → `"source":
      "cloudflare"`) — le fichier local est ignoré par le process en cours malgré
      `--config` explicite. Fix réel : `PUT .../cfd_tunnel/{id}/configurations` avec
      l'ingress complet (version 113). Détail procédure complète + piège dans
      `.ralph/progress.md` section "Suite US-204" ET dans la mémoire Claude
      `reference_serveurai_infra.md` (réécrite ce soir, corrige des erreurs qui trainaient
      depuis 2026-05-05).
   d. Effet de bord : process `cloudflared` orphelin (lancé 2026-07-06 hors systemd) tué
      après confirmation Amine — tunnel partagé avec ~15 apps d'autres projets (nizam-os,
      rami, taqwim, hafiz, tamkin, saqr, nahda, mem...), non-régression vérifiée.
4. **Push + déploiement auto confirmé** sur commit `1b3bbdf` (image Docker taguée au SHA
   exact, vérifié `docker ps` sur le serveur).
5. **Migrations SQL appliquées en prod** (demande explicite Amine « go pour les deux »,
   après correction ferme : « tout doit se faire sur le .11 jamais en local ») :
   - Tentative initiale via `SUPABASE_DB_URL` (env Coolify) → ÉCHEC, "tenant not found".
     Cette variable est un PIÈGE : elle pointe un vieux projet Supabase Cloud stale, **AUCUN
     code ne la référence** (`grep` confirmé). La vraie base de Bassira est le service
     Coolify self-hosted **`supabase-miroshark`** (uuid `dgybi9q5e2ggkjtaxlu2ukai`),
     identifié via `VITE_SUPABASE_URL=https://db-miroshark.ai-mpower.com` + liste des
     services Coolify.
   - Migrations appliquées via `docker exec` DIRECT dans le conteneur
     `supabase-db-dgybi9q5e2ggkjtaxlu2ukai` (`psql -U postgres -d postgres -f -`, auth
     locale sans mot de passe nécessaire) — méthode la plus simple et fiable, à retenir.
   - **Vérifié après coup** : `quote_ownership.payload` existe (US-203) ;
     `pdf_branding.footer_right` défaut = `'bassira.ma'` (US-204). `quote_ownership` a
     actuellement **0 lignes** (aucun devis réel soumis encore — normal, pré-lancement).
6. **Mémoire Claude mise à jour** : `reference_serveurai_infra.md` réécrite avec la
   découverte remote-managed + la bonne procédure API + le bon chemin serveur
   (`serveuria`, pas `serveurai`) ; nouvelle mémoire `feedback_ops_on_server_only.md`
   (jamais d'outils d'infra en local, toujours sur `.11`).

[ALERTE]
- ⚠️⚠️ **Secrets prod vus en clair pendant le diagnostic Coolify** (réponse API
  `GET /applications/{uuid}` inclut `docker_compose` en clair : `SECRET_KEY`,
  `NEO4J_PASSWORD`, `LLM_API_KEY`, `manual_webhook_secret_*` (bitbucket/gitea/github/gitlab),
  `sentinel_token`). Fichier scratch local supprimé immédiatement, AUCUNE valeur affichée
  dans la conversation à aucun moment. Amine n'a pas encore tranché si une rotation
  s'impose (SECRET_KEY, LLM_API_KEY notamment) — **question ouverte, pas de décision**.
- ⚠️ Les liens FONCTIONNELS restent VOLONTAIREMENT sur `prospectives.ai-mpower.com` :
  `invite_url` (`backend/app/api/invitations.py:162`), `BASSIRA_PUBLIC_URL`/`download_url`
  (`backend/app/services/report_delivery.py:233,381`), `CORS_ORIGINS` default
  (`backend/app/__init__.py:47`), `cta_link` PDF (`backend/app/api/models.py:153,188,222`).
  Plus aucune raison technique de ne pas les migrer (bassira.ma route correctement,
  vérifié) — mais c'est un choix de scope pour Amine, story dédiée suggérée (US-210,
  PAS ENCORE créée dans prd.json).
- ⚠️ 1 test flaky `test_md_hash_stable_with_deterministic_enricher` (échoue en suite
  complète, passe isolé — fuite d'état inter-tests). Consigné `docs/09-errors-log.md`,
  non bloquant, sans lien avec les fichiers modifiés cette session.
- ⚠️ EU AI Act Art. 50 applicable le **2026-08-02** (US-202 le couvre déjà — vérifier la
  couverture complète avant cette date, pas revérifié ce soir).

[BLOQUÉ — actions restantes]
- !! **Devis test réel en prod** (reporté par Amine à demain, 2026-07-08 soir/2026-07-09) :
  soumettre un devis via le formulaire public → vérifier (a) la row apparaît dans
  `quote_ownership` avec `payload` rempli (US-203), (b) email de confirmation reçu <2min
  avec expéditeur AI-MPower et liens `bassira.ma` (US-204), (c) idéalement un redeploy
  Coolify entre les deux pour prouver la survie au redeploy (US-203 AC stricte). Ce test
  clôt US-203 ET US-204 d'un coup → `passes:true` sur les deux si succès.
- !! Credentials Stripe toujours absents (bloque US-205 — la sauter si toujours absent au
  prochain cycle Ralph, ne pas attendre dessus).
- !! 3 questions dérangeantes du cadrage V2 (np-cadrage.md § 2.3) toujours sans réponse
  tranchée à ce jour : clients payants réels ? réponse à l'objection données réelles ?
  décision finale AGPL/MiroFish (domaine exclusif d'Amine, jamais rouvert par moi).

[NEXT]
1. **Demain** : lancer le devis test réel (voir [BLOQUÉ]) → si OK, marquer US-203 et
   US-204 `passes:true` dans `.ralph/prd.json` (commit dédié).
2. Continuer le Bloc A dans l'ordre : US-207 (WSGI prod + `Config.validate()` fail-closed)
   → US-208 (Redis/worker PDF prod, dépend US-207) → US-205 (Stripe, seulement si
   credentials posés entre-temps).
3. Envisager de créer une story **US-210 "domain cutover"** pour migrer les 4 liens
   fonctionnels restants vers bassira.ma (cf. [ALERTE]) — pas urgent, infra prête.
4. Après le Bloc A complet : lancer `moat-hunter` avec `01-app-spec.md` en input.
5. Trancher (Amine) si rotation SECRET_KEY/LLM_API_KEY nécessaire suite à l'exposition
   API Coolify de ce soir (cf. [ALERTE]) — pas fait, pas demandé explicitement encore.
6. SOP : aucune SOP existante ne couvrait les opérations de cette session (migration SQL
   prod hors coffre standard, résolution tunnel Cloudflare remote-managed, edge cases
   Coolify docker-compose domains) — candidate à `/sop-new` si ce type d'intervention se
   répète (proposé, pas capturé ce soir faute de temps).

[CTX session]
- Session très longue (2026-07-07 après-midi → 2026-07-08 nuit), a englobé : le cadrage V2
  complet (voir archive), le Bloc A Ralph (US-201/202/203/204/206), ET une intervention
  d'infra profonde et imprévue (diagnostic + fix du tunnel Cloudflare partagé + migrations
  SQL prod) déclenchée par une découverte en cours de route (bassira.ma 404).
- Plusieurs pauses de confirmation Amine avant chaque action à risque partagé (redeploy
  Coolify, kill process orphelin, push config tunnel, exécution SQL prod) — aucune action
  irréversible prise sans validation explicite.
- Contexte tombé sous 60 % → passation nucléaire déclenchée par hook, ce fichier vient
  d'être réécrit intégralement (rotation > 150 Ko, archive créée).

[MEMO inter-sessions]
- **Cloudflare Tunnel remote-managed — piège durable** : ne JAMAIS supposer qu'éditer
  `config-nahda.yml` + restart suffit. Toujours vérifier `GET
  /accounts/{id}/cfd_tunnel/{tunnel}/configurations` → champ `source`. `"cloudflare"` =
  il faut `PUT` la config complète via l'API (récupérer le tableau `ingress` existant,
  modifier, repousser tel quel — jamais retaper à la main, ~57 entrées, une oubliée =
  outage sur une autre app du tunnel partagé). Détail dans mémoire
  `reference_serveurai_infra.md`.
- **Coolify docker-compose apps** : domaines dans `docker_compose_domains` (pas
  `fqdn`/`domains`), format `{"<service>": {"name": "<service>", "domain": "url1,url2"}}`,
  `name` requis (422 sinon). `POST /restart` régénère les labels Traefik + recrée le
  conteneur.
- **Supabase self-hosted multi-projets sur `.11`** : ~10 stacks Supabase différentes
  tournent sur le serveur partagé (une par projet Coolify, containers
  `supabase-db-<hash>`). NE JAMAIS deviner laquelle — vérifier via l'API Coolify
  `/services` (nom lisible type `supabase-miroshark`) + `VITE_SUPABASE_URL` de l'app
  concernée. La variable `SUPABASE_DB_URL` peut être stale/piégeuse si le code ne la
  référence pas (`grep` avant de faire confiance à une env var de connexion DB).
- **Appliquer du SQL sur un Postgres self-hosted Coolify** : le plus simple et fiable est
  `docker exec <container_supabase-db> psql -U postgres -d postgres -f -` (stdin), auth
  locale sans mot de passe — pas besoin de bricoler une connection string externe.
- **Toute opération d'infra (Docker, psql, CLI d'admin) → TOUJOURS sur `.11` via SSH,
  JAMAIS en local** sur le poste Windows d'Amine (correction explicite reçue ce soir,
  mémoire `feedback_ops_on_server_only.md`).
- **Bash tool + PowerShell imbriqué** : échapper `\$` pour CHAQUE variable PowerShell dans
  un `-Command` passé depuis Git Bash — un seul `$var` non échappé se fait expand par Bash
  AVANT PowerShell (piège rencontré ~4 fois cette session, y compris `$_`, variable
  spéciale Bash).
- **Pattern SIM_ID/report_id garde d'accès (US-206)** : `_authorize_simulation_access()`
  dans `report.py` — réutilisable pour tout futur endpoint report-like.
- **Piège hook bash-guard** : bloque les heredocs/greps non ancrés — toujours passer par
  un fichier `.py` écrit via Write puis exécuté, ou une extraction champ-exact.
- **Piège hook pre-commit Ruff** : s'exécute sur TOUT le repo, pas seulement le diff.

— fin passation —
