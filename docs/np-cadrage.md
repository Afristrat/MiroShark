# NP Cadrage — Bassira V2 (base MiroShark)

> Journal d'état du flow `np`. Session du 2026-07-07, mode **autonome** (demande explicite
> d'Amine : « fonctionne en mode autonome ») : les réponses de Phase 1 sont dérivées des
> **preuves système** (code, `.ralph/prd.json`, passations, prod) et non d'un dialogue.
> Tout champ non prouvable est marqué `[HYPOTHÈSE À VALIDER]`. Les points ⏸️ normalement
> bloquants (contre-argument 2.4, verdict 2V) sont soumis à ratification d'Amine en fin
> de livraison au lieu de bloquer le flow.

## Phase 0 — Détection du terrain (2026-07-07)

- `REPO_STATE=EXISTING`, 400+ fichiers scannés, git OK, branche `main` propre (`0f52f25`).
- **Stade : code en production** — https://prospectives.ai-mpower.com (Coolify, auto-deploy
  sur push `main`). Signalé 404 ce jour — diagnostic/fix délégué à un sous-agent en parallèle.
- `.ralph/prd.json` : **134 stories, 133 passes=true**. Seule restante :
  **US-113 — Stripe Checkout API native** → la monétisation self-serve n'existe pas encore.
- `HAS_CLAUDE_MD=false` (un `AGENTS.md` existe), `HAS_TESTS=false` à la racine (les tests
  vivent dans `backend/tests/` et `frontend/tests/e2e/`), CI présente.
- Alerte script : 13 fichiers `backend/tests/test_*.py` avec secrets potentiels —
  qualification (vrais secrets vs fixtures) en cours par l'explorateur infra.
- Audit express complémentaire : 4 agents Explore (backend, frontend, data/infra, produit/docs)
  + 1 agent recherche marché — résultats consolidés en § Deep explore.

## Phase 1 — Réponses (dérivées des preuves, stade « code en prod »)

### Round 1 — Problème et personne
- **Problème** : décider (lancement, com de crise, politique publique) sans pouvoir tester
  la réaction du public coûte cher ; les études de marché classiques prennent des semaines
  et des milliers d'euros. Bassira simule la réaction de centaines de personas LLM en
  ~10 minutes pour ~1-3,50 $ de coût LLM (README.md:34).
- **Persona cible** : CONFIRMÉ (bassira_brand_prompts.md:11-19) — **B2B C-Level MENA +
  institutions internationales** (gouvernements, fonds, think tanks), matrice d'audience
  3 tiers (économique/champion/sceptique). Pricing en vigueur : **12k/35k/20k MAD** et
  $1.2k/$3.5k/$2k USD, jamais EUR (PASSATION.md:1386).
- **Comment ils font aujourd'hui** : études qualitatives/quantitatives classiques, panels,
  ou instinct. `[À sourcer au stress-test]`
- **En une phrase** : « Simulez la réaction du monde à votre décision avant de la prendre —
  des centaines d'agents IA qui débattent, tradent et changent d'avis, rapport C-Level en 10 min. »
- **Modèle de revenu** : vente B2B sur devis (module quotes/devis complet en prod, PDF L99
  COMEX-ready) ; checkout Stripe self-serve **jamais terminé** (US-113). `[Revenu réel actuel :
  HYPOTHÈSE — probablement 0 self-serve ; clients devis à confirmer]`.
- **Pourquoi Amine** : infra souveraine existante (Coolify, SearXNG, Crawl4AI, Saqr),
  position AI-MPower/écosystème institutionnel Maroc (cf. skill linkedin-amine), maîtrise
  du fork complet (134 stories exécutées).

### Round 2 — Périmètre v1 constaté (ce qui EXISTE, preuve prd.json + passations)
- Cœur : scénario → monde simulé (Twitter/Reddit fictifs + marché de prédiction) → timeline
  heure par heure → rapport. Counterfactual branching, Director Mode, galerie publique,
  prédictions vérifiées, share cards, embed.
- Couche Bassira propre (au-dessus d'upstream) : auth Supabase multi-org + RLS, rôles
  super-admin/org, devis (quotes), branding PDF par org, pipeline PDF L99 (4 variantes,
  queue Redis, delivery URL signée + Resend), analytics admin, i18n FR, calibration/offres.
- **Parcours critique** : login → nouvelle simulation (doc ou question) → config auto →
  run → timeline/chat → rapport PDF → (devis/partage).

### Round 3 — Marque
- **Bassira (بصيرة** = clairvoyance) — rebrand frontend uniquement (2026-04-29), backend
  reste `miroshark`. Design tokens `--wi-*`/`design-tokens.css`, design system Stitch exporté
  dans le repo. Langues : FR ; arabe `[HYPOTHÈSE À VALIDER : RTL non implémenté]`.
- Ressenti/palette/ton : à consolider depuis `bassira_brand_prompts.md` + Stitch (explorateur produit).

### Round 4 — Technique
- **Stack constatée** : Vue 3 + Vite + Pinia / Flask (Python) / Supabase / Neo4j / Redis /
  Coolify — ÉCART avec la stack par défaut du poste (Next.js) → ADR-001 (héritage upstream,
  coût de réécriture prohibitif, assumé).
- **LLM** : BYOK affiché, MAIS prod configurée sur un provider serveur unique
  (`LLM_BASE_URL=https://api.moonshot.ai/v1`, `kimi-k2-turbo-preview` — .ralph/progress.md:48).
  Contrainte mémoire : ne jamais imposer un modèle → point de tension v2 à trancher en ADR.
- **Services externes** : Supabase, Neo4j, Redis, Resend (email), Saqr (signaux, contrat
  V2 du 2026-05-15), FeedOracle MCP, OpenRouter/Moonshot. Stripe = jamais fini.
- **Données sensibles** : comptes utilisateurs (PII), données clients B2B, contenus de
  simulations potentiellement confidentiels. Marchés : Maroc (loi 09-08/CNDP) + UE (RGPD)
  → volet légal L6 complet requis.

### Red flags consignés
1. **Monétisation inachevée** (US-113) — un SaaS en prod sans moyen d'encaisser en ligne ;
   bridge manuel Payment Link (PASSATION.md:275, 3272). SMTP jamais configuré en prod →
   les devis n'envoient AUCUN email (PASSATION.md:1399, 1459-1467) : leads invisibles.
2. **Prod 404 ce jour** — fragilité opérationnelle ; pas de monitoring externe évident.
3. **Contradiction BYOK affiché vs provider unique serveur** en prod (Moonshot kimi-k2).
4. **Rebrand partiel** (logo PNG resté MiroShark, identifiants techniques mixtes).
5. **Validité scientifique des personas LLM** = risque existentiel du créneau (sourcé § Phase 2).
6. **Dossier licence** (LICENSE:1-12 = texte AGPL-3.0, fork Afristrat/MiroShark ←
   aaronjmars/miroshark, AGENTS.md:9-11). CORRECTION AMINE 2026-07-07 : dossier instruit
   par LUI exclusivement — position : MiroShark est basé sur une licence MiroFish dont
   aaronjmars s'est octroyé un droit qu'il n'avait pas. L'IA collecte les faits (lignée
   en cours de vérification) et n'émet ni qualification ni prescription (ADR-003).
7. **Sécurité non soldée** : IDOR `/api/report/<id>` sans auth (SECURITY_AUDIT_2026-05.md:52-71,
   P0 jamais fermé) ; 8 CVE npm HIGH non patchées (axios ^1.13.2, frontend/package.json:24) ;
   3 fuites de secrets en session dont rotation non prouvée (PASSATION.md:875-889, 1096, 1175).
8. **Claim « Brier 0,18 vérifié » sur la Home** alors qu'aucun outcome public n'existe
   (PASSATION.md:1274, 1279-1283) — claim invérifiable face à un prospect C-Level, et
   contraire à la RÈGLE N°2 du poste (tolérance zéro données erronées).

## Deep explore — synthèse des rapports d'exploration (2026-07-07)

### Produit (rapport explore-produit)
- Couche Bassira au-dessus d'upstream : i18n FR/AR-RTL/EN, multi-tenant Supabase RLS,
  commercial (/offres, /devis, admin quotes), pipeline PDF L99 (15 chantiers), analytics,
  branding par org, Saqr en API externe. Rien de tout cela documenté dans docs/ — vit
  uniquement dans PASSATION.md et .ralph/prd.json.
- GTM : palette « Causse » #FF8551/#006D44/#FAF7F2/#241915, typo Outfit/Manrope/Tajawal
  (bassira_brand_prompts.md:14-36) ; 27 emails Apollo FR/EN/AR ; 15 posts LinkedIn.
- **AGPL-3.0 + fork = risque juridique n°1** (détail red flag 6).
- Angles morts : Stripe US-113, claim Brier invérifiable, IDOR reports, 8 CVE npm,
  SMTP absent, citations PDF bilingues non corrigées, secrets leakés à rotation non prouvée.

### Backend (rapport explore-backend)
- **Prod sur serveur de DEV Werkzeug** (backend/run.py:45, `app.run(threaded=True)`) —
  pas de gunicorn/waitress. Facteur limitant n°1 avec : IPC subprocess par polling
  filesystem (simulation_ipc.py), cache in-memory SimulationManager, numReplicas:1 →
  architecture verrouillée mono-nœud.
- **Artefacts de simulation filesystem-only** (uploads/ en bind mount, docker-compose.yml:67-68)
  — profils, trajectoires, state.json perdus si le volume Coolify n'est pas réellement
  persistant. Le précédent analytics (admin.py:24-27) a déjà payé ce bug.
- **Worker PDF async mort en pratique** : fallback sync si REDIS_URL absent
  (pdf_generation_worker.py:21-23) et aucun Redis déclaré dans compose/.env.example →
  WeasyPrint + LLM dans le thread HTTP.
- **NEO4J_PASSWORD défaut hardcodé `miroshark`** (config.py:76, compose:5,55).
- Qualité solide par ailleurs : auth JWT double-mode fail-closed, SSRF protégé sur
  webhooks, tests IDOR admin, BYOK OpenRouter-compatible confirmé dans le code
  (llm_client.py — la prod pointe Moonshot via LLM_BASE_URL, le client reste générique).
- **Fixtures de tests = fausses valeurs** (vérifié test_unit_hardening.py:39-60) —
  l'alerte « 13 fichiers suspects » de Phase 0 est LEVÉE.
- God-files : simulation.py 8875 lignes/~50 routes, report_agent.py 3915,
  simulation_runner.py 2151. Zéro TODO/FIXME — dette structurelle, pas d'oublis.
- Coûts : boucle Wonderwall = 850+ appels LLM/run (config.py:173) ; aucun garde-fou dur
  agents×rounds ; full scan simulation_ownership assumé < 10k rows (admin.py:76-99).

### Data / Infra / Qualité (rapport explore-infra)
- **12 tables Supabase, TOUTES RLS-activées** (migrations 20260503→20260506) — règle
  absolue respectée. Audit log immuable (UPDATE/DELETE bloqués). Bon socle.
- **Incohérence** : `public.is_super_admin()` lit une table `super_admin_emails` qui
  n'existe dans AUCUNE migration → toujours `false` ; la vraie whitelist est l'env var
  `BASSIRA_SUPER_ADMIN_EMAILS` côté Flask (decorators.py:278-297). Code mort trompeur,
  piège pour tout futur accès client direct Supabase.
- **[P0 perte de données]** : payload riche des devis (nom, email, message prospect — PII),
  snapshots de rapports et artefacts de simulation vivent sur `backend/uploads/` dont
  l'équipe documente elle-même le caractère ÉPHÉMÈRE sur Coolify (PASSATION.md:36).
  Aucune des 3 configs de deploy ne déclare de volume persistant. Combiné au SMTP absent :
  un devis peut ne jamais notifier ET être effacé au redeploy suivant.
- Policies `FOR ALL TO authenticated` sur report_deliveries/report_downloads : un
  org-admin pourrait forger des lignes de tracking en direct (gap théorique).
- **Outillage qualité inexistant** : aucun ruff/mypy/black backend, aucun eslint/tsconfig
  frontend, aucun script lint/typecheck dans package.json — la règle « zéro dette » n'a
  aucun outil pour être appliquée. CI : pytest backend seul ; le frontend n'est JAMAIS
  buildé/linté/testé en CI ; 4 specs Playwright manuelles.
- Tests : 81 fichiers backend, mais **zéro couverture** sur backend/app/storage/ (cœur
  RAG/Neo4j : entity_resolver, reranker, contradiction_detector…) ni simulation_ipc.
- Configs mortes : railway.json et render.yaml (0 occurrence passations) ; backlog.yaml
  figé à US-034 alors que .ralph/prd.json va à US-145 → à archiver.
- .env.example ne documente pas SUPABASE_URL/SERVICE_ROLE_KEY pourtant critiques en prod.

### Frontend (rapport explore-frontend)
- 27 routes lazy-load, guard 3 niveaux zero-trust (router/index.js:268-309), un seul
  store Pinia métier (stores/auth.js, 314 l.). i18n fr/en/ar à **parité exacte 2013 clés**,
  RTL propre (Tajawal). DOMPurify systématique sur v-html — pas de XSS identifié.
  Zéro TODO/console.log résiduel. 20 specs Playwright e2e.
- **[Image] Watermark d'export = logo requin MiroShark** (utils/chartExport.js:10 →
  public/miroshark-nobg.png) incrusté sur TOUT export PNG (Polymarket, belief drift,
  réseau) — le seul artefact du rebrand qui SORT de l'app vers des tiers.
- Références MiroShark visibles : SettingsPanel.vue:84,399,411,452 (GitHub aaronjmars,
  « miroshark.app », texte MCP) ; ExploreView.vue:11 (vitrine publique).
- **currentOrgId jamais persisté** (stores/auth.js:28) → tout multi-org retombe sur
  orgs[0] au refresh ; sélecteur d'org uniquement sur le dashboard, absent d'AppHeader.
- **Deux design systems mélangés dans 50 fichiers** (--ms-* « Playful & Soft » legacy vs
  --wi-* « Warm Intelligence »/Causse) ; le commentaire de design-tokens.css:291-296 ment
  sur le périmètre réel. Vitrine commerciale au design Causse, cœur produit (Step1-5,
  console, admin) resté visuellement MiroShark → expérience non unifiée vitrine/produit.
- Monolithes : Step4Report.vue 5405 l., Step3Simulation 3200, Step2EnvSetup 3033,
  HistoryDatabase 3001, Step5Interaction 2876 (pattern jumeau de Step4) — 16 fichiers
  > 1000 lignes.
- i18n locale trouée sur EmbedDialog.vue (:137,141,203,209 — anglais hardcodé dans LA
  modale de partage externe).

## Phase 2 — Stress-test (recherche marché reçue 2026-07-07, agents code en cours)

### Recherche préalable — faits clés (rapport research-marche)
- **Concurrents** : Simile (Stanford/Percy Liang, 100 M$ Series A fév. 2026, Index Ventures —
  jumeaux numériques ANCRÉS sur entretiens réels, philosophie opposée au synthétique pur) ;
  Aaru (Series A > 50 M$ déc. 2025, valorisation ~1 Md$ headline, ARR < 10 M$, clients
  Accenture/EY) ; Artificial Societies (YC W25, ~5 M$, PLG 40 $/mois, « 80 % de précision »
  non audité) ; Synthetic Users (bootstrap, 2-27 $/interview, se positionne lui-même en
  complément du réel) ; Ditto (50-75k$/an) ; Fairgen ; Evidenza.
- **Pivot-signal** : Roundtable a PIVOTÉ des personas synthétiques vers « Proof of Human »
  (détection de répondants IA) — désaveu de marché de la thèse « synthétique générique ».
- **Validité scientifique — talon d'Achille** : Bisbee et al., *Political Analysis* 2024 :
  48 % des coefficients issus de réponses LLM statistiquement différents des données humaines ;
  effondrement de variance ; instabilité inter-versions de modèle. Contre-point : Park et al.
  2024 (équipe Simile) — 85 % de fidélité MAIS uniquement avec ancrage sur 2 h d'entretien
  réel par persona. Consensus industrie (ESOMAR/Kantar/Bain) : « explorer synthétiquement,
  valider humainement — jamais remplacer ».
- **Marché** : synthetic data IA ~2-2,75 Md$ 2025-2026, CAGR 30-40 % (rapports vendeurs,
  scepticisme de rigueur) ; « 100 Md$ market research » = argumentaire concurrent non vérifié.
- **Réglementation** : EU AI Act Art. 50 (transparence contenu synthétique, applicable
  **2 août 2026** — dans 3 semaines ; amende jusqu'à 15 M€/3 % CA) ; Maroc loi 09-08 en
  vigueur mais pré-RGPD, cadre mouvant, modernisation non votée.
- **Aucun concurrent identifié** ne combine marché de prédiction + réseaux sociaux simulés +
  timeline heure par heure ; aucun BYOK souverain ; aucun positionné Maroc/Afrique.

### 2.4 — Contre-argument principal (à ratifier par Amine — ⏸️ transformé en ratification)
> Le risque existentiel de Bassira est la **validité scientifique des personas génériques
> non ancrées**. Le concurrent le mieux financé du créneau (Simile, 100 M$) est construit
> sur le principe INVERSE — ancrage sur données d'entretien réelles — précisément parce que
> la littérature (Bisbee 2024) démontre que les personas génériques produisent ~48 % de
> coefficients statistiquement faux et une variance effondrée. Roundtable a pivoté hors du
> synthétique pur. Un client C-Level sophistiqué demandera : « sur quelles données réelles
> ancrez-vous ces personas ? » — la réponse actuelle est : aucune. Vendre un rapport COMEX
> sur cette base est un risque de crédibilité et de responsabilité.

### 2.1 — Reformulation
Bassira = SaaS B2B (base open-source AGPL MiroShark) qui simule la réaction publique à une
décision — des centaines de personas LLM débattent heure par heure sur des réseaux sociaux
simulés et tradent sur un marché de prédiction — et livre un rapport C-Level PDF brandé.
Vendu sur devis (12k-35k MAD) aux dirigeants et institutions MENA. La V2 vise à transformer
un moteur démontré (133 US exécutées) en produit commercialisable, crédible et opérable.

### 2.2 — Angles morts (sourcés)
1. **AGPL-3.0 vs SaaS propriétaire** — jamais mentionné dans aucune passation ; risque
   juridique et de due diligence (LICENSE:1-12).
2. **Validité scientifique du positionnement « prédiction »** — Bisbee 2024 (48 % de
   coefficients faux) ; Simile (100 M$) construit sur la thèse INVERSE (ancrage réel).
3. **EU AI Act Art. 50 applicable le 2026-08-02 — dans moins d'un mois** — obligation de
   marquage machine-readable du contenu synthétique (artificialintelligenceact.eu/article/50).
4. **Perte de leads silencieuse** : devis PII sur volume éphémère + SMTP absent — un
   prospect peut écrire sans que personne ne le sache, puis être effacé au redeploy.
5. **Chaque graphique exporté porte le logo requin MiroShark** chez les tiers
   (chartExport.js:10) — sabotage passif du rebrand à chaque partage.
6. **Claim « Brier 0,18 vérifié » sans outcome public** — viole la règle DÉFCON 1 du poste
   et expose face à tout prospect qui vérifie /calibration.

### 2.3 — Questions dérangeantes (à répondre par Amine)
1. **Combien de clients PAYANTS réels à ce jour ?** Si zéro : qu'est-ce qui prouve que la
   douleur vaut 12-35k MAD, à part le pipeline Apollo non converti ?
2. Quand un DG sophistiqué demande « **sur quelles données réelles ancrez-vous ces
   personas ?** », quelle est ta réponse aujourd'hui — et tient-elle 30 secondes face à un
   cabinet qui connaît Bisbee 2024 ?
3. Es-tu prêt à **publier le code de la couche Bassira** (obligation AGPL en l'état) ou à
   négocier une licence commerciale avec aaronjmars — et sinon, que fais-tu le jour où un
   client fait une due diligence de licence ?

### Réponse structurelle proposée (2.6 — version renforcée, brouillon)
La v2 ne vend plus « la prédiction » mais **« le stress-test de décision »** : (a) encart de
limites de validité en première page de chaque rapport (obligation EU AI Act au 2026-08-02
de toute façon), (b) mécanisme d'ancrage optionnel sur données réelles (calibration Saqr
signaux réels + import sondage court), (c) le marché de prédiction interne présenté comme
mesure de POLARISATION du débat simulé, pas comme prévision du réel. Le différenciateur
défendable reste la combinaison timeline+marché+fork contrefactuel + BYOK souverain + ancrage
Maroc/Afrique.

### 2.5 — Compromis cachés
| Choix | Gain réel | Coût caché payé plus tard |
|---|---|---|
| Fork MiroShark (AGPL) | 134 US livrées en semaines, moteur complet gratuit | Licence AGPL contaminante + dette architecturale héritée (Werkzeug, god-files, filesystem) |
| Vente sur devis B2B | Marge élevée, adaptation institutionnelle | Zéro PLG, cycle long, dépendance totale au fondateur pour vendre |
| BYOK / souveraineté LLM | Différenciateur unique du créneau (sourcé) | Reproductibilité des rapports non maîtrisée (instabilité inter-modèles = Bisbee), support multi-providers coûteux |
| Positionnement « prédiction » | Punchy commercialement (« called it ») | Indéfendable scientifiquement, responsabilité si décision réelle s'appuie dessus |
| Stack héritée Flask/Vue (vs Next.js du poste) | Zéro réécriture | Double compétence à entretenir, aucun typage frontend, outillage qualité à construire de zéro |

### 2.7 — Le plus petit test (avant d'investir la v2 lourde)
**1 semaine, ~0 € :** (a) présenter à 3 prospects du pipeline Apollo le MÊME rapport PDF
sous deux framings — « prédiction de la réaction » vs « stress-test de votre décision » —
et compter les objections de crédibilité ; (b) contacter aaronjmars pour sonder une licence
commerciale (email unique, coût nul). **Critère de réfutation** : si les 3 prospects jugent
le produit « gadget » même reframé, le créneau institutionnel MENA direct n'est pas mûr →
pivot canal (marque blanche via cabinets de conseil).

## Verdict (2V) — RATIFIÉ

**GO conditionnel** (pivot de POSITIONNEMENT intégré, pas de pivot produit).

> **RATIFICATION AMINE — 2026-07-07** : « 2. et 3. go » — verdict ratifié, **Bloc A
> lancé**, cap stack unique engagé (ADR-010 acceptée), **US-220 = merge sélectif**
> upstream (ADR-014), ADR-012 validée (OpenSERP local + Serper.dev fallback) avec ordre
> de **déprovisionner SearXNG partout**, codebase par codebase (SOP-002 en création).

**Ce qui tient (sourcé)** : différenciation produit réelle — aucun concurrent identifié ne
combine marché de prédiction + réseaux simulés + timeline + fork contrefactuel ; BYOK
souverain unique ; positionnement Maroc/Afrique vierge ; marché en croissance (CAGR 30-40 %) ;
actif considérable (moteur + 133 US + GTM prêt).

**Les conditions avant l'investissement v2 en features (révisées 2026-07-07 après
directives d'Amine) :**
1. **Dossier licence** : instruit par Amine exclusivement (ADR-003) — l'IA lui remet les
   faits collectés (lignée MiroFish/MiroShark, textes LICENSE). Plus une condition émise
   par l'IA : c'est sa décision, prise en conscience.
2. **Abandonner le claim prédictif non étayé** (« Brier 0,18 vérifié », « prédisez la
   réaction ») au profit du positionnement « stress-test de décision » + transparence
   AI Act Art. 50 intégrée au rapport.
3. **Solder les P0 opérationnels** : perte de données uploads/, IDOR /api/report, WSGI de
   prod, Resend (AI-MPower/bassira.ma), Stripe Checkout + pricing.

**Niveau** : L6 (prod publique existante, PII réelles). La règle « GO conditionnel → L1 »
vise les projets neufs ; ici la prod existe et Amine a explicitement commandé les 10
documents — générés ci-après, les conditions étant tracées en ADR bloquantes.

**Phase en cours** : 3 (documents de fondation) · Niveau : L6 · Ouvert : 2026-07-07

## Directives d'Amine — 2026-07-07 (post-livraison, intégrées à tous les documents)

1. **Renommage** : Kairos (ex-Zlatan/Isis) s'appelle **Saqr** — corrigé partout.
   Sens des flux précisé : **Saqr et Nahda CONSOMMENT les sorties de Bassira** (US-218).
2. **SearXNG n'est pas fiable** (agrégateur bloqué par ses moteurs, faute d'APIs) —
   alternative **headless** à valider MAINTENANT, pendant le cadrage (ADR-012, agent
   research-search-alt en cours).
3. **Marché de prédiction = mécanisme occidental**, inadapté à la zone Africa/Middle
   East — arènes alternatives sélectionnables par simulation (ADR-011, US-216, agent
   research-prediction-mena en cours).
4. **Polyglotte intégral** : clés i18n ar/en/fr + autres langues, frontend + backend +
   livrables, sans exception (ADR-008 révisée, US-217).
5. **Réécriture mono-stack** : Amine n'y est pas opposé — option ouverte (ADR-010,
   remplace ADR-001).
6. **LLM** : gateway **LiteLLM**, défaut type **DeepSeek v4 Flash** + fallback
   (ADR-004 révisée).
7. **Resend** : expéditeur = adresse AI-MPower ; liens de renvoi = **bassira.ma
   toujours** (ADR-013 — le défaut SQL footer 'bassira.ai' est un bug de marque).
8. **Stripe** : créer le pricing (products/prices) — intégré à US-205.
9. **Dossier licence** : domaine EXCLUSIF d'Amine — position : MiroShark est basé sur
   une licence MiroFish dont aaronjmars s'est octroyé un droit qu'il n'avait pas. L'IA
   s'en tient aux faits, n'émet ni verdict ni prescription, et ne rouvre pas le sujet
   (ADR-003 reformulée ; sujet clos côté IA).
10. **Avant de coder** : s'assurer d'avoir la dernière version de MiroShark (agent
    upstream-mirofish en cours : fetch upstream + écart mesuré).
11. **MiroFish** : à faire cohabiter comme second canal de prospective — **Bassira = B2B**,
    **canal MiroFish = grandes missions / B2G**, au service de **Nahda** (faits en cours
    de collecte).
12. Optimisation du reste en totale autonomie — sans leçons, en particulier sur les
    questions de droit et de juridiction.

## Retours d'enquête — 2026-07-07 soir (3 agents, tous intégrés aux ADR)

- **ADR-012 tranché** : SearXNG bloqué structurellement (fingerprinting TLS/HTTP2 —
  github.com/searxng/searxng/issues/2515) → **OpenSERP** self-hosted retenu (headless
  Chromium, API JSON, MIT, Docker) + repli Serper.dev sur erreur uniquement (US-219).
- **ADR-004 confirmé** : LiteLLM supporte le préfixe `deepseek/` et le fallback natif
  (`litellm_settings.fallbacks`) ; vigilance bug #26395 (reasoning_content multi-tours).
- **ADR-011 outillé** : 5 arènes candidates sourcées (Diwaniya/Majlis, Relais WhatsApp —
  88-89 % des mobinautes LMIC en messagerie quotidienne, Chaire du vendredi/Radio —
  effet khutba→Twitter quantifié, Souk/diaspora, Delphi) ; architecture : arènes
  COMBINABLES + profils régionaux pondérés par données réelles + Delphi comme couche de
  normalisation (indicateur continu + polarisation). Le pattern pluggable existe déjà
  (`wonderwall/simulations/base.py`). Note d'honnêteté : la prémisse « marché de
  prédiction = biais occidental » n'est ni contredite ni corroborée par la littérature
  identifiée — prémisse produit assumée.
- **Upstream** : main = **181 commits de retard** sur aaronjmars/MiroShark (i18n FR
  upstream ~87 % en recouvrement probable, bumps sécurité Dependabot, fix persistance
  compose) vs 244 commits Bassira propres → arbitrage merge/cherry-pick/gel = US-220.
- **MiroFish (faits remis à Amine, ADR-003)** : 666ghj/MiroFish, v0.1.2 (2026-03-07),
  68,1k étoiles, GraphRAG + OASIS (camel-ai) + Zep Cloud (tiers payant — fork
  MiroFish-Offline = Neo4j+Ollama 100 % local), stack Python+Vue, LICENSE AGPL-3.0.
  Aucun lien technique MiroFish↔MiroShark trouvé dans les README/réseau de forks à ce
  stade ; chronologie relative des dépôts non établie. Cohabitation (Bassira=B2B, canal
  MiroFish=B2G pour Nahda) : effort d'hébergement modéré, point souveraineté = Zep Cloud.

## Sources (URLs lues — rapport research-marche, repli WebSearch/WebFetch documenté,
## SearXNG rate-limité après 2 requêtes)
- https://techcrunch.com/2025/12/05/ai-synthetic-research-startup-aaru-raised-a-series-a-at-a-1b-headline-valuation/ → Aaru Series A, ARR < 10 M$
- https://evoailabs.medium.com/the-ultimate-simulation-why-index-ventures-is-leading-similes-100m-series-a-7a41238cde31 → Simile 100 M$, thèse ancrage réel
- https://siliconcanals.com/yc-backed-artificial-societies-bags-e4-5m/ → Artificial Societies levée
- https://techedgeai.com/news/artificial-societies-launches-ai-powered-simulator-to-predict-market-reactions-with-80-accuracy/ → claim 80 % non audité
- https://www.syntheticusers.com/pricing → pricing + auto-positionnement « complément »
- https://theairankings.com/best-ai-synthetic-research/ → cartographie comparative, consensus ESOMAR
- https://www.cambridge.org/core/journals/political-analysis/article/synthetic-replacements-for-human-survey-data-the-perils-of-large-language-models/B92267DC26195C7F36E63EA04A47D2FE → Bisbee 2024, 48 % coefficients faux
- https://techstartups.com/2025/12/09/top-ai-startups-that-shut-down-in-2025-what-founders-can-learn/ → mortalité startups IA 2025-2026
- https://www.researchandmarkets.com/reports/6226369/ai-in-synthetic-data-market-report → taille marché
- https://www.fortunebusinessinsights.com/synthetic-data-generation-market-108433 → taille marché (large)
- https://artificialintelligenceact.eu/article/50/ → EU AI Act Art. 50, applicable 2026-08-02
- https://avocat-jawhari.com/2026/03/25/intelligence-artificielle-maroc-donnees-personnelles-risques-cndp/ → loi 09-08 vs IA
- https://www.village-justice.com/articles/cadre-leadership-africain-cndp-comme-architecte-modele-marocain-gouvernance-des,55421.html → CNDP contexte
