# Moat Hunt — Adhésion et confiance C-Level (Bassira)

**Date** : 2026-07-09 · **Méthode** : V2 falsifiée — 4 agents parallèles (industries
vitales / anciennes / performance / confiance), 23 candidates brutes, fusion des doublons
→ 17 effectives, **7 tuées (41 %)**, scoring 7 Powers via `moat_scorer.py`, **gate VALIDÉ
0 avertissement**. Sourcing : OpenSERP souverain moteur duck (ADR-012 — Google en CAPTCHA
comme anticipé, crawl4ai absent du serveur → lecture de pages via WebFetch en repli
déclaré).

## Question d'origine (Amine)

« Quels sont les angles morts ? Quels produits/services de la plateforme manquent pour une
adhésion rapide et parfaite ? »

## Jobs universels chassés (niveau 3)

1. **Faire confiance à un verdict produit par un système opaque** avant d'engager des
   ressources irréversibles.
2. **Convertir un sceptique de haut rang** par une première expérience à faible risque et
   haute révélation.
3. **Faire vivre le livrable d'expertise** dans l'organisation cliente après la livraison
   (anti rapport-qui-dort).
4. **Établir la crédibilité d'un simulateur SANS historique public de succès** (cold-start
   de la preuve — la contrainte ADR-002 : < 20 outcomes réels, aucun claim de calibration
   autorisé).

## Constats de falsification structurants (vérifiés le 2026-07-09)

- **Aaru** (aaru.com/products, lu intégralement) : produits Lumen/Seraph/Dynamo, AUCUN
  backtest public, AUCUN audit tiers, AUCUN pilote (« Get a demo » seul), AUCUN suivi
  post-livraison — analyses ponctuelles « before committing capital ». La couche de
  confiance est déléguée aux distributeurs Accenture/EY.
- **Artificial Societies** (societies.ai/ai-simulation-research, lu intégralement) :
  crédibilité fondée sur une publication académique (IC2S2 2024, British Journal of
  Psychology) + claims « 95 % distribution accuracy » NON transparents (ni protocole ni
  données publiés) ; le SOC 2 affiché couvre la SÉCURITÉ, pas la validité scientifique.
- **Le conseil bascule massivement vers l'outcome-based pricing** (McKinsey, Business
  Insider 2026-06) → tue toute prétention de nouveauté d'un paiement au résultat.
- **L'infrastructure d'horodatage inviolable de prédictions existe** (certifieddata.io,
  OriginStamp) mais AUCUN acteur du créneau ne la pratique.

## MOATS (3 — verdict FORTE, score 11/10/11)

| # | Mécanisme | Source | Power | Scores (N/F/M) | Pourquoi le temps joue pour nous |
|---|---|---|---|---|---|
| M1 | **Registre de vérification scellé** : chaque verdict horodaté à date certaine (hash, tiers d'horodatage) AVANT l'issue réelle + « QTG Bassira » publié (protocole de comparaison verdicts↔outcomes avec bandes de tolérance, ré-exécuté à chaque outcome) | Aviation 14 CFR Part 60 + NRC 10 CFR 55.46 + notariat (date certaine) | cornered_resource | 4/3/4 = 11 | L'historique scellé est irrecréable rétroactivement — chaque mois d'avance est un actif de preuve qu'aucun concurrent ne peut rattraper. Au 20e outcome, le claim de calibration devient IRRÉFUTABLE (pas juste autorisé). |
| M2 | **Corpus de micro-calibration MENA** : calibrer chaque comportement de persona au niveau micro contre données réelles MENA (études conso, terrain, HCP) + bande d'incertitude affichée sur tout résultat + croisement humain recommandé | NRC PRA (Final Policy Statement 1995) | cornered_resource | 4/2/4 = 10 | Répond frontalement au risque existentiel Bisbee 2024 (~48 % coefficients faux), AGGRAVÉ pour les populations MENA sous-représentées dans le training data. Simile est ancré US ; personne n'a de corpus MENA/darija. Chaque étude terrain ajoutée creuse l'écart. |
| M3 | **Surveillance des verdicts livrés** (CreditWatch) : chaque rapport porte un statut vivant (stable / sous surveillance / hypothèse invalidée), alerte quand le réel bouge sur une hypothèse-clé — signal détectable via Saqr, déjà dans l'écosystème | S&P Rating Outlook / CreditWatch | switching_costs | 4/3/4 = 11 | Convertit le one-shot en abonnement ; l'historique hypothèses×drift par client rend le départ coûteux (perdre la continuité de surveillance de SES décisions passées). Tout le secteur vend du ponctuel. |

## FEATURES (7 — verdict INTÉRESSANTE, backlog)

| Mécanisme | Source | Scores | Effort | Note |
|---|---|---|---|---|
| Attestation tierce de méthodologie Type I → Type II | SOC 2 AICPA + hallmarking orfèvres 1300 | 3/3/2 = 8 | M | Devient un moat UNIQUEMENT si co-émise en exclusivité avec une institution marocaine de référence. AS a un SOC 2 sécurité — le créneau « validité » est vide. |
| Preuve sur cas déjà tranché (AAR privé + chef-d'œuvre public) | US Army TC 25-20 + compagnonnage | 3/4/2 = 9 | S | Onboarding du sceptique : 1ʳᵉ simulation sur une décision DÉJÀ tranchée du client, angles morts révélés sans enjeu. Aaru l'a fait une fois en public (élection), jamais productisé. |
| Indice de convergence multi-runs × multi-signaux | Michelin + Associated Press | 3/4/2 = 9 | S | Les 3 moteurs existent déjà — exposer leur accord/désaccord comme qualificateur de verdict. |
| Impact Check 30/60/90 à propriétaire nommé | ProPublica + waqf mutawalli/nazir | 3/4/2 = 9 | S | Registre d'impact agrégé = futur argument commercial (« nos simulations ont changé X décisions »). |
| Opinion de gouvernance citable | Fairness opinions M&A | 3/4/2 = 9 | S | Le client achète aussi sa protection décisionnelle. Rémunération TOUJOURS découplée de la conclusion (leçon du biais documenté). Le secteur délègue cette couche aux Big4 — en MENA, l'intégrer nativement est un différenciateur. |
| Signature nominative engageante | Appointed Actuary NAIC | 3/5/1 = 9 | XS | Faisable cette semaine. Jamais « généré par IA » ni « l'équipe » : un nom qui endosse. |
| Decision-checklist rejouée à 3 temps | WHO Surgical Safety Checklist | 3/4/1 = 8 | S | Le livrable devient un rituel de comité, pas un PDF. |

## TUÉES (7/17 — 41 %)

| Candidate | Cause de mort |
|---|---|
| Muhtasib / hisba (supervision tierce continue) | Aucune autorité tierce n'existe à mandater ; coût disproportionné ; redondant avec l'attestation de méthodologie. |
| Ijaza / isnad (chaîne de provenance des personas) | Sans données réelles à la racine, la chaîne EXPOSE la faiblesse au lieu de la couvrir — Simile a fait de la provenance réelle son positionnement inverse. Ne devient viable qu'APRÈS le corpus M2. |
| Qirad / success fee (paiement conditionnel à la valeur) | Nouveauté nulle : le conseil adopte massivement l'outcome-based (Business Insider 2026-06) ; « valeur constatée » d'un rapport = critère subjectif ingameable contractuellement à cette échelle. |
| Previews Broadway (run à tarif réduit produit-non-fini) | Redondant avec le palier self-service existant (ADR-007/014) ; le cycle brouillon→final est une pratique standard du conseil. |
| Previs cinéma (« décider tôt et pas cher ») | C'est DÉJÀ le pitch du produit — aucun mécanisme nouveau, du vocabulaire marketing au mieux. |
| Auditions à l'aveugle (verdict sans contexte client) | Transposition floue : la simulation a BESOIN du contexte pour tourner ; la variante honnête (test d'ablation) est un outil interne, pas un mécanisme d'adhésion. |
| Déblocage progressif Grameen (montant suivant fixé par l'usage mesuré) | L'architecture double-canal existe déjà (ADR-007) ; le mécanisme résiduel est une règle de CRM, pas un produit. |

## Angles morts produit constatés en parallèle (hors chasse, preuves repo/prod)

1. **Fulfillment self-service inexistant après paiement Stripe** : le webhook enregistre
   `quote_ownership.status='paid'` (org fallback interne) et… rien d'autre. Pas de compte
   créé, pas d'accès, pas de kickoff automatisé. Le client paie 1 000-2 000 USD au pic de
   son engagement et retombe dans un circuit manuel invisible. C'est LE trou d'adhésion le
   plus immédiat (preuve : `backend/app/api/stripe_checkout.py`, flux vérifié ce jour).
2. **L'intake /devis ne capture aucun contexte de décision** (constat Amine du 2026-07-09,
   payload `q_f767321b` : message = libellé du sélecteur, role/industry/geo vides) — ni
   devis adaptatif ni pré-seed de simulation possibles. Chantier de structuration ouvert
   (parcours calibré Mom Test, voir discussion du jour).
3. **La contrainte ADR-002 est gérée par soustraction, pas par construction** : on a purgé
   le copy prédictif (US-201 ✓) mais RIEN ne construit la preuve en attendant les 20
   outcomes. M1/M2 sont la réponse par construction.
4. **Aucun produit post-livraison** : le rapport meurt à la livraison (M3 + Impact Check +
   checklist rejouée = la réponse). C'est aussi le canal de revenu récurrent manquant.

## Prochaines US suggérées (à arbitrer par Amine — non insérées dans le PRD)

- **US-220 (M1, M)** — Registre de vérification scellé : hash+horodatage de chaque verdict
  à la génération du rapport ; page publique « registre » ; protocole QTG v1 publié.
  AC : tout rapport généré a son empreinte scellée avant livraison ; le protocole de
  comparaison est public ; zéro claim de calibration tant que <20 outcomes.
- **US-221 (M3, M)** — Statut vivant des rapports : table hypothèses-clés par simulation,
  câblage signaux Saqr, statut stable/surveillance/invalidé visible client + alerte email.
- **US-222 (M2, L)** — Corpus de calibration MENA v0 : inventaire des sources licites
  (études publiques, partenariats), schéma de stockage, premier lot de micro-calibrations
  documentées avec bandes d'incertitude.
- **US-223 (features rapides, S)** — Pack crédibilité du rapport : signature nominative +
  indice de convergence + decision-checklist rejouée (3 features XS/S regroupées).

## Sources principales

- https://www.law.cornell.edu/cfr/text/10/55.46 · https://www.ecfr.gov/current/title-14/chapter-I/subchapter-D/part-60
- https://www.federalregister.gov/documents/1995/08/16/95-20237/use-of-probabilistic-risk-assessment-methods-in-nuclear-regulatory-activities-final-policy-statement
- https://www.who.int/docs/default-source/patient-safety/9789241598590-eng-checklist.pdf
- https://www.propublica.org/impact · https://www.ap.org/the-definitive-source/behind-the-news/when-is-it-ok-to-use-anonymous-sources
- https://www.thegoldsmiths.co.uk/hallmarking-stories/the-history-of-hallmarking · https://www.ijmar.org/v12n2/25-010.html
- https://grameenbank.org.bd/loan/basic-loan- · https://www.actuary.org/professionalism/us-qualification-standards
- https://www.wallstreetprep.com/knowledge/fairness-opinions-whats-dont-really-tell-much · https://secureframe.com/hub/soc-2/type-1-vs-type-2
- https://aaru.com/products · https://societies.ai/ai-simulation-research · https://certifieddata.io/use-cases/prediction-integrity
- https://arxiv.org/abs/2505.07850 (audit éthique de personas — état académique)
