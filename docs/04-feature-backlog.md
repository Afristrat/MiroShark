# Feature Backlog — Bassira V2

> V2 gelée le 2026-07-07 — toute addition passe par une ADR. Filtre Ponytail échelon 1 :
> indispensable au parcours critique (y compris l'exploitation sûre d'une prod avec PII),
> sinon parking lot. Chaque item cite sa preuve d'origine (deep explore 2026-07-07).
> Numérotation US-2xx pour ne pas entrer en collision avec la v1 (US-000→US-145,
> `.ralph/prd.json`).

## V2 gelée

### Bloc A — Conditions du verdict (bloquantes, ordre d'exécution)

| # | Feature | Critère d'acceptation (binaire) | Preuve d'origine |
|---|---|---|---|
| US-200 | **Dossier licence — instruction par Amine** (domaine exclusif du propriétaire ; position d'Amine : MiroShark est basé sur MiroFish, aaronjmars s'est octroyé un droit qu'il n'avait pas). Support IA : faits uniquement (lignée MiroFish/MiroShark vérifiée, textes des LICENSE collectés — agent upstream-mirofish) | Faits collectés et remis à Amine ; décision consignée par LUI en ADR-003 | Directive Amine 2026-07-07 |
| US-201 | **Repositionnement « stress-test de décision »** : purge du mot « prédiction » et du claim « Brier 0,18 vérifié » de tout le copy commercial (3 locales), Home, /calibration, PDF | grep « prédi\|Brier » sur frontend/src/locales + templates PDF = 0 occurrence commerciale non étayée | PASSATION.md:1274-1283 |
| US-202 | **Encart « Méthode et limites » obligatoire** en page 2 de chaque variante PDF + marquage machine-readable du contenu synthétique (métadonnées PDF/XMP) — conformité EU AI Act Art. 50 avant le 2026-08-02 | Chaque PDF généré contient l'encart trilingue + métadonnée `synthetic_content=true` vérifiable | artificialintelligenceact.eu/article/50 |
| US-203 | **Migration payload riche devis → Supabase** (colonnes full_name, message, geo_focus… dans quote_ownership ou table quote_payloads RLS) + vérification volume persistant Coolify pour uploads/ | Un devis soumis survit à un redeploy complet (test prouvé) ; 02-data-dictionary mis à jour même commit | explore-infra P0, PASSATION.md:36 |
| US-204 | **Resend opérationnel en prod** : notification à chaque devis reçu — expéditeur = adresse AI-MPower, TOUS les liens de renvoi = bassira.ma (ADR-013) | Devis test en prod → email reçu < 2 min, liens vérifiés bassira.ma | PASSATION.md:1399,1459-1467 + directive Amine 2026-07-07 |
| US-205 | **Stripe Checkout natif + PRICING** (reprise US-113 v1) : créer les products/prices Stripe des packages (MAD/USD, jamais EUR), Payment Sessions + webhook, /offres câblée | Pricing visible dans le dashboard Stripe + paiement test mode complet → quote_ownership.status='paid' automatique | .ralph/prd.json:3472-3493 + directive Amine 2026-07-07 |
| US-206 | **Fermer l'IDOR /api/report/<id>** : auth sur get_report, download, generate, chat | Accès anonyme aux 4 endpoints = 401/403 ; tests IDOR étendus verts | docs/SECURITY_AUDIT_2026-05.md:52-71 |
| US-207 | **Serveur WSGI de production** (gunicorn/waitress) + gate FLASK_DEBUG=false + refus de boot si NEO4J_PASSWORD == défaut 'miroshark' | run.py n'appelle plus app.run() en prod ; Config.validate() fail-closed sur les 2 points | backend/run.py:45, config.py:76 |
| US-208 | **Redis + worker RQ PDF actifs en prod** : plus aucune génération PDF dans le thread HTTP | REDIS_URL déclaré Coolify ; job async vérifié ; fallback sync loggé WARNING | pdf_generation_worker.py:21-23 |

### Bloc B — Crédibilité et image (après Bloc A)

| # | Feature | Critère d'acceptation (binaire) | Preuve d'origine |
|---|---|---|---|
| US-210 | **Rebrand des assets sortants** : logo Bassira remplace miroshark-nobg.png dans le watermark d'export + purge SettingsPanel/ExploreView des liens MiroShark + i18n EmbedDialog | Export PNG test porte le logo Bassira ; grep « miroshark\|MiroShark » sur les strings visibles utilisateur = 0 (identifiants techniques exclus) | chartExport.js:10, SettingsPanel.vue:84-452 |
| US-211 | **Persistance currentOrgId** (localStorage) + sélecteur d'org global dans AppHeader | Refresh de page conserve l'org choisie ; sélecteur visible sur toute page authentifiée si orgs>1 ; spec Playwright dédiée verte | stores/auth.js:28 |
| US-212 | **Outillage qualité** : ruff+mypy backend, eslint frontend, scripts npm lint/typecheck, CI frontend (build+lint+smoke Playwright) | `npm run lint` et `npm run typecheck` existent et passent ; CI exécute le job frontend sur PR | explore-infra P0 outillage |
| US-213 | **Patch des 8 CVE npm** (axios en tête) | `npm audit` = 0 HIGH/CRITICAL | SECURITY_AUDIT_2026-05.md:231-247 |
| US-214 | **Pre-check EntityReader bloquant** : impossible de créer une simulation sur graphe vide | Tentative sur graphe vide → erreur explicite AVANT création ; zéro simulation fantôme possible | PASSATION.md:1394,1422-1425 |
| US-215 | **Ancrage réel optionnel** : calibration des personas par signaux Saqr + import de données réelles (sondage court CSV) affiché dans l'encart méthode | Une simulation « ancrée » affiche ses sources d'ancrage dans le rapport ; démo A/B possible | Contre-argument 2.4 (Bisbee 2024, Simile) |
| US-216 | **Arènes de simulation configurables par région** (ADR-011) : sélection COMBINABLE multi-arènes sur la même population d'agents + profils régionaux pondérés par données réelles (GSMA/Afrobarometer) + Delphi simulé comme couche de normalisation (indicateur continu + polarisation). 5 arènes candidates sourcées : Diwaniya/Majlis, Relais WhatsApp/Telegram, Chaire du vendredi/Radio, Souk/diaspora, Delphi. Modules `wonderwall/simulations/<arena>/` (pattern `base.py` SimulationConfig déjà pluggable — vérifié) | À la création d'une simulation, l'utilisateur choisit/combine ses arènes ; ≥ 1 arène MENA implémentée + la couche Delphi produit un indicateur continu comparable au prix AMM | Directive Amine 2026-07-07 + ADR-011 (sources) |
| US-217 | **Polyglotte intégral** : i18n extensible N langues (ar/en/fr + additions) sur frontend, backend (messages/erreurs API) ET livrables (PDF, emails) — sans exception | Ajouter une 4ᵉ langue = fichiers de locale uniquement (0 modification de code) ; PDF et emails générés dans la langue demandée ; parité de clés vérifiée en CI | Directive Amine 2026-07-07 |
| US-218 | **Contrat API sortant Bassira** pour les consommateurs Saqr et Nahda (auth par clé API, endpoints de lecture des rapports/simulations publiés, versionné) | Un client externe muni d'une clé lit un rapport publié via l'API ; contrat documenté dans docs/ | Directive Amine 2026-07-07 |
| US-219 | **Déployer OpenSERP et remplacer SearXNG** (ADR-012) : service Coolify `karust/openserp` (Chromium headless, API JSON multi-moteurs) + repli Serper.dev câblé uniquement sur erreur/CAPTCHA | OpenSERP répond en JSON sur serveuria sans blocage sur 20 requêtes consécutives ; web_enrichment/trending basculés | ADR-012 (comparatif sourcé 2026-07-07) |
| US-220 | **Arbitrer la synchronisation upstream** : notre main = 181 commits de retard sur aaronjmars/MiroShark (i18n FR ~87 % en recouvrement probable avec la nôtre, bumps sécurité Dependabot, fix persistance compose) vs 244 commits Bassira propres — décision d'Amine : merge sélectif / cherry-pick sécurité / gel du fork | Décision consignée en ADR + exécutée ; si cherry-pick sécurité : `npm audit`/bumps upstream intégrés (synergie US-213) | Rapport upstream-mirofish 2026-07-07 |

## Parking lot

| Feature | Origine | Condition de sortie du parking |
|---|---|---|
| Découpage simulation.py (8875 l.) et report_agent.py (3915 l.) en modules | explore-backend | Avant le premier chantier feature qui touche ces fichiers > 500 lignes de diff |
| Unification complète --wi-* sur le cœur produit (Step1-5, console, admin) | explore-frontend | Premier retour client négatif sur l'incohérence visuelle, OU refonte UX planifiée |
| Scaling multi-nœud (queue distribuée, IPC Redis pub/sub) | explore-backend | > 10 orgs actives simultanées OU > 5 runs concurrents réguliers |
| Pagination + vue matérialisée analytics admin | admin.py:84-87 | simulation_ownership > 10 000 lignes |
| Combobox searchable sélecteurs d'org | PASSATION.md:64 | Un tenant dépasse 30 orgs |
| PLG freemium (à la Artificial Societies, 40 $/mois) | research-marche | 3 refus prospects pour cause de ticket d'entrée |
| Marque blanche cabinets de conseil | 2.7 plus petit test | Réfutation du test framing (3/3 « gadget ») |
| Garde-fou dur agents × rounds × plateformes | explore-backend | Premier run qui monopolise la prod > 1 h |
| Limites mémoire par conteneur Coolify (miroshark/neo4j — `limits_memory: '0'` actuel) + `depends_on: service_healthy` neo4j | incident 404 2026-07-07 | Prochaine récidive de crash au reboot serveur, OU chantier infra planifié |
| Investigation pression mémoire hôte serveuria (swap 100 %, 187 conteneurs) | incident 404 2026-07-07 | Hors périmètre Bassira — à ouvrir dans la session propriétaire du serveur |
| Suppression railway.json / render.yaml + archivage backlog.yaml | explore-infra | Prochain commit de housekeeping |
| Tests unitaires backend/app/storage/ (cœur RAG) | explore-infra | Premier bug en prod imputable à cette couche, OU chantier refacto storage |
| Audit accessibilité D3 (clavier, contrastes) | explore-frontend | Premier client institutionnel exigeant WCAG |
| Post-traduction citations agents dans PDF | explore-produit | Premier retour client sur la qualité linguistique du PDF |
| Fonction is_super_admin() : implémenter ou supprimer | explore-infra | Premier accès client direct Supabase (anon/authenticated) planifié |
| Moat-hunt inter-industries (skill moat-hunter) | Phase 4 np | À lancer avant le gel définitif du backlog V2 — recommandé immédiatement |
