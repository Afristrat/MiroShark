# Decisions Log (ADR) — Bassira V2

> Une décision = une entrée. Format : skill np, `references/sourcing-adr.md`.
> Ce fichier est la mémoire longue du projet — un choix non consigné sera re-débattu.
> Ouvert le 2026-07-07 (cadrage V2). Les décisions v1 antérieures vivent dans les
> passations ; seules celles encore structurantes sont reprises ici.

## ADR-001 — Conserver la stack héritée du fork (Flask + Vue), pas de réécriture
**Date** : 2026-07-07 · **Statut** : **remplacé par ADR-010** (directive Amine du même jour : la réécriture mono-stack est une option ouverte)
**Quoi** : la V2 durcit la stack Flask/Vue/Supabase/Neo4j existante ; aucune migration
vers la stack par défaut du poste (Next.js).
**Pourquoi** : 134 US déjà livrées sur cette stack ; le moteur wonderwall (cœur de la
valeur) est en Python ; une réécriture différerait de plusieurs mois les 3 conditions du
verdict sans valeur client.
**Sources** : décision interne — inventaire deep explore 2026-07-07 (.ralph/prd.json,
133/134 passes).
**Alternatives rejetées** : réécriture Next.js (coût prohibitif, aucun gain client) ;
migration partielle du front (double stack durable, pire).
**Signal de réexamen** : impossibilité de recruter/outiller sur Flask+Vue, ou blocage
upstream AGPL forçant une réécriture (lié ADR-003).

## ADR-002 — Positionnement « stress-test de décision », abandon du claim prédictif
**Date** : 2026-07-07 · **Statut** : accepté · réversible sous condition
**Quoi** : tout le copy commercial (Home, /offres, PDF, séquences) vend le stress-test
de décision et la cartographie des réactions — jamais la prédiction du réel ; le claim
« Brier 0,18 vérifié » est retiré tant que < 20 outcomes réels publics.
**Pourquoi** : (1) Bisbee et al. 2024 : ~48 % de coefficients statistiquement faux et
variance effondrée pour les personas LLM génériques ; (2) le concurrent le mieux financé
(Simile, 100 M$) est construit sur l'ancrage réel — vendre la prédiction générique nous
place du côté faible du spectre ; (3) le claim actuel est invérifiable (base calibration
vide) — contraire à la règle DÉFCON 1 du poste.
**Sources** : https://www.cambridge.org/core/journals/political-analysis/article/synthetic-replacements-for-human-survey-data-the-perils-of-large-language-models/B92267DC26195C7F36E63EA04A47D2FE ·
https://evoailabs.medium.com/the-ultimate-simulation-why-index-ventures-is-leading-similes-100m-series-a-7a41238cde31 · PASSATION.md:1274-1283.
**Alternatives rejetées** : garder « prédiction » avec disclaimer (le disclaimer ne
survit pas à une due diligence sophistiquée) ; construire d'abord la calibration réelle
(6+ mois sans vendre).
**Signal de réexamen** : ≥ 20 outcomes réels marqués publiquement avec Brier honnête →
le claim prédictif redevient étayable.

## ADR-003 — Dossier licence : domaine exclusif d'Amine (l'IA s'en tient aux faits)
**Date** : 2026-07-07 · **Statut** : instruit par Amine — hors périmètre IA
**Quoi** : la question de la licence du fork est instruite et tranchée par Amine seul.
Position d'Amine (2026-07-07) : MiroShark est basé sur une licence MiroFish dont
aaronjmars s'est octroyé un droit qu'il n'avait pas.
**Pourquoi** : les questions de droit et de juridiction relèvent du propriétaire du
projet, en conscience — l'IA rapporte des faits vérifiables (contenus des fichiers
LICENSE, lignée des projets amont), n'émet ni qualification ni prescription, et
n'en fait pas une condition de quoi que ce soit.
**Faits au dossier (collectés le 2026-07-07, remis à Amine sans commentaire)** :
- LICENSE du repo Bassira = texte AGPL-3.0 (LICENSE:1-12) ; repo = fork
  Afristrat/MiroShark ← aaronjmars/miroshark (AGENTS.md:9-11).
- MiroFish = 666ghj/MiroFish ; sa LICENSE à la racine = AGPL-3.0 (vérifiée sur
  raw.githubusercontent.com/666ghj/MiroFish/main/LICENSE) ; v0.1.2 du 2026-03-07 ;
  68,1k étoiles / 10,6k forks ; en tendance GitHub mondiale début mars 2026.
- Le README brut de MiroFish ne mentionne ni « MiroShark » ni « aaronjmars » ; son seul
  crédit tiers explicite est OASIS (camel-ai), dont il dit que son moteur est
  « powered by » ; aaronjmars/MiroShark n'apparaît pas dans le réseau de forks de
  MiroFish (état des recherches du 2026-07-07 — README, LICENSE, réseau de forks).
- Chronologie relative des deux dépôts (dates de création, antériorité de l'un sur
  l'autre) : NON établie par les recherches du 2026-07-07 — élément restant à instruire
  dans le dossier d'Amine s'il le juge utile.
**Alternatives rejetées** : sans objet (décision propriétaire).
**Signal de réexamen** : décision d'Amine consignée ici par lui ou sur sa dictée.

## ADR-004 — LLM : gateway LiteLLM, défaut DeepSeek v4 Flash + fallback
**Date** : 2026-07-07 (décision Amine, remplace la formulation initiale) · **Statut** : accepté · réversible
**Quoi** : le backend consomme le LLM via une gateway **LiteLLM** ; modèle par défaut
type **DeepSeek v4 Flash**, avec **fallback** configuré sur un autre modèle. Le client
code (`llm_client.py`) reste OpenAI-compatible générique — le BYOK client passe par la
gateway. Le choix des modèles appartient à Amine.
**Pourquoi** : (1) cohérence avec Saqr (DeepSeek-v4-flash déjà règle business côté
enrichment — vitesse/prix) ; (2) LiteLLM centralise routing, fallback et quotas sans
toucher au code applicatif ; (3) l'argument souveraineté/BYOK du créneau est préservé
par la gateway (aucun concurrent identifié ne le propose — recherche 2026-07-07).
**Sources** : directive Amine 2026-07-07 · https://docs.litellm.ai/docs/providers/deepseek
(préfixe `deepseek/` supporté pour tous les modèles DeepSeek) ·
https://docs.litellm.ai/docs/proxy/reliability (fallbacks natifs via
`litellm_settings.fallbacks` + num_retries + cooldown). ⚠️ Vigilance à l'implémentation :
bug LiteLLM #26395 (reasoning_content effacé en multi-tours avec DeepSeek V4 Pro) — à
tester avant prod si conversations multi-tours avec raisonnement.
**Alternatives rejetées** : provider unique câblé en dur (dépendance, perte BYOK) ;
statu quo Moonshot direct sans gateway (pas de fallback natif).
**Signal de réexamen** : latence/qualité insuffisante du modèle par défaut sur les runs
de simulation (850+ appels) — le fallback et le choix des modèles restent à la main d'Amine.

## ADR-005 — Supabase source de vérité ; migration du payload riche hors filesystem
**Date** : 2026-07-07 · **Statut** : accepté · réversible
**Quoi** : toute donnée métier persistante (payload devis, snapshots rapports, à terme
artefacts de simulation critiques) vit en Supabase (tables RLS ou Storage) ; le
filesystem `backend/uploads/` est traité comme cache éphémère.
**Pourquoi** : (1) volumes Coolify réinitialisés au deploy — bug déjà payé sur les
analytics (admin.py:24-27) ; (2) PII de prospects actuellement sur stockage volatil
(quote payloads) = perte de leads + exposition légale.
**Sources** : PASSATION.md:36 · migration 20260505_001 (commentaire « filesystem reste
la source de vérité pour le payload riche ») · rapport explore-infra 2026-07-07.
**Alternatives rejetées** : volume persistant seul (ne résout ni backups ni RLS ni
requêtabilité) — retenu uniquement comme mesure transitoire.
**Signal de réexamen** : coût Supabase Storage prohibitif à volume élevé.

## ADR-006 — Serveur WSGI de production + fail-closed sur les défauts dangereux
**Date** : 2026-07-07 · **Statut** : accepté · réversible
**Quoi** : remplacer `app.run()` (Werkzeug dev) par gunicorn/waitress ; `Config.validate()`
refuse de booter si `NEO4J_PASSWORD` == défaut connu ou `FLASK_DEBUG` actif en prod.
**Pourquoi** : serveur de dev mono-process en prod = fragilité (le pattern restart-loop
FLASK_DEBUG a déjà frappé, .ralph/progress.md:16) ; défaut 'miroshark' hardcodé = secret
trivial (config.py:76).
**Sources** : backend/run.py:45 · config.py:76 · .ralph/progress.md:16.
**Alternatives rejetées** : garder Werkzeug threaded (déjà en échec opérationnel).
**Signal de réexamen** : passage à un runtime async (hors périmètre V2).

## ADR-007 — Double canal de revenu : devis B2B principal + Stripe self-service
**Date** : 2026-07-07 · **Statut** : accepté · réversible
**Quoi** : le devis (12k/35k/20k MAD — $1.2k/$3.5k/$2k, jamais EUR) reste le canal
principal ; Stripe Checkout (US-205) ouvre le tier bas en self-service.
**Pourquoi** : cohérent avec la cible institutionnelle (cycle accompagné) ; le self-serve
débloque le pipeline Apollo sans intervention manuelle ; le bridge Payment Link manuel
actuel ne passe pas l'échelle.
**Sources** : PASSATION.md:1386 (pricing corrigé) · rapport recherche marché (Aaru vend
via grands comptes ; Artificial Societies en PLG — les deux modèles coexistent sur le
créneau).
**Alternatives rejetées** : PLG freemium intégral (casse le positionnement institutionnel,
parking lot avec condition de sortie).
**Signal de réexamen** : 3 refus prospects pour cause de ticket d'entrée.

## ADR-008 — Polyglotte intégral : i18n extensible N langues, frontend + backend + livrables
**Date** : 2026-07-07 (directive Amine, étend la version initiale) · **Statut** : accepté · irréversible en pratique
**Quoi** : architecture i18n par clés couvrant ar/en/fr ET des langues additionnelles,
sur TOUT : frontend, backend (messages, erreurs API), livrables (PDF, emails) — sans
exception (US-217). Ajouter une langue = ajouter des fichiers de locale, zéro code.
RTL complet conservé pour l'arabe.
**Pourquoi** : décision d'Amine (« vraiment polyglotte ») ; la cible institutionnelle
multi-pays (Maroc, Golfe, Afrique francophone/anglophone) impose la langue du LIVRABLE,
pas seulement de l'UI ; l'arabe reste un différenciateur face aux concurrents US/UK.
**Sources** : directive Amine 2026-07-07 · état vérifié : parité 2013 clés × 3 locales
frontend (rapport explore-frontend), backend et PDF partiellement localisés seulement.
**Alternatives rejetées** : rester à 3 locales frontend-only (contredit la directive) ;
traduction à la volée par LLM sans clés (qualité non maîtrisée sur livrable C-Level).
**Signal de réexamen** : coût de parité si > 6 locales actives (envisager alors une
locale « pivot + révision humaine » par marché).

## ADR-009 — Monitoring externe de la prod
**Date** : 2026-07-07 · **Statut** : accepté · réversible
**Quoi** : ajouter une sonde uptime externe avec alerte (solution à choisir à l'exécution —
échelle Ponytail : vérifier d'abord ce que Coolify/serveuria offre nativement avant tout
nouveau service).
**Pourquoi** : le 404 du 2026-07-07 a été découvert par Amine, pas par une alerte — pour
un produit vendu à des institutions, un down silencieux est inacceptable.
**Sources** : incident du jour (np-cadrage red flag 2) — décision interne.
**Alternatives rejetées** : statu quo (down silencieux) ; ⚠️ Plausible/PostHog/GA déjà
REFUSÉS par Amine (mémoire poste) — le monitoring uptime n'est pas de l'analytics, mais
ne pas re-proposer ces outils.
**Signal de réexamen** : sonde native Coolify suffisante → clore sans service tiers.

## ADR-010 — Réécriture mono-stack : option OUVERTE (remplace ADR-001)
**Date** : 2026-07-07 (directive Amine : « si je dois réécrire le code je n'ai rien
contre, pour être aligné avec une seule stack ») · **Statut** : ouvert
**Quoi** : évaluer l'alignement du produit sur UNE seule stack (candidate naturelle :
la stack par défaut du poste — Next.js + Supabase + TS), au lieu du duo Flask/Vue hérité.
**Pourquoi** : une seule stack = un seul outillage qualité, un seul vivier de compétences,
et une cohérence avec les autres produits d'Amine ; le moteur de simulation (wonderwall,
Python) et la cohabitation MiroFish pèsent dans l'arbitrage.
**Sources** : directive Amine 2026-07-07 · faits collectés le 2026-07-07 (agent
upstream-mirofish) :
- **Upstream MiroShark** : notre main est à **181 commits de retard** sur
  aaronjmars/MiroShark (divergence depuis l'ancêtre commun 555c6bd du 2026-04-28 ;
  notre couche Bassira = 244 commits propres ; diff 389 fichiers/+89k lignes). Upstream
  notable : i18n FR ~87 % (#222/#239 — RECOUVREMENT probable avec l'i18n Bassira, à
  arbitrer avant tout merge), bumps de sécurité Dependabot (#229/#230/#231 — synergie
  avec US-213), persistance backend/data dans compose (#238 — même classe de problème
  que notre US-203).
- **MiroFish** (666ghj/MiroFish, v0.1.2 du 2026-03-07, 68,1k étoiles) : moteur de
  simulation sociale prédictive — GraphRAG + moteur OASIS (camel-ai) + mémoire Zep Cloud
  (service tiers payant — point de souveraineté à traiter, fork communautaire
  MiroFish-Offline = Neo4j+Ollama 100 % local) ; stack Python 3.11-3.12 + Vue.js ;
  LICENSE = AGPL-3.0 ; effort d'auto-hébergement modéré, comparable à MiroShark.
  Recouvrement : simulation sociale à mémoire longue que wonderwall n'a pas.
**Alternatives en lice** : (a) statu quo durci (ex-ADR-001) ; (b) réécriture frontend
seul (Vue→Next) ; (c) réécriture complète autour du moteur Python conservé ; (d) bascule
vers MiroFish comme base et portage de la couche Bassira ; (e) cohabitation (décidée
par Amine : Bassira=B2B, canal MiroFish=B2G/grandes missions pour Nahda) avec
convergence progressive.
**DÉCISION AMINE (2026-07-07, « 2. go »)** : cap ACCEPTÉ vers l'alignement mono-stack.
Séquencement retenu : le Bloc A (P0 opérationnels) s'exécute d'abord sur l'existant —
les P0 ne peuvent pas attendre une réécriture ; l'arbitrage fin de la stack cible
(options a-e ci-dessus) s'instruit au démarrage du chantier réécriture, avec les faits
MiroFish déjà au dossier. Reste ouvert à ce stade : QUELLE stack unique (non nommée par
Amine — à trancher par lui au moment du chantier).
**Signal de réexamen** : démarrage du chantier réécriture (fin du Bloc A).

## ADR-014 — Synchronisation upstream : MERGE SÉLECTIF (US-220)
**Date** : 2026-07-07 (décision Amine : « US-220 ok pour le merge sélectif ») ·
**Statut** : accepté · réversible
**Quoi** : rattraper les 181 commits de retard sur aaronjmars/MiroShark par MERGE
SÉLECTIF — cherry-pick ciblé, pas de merge intégral. Priorités : (1) bumps de sécurité
Dependabot (#229/#230/#231 — synergie US-213), (2) fix persistance compose (#238 —
même classe que US-203), (3) correctifs moteur (tool_calls #232/#241). L'i18n FR
upstream (#222/#239) s'ARBITRE au cas par cas contre l'i18n Bassira existante (2013
clés à parité — risque de conflit massif, ne cherry-picker que ce qui comble des trous).
**Pourquoi** : 244 commits Bassira propres divergents — un merge intégral (389 fichiers,
+89k lignes) écraserait ou conflicterait la couche commerciale ; le sélectif prend la
sécurité et les fixes sans risquer l'acquis.
**Sources** : rapport upstream-mirofish 2026-07-07 (rev-list 181/244, ancêtre 555c6bd).
**Alternatives rejetées** : merge intégral (risque destructif sur la couche Bassira) ;
gel du fork (laisse des CVE corrigées upstream non prises).
**Signal de réexamen** : chaque nouveau lot de commits upstream significatif (revue
trimestrielle du delta `git fetch upstream && git rev-list --count main..upstream/main`).

## ADR-011 — Arènes de simulation configurables (le marché de prédiction n'est plus l'arène unique)
**Date** : 2026-07-07 (directive Amine) · **Statut** : accepté · réversible
**Quoi** : l'arène « marché de prédiction » devient UNE option parmi plusieurs ; chaque
simulation choisit ses arènes ; des arènes adaptées Africa/Middle East sont ajoutées
(US-216), architecture en modules `wonderwall/simulations/<arena>/`.
**Pourquoi** : constat d'Amine — le marché de prédiction est un mécanisme culturellement
occidental, peu représentatif des dynamiques d'opinion Africa/ME ; la crédibilité du
livrable dans la zone cible en dépend.
**Architecture retenue (recherche du 2026-07-07)** : (1) le pattern pluggable existe
déjà — `wonderwall/simulations/base.py` (`SimulationConfig`), polymarket/ et
social_media/ en sont deux instances ; une arène = un module. (2) Sélection
**combinable multi-arènes** sur la même population d'agents (pas un remplacement 1:1) —
le sermon alimente le relais WhatsApp qui alimente la diwaniya. (3) **Profils régionaux**
pondérant le poids de chaque arène selon des données réelles de pénétration
(GSMA/Afrobarometer/Arab Barometer). (4) **Delphi simulé = couche de normalisation** :
convertit les signaux hétérogènes en distribution de probabilité continue (équivalent
du prix AMM) ; la polarisation = écart-type de cette distribution (proxy du spread).
**5 arènes candidates sourcées** : Diwaniya/Majlis (ijoc.org/index.php/ijoc/article/view/15881) ·
Relais WhatsApp/Telegram (88-89 % des mobinautes 18+ des pays LMIC utilisent la
messagerie quotidiennement — gsma.com Mobile Economy Africa 2026 ; Zimbabwe : ~50 % du
trafic Internet national = WhatsApp — pmc.ncbi.nlm.nih.gov/articles/PMC7556529) ·
Chaire du vendredi/Radio (khutbas centralisées → +0,3 pt de proba thématique double le
volume Twitter la semaine suivante — journals.sagepub.com/doi/full/10.1177/23780231231182909 ;
radio = 1ᵉʳ canal d'info en Afrique, 59 % — afrobarometer.org) · Souk/diaspora
(tandfonline.com/doi/full/10.1080/1369183X.2024.2357833) · Delphi/Good Judgment
(goodjudgment.com, arxiv.org/pdf/1910.03779).
**Note d'honnêteté** : aucune littérature trouvée qui qualifie explicitement les marchés
de prédiction de « biais culturel occidental » — prémisse produit d'Amine assumée telle
quelle (non contredite, non corroborée par une source tierce identifiée).
**Alternatives rejetées** : garder le marché seul (contredit le terrain de la zone
cible) ; le supprimer partout (il reste sélectionnable — et le Delphi préserve la
métrique continue de polarisation).
**Signal de réexamen** : données d'usage — si une arène n'est jamais sélectionnée en
12 mois, la déprécier.

## ADR-012 — Remplacement de SearXNG par une solution de recherche headless
**Date** : 2026-07-07 (constat Amine : SearXNG bloqué — agrégateur dépendant d'APIs,
rejeté comme robot par ses moteurs) · **Statut** : ouvert — validation EN COURS pendant
le cadrage (exigence d'Amine)
**Quoi** : retenir une solution de recherche web headless (navigateur réel anti-blocage),
self-hosted de préférence, API JSON, pour le sourcing (np, moat-hunter) et
l'enrichissement web des simulations (US-219).
**Pourquoi** : le sourcing souverain est une dépendance critique du produit (ancrage,
veille) et de la méthode de travail ; le blocage Google de SearXNG est STRUCTUREL
(fingerprinting TLS/HTTP2 du client Python, pas de fix durable côté mainteneurs —
github.com/searxng/searxng/issues/2515).
**Décision (comparatif du 2026-07-07)** : **OpenSERP self-hosted** (karust/openserp —
Chromium headless via chromedp, stealth + anti-détection + gestion CAPTCHA intégrées,
MIT, image Docker officielle, API JSON multi-moteurs `/mega/search`, v0.8.6 juin 2026).
Installation triviale en service Coolify :
`docker run -p 127.0.0.1:7000:7000 karust/openserp:latest serve -a 0.0.0.0 -p 7000`.
**Repli non souverain** (filet de disponibilité uniquement, jamais chemin par défaut) :
Serper.dev (~0,30-1 $/1000 requêtes — coût réel < 2 $/mois au volume visé).
**Sources** : github.com/karust/openserp · openserp.org ·
github.com/searxng/searxng/issues/2515 · firecrawl SELF_HOST.md ·
docs.crawl4ai.com/advanced/undetected-browser · scrapling.readthedocs.io ·
awesomeagents.ai/pricing/search-api-pricing.
**Alternatives rejetées** : Firecrawl self-hosted (son /search délègue à une clé tierce
ou à un SearXNG sous-jacent — ne résout rien) ; Crawl4AI seul / Camoufox+Scrapling
(excellents substrats anti-détection mais aucun parseur SERP prêt — scraper maison à
coder et maintenir, effort disproportionné) ; SearXNG durci aux proxies (pansement sur
une impasse structurelle).
**Statut détaillé** : **VALIDÉ par Amine le 2026-07-07** (« ok pour les deux options »).
Portée étendue par Amine : **déprovisionner SearXNG PARTOUT** (toutes les codebases qui
le consomment), remplacement au fur et à mesure par la stack OpenSERP+Serper —
procédure standardisée dans **SOP-002** (bibliothèque SOP du poste).
**Signal de réexamen** : OpenSERP abandonné/cassé, ou CAPTCHA systématique au volume réel.

## ADR-013 — Domaine public bassira.ma partout ; emails Resend via l'adresse AI-MPower
**Date** : 2026-07-07 (directive Amine) · **Statut** : accepté · réversible
**Quoi** : toute URL publique et tout lien de renvoi (emails, PDF, share cards) pointe
**bassira.ma** ; l'expéditeur Resend est l'adresse AI-MPower.
**Pourquoi** : décision de marque d'Amine ; le défaut SQL actuel
`pdf_branding.footer_right='bassira.ai'` (migration 20260506_001) et tout lien résiduel
divergent sont des bugs de marque à corriger (rattaché US-204/US-210).
**Sources** : directive Amine 2026-07-07.
**Alternatives rejetées** : bassira.ai (défaut SQL actuel — non retenu par Amine).
**Signal de réexamen** : acquisition d'un autre domaine par Amine.
