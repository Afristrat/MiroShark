# Bassira — Design Prompts exhaustifs

>   Un prompt par page/feature. Palette Causse calibrée MENA + Europe.  
>   Usage : Stitch (Google), Canva AI, Figma AI, v0, Lovable, ou prompt direct Claude/GPT-4o.

***

## PALETTE CAUSSE MAÎTRESSE — Référence globale

```
BASSIRA CAUSSE MASTER PALETTE

Cultural calibration: Dual MENA (Morocco, GCC) + European (France, UK) audience.
All prompts derive from this palette. Never deviate without explicit reason.

PRIMARY ACTIONS & CONFIDENCE
  #FF8551  Warm Orange
  MENA:    Sun, generosity, celebration, decisive energy — universally positive
  Europe:  Innovation, approachability — avoid overuse (France: "low-cost" risk)
  Trigger: Action readiness, optimism, forward motion
  Use:     CTAs, highlights, active states, key numbers

TRUST & METHODOLOGICAL AUTHORITY  
  #006D44  Deep Mint-Green
  MENA:    Islam, paradise, growth, trustworthiness — highest positive charge
  Europe:  Sustainability, reliability, safety — strong positive signal
  Trigger: Confidence, methodological trust, calm authority
  Use:     Success states, validation badges, trust signals, verified data

PREMIUM SURFACE & CLARITY
  #FAF7F2  Cream Off-White
  MENA:    Marble, parchment, manuscript — evokes refinement and wisdom
  Europe:  Artisanal luxury, Bauhaus minimalism, editorial quality
  Trigger: Mental space, premium feel, reduced cognitive load
  Use:     Primary background, breathing room, hero sections

AUTHORITY WITHOUT COLDNESS
  #241915  Warm Charcoal-Brown
  MENA:    Earth, roots, ink — resonates with traditional authority + modernity
  Europe:  Serious professionalism — warmer than pure black, more trustworthy
  Trigger: Credibility, weight, permanence
  Use:     Primary text, headlines, borders of importance

URGENCY WITHOUT AGGRESSION
  #A13F0F  Deep Terracotta
  MENA:    Tadelakt, clay, desert — deeply authentic, evokes Moroccan craft luxury
  Europe:  Warmth, artisanal quality — bridges premium and approachable
  Trigger: Decisive action, scarcity, importance without panic
  Use:     Primary CTAs, pricing emphasis, featured badges

FORBIDDEN COMBINATIONS (cultural misfires):
  ✗ Red (#FF4444) as primary — aggression in MENA executive contexts
  ✗ Pure black backgrounds — funeral associations in some MENA cultures
  ✗ Yellow as primary — cheapness signal in GCC premium contexts
  ✗ High-saturation blue as dominant — too "tech startup generic"
```

***

## TYPOGRAPHY MASTER REFERENCE

```
OUTFIT (headings, display, numbers)
  Role: Authority + geometric friendliness. The "thinking" voice.
  Weights used: 400 (body display), 500 (subheadings), 600 (H1-H2), 700 (hero only)
  Letter-spacing: H1 -0.02em, H2 -0.01em, body 0
  Never use below 14px.

MANROPE (body, UI labels, descriptions)
  Role: High-legibility for dense data and long-form content.
  Weights used: 400 (body), 500 (labels, meta), 600 (strong emphasis)
  Line-height: 1.6 for body, 1.2 for labels
  Never use above 24px for display.

TAJAWAL (Arabic content only)
  Role: Premium Arabic type that pairs with Outfit/Manrope visually.
  Formality: Use Modern Standard Arabic (fusha) for B2B executive contexts.
  Never use Darija (dialectal) in UI strings — always fusha for credibility.
  Direction: RTL, logical CSS properties, no mirroring of icons except arrows.

JETBRAINS MONO (code, IDs, data values, terminal output)
  Role: Technical credibility, precision signals.
  Use: Simulation IDs, API keys, probability numbers, agent logs.
  Never use for prose or marketing copy.
```

***

# PAGES EXISTANTES

***

## 1. Home.vue — Page d'accueil / Création de simulation

**Audience :** Prospect découvrant Bassira + Tier 2 Analyst en session active  
**Funnel :** Discovery → Activation  
**Objectif cognitif :** Déclencher la curiosité + supprimer l'anxiété technique → *"Je comprends ce que c'est et je veux essayer maintenant"*

```
Redesign the Bassira Home page — the primary entry point for a B2B SaaS 
strategic forecasting platform targeting C-Level executives in MENA + Europe.

CONTEXT:
This page has two simultaneous jobs:
1. Convert cold prospects (they just landed from LinkedIn or Google)
2. Enable returning analysts to create a new simulation immediately
Both audiences must be served without confusion.

AUDIENCE:
Primary: Strategy analyst, age 30–45, Morocco/GCC/France, overwhelmed by 
decision-making without structured forecasting tools. Their pain: "I spend 
weeks building scenarios in Excel that no one trusts."
Secondary: CEO/CFO, age 40–58, scanning in 8 seconds whether this is 
credible enough to forward to their team.

COGNITIVE OBJECTIVE:
Trigger "this is exactly what I was missing" within 3 seconds of landing.
Reduce technical anxiety: the platform looks approachable, not intimidating.
Create progressive disclosure: simple surface, powerful depth.

PALETTE CAUSSE APPLICATION:
  Background: #FAF7F2 cream — premium editorial quality, not a "startup"
  Hero headline: #241915 warm charcoal — authority, weight
  Primary CTA: #A13F0F terracotta — decisive action, MENA authenticity
  Hover CTA: #FF8551 orange — warmth on interaction
  Trust signals (Brier score, n_simulations): #006D44 mint-green — 
    methodological credibility, Islamic cultural positive charge
  Section dividers: cream to white gradient — depth without borders

TYPOGRAPHY:
  Hero H1: Outfit 600, 48–64px (clamp), letter-spacing -0.02em, #241915
  Hero subtext: Manrope 400, 18–20px, #57423A (warm muted charcoal)
  Section labels ("01 / Graines de réalité"): JetBrains Mono 500, 12px, 
    #A13F0F — technical precision marker
  CTA text: Outfit 600, 16px, on terracotta background
  Arabic hero (lang=ar): Tajawal 500, same sizes, right-aligned

LAYOUT:
  Sticky header: Bassira wordmark left, Language switcher right (FR/AR/EN pill)
  Hero: Full-width cream, centered, max-width 720px. 
    Eyebrow pill: "بصيرة · Strategic Foresight" — orange pill, Outfit 500
    H1: 2–3 lines, bold claim about foresight/decision-making
    Subtext: 1 sentence, Manrope, warm muted tone
    Primary CTA: terracotta pill button "Lancer une simulation →"
    Trust strip below CTA: Brier 0.18 (green) · N simulations (orange) · 
      ISO-calibrated (green checkmark)
  
  Console section (workflow creation):
    4 numbered steps with pill labels (#A13F0F mono)
    Step cards: white surface, 24px radius, ambient shadow, 
      left orange border on active step
    File upload zone: dashed cream border, hover → orange dashed
    URL import: clean input, focus ring 2px #FF8551
    "Posez simplement" ask input: slightly elevated card, 
      mint-green accent for the AI indication
  
  Template Gallery: 
    3-column grid on desktop, cards with terracotta category badges
    Hover: lift 4px + orange shadow

STATES:
  Loading: cream skeleton with subtle shimmer (warm-tinted, not cold grey)
  Empty: illustrated empty state with Arabic calligraphy accent pattern
  Error: #A13F0F border, warm error messaging, never cold red

DARK MODE:
  Background: #0f1117 (near-black, not pure black — cultural sensitivity)
  Cards: #1a1d27
  Orange stays #FF8551 (slightly brightened)
  Green stays #006D44 (lightened to #7FD8A6 for legibility)
  Text: #e8eaf0

RTL (lang=ar):
  All padding/margin via logical CSS properties
  Arrow icons flip (→ becomes ←)
  Tajawal replaces Outfit/Manrope
  Number formatting: Arabic-Indic numerals for cultural resonance in GCC
```

***

## 2. OffersView.vue — Page /offres · Pricing packages

**Audience :** Prospect chaud → Tier 1 CEO/CFO  
**Funnel :** Consideration → Decision  
**Objectif cognitif :** Justifier le premium + créer l'envie → *"Ce prix est juste parce que la valeur est évidente"*

```
Design the Bassira /offres pricing page for a premium B2B strategic 
simulation platform. 10 packages across 5 tiers. Target: C-Level 
executives deciding whether to purchase or request a demo.

CONTEXT:
Prices range from 8,000 MAD (Entry) to custom enterprise. The page must 
overcome the "why not just use McKinsey" objection. The design must signal 
premium without being cold, and accessible without being cheap.

AUDIENCE:
CEO/CFO Morocco/GCC, age 40–58. Pain: "Every consultant gives me a 
different answer. I need a system, not another opinion."
Also CFO concern: "What exactly am I paying for?"

COGNITIVE OBJECTIVE:
Anchor high — make the mid-tier feel like the obvious rational choice.
Use the "featured center" technique: middle tier scale 1.04, orange border.
Reduce decision anxiety: clear feature comparison, no hidden costs.

PALETTE CAUSSE:
  Page background: #FAF7F2 — editorial quality, not a marketplace
  Featured card border: #FF8551 orange — premium signal, sun energy
  Featured card badge "Le plus choisi": #A13F0F terracotta pill
  Trust icons (✓ included): #006D44 mint — reliability, methodological trust
  Price numbers: Outfit 700, #241915 — weight and authority
  Currency toggle (MAD/USD): #FF8551 active, cream inactive — 
    MAD first (MENA cultural priority — local currency = local credibility)
  Tier filter chips: terracotta active, cream/charcoal inactive
  CTA "Demander un devis": #A13F0F bg, #FAF7F2 text — decisive but warm

TYPOGRAPHY:
  Section headline: Outfit 600, 36px, "Nos formules", letter-spacing -0.01em
  Package name: Outfit 600, 22px, #241915
  Price: Outfit 700, 48px, #241915 + Manrope 400 14px "/simulation" muted
  Feature list: Manrope 400, 15px, #57423A
  Badge text: Outfit 600, 12px, uppercase, letter-spacing 0.04em

LAYOUT:
  Filter chips row: all 5 tier names as pills, scrollable on mobile
  Billing toggle: "Standard / Flexible" — pill toggle, orange active state
  Carousel: 3 visible cards, arrow navigation, dot pagination
  Featured card: scale(1.04), orange glow shadow, "Featured" badge top-right
  FAQ accordion: 4 questions, smooth expand, orange chevron active
  Footer CTA band: "Besoin d'une formule sur mesure ?" — terracotta bg, 
    cream text, mailto CTA

DARK MODE:
  Cards: #1a1d27 surface, #FF8551 border for featured
  Price numbers stay #e8eaf0 (legibility priority)
  
RTL: Price display right-to-left, MAD/درهم label in Arabic
```

***

## 3. CalibrationView.vue — Page /calibration · Track record

**Audience :** Tier 1 CEO + Tier 3 Skeptic (CTO, Risk Officer)  
**Funnel :** Consideration → Trust  
**Objectif cognitif :** Construire la confiance méthodologique → *"Ces gens savent mesurer leur propre performance. C'est rare."*

```
Design the Bassira /calibration public page. This is the methodological 
credibility page — the one a skeptical CTO or Risk Officer reads before 
approving the purchase. It must feel like a scientific publication, 
not a marketing page.

CONTEXT:
Displays Brier score (0.18 = excellent, 0 = perfect, 1 = random), 
calibration scatter plot, and breakdown of predictions made vs outcomes.
Key differentiator: Bassira publicly tracks its own accuracy. 
This is rare in the consulting/forecasting industry.

AUDIENCE:
Tier 3: CTO, Risk Officer, General Counsel — age 38–55, technically 
sophisticated, resistant to vendor claims. Pain: "Every AI vendor claims 
accuracy. None of them measure it properly."

COGNITIVE OBJECTIVE:
Trigger methodological respect. The page must feel like a Nature paper, 
not a SaaS dashboard. Data density is a trust signal here.
No animations on the data — it must feel static, measured, certain.

PALETTE CAUSSE:
  Background: #FAF7F2 — academic paper quality, not dashboard blue
  Hero Brier score: Outfit 700, 80px, #006D44 mint — 
    Green = methodological trust, Islamic cultural: "this is true and good"
  Delta chip "+0.02 vs. last quarter": mint-green pill — improvement signal
  Stats cards: white surface, 24px radius, ambient shadow — 
    lifted data, clean reading
  "Called it" stat: #006D44 — success, verified
  "Partial" stat: #FF8551 — acceptable, still honest
  "Wrong" stat: #A13F0F terracotta — honest accountability (not red/alarm)
  Scatter plot dots: mint-green (accurate) + orange (overconfident) + 
    terracotta (underconfident) — warm palette even for error states
  Diagonal "perfect calibration" line: #241915 dashed — authority reference
  Evaluables inbox badge "Pending": #FF8551 pill
  Admin "Mark outcome" button: #A13F0F — restricted action, deliberate

TYPOGRAPHY:
  Brier score: Outfit 700, 80–96px (the visual anchor of the page)
  Score label "Brier Score": Manrope 500, 13px, uppercase, muted, above
  Stats numbers: Outfit 600, 36px
  Stats labels: Manrope 400, 13px, #57423A
  Plot axis labels: JetBrains Mono 400, 11px, muted — technical precision
  How-it-works section: Manrope 400, 16px, generous line-height 1.7

LAYOUT:
  Hero: full-width cream band, centered score + delta chip
  Stats strip: 4 equal cards in a row, mint/orange/terracotta accents
  Plot card: white 24px radius, full width. Tooltip: orange pill on hover.
  "Méthodologie" section: academic prose, 2-column desktop
  Evaluables inbox: filterable table (pending / evaluated / all)
  Admin panel: revealed only with valid BASSIRA_ADMIN_TOKEN

DARK MODE:
  Background: #0f1117 — near-black, academic evening reading
  Brier score: stays #7FD8A6 (lightened mint for contrast)
  Plot background: #1a1d27 card
```

***

## 4. QuoteView.vue — Page /devis · Formulaire demande

**Audience :** Prospect chaud (a vu les offres, veut aller plus loin)  
**Funnel :** Decision → Conversion  
**Objectif cognitif :** Réduire la friction → *"C'est simple, rapide, et je ne m'engage à rien"*

```
Design the Bassira /devis multi-step quote request form (3 steps).
A warm prospect who just came from /offres. They need reassurance, 
not pressure. Make the form feel like a conversation, not an interrogation.

AUDIENCE:
Strategy Director or Chief of Staff, age 32–48, Morocco/France.
Pain: "Every time I fill a contact form I get called 3 times by a sales rep."
Need: Confidence that this is a curated, consultative process.

COGNITIVE OBJECTIVE:
"This team is serious and respectful of my time."
Reduce form abandonment: progress visibility, no surprise fields.
Trust signals must be visible at every step.

PALETTE CAUSSE:
  Page background: #FAF7F2 — calm, premium, not clinical
  Form card: pure white, 24px radius, ambient shadow — lifted, focused
  Stepper active circle: #A13F0F terracotta — deliberate step progress
  Stepper done circle: #006D44 mint checkmark — completion, trust
  Stepper inactive: #DEC0B6 (warm outline-variant) — path ahead, not greyed
  Input focus ring: 2px #FF8551 orange — active, warm engagement
  CTA "Suivant →": #A13F0F bg + #FAF7F2 text — decisive but not aggressive
  Trust banner: cream bg, #006D44 verified icon — "Your data is safe"
  Radio option selected: #FF8551 left border + cream bg — selection warmth

TYPOGRAPHY:
  Step title: Outfit 600, 24px
  Field labels: Manrope 600, 14px, #241915
  Input text: Manrope 400, 15px
  Helper text: Manrope 400, 13px, #8A7269 (warm muted)
  Trust banner text: Manrope 500, 13px, #006D44

LAYOUT:
  Centered card, max-width 640px, min-height 70vh
  Trust banner: top of form, icon + one reassuring sentence
  Stepper: 3 circles + connecting line, above form
  Step 1: 3 radio option cards (situation type)
  Step 2: 4 fields (name, email, company, role) + deadline select + consent
  Step 3: success/error state
  Back button: ghost style, left-aligned, never disabled

SUCCESS STATE:
  Mint-green checkmark icon (large, 64px)
  "Votre demande a été transmise" — Outfit 600, 24px
  Expected response time: Manrope 400, 15px, warm muted
  "En attendant, explorez nos simulations →" CTA — ghost orange

RTL: Form fields remain LTR for email/company (mixed content rule)
     Step labels switch to Arabic, right-to-left stepper direction
```

***

## 5. SimulationView.vue — Vue simulation /simulation/:id

**Audience :** Tier 2 Analyst (opérateur principal)  
**Funnel :** Activation → Retention  
**Objectif cognitif :** Sentiment de contrôle + puissance → *"Je maîtrise ce que je fais, tout est à portée"*

```
Design the Bassira main simulation view — a split-panel interface 
(graph left, agent setup right) for a strategic forecasting platform.
This is the "cockpit" view. The analyst spends 30–90 minutes here.

AUDIENCE:
Head of Strategy or Senior Analyst, age 30–45. Pain: "Complex tools 
make me feel like I need training to use them. I want power AND simplicity."

COGNITIVE OBJECTIVE:
Flow state — the user must feel in control, not lost.
Dense information without cognitive overload.
Every action must have immediate visual feedback.

PALETTE CAUSSE:
  App shell: #0f1117 dark (default — analysts prefer dark for focus sessions)
  Left panel (graph): #1a1d27 surface — deep focus environment
  Right panel (agent config): #22263a slightly lighter — operational area
  Graph nodes: orange for active agents, mint for confirmed, 
    terracotta for flagged, charcoal for dormant
  Graph edges: #3a3f5c (dark border-strong) — subtle connections
  Active step indicator: #FF8551 orange left border — "where you are"
  Phase progress: mint-green filled dots — completed phases
  Admin actions (add agent, mark outcome): #A13F0F terracotta — restricted
  Header brand: "BASSIRA" Outfit 600, 14px, cream — present but not dominant
  TrendingTopics toggle button: cream pill, bottom-right — discoverable
  
TYPOGRAPHY:
  Panel section headers: Outfit 600, 13px, uppercase, #FF8551 orange
  Agent names: Manrope 600, 15px, cream
  Log output: JetBrains Mono 400, 12px, #b0b5c8 — terminal feel
  Status chips: Manrope 600, 11px, uppercase, colored by status
  Phase labels: Outfit 500, 12px, muted cream

LAYOUT:
  Full viewport, no scroll — contained experience
  Resizable split panels (drag divider)
  Left panel: GraphPanel with D3 force graph
  Right panel: Step2EnvSetup — agent list, config, add agent button
  Header: sticky, minimal — brand + view switcher + simulation ID (mono)
  TrendingTopics: fixed bottom-right toggle pill → expands to drawer
  Empty graph recovery panel: centered card, 3 suggested actions, 
    orange CTA "Ajouter des entités"

STATES:
  Graph loading: orange pulsing nodes skeleton
  Graph empty: illustrated empty state, recovery panel
  Agent adding: optimistic UI — agent appears immediately, then confirms
  Error: toast notification, warm terracotta, never blocking modal

DARK MODE ONLY:
  This view is dark-mode-first. Light mode is a secondary concern.
  Reason: analysts work in low-light environments during decision sessions.
```

***

## 6. SimulationRunView.vue — Exécution simulation live

**Audience :** Tier 2 Analyst  
**Funnel :** Activation  
**Objectif cognitif :** Anticipation + suivi → *"Je vois ça se construire en temps réel"*

```
Design the Bassira simulation execution view — the live run dashboard
where the analyst watches the simulation unfold round by round.

CONTEXT:
Agents interact in real-time. Each round produces posts, belief shifts,
influence scores. The analyst can inject "director events" to steer 
the simulation. This is the most technically impressive view.

AUDIENCE:
Senior Analyst running a Crisis Drill or Policy Brief stress-test.
Need: transparency into what the AI is doing + ability to intervene.

COGNITIVE OBJECTIVE:
Build excitement and trust simultaneously. "This is real intelligence 
at work, and I can control it." 
Avoid the "black box" feeling — every agent action must be traceable.

PALETTE CAUSSE:
  Background: #0f1117 — deep focus, cinematic quality
  Round counter: Outfit 700, 64px, #FF8551 — the heartbeat of the simulation
  Agent activity feed: cards, #1a1d27 surface, left border color by stance
    Bull/Bullish: #FF8551 orange
    Bear/Bearish: #A13F0F terracotta  
    Neutral: #8A7269 warm outline
    Crisis Amplifier: #FF8551 orange
    Crisis Attenuator: #006D44 mint
  Belief drift chart: orange line (main), mint reference, cream grid
  Progress bar (rounds): orange fill on dark track
  "Director event" inject button: #A13F0F with flash animation on click
  Stop simulation: ghost button, terracotta border — serious but not alarming
  Phase complete toast: mint-green, bottom-right, 3s auto-dismiss

TYPOGRAPHY:
  Round counter: Outfit 700, 64px
  Agent post text: Manrope 400, 14px, #b0b5c8
  Agent name in feed: Manrope 600, 13px, colored by stance
  Event injection label: Outfit 600, 12px, uppercase, terracotta
  Log console: JetBrains Mono 400, 11px, #8b90a0

LAYOUT:
  Split: activity feed (60%) + charts (40%)
  Feed: reverse chronological, smooth scroll, agent avatar circles
  Charts: BeliefDriftChart + InfluenceLeaderboard stacked
  Director event panel: slide-in from right on trigger
  Progress indicator: top bar, thin orange fill

ANIMATION RULES:
  New agent post: fade-in from bottom, 200ms ease-out
  Round transition: subtle pulse on round counter
  Belief shift: chart line updates with 300ms transition
  No heavy animations — this is a professional tool, not a game
```

***

## 7. ReportView.vue — Rapport final simulation

**Audience :** Tier 1 CEO/CFO (le rapport est présenté en board)  
**Funnel :** Retention → Expansion  
**Objectif cognitif :** Clarté + autorité → *"Je peux présenter ça en comité exécutif demain matin"*

```
Design the Bassira simulation report view — the final deliverable 
that a CEO will present to their board or executive committee.
This is the most important page for renewal and expansion revenue.

CONTEXT:
Contains: executive summary, key findings, agent behavior analysis,
demographic breakdown, belief drift over time, counterfactual scenarios,
export to PDF button. Must feel like a McKinsey deliverable, not a dashboard.

AUDIENCE:
CEO/CFO/Strategy Director, age 40–58. Will screenshot or print this page.
Pain: "The output of AI tools looks too technical to share with my board."

COGNITIVE OBJECTIVE:
"Board-ready in one click." Professional gravitas. 
The report must look expensive — as if a senior consultant produced it.

PALETTE CAUSSE:
  Page background: #FAF7F2 — premium paper quality, print-ready
  Section headers: #A13F0F terracotta — authoritative section markers
  Key insight callout boxes: cream bg + left border #FF8551 orange
  "Critical finding" highlight: light terracotta bg (#FFE8DD) + 
    #A13F0F text — draws the executive eye without alarming
  Charts: brand palette (orange dominant, mint accent, terracotta thirds)
  Export PDF button: #241915 bg + #FAF7F2 text — premium, serious action
  Simulation metadata (ID, date, n_rounds): JetBrains Mono, muted

TYPOGRAPHY:
  Report title: Outfit 600, 36px, #241915
  Section headers: Outfit 600, 20px, #A13F0F, uppercase, letter-spacing 0.04em
  Body text (findings): Manrope 400, 15px, #241915, line-height 1.7
  Key metric callouts: Outfit 700, 48px, color by type
  Chart labels: Manrope 500, 12px
  Footer/metadata: JetBrains Mono 400, 11px, muted

LAYOUT:
  Max-width 1000px, centered — magazine layout, not full-bleed dashboard
  Executive summary: first section, highlighted card, 3 key bullets
  Section order: Context → Key Findings → Agent Dynamics → 
    Demographics → Belief Drift → Counterfactuals → Methodology
  Each section: full-width card, white, 24px radius, ambient shadow
  Charts: always within cards, never full-bleed
  Export toolbar: sticky, top of page, PDF + Share + Copy link
  Watermark: "BASSIRA · بصيرة" very subtle, cream-on-cream, print version only

PRINT STYLES:
  Remove navigation, shadows, sticky elements
  Expand all accordions
  Force cream background (even if dark mode is active)
  Show BASSIRA logo + simulation date in print header
```

***

## 8. ExploreView.vue — Galerie /explore · Simulations publiques

**Audience :** Public / Prospect découvrant la plateforme  
**Funnel :** Discovery → Social proof  
**Objectif cognitif :** Social proof + curiosité → *"D'autres décideurs utilisent ça sur des sujets réels"*

```
Design the Bassira /explore gallery — a public showcase of past 
simulations (anonymized). The "portfolio" of the platform.

CONTEXT:
Each card shows: simulation title, category, n_rounds, n_agents,
key finding excerpt, Brier score if available.
Purpose: convince a skeptical prospect that real decisions are being 
stress-tested with this platform.

AUDIENCE:
Cold prospect referred by a colleague or LinkedIn post.
Pain: "Show me real examples, not demo data."

COGNITIVE OBJECTIVE:
Create "fear of missing out" — other decision-makers are already using 
this. I'm behind if I don't. Show variety of use cases.

PALETTE CAUSSE:
  Page bg: #FAF7F2 — museum/gallery quality
  Category badges: colored by type
    Crisis: #A13F0F terracotta
    Market: #FF8551 orange
    Policy: #006D44 mint
    Decision: #241915 charcoal (inverted, cream text)
  Card hover: lift 6px + warm orange shadow
  Featured card: full-width banner, orange left border, slight cream tint
  Search/filter bar: white surface, orange focus ring
  "View simulation" CTA: ghost button, terracotta border → fill on hover

LAYOUT:
  Hero: short — "Simulations en cours et passées" + search bar
  Filter row: category chips + sort (recent / most agents / Brier score)
  Grid: 3 columns desktop, 2 tablet, 1 mobile
  Card anatomy: badge top-left + title + excerpt + 
    3 micro-stats (agents, rounds, Brier) + CTA
  Empty state: "Aucune simulation publique pour ce filtre" — 
    illustrated, suggest removing filter

DARK MODE:
  Cards: #1a1d27 surface, category badges keep their colors
  Search bar: #22263a
```

***

## 9. MainView.vue — Vue principale multi-modes

**Audience :** Tier 2 Analyst (utilisateur avancé)  
**Funnel :** Retention  
**Objectif cognitif :** Puissance + efficacité → *"Tout est là, rien ne me manque"*

```
Design the Bassira MainView — the advanced multi-panel simulation 
management interface for power users. Contains graph panel, multiple 
step panels, view switcher, and simulation controls.

AUDIENCE:
Senior Analyst who runs 5+ simulations per month.
Need: keyboard shortcuts, dense information, zero redundancy.

COGNITIVE OBJECTIVE:
Flow state. Information density as a trust signal — this is a 
professional tool, not a simplified consumer app.

PALETTE CAUSSE:
  Shell: #0f1117 dark default — professional focus environment
  View switcher tabs: orange active, cream/charcoal inactive
  Panel borders: #2e3248 subtle — separation without weight
  Action buttons: categorized by consequence
    Constructive: orange
    Confirmatory: mint-green
    Destructive: terracotta (not red — cultural sensitivity)
  Loading states: warm skeleton (tinted, not cold grey)
  Keyboard shortcut labels: JetBrains Mono, muted cream

LAYOUT:
  Resizable panels — horizontal drag divider
  View switcher: icon + label tabs in header
  Dense header: simulation title + ID + status chip + action menu
  Responsive collapse: panels stack on tablet, tabs on mobile
  Panel maximize button: top-right of each panel
```

***

## 10. ReviewEntitiesView.vue — Révision des entités

**Audience :** Tier 2 Analyst  
**Funnel :** Activation  
**Objectif cognitif :** Contrôle + précision → *"Je valide avant de lancer — rien ne m'échappe"*

```
Design the Bassira entity review view — where the analyst reviews, 
edits, and validates the knowledge graph entities before simulation launch.

CONTEXT:
After graph build, the system extracted entities (people, organizations,
concepts) from the seed documents. The analyst must validate them.
Wrong entities = poor simulation. This step is critical quality control.

AUDIENCE:
Detail-oriented analyst who will be held accountable for simulation quality.
Pain: "The AI extracted the wrong people. I need to be able to fix it quickly."

COGNITIVE OBJECTIVE:
"I'm in control. Nothing is automatic without my approval."
Speed + precision: edit fast, validate fast.

PALETTE CAUSSE:
  Valid entity chip: #006D44 mint bg, cream text — confirmed, trustworthy
  Flagged entity chip: #FF8551 orange bg — needs attention
  Removed entity: strikethrough, #8A7269 muted — clearly removed
  Edit mode active: orange input border + label
  Confirm button: mint-green — constructive, positive action
  Warning (duplicate entity): #FF8551 pill, not blocking
  Empty state (no entities): terracotta icon + action CTA

LAYOUT:
  Two-column: entity list left (70%) + entity detail panel right (30%)
  List: filterable by type (Person / Organization / Concept / Location)
  Entity card: type badge + name + source excerpt + confidence score
  Batch actions toolbar: appears on multi-select
  "Launch simulation" CTA: mint-green, bottom of page, disabled until 
    minimum 3 valid entities confirmed
```

***

## 11. ComparisonView.vue — Comparaison deux simulations

**Audience :** Tier 2 Analyst → Tier 1 CEO (décision finale)  
**Funnel :** Decision  
**Objectif cognitif :** Delta immédiat → *"Je vois la différence en 5 secondes"*

```
Design the Bassira comparison view — side-by-side comparison of two 
simulation runs with the same base scenario but different parameters.

CONTEXT:
Used to compare "what if X vs what if Y" — e.g., acquisition vs 
organic growth. The output is a delta view that directly informs 
a strategic decision.

AUDIENCE:
Strategy Director preparing a board recommendation.
Pain: "I have two scenarios but no way to present the delta cleanly."

COGNITIVE OBJECTIVE:
Make the difference undeniable. The winning scenario must be visually 
obvious without interpretation. Delta = decision.

PALETTE CAUSSE:
  Simulation A: #FF8551 orange — the "current path" or hypothesis A
  Simulation B: #006D44 mint-green — the "alternative path" or hypothesis B
  Delta positive: mint-green arrow + number — better outcome
  Delta negative: terracotta arrow + number — worse outcome
  Neutral delta: charcoal — no significant difference
  Divider between simulations: #FAF7F2 cream line — clean separation

LAYOUT:
  Header: "Simulation A vs Simulation B" with metadata
  Metric comparison table: side-by-side rows, delta column highlighted
  Chart overlay: both simulations on same axes, A=orange, B=mint
  Key finding callout: "Simulation B produced 40% less belief polarization"
    — centered, large, with delta chip
  Export: "Export comparison PDF" — #241915 button
```

***

## 12. EmbedView.vue — Widget embarqué iframe

**Audience :** Public / Partenaire (média, think tank)  
**Funnel :** Awareness → Social proof  
**Objectif cognitif :** Confiance + partage → *"Ce widget est propre, je peux l'intégrer dans mon article"*

```
Design the Bassira embed widget — a compact iframe-friendly view 
of a single simulation result, designed to be embedded in news articles,
research papers, or partner websites.

CONTEXT:
Must work at 400px width minimum. Must be self-explanatory with 
zero context from the host page. Bassira branding must be visible 
but not dominant.

AUDIENCE:
Journalist, researcher, or think tank analyst embedding in their content.
Their readers: educated public, executives, policymakers.

COGNITIVE OBJECTIVE:
Instant credibility for the host content. 
"This forecast is backed by a serious simulation platform."

PALETTE CAUSSE:
  Background: white #FFFFFF — maximum compatibility with host pages
  Header band: #FAF7F2 cream + BASSIRA wordmark (Outfit 600, 12px, charcoal)
  Key finding: #241915 bold, centered
  Simulation metadata: JetBrains Mono, muted
  Category badge: colored by type (crisis/market/policy)
  "View full simulation →": #A13F0F terracotta ghost link
  Border: 1px #DEC0B6 (warm outline-variant) — warm, not cold grey

LAYOUT:
  Max-width 600px, responsive down to 360px
  Header: logo + simulation title + date
  Key metric: large number + label (Outfit 700, 48px)
  Mini chart: sparkline, 80px height
  3 key findings: Manrope 400, 14px, bulleted
  Attribution footer: "Powered by Bassira · بصيرة" — cream, subtle
```

***

## 13. InteractionView.vue — Interactions agents temps réel

**Audience :** Tier 3 Skeptic (CTO, Risk Officer)  
**Funnel :** Trust → Decision  
**Objectif cognitif :** Transparence + rigueur → *"Je vois comment les agents raisonnent. Ce n'est pas une boîte noire."*

```
Design the Bassira interaction view — a deep dive into individual 
agent reasoning and interaction logs. This is the "open the hood" view
for technical skeptics who need to understand the methodology.

AUDIENCE:
CTO or Risk Officer who approved the trial but needs to validate 
the methodology before signing off. Pain: "I don't trust AI systems 
I can't audit."

COGNITIVE OBJECTIVE:
"This is more rigorous than I expected." Transparency as a feature.
Every agent action must be traceable to an explicit reason.

PALETTE CAUSSE:
  Background: #FAF7F2 — academic paper aesthetic, not dashboard
  Agent interaction graph: network viz, orange/mint/terracotta nodes
  Reasoning log: JetBrains Mono, grouped by agent, timestamped
  Belief state indicator: small colored pill — visual continuity
  Methodology link: #006D44 underline — trust, academic reference
  Audit export button: #241915 — serious, archival action

LAYOUT:
  Left: InteractionNetwork graph (D3 force, 60%)
  Right: Agent log panel (40%) — filterable by agent, by round
  Log entry: agent avatar + stance chip + message + timestamp + 
    reasoning excerpt (expandable)
  "Methodology explainer" sticky card: bottom of right panel
```

***

## 14. ReplayView.vue — Lecture enregistrement simulation

**Audience :** Tier 2 Analyst → Tier 1 CEO  
**Funnel :** Retention → Expansion  
**Objectif cognitif :** Narration + insight → *"Je comprends ce qui s'est passé et pourquoi"*

```
Design the Bassira replay view — a timeline scrubber to replay 
a completed simulation round by round, like a video player for strategy.

CONTEXT:
The user can scrub through time, pause at key moments, and see 
the exact state of the simulation at each round. Useful for debriefs 
and presentations.

AUDIENCE:
Analyst preparing a debrief for their CEO, or a CEO reviewing 
a simulation they commissioned.

COGNITIVE OBJECTIVE:
Narrative flow — the user must feel like they're watching a story unfold,
not browsing data. Each round is a chapter.

PALETTE CAUSSE:
  Timeline scrubber: orange fill on cream track — warm, cinematic
  Round marker: orange dot (key events), mint dot (calm rounds)
  "Inflection point" marker: terracotta diamond — notable shift
  Current round card: elevated, orange left border
  Historical round card: cream, muted — past but accessible
  Play/Pause: #A13F0F terracotta fill — deliberate media control
  Speed control: Outfit 500, 13px, cream on charcoal pills

LAYOUT:
  Top: timeline scrubber full width + round counter + play controls
  Center: main event card (current round) — large, readable
  Below: belief drift chart with current position marker
  Side panel: agent state at current round (mini avatars + stances)
  Keyboard navigation: ← → arrows, Space to pause
```

***

# FEATURES HORIZON 1–2–3

***

## 15. Onboarding solo — Guided tour (Horizon 2)

**Audience :** Tier 2 Analyst (premier usage autonome)  
**Funnel :** Activation  
**Objectif cognitif :** Confiance + progression → *"Je sais exactement quoi faire ensuite"*

```
Design the Bassira onboarding flow — a first-time user experience 
guiding a new analyst through their first simulation without assistance.

CONTEXT:
Currently, a new user landing on Home.vue sees a blank form with no guidance.
Churn point: 80% of SaaS trials fail because the user never completes 
their first meaningful action. The onboarding must lead them to 
"first simulation launched" in under 10 minutes.

AUDIENCE:
Strategy Analyst, age 30–45, technically competent but new to 
agent-based simulation. Pain: "I signed up but I don't know where to start."

COGNITIVE OBJECTIVE:
Progressive confidence. Each step should make the user feel 
slightly more capable than the last.

PALETTE CAUSSE:
  Progress bar: orange fill — forward motion, energy
  Step tooltip: white card, 24px radius, orange left border
  Completed step: mint-green checkmark — reinforcement
  Spotlight overlay: #0f1117 at 70% opacity — focused attention
  Skip button: ghost, muted charcoal — always available, never prominent
  "You're ready" celebration: mint-green + orange confetti (warm tones only)

COMPONENTS:
  Step 1 tooltip: "Déposez un article ou un rapport — c'est votre graine"
    → highlight the file upload zone with orange spotlight
  Step 2 tooltip: "Décrivez votre question en une phrase"
    → highlight the simulation requirement input
  Step 3 tooltip: "Choisissez un scénario suggéré ou écrivez le vôtre"
    → highlight ScenarioSuggestions
  Step 4 tooltip: "Lancez — votre première simulation démarre"
    → highlight primary CTA

  Beacon dot: pulsing orange dot on each step's target element
  Tooltip anatomy: step counter (1/4) + title + body + Next/Skip
  
  Pre-loaded demo template: "Lancer avec un exemple →" 
    → loads budget_loi_finances template automatically
    → user sees a real simulation immediately, builds confidence
```

***

## 16. Landing page SEO (Horizon 2)

**Audience :** Prospect froid (LinkedIn, Google, presse)  
**Funnel :** Awareness → Discovery  
**Objectif cognitif :** Arrêter le scroll → *"C'est exactement ce problème que j'ai"*

```
Design a full marketing landing page for Bassira — separate from the app,
optimized for SEO and cold traffic conversion. 
URL: bassira.ai or ai-mpower.com/bassira

CONTEXT:
The current Home.vue is an app, not a landing page. A cold prospect 
from a LinkedIn post or Google search needs a different experience:
value proposition first, product second.

AUDIENCE:
Cold prospect: C-Level or Strategy Director who saw a LinkedIn post 
about AI forecasting. 8-second attention span. 
Pain: "I don't have time to figure out what this does."

COGNITIVE OBJECTIVE:
"This solves a problem I have RIGHT NOW. I need to see a demo."

SECTIONS:

HERO (above fold, 100vh):
  Palette: #FAF7F2 bg, large H1 in #241915, terracotta CTA
  H1 formula: [outcome] + [timeframe] + [without painful thing]
    Ex: "Stress-testez votre stratégie en 48h — sans consultants."
  Social proof strip: logos of client industries/types (not names if NDA)
  Two CTAs: "Demander une démo" (terracotta) + "Voir un exemple" (ghost)

PAIN SECTION (scroll 1):
  Palette: white cards on cream bg
  3 pain cards — each with a real quote format:
    Icon + pain statement + "Avec Bassira :" + solution statement
  Orange quote marks, terracotta pain label, mint solution label

PRODUCT SECTION (scroll 2):
  Split layout: text left, animated simulation screenshot right
  Key capabilities: 3 bullet points, mint checkmarks
  Palette: cream bg, Outfit headlines, Manrope body

PROOF SECTION (scroll 3):
  Calibration teaser: Brier score 0.18, link to /calibration
  Palette: dark (#0f1117) — contrast break, cinematic quality
  Orange Brier number, cream text, mint checkmarks

PRICING TEASER (scroll 4):
  3 tier cards, no prices — "À partir de 8,000 MAD / $800 USD"
  CTA: "Voir toutes les formules →" → /offres

FINAL CTA (scroll 5):
  Full-width terracotta band
  H2: "Votre prochain comité stratégique mérite mieux qu'un PowerPoint"
  CTA: "Lancer ma première simulation →"
  
SEO META:
  Title: "Bassira · Simulation Stratégique par IA | Forecasting MENA"
  Description: 155 chars, includes "simulation", "stratégie", "MENA", "IA"
```

***

## 17. Analytics dashboard interne (Horizon 2)

**Audience :** Admin Bassira (Amine + équipe)  
**Funnel :** Opérationnel  
**Objectif cognitif :** Visibilité totale → *"Je sais en 30 secondes comment se porte la plateforme"*

```
Design the Bassira internal analytics dashboard — a private admin view
showing platform health, user engagement, and commercial pipeline signals.
Stack: Plausible (self-hosted) or Posthog embedded in a custom view.

AUDIENCE:
Founders/operators. Pain: "I don't know if users are converting 
or where they drop off."

KEY METRICS TO DISPLAY:
  Acquisition: visits /offres, visits /calibration, quote form starts
  Activation: simulations created, first simulation completed
  Retention: simulations per user per month
  Revenue signals: quotes submitted, packages selected

PALETTE CAUSSE:
  Dashboard bg: #0f1117 — ops environment, dark default
  Metric cards: #1a1d27 surface, orange number, mint trend arrows
  Positive trend: #7FD8A6 mint (up is good)
  Negative trend: #A13F0F terracotta (down needs attention, not alarm)
  Neutral: #8A7269 muted — baseline
  Chart lines: orange (primary metric) + mint (comparison/target)

LAYOUT:
  Row 1: 4 KPI cards (visits, activations, completions, quote rate)
  Row 2: Funnel chart (acquisition → activation → completion)
  Row 3: Time series (30d / 90d toggle) + geographic breakdown (MENA/EU)
  Row 4: Recent quote requests table (anonymized for privacy)
```

***

## 18. Séquences Apollo CRM outreach (Horizon 3)

**Audience :** Prospects froids MENA Strategy Directors  
**Funnel :** Awareness → Meeting  
**Objectif cognitif :** Curiosité calibrée → *"Ce message parle de mon problème exact"*

```
Design the visual and copy template system for Bassira Apollo outreach 
sequences. 3 sequences targeting 3 different buying contexts.

CONTEXT:
Apollo.io MCP is available. Need email templates + LinkedIn DM templates
that match Bassira brand DNA. Cold outreach targeting Strategy Directors 
in Morocco, GCC, France.

SEQUENCE 1 — "Pre-decision anxiety" (Decision context):
  Trigger: prospect has an announced M&A, election, product launch coming
  Tone: urgent but consultative, not salesy
  Hook formula: "[Event] → [Risk] → [Bassira solves this in X hours]"
  
SEQUENCE 2 — "Blindspot" (Post-crisis):
  Trigger: prospect's industry just had a surprise event
  Tone: empathetic, analytical
  Hook: "When [industry event] happened, how many scenarios had you modeled?"

SEQUENCE 3 — "Calibration proof" (Trust-building):
  Trigger: cold contact who needs methodology proof first
  Tone: academic, data-first
  Hook: "Our Brier score is 0.18. Here's what that means for your decisions."

EMAIL TEMPLATE STRUCTURE:
  Subject line: [Pain trigger] — 6–9 words, no emoji for MENA executives
  Body: 3 sentences max (busy C-Levels) + 1 link to relevant simulation
  Sign-off: "— [Name], Bassira" — no title inflation
  
COLOR/FONT GUIDANCE FOR HTML EMAILS:
  Background: #FAF7F2 — premium, not generic white
  CTA button: #A13F0F terracotta — works across email clients
  Footer: Outfit 500, 12px, #8A7269 muted
  Arabic version: RTL table layout, Tajawal font stack
```

***

## 19. Contenu LinkedIn — Piliers éditoriaux (Horizon 3)

**Audience :** Strategy Director / C-Level MENA + Europe  
**Funnel :** Awareness → Trust  
**Objectif cognitif :** Thought leadership → *"Ces gens pensent différemment des autres fournisseurs"*

```
Design the LinkedIn content visual system for Bassira — 
post templates, carousel designs, and data visualization posts.

AUDIENCE:
Followers: Strategy Directors, CFOs, Policy Advisors, Think Tank leads.
Pain: "Too many AI vendors, not enough substance."

PILLAR 1 — "The Blindspot" (Humility + Insight)
  Visual: split — "What decision-makers assumed" vs "What the simulation showed"
  Palette: left panel cream, right panel dark (#0f1117) — before/after
  Hook: "Everyone said X was obvious in hindsight. Our simulation called it 
         3 weeks before it happened. Here's the thread."

PILLAR 2 — "Calibration Log" (Methodological credibility)
  Visual: data post — prediction made + outcome + Brier delta
  Palette: white bg, mint-green correct/orange close/terracotta miss
  Hook: "We were [right/close/wrong] about [topic]. Here's why."

PILLAR 3 — "Simulation Debrief" (Case study format)
  Visual: 5-slide carousel — scenario + agents + key finding + 
          implication + call to simulate
  Palette: cream bg, orange section markers, dark text
  Hook: "[Company/Country] faced [decision]. We ran 1,000 scenarios. 
         Here's what the agents revealed."

PILLAR 4 — "Decision Science" (Education + positioning)
  Visual: illustrated concept post — mental model, framework, 
          or cognitive bias relevant to strategic decision-making
  Palette: cream + single accent color (varies by concept)
  Hook: "The [cognitive bias] that cost [famous decision-maker] everything.
         And how to simulate past it."

POST TEMPLATE SPECS:
  Carousel: 1080×1080px, Outfit headlines, Manrope body
  Cover slide: BASSIRA watermark bottom-right, cream bg, large headline
  Data slide: white card on cream, brand chart colors
  CTA slide: terracotta bg, cream text, "Simulate this →"
  Ratio: 1:1 for feed, 4:5 for recommended LinkedIn
```

***

## 20. Pages partenariat — Think tanks & Cabinets conseil (Horizon 3)

**Audience :** Head of Research (think tank) / Partner (cabinet conseil)  
**Funnel :** Partnership → Distribution  
**Objectif cognitif :** Alignement méthodologique → *"Cette plateforme renforce notre crédibilité, pas la concurrence"*

```
Design the Bassira partnership pages — targeted at think tanks, 
policy research institutes, and strategic consulting firms 
who would recommend or co-brand Bassira to their clients.

CONTEXT:
Partner value prop: "Bassira gives your research output a computational 
backbone. Your scenarios, your conclusions — stress-tested by 1,000 agents."
Not: "Use Bassira instead of consultants." That would kill the deal.

AUDIENCE:
Head of Research at OCP Policy Center, Carnegie Middle East, OCDE, 
or Partner at McKinsey/Roland Berger Africa.
Pain: "Our clients want quantitative rigor. Our scenarios are still qualitative."

COGNITIVE OBJECTIVE:
"Bassira complements our work and elevates our product."
Position as enhancement, not replacement.

PALETTE CAUSSE:
  Page bg: #FAF7F2 — institutional quality, not startup
  Partner logos section: greyscale logos on cream — respectful, equal billing
  Co-brand examples: split BASSIRA / Partner logo — equal size, 
    separated by a thin terracotta line
  Methodology diagram: cream cards + mint arrows + orange nodes
  Partnership tiers: 3 cards — Research Partner / Integration Partner / 
    White-label — orange featured center
  Contact CTA: #241915 bg + cream text — institutional gravity

LAYOUT:
  Hero: "Renforcez vos scénarios avec la simulation computationnelle"
    No startup language, no "AI-powered" — academic/institutional register
  Partner logos: horizontal scroll of partner categories
  How it works for partners: 3-step visual (your scenario → Bassira agents 
    → your branded report)
  Pricing: confidential, "Contact us" only — no public partner pricing
  Testimonial format: full name + title + institution + 2-sentence quote
    (never anonymous for institutional partners — credibility requires names)
```

***

*Généré le 2026-05-02 — Bassira Brand System v1.0*  
*Palette Causse calibrée MENA (Maroc, GCC) + Europe (France, UK)*  
*20 prompts couvrant 14 vues existantes + 6 features horizon 1–3*
