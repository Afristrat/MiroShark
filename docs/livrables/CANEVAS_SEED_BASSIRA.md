# Canevas seed Bassira, brief de simulation dynamique adaptatif

Document destiné à un double usage :

1. **Projet Claude** : template à coller dans un projet Claude pour structurer une graine avant envoi à Bassira. Le projet Claude lit ce canevas et pose les bonnes questions selon le type de sujet.
2. **Questionnaire devis** `prospectives.ai-mpower.com/devis` : spécification des champs et des branches conditionnelles côté UI client.

Le canevas est **dynamique**, c'est-à-dire que les champs s'activent ou se désactivent en fonction des réponses précédentes. Il n'y a pas de formulaire monolithique avec 50 champs obligatoires, mais un arbre adaptatif qui ne demande que ce qui est pertinent pour la graine fournie.

---

## 1. Architecture du canevas dynamique

### 1.1 Principe d'adaptation

Le canevas se déploie en trois temps :

1. **Tronc commun** (5 champs requis) : la graine et le type de sujet, posés systématiquement.
2. **Branches conditionnelles** (champs activés selon le type) : sectorisées par profil de question.
3. **Surcouche optionnelle** (5 à 10 champs facultatifs) : qualité de la simulation, calibration fine.

Chaque champ porte un **trigger conditionnel** (expression booléenne sur les valeurs précédentes) et un **degré de blocage** (`required` qui empêche la soumission si vide, `recommended` qui dégrade le score qualité, `optional` qui enrichit sans bloquer).

### 1.2 Sortie attendue de la graine

À l'issue du canevas, Bassira produit un brief simulable comprenant :

- Une question stratégique formulée
- Des conditions de succès chiffrées
- Un framework analytique sélectionné (CERBERUS, MARKET, CRISIS, POLICY, DECISION)
- Une population synthétique de 20 à 60 personas avec démographie, biais, postures initiales
- Des signaux Kairos préinjectés (X, Reddit, ArXiv, presse, LinkedIn) scopés au sujet
- Des scénarios contrefactuels suggérés par le moteur
- Un horizon temporel et un calendrier de jalons

---

## 2. Tronc commun, 5 champs requis (toujours actifs)

### 2.1 Question stratégique (libellé long)

- **Champ devis** : `simulation_requirement` (textarea, 50 à 500 mots)
- **Prompt Claude** : « Formule la question opérationnelle exacte, en une à trois phrases. La question doit être actionnable, ancrée dans un contexte daté, et porter sur un choix ou un arbitrage. »
- **Validation** : longueur ≥ 80 caractères, contient au moins un verbe d'action (décider, arbitrer, modéliser, simuler, anticiper, valider, choisir, prioriser, segmenter, calibrer).
- **Exemple validé L99** : « Modéliser 30 partners avec leur niveau de confiance initial, leur courbe d'apprentissage prompt-engineering, et leur gain de temps par projet, est-ce que j'arrive à passer la barre des 70 % d'adoption et 50 % de réduction de temps de reformulation stratégique ? »
- **Anti-exemple** : « Comment améliorer la performance ? » (vague, sans verbe d'arbitrage, sans population, sans cible chiffrée).

### 2.2 Type de sujet (sélecteur racine, déclenche les branches)

- **Champ devis** : `topic_type` (select avec 6 valeurs exclusives)
- **Prompt Claude** : « Quel est le type opérationnel du sujet ? »
- **Valeurs** :
  - `internal_adoption` : adoption interne d'un outil ou d'une méthode (cas L99, déploiement partners)
  - `market_dynamics` : dynamique de marché, multi-acteurs concurrentiels
  - `crisis_management` : gestion de crise, choc exogène, fenêtre 24 h à 30 jours
  - `policy_arbitration` : arbitrage réglementaire, multi-stakeholders publics
  - `product_launch` : lancement produit ou go-to-market
  - `m_and_a_negotiation` : négociation M&A, valuation, deal-breakers

Cette valeur **conditionne dynamiquement** la sélection du framework §3.1 et l'activation des branches §4.

### 2.3 Conditions de succès chiffrées

- **Champ devis** : `success_criteria` (textarea structurée, format YAML-light)
- **Prompt Claude** : « Quelles conditions chiffrées définissent le succès ? Au moins deux métriques avec seuil numérique. »
- **Validation** : au moins 2 paires `métrique : seuil`. Si moins, le canevas refuse la soumission.
- **Exemple** :
  ```
  adoption_pct: > 70
  time_reduction_pct: > 50
  break_even_horizon_months: < 6
  ```

### 2.4 Horizon temporel

- **Champ devis** : `time_horizon` (select)
- **Prompt Claude** : « Sur quel horizon le sujet se joue-t-il ? »
- **Valeurs** : `24h_to_7d` / `1m_to_3m` / `3m_to_12m` / `1y_to_3y` / `3y_to_10y`
- **Impact** : conditionne la longueur de la trajectoire de simulation (rounds 30 / 50 / 72 / 100 / 150).

### 2.5 Langue de simulation

- **Champ devis** : `simulation_lang` (select)
- **Prompt Claude** : « Quelle langue principale pour les échanges agents ? »
- **Valeurs** : `fr` / `en` / `ar` / `fr_with_darija_microcode` / `fr_ar_bilingual`
- **Impact** : pilote la génération des verbatims, les sources Kairos priorisées et la langue du rapport PDF.

---

## 3. Branche framework, conditionnée par le type de sujet

### 3.1 Sélecteur de framework analytique

| Type de sujet (§2.2) | Framework par défaut | Frameworks alternatifs autorisés |
| --- | --- | --- |
| `internal_adoption` | **CERBERUS** (Champion + Sceptique + Indifférent + Garde-fou) | DECISION si arbitrage binaire pur |
| `market_dynamics` | **MARKET** (acheteur + vendeur + analyste + faiseur de marché) | DECISION |
| `crisis_management` | **CRISIS** (décideur + communicant + technique + journaliste + opinion) | POLICY si stakeholders publics |
| `policy_arbitration` | **POLICY** (régulateur + lobby + société civile + expert + média) | CRISIS |
| `product_launch` | **MARKET** | DECISION ou CRISIS si lancement sous pression |
| `m_and_a_negotiation` | **DECISION** (porteur + cible + actionnaire minoritaire + conseil + arbitre) | MARKET |

- **Champ devis** : `framework_choice` (select pré-rempli par la valeur par défaut, modifiable)
- **Prompt Claude** : « Le framework par défaut pour ce type de sujet est X. Souhaites-tu en changer ? Justifie en une ligne. »

### 3.2 Branche internal_adoption (cas L99)

Champs supplémentaires actifs uniquement si `topic_type = internal_adoption` :

- `population_size` (required, int 10 à 100) : nombre de personas à simuler. Défaut 30.
- `champion_persona_brief` (required, textarea) : profil du champion sponsor (qui porte la décision en interne).
- `skeptic_archetype_brief` (recommended, textarea) : profil du sceptique compétent attendu (qui fixera la barre évidentiaire).
- `breakeven_metric` (recommended, textarea) : seuil économique au-delà duquel l'outil est rentable (ex : 14 000 req/mois).
- `compensation_model_lever` (recommended, select) : `aligned` / `partially_aligned` / `misaligned`. Détecte le verrou structurel.

### 3.3 Branche market_dynamics

- `competitors_named` (required, list[str], min 2) : concurrents nommés et caractérisés.
- `market_share_current` (recommended, dict) : parts de marché actuelles par acteur.
- `price_elasticity_hint` (optional, float) : sensibilité prix observée.
- `regulator_pressure_index` (optional, select 0 à 5) : pression réglementaire ambiante.

### 3.4 Branche crisis_management

- `trigger_event_description` (required, textarea) : événement déclencheur de la crise.
- `crisis_horizon_hours` (required, int) : fenêtre temporelle de gestion (24, 48, 72, 168, 720).
- `media_exposure_level` (required, select) : `none` / `local` / `national` / `international`.
- `internal_communication_channels` (recommended, list) : Slack, email, WhatsApp, all-hands, press release.

### 3.5 Branche policy_arbitration

- `regulatory_framework_named` (required, list[str]) : textes réglementaires applicables (CNDP, RGPD, OMPIC, etc.).
- `public_stakeholders` (required, list[str]) : autorités publiques impliquées.
- `civil_society_stakeholders` (recommended, list[str]) : associations, syndicats, ONG.
- `electoral_calendar_proximity_days` (optional, int) : nombre de jours avant prochaine échéance électorale, peut peser sur la dynamique.

### 3.6 Branche product_launch

- `target_segment_demographics` (required, textarea) : segment cible avec démographie.
- `psychological_price_point` (required, float ou range) : prix psychologique cible.
- `competitor_alternative_price` (recommended, float) : prix alternative concurrente.
- `launch_channels` (recommended, list) : canaux de distribution.

### 3.7 Branche m_and_a_negotiation

- `acquirer_brief` (required, textarea) : profil acquéreur.
- `target_brief` (required, textarea) : profil cible.
- `valuation_range_min_max_meur` (required, range) : fourchette de valuation en M€.
- `deal_breakers_listed` (recommended, list[str]) : points de blocage anticipés.
- `regulatory_clearances_required` (optional, list) : autorisations réglementaires nécessaires.

---

## 4. Branche sources externes (Kairos, conditionnée par §2.2)

### 4.1 Niveau d'enrichissement Kairos demandé

- **Champ devis** : `kairos_enrichment_level` (select)
- **Valeurs** :
  - `none` : pas de Kairos, simulation sur signaux internes uniquement
  - `light` : 5 à 10 signaux Kairos préinjectés
  - `standard` : 15 à 30 signaux (cas L99, recommandé pour C-Level)
  - `deep` : 50 à 100 signaux + scraping ciblé sur demande

### 4.2 Sources Kairos activables par défaut selon §2.2

| Type sujet | Sources Kairos activées par défaut |
| --- | --- |
| `internal_adoption` | X tech, Reddit r/MachineLearning, HuggingFace blog, ArXiv, LinkedIn CIO |
| `market_dynamics` | X finance, Reddit r/business, Bloomberg, Reuters, LinkedIn analystes |
| `crisis_management` | X temps réel, AP / Reuters / MAP, Mastodon, Substack, Telegram public |
| `policy_arbitration` | Bulletin Officiel, journaux officiels, X public policy, Reddit r/politics, LinkedIn lobbyistes |
| `product_launch` | X consumer, Reddit r/[product_category], TrustPilot, Google Trends, LinkedIn growth |
| `m_and_a_negotiation` | Bloomberg, Reuters, Financial Times, LinkedIn corporate, SEC filings |

### 4.3 Documents internes uploadables

- **Champ devis** : `documents_upload` (multi-upload, max 20 Mo total)
- **Formats acceptés** : PDF, DOCX, MD, TXT, RTF, XLSX (extraction tabulaire)
- **Type attendu** : brief stratégique, rapport interne, transcription, deck concurrent, PDF analytique externe.

### 4.4 URLs à scraper

- **Champ devis** : `urls_to_scrape` (list[url], max 10)
- **Validation** : URLs accessibles publiquement ou avec credentials fournis hors canevas.

---

## 5. Branche surcouche optionnelle (toujours visible mais facultative)

### 5.1 Scénarios contrefactuels souhaités

- **Champ devis** : `counterfactuals_requested` (textarea libre + suggestions auto)
- **Prompt Claude** : « Quels scénarios "et si" veux-tu chiffrer ? Le moteur en propose 3 par défaut si tu laisses vide. »

### 5.2 Personas spécifiques nommées

- **Champ devis** : `named_personas` (list[dict])
- **Format** : `[{name, role, posture_initiale, biais_principal}, ...]`
- **Impact** : Bassira intègre ces personas par-dessus la génération synthétique Wonderwall.

### 5.3 Posts sociaux simulés et articles presse

- **Champ devis** : `social_posts_requested` (multiSelect plateformes)
- **Valeurs** : `facebook`, `x`, `reddit`, `linkedin`, `instagram`, `tiktok_descriptive`
- **Champ devis** : `press_articles_requested` (multiSelect médias par défaut)
- **Valeurs** : `techcrunch_mena`, `jeune_afrique`, `huggingface_blog`, `reuters`, `local_press_morocco`, `bloomberg`, `financial_times`

### 5.4 Calibration de la simulation

- **Champ devis** : `simulation_calibration` (group)
  - `nb_rounds` (int, 30 à 150, défaut adapté par §2.4)
  - `coherence_target` (float 0 à 1, défaut 0.70)
  - `diversity_target` (float 0 à 1, défaut 0.40)
  - `enable_director_events` (bool, défaut true) : autoriser des injections exogènes au cours de la simulation

### 5.5 Budget et délai

- **Champ devis** : `budget_meur` (float, optionnel)
- **Champ devis** : `delivery_deadline_iso` (date)

---

## 6. Validation et soumission

### 6.1 Score de qualité de la graine

À mesure que le canevas se remplit, le système calcule un **Score Seed Quality** en temps réel (0 à 100) :

| Tranche | Couleur UI | Sens |
| --- | --- | --- |
| 0 à 39 | Rouge | Graine insuffisante, refus de soumission |
| 40 à 59 | Orange | Graine acceptable mais résultats moins fiables |
| 60 à 79 | Jaune | Graine standard, fiabilité attendue |
| 80 à 100 | Vert | Graine premium, fiabilité maximale |

Composition du score :
- 40 points : tronc commun complet et formulé correctement
- 30 points : branche conditionnelle complète selon §2.2
- 20 points : Kairos enrichissement ≥ standard et documents uploadés
- 10 points : surcouche optionnelle activée partiellement

### 6.2 Aperçu avant lancement

Le canevas génère un **Brief Preview** structuré, montrant à l'utilisateur :
- La question stratégique formulée
- Le framework retenu
- La population estimée
- Les sources Kairos qui seront mobilisées
- Le score Seed Quality
- Le délai de simulation estimé en minutes
- Le coût estimé en MAD

L'utilisateur valide ou retourne sur les champs faibles.

---

## 7. Template prêt-à-coller pour projet Claude

```
# Brief de simulation Bassira, projet [NOM_PROJET]

## 1. Tronc commun
- Question stratégique : ...
- Type de sujet : [internal_adoption | market_dynamics | crisis_management | policy_arbitration | product_launch | m_and_a_negotiation]
- Conditions de succès chiffrées :
  - ...
  - ...
- Horizon temporel : [24h_to_7d | 1m_to_3m | 3m_to_12m | 1y_to_3y | 3y_to_10y]
- Langue : [fr | en | ar | fr_with_darija_microcode | fr_ar_bilingual]

## 2. Framework
- Framework choisi : [CERBERUS | MARKET | CRISIS | POLICY | DECISION]
- Justification du choix vs défaut : ...

## 3. Branche conditionnelle (remplir uniquement la section correspondant à §1.type)

### Si internal_adoption :
- Population size : ...
- Champion sponsor brief : ...
- Sceptique compétent archetype : ...
- Break-even économique : ...
- Modèle de compensation : [aligned | partially_aligned | misaligned]

### Si market_dynamics :
- Concurrents nommés : ...
- Parts de marché actuelles : ...
- Élasticité prix : ...
- Pression réglementaire : ...

### Si crisis_management :
- Événement déclencheur : ...
- Horizon en heures : ...
- Niveau d'exposition médiatique : ...
- Canaux de communication interne : ...

### Si policy_arbitration :
- Cadres réglementaires nommés : ...
- Stakeholders publics : ...
- Société civile : ...
- Calendrier électoral : ...

### Si product_launch :
- Segment cible : ...
- Prix psychologique : ...
- Prix alternative concurrente : ...
- Canaux : ...

### Si m_and_a_negotiation :
- Acquéreur : ...
- Cible : ...
- Valuation range : ...
- Deal-breakers : ...

## 4. Sources externes
- Niveau Kairos : [none | light | standard | deep]
- Documents uploadés : ...
- URLs à scraper : ...

## 5. Surcouche optionnelle
- Scénarios contrefactuels : ...
- Personas nommées spécifiquement : ...
- Posts sociaux à simuler : ...
- Articles presse à simuler : ...
- Calibration : nb_rounds=..., coherence_target=..., diversity_target=..., director_events=...
- Budget : ... MAD
- Délai : ...
```

---

## 8. Mapping vers formulaire devis dynamique

| Champ canevas | Type devis | Required | Trigger conditionnel |
| --- | --- | --- | --- |
| simulation_requirement | textarea | oui | toujours visible |
| topic_type | select | oui | toujours visible |
| success_criteria | textarea | oui | toujours visible |
| time_horizon | select | oui | toujours visible |
| simulation_lang | select | oui | toujours visible |
| framework_choice | select | oui | toujours visible (pré-rempli) |
| population_size | int | oui si IA | `topic_type == 'internal_adoption'` |
| champion_persona_brief | textarea | oui si IA | `topic_type == 'internal_adoption'` |
| skeptic_archetype_brief | textarea | recommandé | `topic_type == 'internal_adoption'` |
| breakeven_metric | textarea | recommandé | `topic_type == 'internal_adoption'` |
| compensation_model_lever | select | recommandé | `topic_type == 'internal_adoption'` |
| competitors_named | list | oui si MD | `topic_type == 'market_dynamics'` |
| market_share_current | dict | recommandé | `topic_type == 'market_dynamics'` |
| price_elasticity_hint | float | optionnel | `topic_type == 'market_dynamics'` |
| regulator_pressure_index | select | optionnel | `topic_type in ['market_dynamics', 'product_launch']` |
| trigger_event_description | textarea | oui si CM | `topic_type == 'crisis_management'` |
| crisis_horizon_hours | int | oui si CM | `topic_type == 'crisis_management'` |
| media_exposure_level | select | oui si CM | `topic_type == 'crisis_management'` |
| internal_communication_channels | list | recommandé | `topic_type == 'crisis_management'` |
| regulatory_framework_named | list | oui si PA | `topic_type == 'policy_arbitration'` |
| public_stakeholders | list | oui si PA | `topic_type == 'policy_arbitration'` |
| civil_society_stakeholders | list | recommandé | `topic_type == 'policy_arbitration'` |
| electoral_calendar_proximity_days | int | optionnel | `topic_type == 'policy_arbitration'` |
| target_segment_demographics | textarea | oui si PL | `topic_type == 'product_launch'` |
| psychological_price_point | float | oui si PL | `topic_type == 'product_launch'` |
| competitor_alternative_price | float | recommandé | `topic_type == 'product_launch'` |
| launch_channels | list | recommandé | `topic_type == 'product_launch'` |
| acquirer_brief | textarea | oui si MA | `topic_type == 'm_and_a_negotiation'` |
| target_brief | textarea | oui si MA | `topic_type == 'm_and_a_negotiation'` |
| valuation_range_min_max_meur | range | oui si MA | `topic_type == 'm_and_a_negotiation'` |
| deal_breakers_listed | list | recommandé | `topic_type == 'm_and_a_negotiation'` |
| regulatory_clearances_required | list | optionnel | `topic_type == 'm_and_a_negotiation'` |
| kairos_enrichment_level | select | recommandé | toujours visible |
| documents_upload | multi-upload | optionnel | toujours visible |
| urls_to_scrape | list[url] | optionnel | toujours visible |
| counterfactuals_requested | textarea | optionnel | toujours visible |
| named_personas | list[dict] | optionnel | toujours visible |
| social_posts_requested | multiSelect | optionnel | toujours visible |
| press_articles_requested | multiSelect | optionnel | toujours visible |
| simulation_calibration | group | optionnel | toujours visible |
| budget_meur | float | optionnel | toujours visible |
| delivery_deadline_iso | date | optionnel | toujours visible |

---

## 9. Notes d'implémentation

### 9.1 Côté projet Claude

Coller ce canevas en tant que **system prompt** dans un projet Claude. Quand l'utilisateur arrive avec une graine vague, Claude doit :

1. Lire le tronc commun §2 et poser les 5 questions une par une.
2. Détecter la valeur de `topic_type` et activer la branche §3 correspondante.
3. Suggérer des valeurs par défaut pour `framework_choice` selon §3.1.
4. Proposer un niveau d'enrichissement Kairos §4 selon le contexte.
5. Générer le Brief Preview §6.2 et valider avec l'utilisateur.
6. Coller le résultat final dans le format §7 prêt à soumettre à Bassira.

### 9.2 Côté questionnaire devis

Le formulaire `prospectives.ai-mpower.com/devis` doit :

1. Implémenter les triggers conditionnels du mapping §8 (Vue 3 reactive ou équivalent).
2. Afficher le Score Seed Quality §6.1 en temps réel à droite du formulaire.
3. Pré-remplir `framework_choice` selon §3.1 dès que `topic_type` est sélectionné.
4. Pré-cocher les sources Kairos par défaut §4.2 selon `topic_type`.
5. Bloquer la soumission tant que le tronc commun §2 + la branche §3 active sont incomplets.
6. Générer le Brief Preview §6.2 avant le bouton « Soumettre la graine à Bassira ».

### 9.3 Évolution du canevas

Ce canevas est **versionné** (v1.0 ici). Les ajouts futurs (nouveaux types de sujet, nouveaux frameworks, nouvelles sources Kairos) doivent passer par un PR sur ce fichier avec changelog explicite. Le numéro de version est exposé dans le devis pour traçabilité.

---

© 2026 AIMPOWER, canevas seed Bassira v1.0 du 18 mai 2026, livrable du goal L99.
