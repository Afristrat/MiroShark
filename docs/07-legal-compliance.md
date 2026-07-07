# Legal & Compliance — Bassira V2

> Généré le 2026-07-07. Les textes cités ci-dessous marqués « vérifié » ont été confrontés
> à une source lue ce jour (recherche du 2026-07-07, URLs en table). Ce document ne
> remplace pas un avis d'avocat — deux points (AGPL, formalités CNDP) le requièrent.

## Synthèse

Marchés : **Maroc (principal) + institutions internationales (UE possible)** ·
Juridictions données perso : loi 09-08 (CNDP) + RGPD si prospects/destinataires UE ·
Régime appliqué : **max(exigences)** (règle du poste). PII réellement traitées (cf.
`02-data-dictionary.md`) : emails clients/prospects/destinataires, IP, user_agent,
géolocalisation pays des téléchargements, identités auth.users.

## Obligations

| Obligation | Texte/source (URL, consultée le) | Statut | Coût estimé |
|---|---|---|---|
| **Dossier licence du fork** — domaine exclusif d'Amine (ADR-003). Faits au dossier : le fichier LICENSE du repo contient le texte AGPL-3.0 ; repo = fork Afristrat/MiroShark ← aaronjmars/miroshark. Position d'Amine (2026-07-07) : MiroShark est basé sur une licence MiroFish dont aaronjmars s'est octroyé un droit qu'il n'avait pas | LICENSE:1-12 ; AGENTS.md:9-11 ; vérification factuelle de la lignée MiroFish en cours (agent upstream-mirofish) | **Instruit par Amine** — l'IA collecte les faits et les remet (US-200) ; aucune qualification ni prescription de sa part | — |
| **EU AI Act Art. 50 — transparence contenu synthétique** : marquage machine-readable + information des personnes ; applicable aux fournisseurs dès le **2026-08-02** | https://artificialintelligenceact.eu/article/50/ (2026-07-07, vérifié en vigueur — lignes directrices Commission du 2026-05-08) ; amende max 15 M€ / 3 % CA | **Dette assumée à J-26** → US-202 (encart méthode + métadonnées PDF). Déclencheur déjà atteint : tout prospect UE | 2-4 j de dev |
| **Loi 09-08 (Maroc) — traitement de données perso** : déclaration/autorisation CNDP selon les traitements, information des personnes, sécurité | https://avocat-jawhari.com/2026/03/25/intelligence-artificielle-maroc-donnees-personnelles-risques-cndp/ (2026-07-07 — loi en vigueur, héritée pré-RGPD, modernisation non votée à ce jour) | **Dette assumée** : formalités CNDP (F211/F112) non déposées. Déclencheur : premier client marocain signé → **délégation skill `rgpd-bounty-hunter`** (audit + génération formulaires) | 1-2 j via la skill |
| **RGPD (si prospects/destinataires UE)** : base légale prospection, registre Art. 30, politique de confidentialité, DPA avec sous-traitants | Régime connu du poste ; audit à la charge de `rgpd-bounty-hunter` | **Dette assumée**. Déclencheur : campagne Apollo vers cibles UE (les séquences existent déjà → déclencheur PROCHE) | 2-3 j via la skill |
| **CGU/CGV + SLA B2B** : obligatoires dès l'encaissement (devis payés, futur Stripe) | Obligation générale contractuelle B2B | **Dette assumée** — aucun document contractuel dans le repo. Déclencheur : AVANT le premier paiement Stripe (US-205) ; le canal devis actuel repose sur le contrat signé au cas par cas `[HYPOTHÈSE À VALIDER : un modèle de contrat devis existe-t-il hors repo ?]` | 1-2 j + relecture avocat |
| **PCI-DSS via Stripe** : responsabilité partagée du PSP | Doc Stripe à lire à l'exécution d'US-205 | Non applicable tant que Stripe non câblé ; SAQ-A attendu (Checkout hébergé) | Inclus US-205 |
| **Marque « Bassira »** : disponibilité OMPIC (Maroc) / EUIPO (UE), domaine, handles | Non recherché ce jour | `[HYPOTHÈSE À VALIDER : recherche OMPIC/EUIPO à faire avant tout investissement marketing lourd]` | 0,5 j + taxes dépôt |
| **Licences des dépendances** (PI entrante) : scan complet npm + pip, signaler copyleft | À exécuter (`license-checker`, `pip-licenses`) | **Dette assumée**. Déclencheur : US-200 (le scan documente aussi l'exposition AGPL) → résultat en ADR | 0,5 j |
| **Responsabilité sur le contenu simulé** : un rapport « stress-test » qui influence une décision réelle | Analyse interne (contre-argument 2.4 sourcé Bisbee 2024) | Mitigé par US-201/US-202 (repositionnement + encart limites + disclaimer trilingue déjà en défaut SQL `pdf_branding.disclaimer_text` : « Confidentiel · Probabiliste · Usage interne ») ; clause de non-responsabilité à intégrer aux CGV | Inclus CGV |

## Dettes légales assumées — vue d'ordre d'exécution

1. **Dossier licence (US-200)** — instruit par Amine ; l'IA remet les faits collectés (lignée MiroFish, textes LICENSE).
2. **AI Act Art. 50 (US-202)** — échéance dure 2026-08-02.
3. **CGU/CGV** — avant le premier paiement Stripe.
4. **CNDP + RGPD** — au premier client signé / première campagne UE → skill `rgpd-bounty-hunter` (fait autorité, ne pas dupliquer ici).
5. **Marque OMPIC/EUIPO + scan licences** — housekeeping du Bloc A.

## Audit complet

→ skill `rgpd-bounty-hunter` (mode audit + remédiation) — déclencheur : signature du
premier client OU lancement de la première campagne sortante vers l'UE, selon le premier
des deux. Ce document identifie QUE c'est requis ; la skill produit les artefacts.
