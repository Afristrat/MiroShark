# Prompts d'exécution — Bassira V2

> Prompts EXACTS pour les IA exécutantes externes (Stitch, générateurs d'images, etc.).
> Règle : l'exécutant n'a accès à AUCUN document du projet — chaque prompt embarque tout
> le contexte. Un prompt qui contredit un document de fondation (app-spec, brand-brief,
> data-dictionary) est un bug de fondation : corriger le prompt, jamais improviser.
> Dérivés du backlog V2 (US-210, parking lot design system) et du brand-brief.

## EP-01 — Logo Bassira (remplace le requin MiroShark)

- **Outil/IA cible** : générateur d'images (aidesigner / Ideogram / designer humain) —
  itérations multiples attendues, choix final par Amine.
- **Périmètre** : produire le logo ; s'ARRÊTE là — ne décide ni la palette (imposée), ni
  le naming, ni les déclinaisons d'usage. Livrables : PNG fond transparent ≥ 1024×1024 +
  variante monochrome brun `#241915` + variante blanche pour fonds sombres.
- **Critères d'acceptation** : lisible à 24×24 px (watermark d'export de graphiques) ;
  aucune ressemblance avec le requin MiroShark ; fonctionne sur fond crème `#FAF7F2` ET
  sur photo ; pas de dégradés (impression PDF).
- **Intégration** : remplace `frontend/public/miroshark-nobg.png` (US-210) + branding PDF
  (`pdf_branding.logo_url`) ; validation par Amine avant tout déploiement.
- **Prompt exact** :

```text
Design a logo for "Bassira" (بصيرة — Arabic for "clairvoyance / inner sight"), a premium
B2B decision-intelligence SaaS for C-level executives and institutions in the MENA region.

Concept direction: an abstract eye, lens or aperture motif suggesting foresight and
clarity — NOT a literal eye with lashes, NOT mystical/esoteric imagery, NOT a shark or
any animal. Bauhaus / artisanal-luxury aesthetic: geometric, warm, confident, minimal.

Colors (strict): terracotta orange #FF8551 as the primary mark color, deep green #006D44
as optional accent, warm near-black #241915 for any text. Background: transparent.
The mark must also work in single-color #241915.

Typography if a wordmark is included: geometric sans-serif in the spirit of "Outfit",
lowercase or small-caps "bassira". Optionally pair with the Arabic بصيرة in a matching
weight (font spirit: "Tajawal") — Arabic must be typographically correct, right-to-left,
properly ligatured.

Constraints: flat design, no gradients, no drop shadows, legible at 24×24 px, balanced
silhouette usable as a watermark on charts. Deliver: main color version, monochrome
#241915 version, white version.
```

## EP-02 — Maquettes Stitch : unification Causse du cœur produit (Step 1→5)

- **Outil/IA cible** : Google Stitch (projet existant « Bassira global design system »,
  cf. mémoire poste bassira_stitch_designs).
- **Périmètre** : maquettes haute fidélité des 5 écrans du workflow simulation dans le
  design system Causse ; s'ARRÊTE à la maquette — n'invente aucune feature, ne modifie ni
  le parcours (7 écrans figés dans 01-app-spec) ni la palette ni les données affichées.
- **Critères d'acceptation** : les 5 écrans utilisent exclusivement la palette et les
  typos ci-dessous ; chaque écran garde TOUTES les fonctions de l'existant (aucune
  fonctionnalité maquettée en moins) ; version RTL fournie pour au moins l'écran Rapport.
- **Intégration** : référence visuelle pour le chantier parking-lot « unification --wi-* » ;
  export dans `stitch_bassira_global_design_system/` ; aucune implémentation sans story.
- **Prompt exact** :

```text
Redesign 5 existing screens of a B2B decision-simulation SaaS ("Bassira") to match its
commercial design system, called "Causse" — Bauhaus / artisanal luxury / terracotta.

Design system (strict, non negotiable):
- Background #FAF7F2 (warm cream), text #241915 (warm near-black)
- Primary accent #FF8551 (terracotta orange) for CTAs and active states
- Secondary #006D44 (deep green) for success/validation states
- Titles: "Outfit" font. Body: "Manrope". Numbers/IDs: "JetBrains Mono"
- Generous whitespace, 8px radius cards, flat surfaces, thin 1px borders, no glassmorphism,
  no neon, no dark mode

The 5 screens (keep every function visible in each, do not remove features):
1. GRAPH BUILD — document upload + knowledge-graph construction progress, entity count,
   validation CTA
2. ENVIRONMENT SETUP — auto-generated simulation config: scenario summary card, agent
   population size, platforms toggles (social feed / forum / prediction market), rounds
   count, Bull/Bear/Neutral scenario picker
3. SIMULATION RUN — hour-by-hour timeline of agent posts, live prediction-market price
   chart, "inject breaking news" (Director Mode) input, pause/fork controls
4. REPORT — long-form executive report with sections outline (left rail), inline charts,
   a mandatory "Method & limitations" callout box near the top (distinct cream card with
   #006D44 left border), export PDF button
5. INTERACTION — force-directed agent network graph, agent inspector side panel, chat
   with a selected agent

Audience: C-level executives and institutional analysts (MENA region). The tone is a
premium foresight consultancy, not a consumer app. Language of the mockups: French.
Also deliver screen 4 (REPORT) in an Arabic right-to-left variant (font: Tajawal).
```

## EP-03 — Maquette Stitch : page « Méthodologie » (remplace /calibration)

- **Outil/IA cible** : Google Stitch (même projet).
- **Périmètre** : maquette d'UNE page vitrine expliquant honnêtement la méthode et ses
  limites (support d'US-201/US-202) ; s'ARRÊTE à la maquette — le contenu scientifique
  exact (chiffres, références) sera injecté depuis les documents du projet, ne pas en
  inventer.
- **Critères d'acceptation** : aucune promesse de précision chiffrée inventée (pas de
  « 80 % accuracy ») ; une section « Ce que Bassira ne fait pas » visuellement assumée ;
  palette/typos Causse strictes.
- **Intégration** : remplace la page /calibration actuelle (claim Brier retiré) ; le copy
  final est écrit en interne depuis ADR-002, la maquette ne porte que du placeholder FR.
- **Prompt exact** :

```text
Design a single marketing/credibility page called "Méthodologie" for Bassira, a B2B
decision-simulation SaaS (design system: cream #FAF7F2 background, #241915 text,
terracotta #FF8551 accents, green #006D44 validation accents, Outfit titles, Manrope
body — Bauhaus / artisanal luxury, French language, premium institutional tone).

Page goal: convince a skeptical C-level buyer that the product is honest about what
synthetic multi-agent simulation can and cannot do. Structure:
1. Hero: "Comment fonctionne une simulation Bassira" + one abstract diagram
   (document → knowledge graph → hundreds of AI personas → simulated debate + prediction
   market → executive report)
2. Section "Ce que vous obtenez": stress-test of a decision, mapping of objections,
   polarization dynamics, scenario forks — 4 cards
3. Section "Ce que Bassira ne fait PAS" (equally prominent, deep green border cards):
   no prediction of real-world outcomes, no replacement for field research, results vary
   with the underlying AI model — 3 cards with placeholder text
4. Section "Ancrage sur données réelles (optionnel)": explain that simulations can be
   calibrated with real signals and imported survey data — 1 wide card
5. Footer CTA: "Stress-testez votre prochaine décision" → button to /devis

Use placeholder French text (lorem-style but plausible), NO invented accuracy numbers,
NO percentage claims anywhere on the page.
```
