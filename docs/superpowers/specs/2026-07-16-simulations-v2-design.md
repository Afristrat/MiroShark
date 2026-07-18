# Spec — Chantier Simulations V2 : dénouement économique, personas ESCO, prompts L99, arènes combinables

> **Date** : 2026-07-16 · **Commandé par** : Amine (directives des 2026-07-15/16)
> **Statut** : validé sur les arbitrages structurants — voir ADR-015 → ADR-019
> **Stories** : US-221 → US-237 (`.ralph/prd.json`, chantier `16-simulations-v2`)

## 1. Mandat et arbitrages d'Amine (actés)

1. **Dénouement simulé avec un vrai sens économique** — les marchés simulés doivent se
   résoudre et payer les positions (aujourd'hui `resolve_market()` n'a aucun appelant).
2. **Personas fondées sur le standard ESCO** — grounding métier vérifié (API publique
   Commission européenne, FR/EN/AR prouvés opérationnels le 2026-07-15), enrichissement
   des rôles hors-taxonomie par **le modèle 122B** (choix de modèle = Amine, via gateway
   LiteLLM) écrivant directement dans Supabase.
3. **Élévation L99 de tous les prompts de simulation** (skill `prompt-engineer-pro`) +
   **page console super-admin** listant ces prompts — **éditables en base** (décision
   Amine : « en base c'est mieux »), avec versionnage et garde-fous.
4. **Garder le calque marché + règle déterministe de routage + confrontation d'approches**
   (« l'un ne peut pas aller sans l'autre ») — pas de remplacement 1:1, conforme ADR-011.
5. **Renommage client-facing** : « marché de prédiction » → **« arène de convictions »**
   (FR), « conviction arena » (EN), « ساحة القناعات » (AR) — option « renommage complet »
   choisie le 2026-07-16, nom révisé le 2026-07-16 après verdict Council (ADR-018 amendé,
   cf. §7.4). Le halo lexical (oracle/verdict/confiance/dénouement/Delphi) reste à
   trancher — deux variantes commutables au prototype v2.

## 2. État des lieux vérifié (deep-explore du 2026-07-15, faits sourcés)

### 2.1 Le marché simulé est économiquement décoratif
- `resolve_market()` défini (`wonderwall/simulations/polymarket/platform.py:378-429`)
  mais **jamais appelé** (grep exhaustif backend) → aucun marché n'est résolu, aucune
  position payée.
- P&L observé par les agents **faux par construction** : `cost_basis = shares * 0.50`
  codé en dur (`polymarket/environment.py:40`).
- Les prix AMM n'atteignent jamais le PDF : `polymarket_curves` trace les stances de
  trajectoire, pas les prix (`report_pdf/charts.py:251-262`) ; les prix ne vivent que
  dans l'overlay frontend (`PolymarketChart.vue`, API `simulation.py:5151`).
- AMM constant-product binaire strict YES/NO (`polymarket/amm.py:14-25`).

### 2.2 Prompts de simulation loin du niveau production
- Personas nus (nom + bio libre) sans grounding métier
  (`polymarket/prompts.py:28-36`, `social_media/prompts.py:23-38`).
- Anglais uniquement, codé en dur, dans les 3 arènes (tension avec US-217 polyglotte).
- Incohérence factuelle : « There is one prediction market »
  (`polymarket/prompts.py:80`) alors que `polymarket_market_count` permet N marchés.
- Psychologie soufflée : sections « TRADING PSYCHOLOGY » identiques pour tous
  (`polymarket/prompts.py:84-92`) ; heuristiques injectées dans l'observation
  (« consider taking profit », `polymarket/environment.py:49-56,103-107`).
- Contamination du contrat de base : `do_nothing()` générique parle de « market
  state », « conserve capital », « Good traders » pour TOUTES les arènes
  (`simulations/base.py:299-310`).
- Courbe d'activité horaire calée sur Pékin : `CHINA_TIMEZONE_CONFIG`
  (`simulation_config_generator.py:30`).
- Prompts éparpillés dans 4 fichiers moteur + 8 services, sans versionnage ni éval.

### 2.3 Multi-arènes : le squelette existe, les fondations manquent
- 3 arènes réelles (`twitter_simulation`, `reddit_simulation`, `polymarket_simulation`),
  contrat de plugin propre (`SimulationConfig`, `simulations/base.py:361-376`).
- Twitter/Reddit partagent les mêmes classes (seuls prompts/actions/recsys diffèrent,
  `social_media/__init__.py:44-80`) → **une arène MENA = un 4ᵉ SimulationConfig**, pas
  une nouvelle plateforme.
- Mode lock-step 3 arènes opérationnel (`run_parallel_simulation.py:2289-2398`) avec
  ponts inter-arènes réels (`MarketMediaBridge`, `extra_observation_context` alimenté
  en `run_parallel_simulation.py:2674-2675`, `CrossPlatformLog`, `RoundMemory`).
- MAIS : choix d'arène = 3 booléens utilisateur sans règle ni validation croisée
  (`simulation_manager.py:56-58`, `/start` accepte tout — `simulation_runner.py:560-574`) ;
  enum de plateformes codé en dur (`simulation.py:3771`) ; arènes activées non
  requêtables (pas de colonne dédiée dans `simulation_ownership`) ; artefacts sur
  volume éphémère (`backend/uploads/`, ADR-005 ouvert) ; `BeliefState` fragmenté par
  arène sans fusion (`run_parallel_simulation.py:2412-2414`).

## 3. Architecture cible

### 3.1 Dénouement par spécification + oracle de clôture (ADR-015)

Principe : **l'infini des scénarios est absorbé à la création du marché, jamais à la
résolution**. Chaque marché naît avec son contrat de dénouement ; l'oracle applique,
il n'invente pas.

1. **Naissance** : l'appel LLM qui génère la question de marché
   (`simulation_config_generator.py:1101-1138`) génère AUSSI sa `resolution_spec`
   (structured output validé) : critères mesurables sur l'état final de la simulation
   (stances finales, contenus produits, trajectoire, événements), échéance, conditions
   d'invalidité. Une spec non mesurable → régénération. Jamais de marché sans contrat.
2. **Clôture** : l'**oracle de résolution** (prompt L99 distinct, chain-of-verification,
   structured output) reçoit spec + artefacts finaux → verdict `YES | NO | INVALID` +
   justification citant les éléments de simulation + confiance. `INVALID` → **void** :
   remboursement des positions au coût réel (comme un marché réel annulé).
3. **Paiement** : `resolve_market()` (existant) paie les positions ; `cost_basis` réel
   recalculé depuis la table `trade` (supprime le 0.50 codé en dur) ; **la richesse
   finale de chaque persona devient son score de justesse** (réutilisable pour pondérer
   la crédibilité dans la couche Delphi et les simulations suivantes).
4. **Audit** : verdict + justification + confiance + version du prompt oracle persistés
   en Supabase (`market_resolutions`) et restitués dans le PDF.
5. **Preuve** : golden set d'éval de l'oracle (états finaux → verdicts attendus, dont
   des cas INVALID), rejoué avant activation de toute nouvelle version du prompt.

### 3.2 Personas ESCO + enrichissement 122B (ADR-016)

- Cache Supabase `occupation_profiles` : fiches métiers (URI ESCO, libellé, définition,
  compétences essentielles/optionnelles, langue, `source` ∈ {`esco`, `llm_122b`}).
- `wonderwall_profile_generator` mappe la profession de chaque entité → fiche (cache
  d'abord, API ESCO sinon, échec réseau → fallback documenté) et injecte un bloc
  `<expertise_metier>` (définition + compétences = axes de comportement) dans le system
  prompt. MBTI / risk_tolerance existants = couche style ; ESCO = couche compétence.
- Rôles hors-taxonomie (influenceur, militant en ligne…) : fiches générées par le 122B
  via la gateway LiteLLM, écrites dans `occupation_profiles` avec `source='llm_122b'`
  (provenance tracée, revue possible depuis l'admin).
- FR/EN/AR : fiches par langue (l'API ESCO les fournit nativement — vérifié).

### 3.3 Registre de prompts en base + console super-admin (ADR-017)

- Table `simulation_prompts` : `key` (ex. `arena.polymarket.system`,
  `oracle.resolution`, `config.market_generation`), `scope` (arène/service), `locale`,
  `version`, `content`, `variables` (jsonb), `is_active`, `created_by`. **Une ligne =
  une version immuable** ; activer = basculer `is_active`, jamais écraser.
- Backend `PromptRegistry` : résolution `key+locale` → version active, cache
  in-process, **fallback sur le prompt codé** si table vide/injoignable (le moteur ne
  casse jamais à cause du registre).
- Console super-admin (guard existant) : liste par arène/service, lecture, **édition =
  création de nouvelle version**, diff entre versions, rollback un clic, activation
  conditionnée au passage du golden set du prompt (garde-fou anti-régression).
- Élévation L99 (skill `prompt-engineer-pro`) de tous les prompts au moment de leur
  externalisation : checklist qualité, negative prompting structuré, localisation,
  correction des incohérences (§2.2), golden set par prompt (`eval-runner.py`).

### 3.4 Routage déterministe + confrontation (ADR-019, étend ADR-011)

- **Règle déterministe par défaut, override explicite, journalisation** : table
  déclarative type de scénario → arènes recommandées ; l'utilisateur peut outrepasser ;
  chaque choix (règle appliquée ou override) est journalisé pour réviser la table sur
  données d'usage (signal de réexamen ADR-011). Le CONTENU de la table = décision
  produit d'Amine ; le mécanisme + une table par défaut = ce chantier.
- Validation croisée `/start` ↔ arènes activées (ferme l'angle mort §2.3).
- **Confrontation d'approches** : couche Delphi de normalisation (ADR-011) convertit
  les signaux hétérogènes de chaque arène (prix de convictions, stances sociales,
  belief drift) en distributions comparables ; section PDF comparative « ce que dit
  chaque arène » ; richesse finale des traders (§3.1) comme pondération de crédibilité.
- Première arène MENA (relais WhatsApp/groupe) en `SimulationConfig` sur la plateforme
  sociale existante (US-216 → US-237).

### 3.5 Renommage « arène de convictions » (ADR-018 amendé — cf. §7.4)

Périmètre : tout le visible client — encart PDF `_method_limits.md.j2` (3 langues),
libellés UI (`charts.polymarket.title`, `marketCountTitle`, `predictionMarkets`, clé
fallback l.149, etc.), parité stricte fr/en/ar dans le même commit (US-217).
Le mécanisme est une **arène parmi les arènes** (cohérence produit) ; les marchés
individuels deviennent des « questions » côté client. Le vocabulaire technique interne
(code, `polymarket_*`, tables SQLite) ne change pas.

## 4. Tables et colonnes planifiées (à confirmer dans le dictionnaire au commit de migration)

| Objet | Rôle | RLS |
|---|---|---|
| `simulation_prompts` (nouvelle) | Registre versionné des prompts (une ligne = une version) | super-admin uniquement |
| `occupation_profiles` (nouvelle) | Cache fiches métiers ESCO + 122B, par langue, provenance tracée | lecture service, écriture super-admin/pipeline |
| `market_resolutions` (migrée US-226) | Adjudication durable : snapshots, preuves digest, issue, prix et état payout | lecture org propriétaire, écriture service_role |
| `simulation_ownership.enabled_platforms` (colonne `text[]`) | Arènes activées, requêtables | héritée de la table |

## 5. Contraintes transverses

- **ADR-002** : le renommage (§3.5) purge « prédiction » du visible client ; le
  mécanisme interne reste libre. Aucun claim de calibration tant que < 20 outcomes.
- **US-217 polyglotte** : tout nouveau libellé/prompt localisé fr/en/ar, parité stricte
  même commit ; échapper `@` en `{'@'}` (piège vue-i18n).
- **SOP-013** : maquette navigable de la page super-admin AVANT exécution Ralph des
  stories UI (US-234).
- **SOP-012** : évals de prompts et tâches mécaniques du chantier sur le modèle le
  moins cher suffisant.
- **Ponytail full** : ESCO via `urllib` stdlib (zéro dépendance nouvelle) ; le registre
  de prompts réutilise le guard super-admin et la console existants.
- **Écriture données** : Supabase = source de vérité (jamais `backend/uploads/` pour
  du persistant — la migration ADR-005 est justement US-221).

## 6. Ordre d'exécution (hard things first) et dépendances

```
US-221 (persistance artefacts, ADR-005)  ─┐
US-222 (enabled_platforms + registre arènes + validation /start) ─┤ Lot 0 — fondations
US-223 (table simulation_prompts + PromptRegistry) ─┘
US-224 (renommage convictions)            — quick win indépendant, livrable immédiat
US-225 (resolution_spec par marché)       → US-226 (oracle + payout) → US-227 (restitution PDF)
US-228 (cache ESCO)                       → US-229 (blocs expertise personas) ; US-230 (122B)
US-231 (L99 prompts d'arènes)             ← US-223
US-232 (L99 prompts services + fuseaux paramétrables) ← US-223
US-233 (API prompts versionnée)           ← US-223 → US-234 (page super-admin, SOP-013)
US-235 (routage déterministe)             ← US-222 → US-236 (Delphi + PDF comparatif) ← US-226
US-237 (arène MENA WhatsApp)              ← US-222, US-231
```

Ajustements post-Council (2026-07-16) : **US-212** (outillage lint/typecheck, converti
du backlog en story prd.json) rejoint le Lot 0 — un loop long sans gate lint est une
dette de validation ; **US-IQ-05/06/07** passent P0 (fil rouge « premier cas Porte 2
réel au plus tôt » — First Principles, arbitré par le Chairman).

## 7. Addenda post-Council (2026-07-16 — re-soumission SOP-013)

> Verdict Council : NO-GO en l'état, correctifs ciblés sans refonte. Les trous de spec
> identifiés sont comblés ici ; le prototype v2 (même URL) intègre les états manquants,
> le disclaimer S4 = S3, le scénario démo neutralisé, l'aperçu ar/RTL et le commutateur
> de lexique. Rien n'est codé avant le go explicite d'Amine (SOP-013 §9).

### 7.1 Contrat d'interface de l'oracle + série de prix durable (complète §3.1 — US-225/226/227/236)

**Série de prix par round (durable)** — constat vérifié : le prix n'existe aujourd'hui
qu'en lecture live des réserves AMM (`simulation.py:5151-5190`) ; la table `trade`
porte un prix effectif par transaction (`schema/trade.sql`) mais aucune notion de
round. Décision :

- Nouvelle table SQLite `market_price_snapshot` (`market_id`, `round`, `price_yes`,
  `reserve_a`, `reserve_b`) dans `polymarket_simulation.db`, écrite au tick de chaque
  round (hook existant `platform.tick_clock()`). Coût : un INSERT par marché par round.
  L'artefact devient durable via US-221 (Supabase Storage).
- À la clôture, la série complète est copiée en jsonb dans
  `market_resolutions.price_series` : le PDF, l'API et le comparatif Delphi (US-236)
  lisent **Supabase**, jamais l'artefact brut.
- `cost_basis` réel : somme des `trade.cost` par (user, market, outcome) — supprime le
  0,50 codé en dur (`environment.py:40`).

**Contrat d'interface oracle (I/O gelé)** :

- **Entrée** (JSON) : `resolution_spec` du marché (criteria[] mesurables,
  `deadline_round`, `invalid_conditions[]`) + `simulation_digest` (stances finales,
  extraits de contenus produits pertinents aux critères, métriques de trajectoire,
  `price_series`) + `market` (question, outcomes).
- **Sortie** (structured output validé par schéma) : `{ verdict: YES|NO|INVALID,
  justification (citant rounds et preuves), confidence ∈ [0,1],
  evidence: [{round, type, ref}] }`. `UNRESOLVED` n'est jamais une sortie LLM : il est
  produit exclusivement par le service après deux sorties invalides ou un échec technique.
- **Modes d'échec** : sortie invalide → 1 retry ; échec persistant → statut
  `UNRESOLVED` persisté, AUCUN paiement, le PDF affiche « non clôturé — incident
  technique ». L'oracle n'invente jamais de verdict par défaut. `INVALID` → void :
  remboursement de chaque position au coût réel.
- **`market_resolutions` (schéma gelé)** : `simulation_id`, `market_id` bigint,
  `org_id`, `question`, `resolution_spec` jsonb, `verdict`, `justification`,
  `confidence`, `evidence` jsonb, `price_series` jsonb not null (défaut `[]`),
  `payout_summary` jsonb not null (défaut `{}`), `prompt_key`, `prompt_version`,
  `resolved_at`. PK (`simulation_id`, `market_id`), FK composite vers ownership et index
  (`org_id`, `resolved_at`) pour les requêtes cross-simulations de l'organisation.

**Précision US-226** : `market_resolutions` emploie `market_id bigint` et la PK
`(simulation_id, market_id)`. `org_id` est requis pour la RLS et la FK composite vers
`simulation_ownership` ; il ne s'agit donc pas d'une simple dénormalisation. `question`
et `resolution_spec` sont des snapshots durables. `evidence` est un tableau borné de
`{round,type,ref}` pointant exclusivement dans le digest déterministe. `price_series`
et `payout_summary` sont non nuls (défauts `[]` et `{}`) afin de fournir un état durable
et idempotent ; leurs mises à jour sont limitées au `service_role`.

### 7.2 Scellement ADR-IQ-05 — TRANCHÉ, validé par Amine (US-IQ-05)

| Critère | Chiffrement applicatif | Hachage + révélation différée |
|---|---|---|
| Garantie de non-accès | Organisationnelle (une clé existe côté serveur) | Cryptographique (le clair n'est jamais stocké) |
| UX de restitution | Automatique (déchiffrement serveur) | Le prospect doit re-saisir l'issue à l'identique |
| Risque business | Faible | Élevé : prospect absent ou re-saisie divergente → restitution comparée impossible (le livrable meurt) |
| Complexité | Faible (Fernet, clé env dédiée) | Moyenne (canonicalisation fragile sur texte libre) |

**Tranche de la revue technique** : **chiffrement applicatif** — clé env dédiée
`INTAKE_SEAL_KEY` (jamais la clé Supabase), déchiffrement uniquement dans le chemin de
restitution — **plus** empreinte SHA-256 du clair remise au prospect à la soumission
(commitment : à la restitution, le déchiffré re-hache vers la même empreinte, le
prospect vérifie que rien n'a été altéré). La révélation différée pure est rejetée :
elle transfère le risque d'échec de la démonstration au prospect. Le test unitaire
d'US-IQ-05 (le champ n'apparaît dans AUCUN contexte agent ni pré-seed) reste le
garde-fou principal ; mutualisation avec le registre scellé M1 (US-220) au signal de
réexamen d'ADR-IQ-05. **Validé par Amine (2026-07-16)** : ADR-IQ-05 et le critère
d'US-IQ-05 sont fixés sur cette option (docs/intake/08-decisions-log.md,
docs/intake/02-data-dictionary-delta.md).

### 7.3 Périmètre de lecture du routage Branche B (clarification — US-IQ-06/07)

Le routage est déjà déterministe, pur et testé par table de vérité (`_decide_route`,
`intake_service.py:386-415`, ADR-IQ-02/ADR-IQ-12). **Contrat de lecture gelé** — le
routage lit exactement : `stakes.budget_bracket` (tranche déclarée par le prospect,
jamais scellée), `stakes.exposure`, `governance`, `deadline`, et le **nombre** de
sujets confidentiels (`len(confidential_flags)`) — jamais leur contenu. Il ne lit
JAMAIS `aar_known_outcome` (exclu de tout contexte : `safe_brief`,
`intake_service.py:928` ; test unitaire partagé US-IQ-05/07). L'écran admin (proto S8)
peut donc afficher « montant estimé > palier self-service » : le montant est une
déclaration non scellée du brief. Toute évolution du routage qui voudrait lire un
champ supplémentaire exige un amendement d'ADR-IQ-02.

### 7.4 Lexique client — TRANCHÉ (2026-07-16)

- **Nom du mécanisme** (arbitrage Amine, session du 2026-07-16) : **« arène de
  convictions »** (fr) / « conviction arena » (en) / « ساحة القناعات » (ar) remplace
  « marché de convictions » — ADR-018 amendé. Motif sourcé : les prediction markets
  sont unanimement classés maysir (jeu de hasard prohibé) par les jurisprudences de
  finance islamique — le mot « marché »/« سوق » porte cette connotation pour la cible
  institutionnelle MENA ; « arène » est en outre cohérent avec le vocabulaire produit
  existant (les arènes sociales). Les marchés individuels deviennent des
  « questions » côté client.
- **Halo lexical** (arbitrage Amine, même session, après comparaison des deux
  variantes commutables sur le prototype v2) : **Variante A retenue — registre
  wargaming professionnel**, sourcé CICDE Wargaming Handbook (ministère des Armées,
  France) et littérature de l'adjudication en wargaming (ScienceDirect,
  « Wargaming adjudication in the air-force and other military areas of
  education »). Glossaire final gelé :

  | Terme abandonné | Terme retenu (FR) | EN | AR |
  |---|---|---|---|
  | oracle / verdict de l'oracle | adjudication / issue d'adjudication | adjudication / adjudicated outcome | التحكيم / محصلة التحكيم |
  | verdict (isolé) | issue | outcome | محصلة |
  | dénouement | clôture (de scénario) | scenario closure | إغلاق السيناريو |
  | confiance (score) | degré de convergence | convergence score | درجة التقارب |
  | Delphi / comparatif Delphi | lecture croisée des arènes | cross-arena reading | القراءة المتقاطعة للساحات |

  Variante B (halo actuel conservé) est rejetée. US-224 exécute ce glossaire pour
  tout le visible client (PDF, UI, 3 locales, parité stricte même commit) — aucune
  occurrence des termes abandonnés (y compris « Delphi » et « oracle ») ne doit
  subsister. Le vocabulaire technique interne (clés `simulation_prompts.key` telles
  que `oracle.resolution`, tables SQLite) ne change pas (US-217, ADR-018).
